"""Whole-file geometry and dynamics verification for coupled support edits."""
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from strep import read, sha256
from verify_breadth_contact import verify as original_bounds


def measure(path, spec):
    rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
    frames = spec['frames']
    world = np.array([sampler.sample(float(np.float32(f/30))) for f in range(frames)])
    vertices = np.array([rig.vertices(w) for w in world])
    half = np.array([rig.vertices(sampler.sample((f+.5)/30)) for f in range(frames-1)])
    centers = np.array([[v[p['vertices']].mean(axis=0) for p in spec['patches'].values()] for v in vertices])
    local = localize(world, rig.parents); nodes = [j['node'] for j in spec['edit_joints'].values()]
    q = local[:, nodes, :3, :3]
    angles = Rotation.from_matrix((q[:-1].swapaxes(-1, -2)@q[1:]).reshape(-1, 3, 3)).magnitude().reshape(frames-1, len(nodes))
    return dict(world=world, vertices=vertices, half=half, centers=centers, local=local,
        angles=angles, speed=np.linalg.norm(np.diff(centers[:, :, [0, 2]], axis=0), axis=2)*30,
        root_acc=np.linalg.norm(np.diff(world[:, spec['root_node'], :3, 3], n=2, axis=0), axis=1)*900,
        foot_acc=np.linalg.norm(np.diff(centers, n=2, axis=0), axis=2)*900)


def inspect(take, source, edited_frames):
    # Original decoded root/joint limits and untouched transform checks are
    # independent of the incremental solver and its parameterization.
    original = original_bounds(take)
    spec, request = read(take/'spec.json'), read(take/'request.json')
    annotations = read(take/'input/contacts.json')['intervals']; frames = spec['frames']
    before, after = [measure(path, spec) for path in (source, take/'candidate/character.glb')]
    checks = dict(original_bounds=original['bounds_and_preservation_passed'])
    root_excess = float((after['root_acc']-before['root_acc']).max())
    foot_excess = float((after['foot_acc']-before['foot_acc']).max())
    floor_excess = max(float((np.maximum(-after[k][:, :, 1], 0)-np.maximum(-before[k][:, :, 1], 0)).max())
                       for k in ('vertices', 'half'))
    angle_excess = float((after['angles']-before['angles']).max())
    checks.update(root_acceleration=root_excess <= .0036, foot_acceleration=foot_excess <= .0036,
                  floor=floor_excess <= 1e-6, joint_rotation_steps=angle_excess <= np.radians(1e-4))
    fixed = np.ones(frames, bool); fixed[edited_frames] = False
    untouched_error = float(np.abs(after['local'][fixed]-before['local'][fixed]).max())
    checks['outside_blocks'] = untouched_error <= 1e-6
    trace = read(take/'raw-traces.json')
    raw = next(v for v in trace['variants'] if v['variant'] == 'input')
    rows, energies = [], [0., 0.]
    for side_index, (side, patch) in enumerate(spec['patches'].items()):
        active = np.array([any(c['joint'] in (side+'Foot', side+'ToeBase') and c['start_frame'] <= f < c['end_frame_exclusive']
                              for c in annotations) for f in range(frames)])
        changes = [end for end in range(1, frames) if active[end-1] != active[end]]
        guarded = np.array([active[end-1] or active[end] or any(abs(end-boundary) <= 1 for boundary in changes)
                            for end in range(1, frames)])
        support = active[:-1]&active[1:]
        guide = request['support']['guides'][side]; used = np.asarray(guide['weights']) > 0
        speeds = [m['speed'][:, side_index] for m in (before, after)]
        errors = [np.linalg.norm(m['centers'][:, side_index, [0, 2]]-guide['anchors_xz_m'], axis=1) for m in (before, after)]
        heights = [m['vertices'][:, patch['vertices'], 1].min(axis=1) for m in (before, after)]
        peak = raw['feet'][side]['predicted_support_max_m_s']
        if peak is not None:
            for i, speed in enumerate(speeds): energies[i] += float(np.square(np.maximum(speed[support]-peak, 0.)).sum())
        rows.append(dict(side=side,
            speed_excess_m_s=float((speeds[1]-speeds[0])[guarded].max()) if guarded.any() else None,
            anchor_excess_m=float((errors[1]-errors[0])[used].max()) if used.any() else None,
            hover_excess_m=float((heights[1]-heights[0])[active].max()) if active.any() else None,
            support_peak_before_m_s=float(speeds[0][support].max()) if support.any() else None,
            support_peak_after_m_s=float(speeds[1][support].max()) if support.any() else None,
            raw_peak_target_m_s=peak))
    checks.update(support_boundary_speed=all(r['speed_excess_m_s'] is None or r['speed_excess_m_s'] <= .00006 for r in rows),
        anchors=all(r['anchor_excess_m'] is None or r['anchor_excess_m'] <= 1e-6 for r in rows),
        supported_height=all(r['hover_excess_m'] is None or r['hover_excess_m'] <= 1e-6 for r in rows),
        objective=energies[1] < energies[0]-max(1e-9, .001*energies[0]))
    checks = {key: bool(value) for key, value in checks.items()}
    return dict(checks=checks, passed=all(checks.values()), source_sha256=sha256(source),
        candidate_sha256=sha256(take/'candidate/character.glb'), original_verification=original,
        foot_speed_excess_energy_before=energies[0], foot_speed_excess_energy_after=energies[1],
        root_acceleration_excess_m_s2=root_excess, foot_acceleration_excess_m_s2=foot_excess,
        floor_depth_excess_m=floor_excess, rotation_step_excess_degrees=float(np.degrees(angle_excess)),
        untouched_local_error=untouched_error, feet=rows, quality_approved=False)
