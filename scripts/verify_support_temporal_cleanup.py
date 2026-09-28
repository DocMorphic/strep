"""Decoded audit independent of support cleanup proposal matrices."""
import numpy as np
from strep import read
from verify_authored_root_correction import inspect as inspect_root, samples


def inspect(folder, candidate, policy):
    spec = read(folder/'contact-spec.json')
    frames = spec['frames']
    base = inspect_root(folder/'candidate/character.glb', candidate,
        folder/'input/character.glb', folder/'contact-spec.json', frames, policy)
    rig0, world0 = samples(folder/'candidate/character.glb', frames)
    rig1, world1 = samples(candidate, frames)
    points = [np.array([rig.vertices(w) for w in world[::2]])
              for rig, world in ((rig0, world0), (rig1, world1))]
    annotations = read(folder/'input/contacts.json')['intervals']
    guides = read(folder/'support-request.json')['support']['guides']
    rows = []
    for side, patch in spec['patches'].items():
        active = [any(c['joint'] in (side+'Foot', side+'ToeBase') and
                     c['start_frame'] <= f < c['end_frame_exclusive'] for c in annotations)
                  for f in range(frames)]
        # Explicit edge enumeration, independent of the proposal mask helper.
        changes = [end for end in range(1, frames) if active[end-1] != active[end]]
        ends = [end for end in range(1, frames) if active[end-1] or active[end]
                or any(abs(end-boundary) <= 1 for boundary in changes)]
        ids = patch['vertices']
        tracks = [p[:, ids].mean(axis=1)[:, [0, 2]] for p in points]
        speeds = [np.linalg.norm(t[1:]-t[:-1], axis=1)*30 for t in tracks]
        used = np.asarray(guides[side]['weights']) > 0
        errors = [np.linalg.norm(t-guides[side]['anchors_xz_m'], axis=1) for t in tracks]
        heights = [p[:, ids, 1].min(axis=1) for p in points]
        steps = np.asarray([active[f-1] and active[f] for f in range(1, frames)])
        indices = np.asarray(ends, int)-1
        rows.append(dict(side=side, guarded_step_end_frames=ends,
            guarded_speed_excess_m_s=float((speeds[1]-speeds[0])[indices].max()) if ends else None,
            drafted_anchor_excess_m=float((errors[1]-errors[0])[used].max()) if used.any() else None,
            support_height_excess_m=float((heights[1]-heights[0])[active].max()) if any(active) else None,
            support_peak_before_m_s=float(speeds[0][steps].max()) if steps.any() else None,
            support_peak_after_m_s=float(speeds[1][steps].max()) if steps.any() else None))
    checks = dict(base=base['all_checks_passed'],
        support_and_boundary_speed=all(r['guarded_speed_excess_m_s'] is None or
            r['guarded_speed_excess_m_s'] <= policy['support_speed_tolerance_m_s'] for r in rows),
        drafted_anchors=all(r['drafted_anchor_excess_m'] is None or
            r['drafted_anchor_excess_m'] <= policy['position_tolerance_m'] for r in rows),
        support_height=all(r['support_height_excess_m'] is None or
            r['support_height_excess_m'] <= policy['position_tolerance_m'] for r in rows),
        # The original whole-support verifier uses one micrometre here, while
        # the reused generic root verifier permits two. Preserve the stricter bound.
        original_root_step=True)
    _, raw = samples(folder/'input/character.glb', frames)
    edit = world1[::2, spec['root_node'], :3, 3]-raw[::2, spec['root_node'], :3, 3]
    checks['original_root_step'] = bool(np.linalg.norm(np.diff(edit, axis=0), axis=1).max()
        <= spec['limits']['root_step_m']+policy['position_tolerance_m'])
    return dict(checks=checks, all_checks_passed=all(checks.values()), root=base,
                feet=rows, quality_approved=False)
