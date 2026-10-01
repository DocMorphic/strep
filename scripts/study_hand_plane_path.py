"""Diagnose a supported-hand approach path before fitting native animation keys."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now


def run(source, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from paired_approach_basis import BoundSkin
    from hand_plane_retraction import retract
    from elbow_swivel import local_transforms
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh approach-path study required')
    sr, sq = read(source/'result.json'), read(source/'request.json')
    if not (sr['status'] == 'complete' and sr['contact_target_pass'] and sr['contact_mesh_screen_pass']):
        raise ValueError('Clean decoded contact instant required')
    files = dict(sq['inputs']); files[str(source/'result.json')] = sha256(source/'result.json')
    for name, digest in sr['outputs'].items():
        path = (source/name).resolve()
        if path.parent != source: raise ValueError('Escaping source output')
        files[str(path)] = digest
    for name, digest in sq['implementation'].items():
        path = (source/'implementation'/name).resolve()
        if path.parent != source/'implementation': raise ValueError('Escaping method archive')
        files[str(path)] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed bound evidence')
    def bound(path):
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence: '+str(path))
        return read(path)
    pose = bound(Path(sq['source'])/'request.json'); region = bound(Path(pose['source'])/'request.json')
    donor = bound(Path(region['source'])/'request.json'); ball = bound(Path(donor['source'])/'request.json')
    shared = bound(Path(ball['source'])/'request.json'); protected = shared['remaining_protected_spans']
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    prepared, actors = load_actors(region['prepared']); event = sq['event_time_s']; window = sq['window_s']
    uniform = np.asarray(sq['uniform_times_s']); guard = np.asarray(sq['guard_times_s']); target = sq['target']
    midpoint = np.asarray(target['midpoint_m']); clearance = target['separation_m']/2
    rigs = []; refs = []; readers = []; ref_readers = []; clocks = []
    for i, entry in enumerate(trial['actors']):
        path = source/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Bound rig source and reference required')
        rigs.append(RigAsset.load(path)); refs.append(RigAsset.load(reference))
        readers.append(AnimationSampler(rigs[-1].document, rigs[-1].binary, 0)); ref_readers.append(AnimationSampler(refs[-1].document, refs[-1].binary, 0))
        chain = donor['actors'][i]['nodes'][:3]
        clocks.extend(c[2] for c in readers[-1].channels if c[0] in chain and c[1] == 'rotation')
    all_times = np.unique(np.concatenate([uniform, guard, np.asarray(window), np.array([event]), *clocks]))
    times = all_times[(all_times >= window[0]) & (all_times <= window[1])]
    # Include the uniform halo needed for the unchanged sampled motion caps.
    times = np.unique(np.r_[times, uniform, guard])
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'hand_plane_retraction.py', 'study_hand_plane_path.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        times_s=times.tolist(), guard_times_s=guard.tolist(), uniform_times_s=uniform.tolist(), original_bins_s=sq['original_bins_s'],
        event_time_s=event, window_s=window, protected_spans=protected, target=target, contact_regions=sq['contact_regions'],
        policy='At each declared time, retract the wrist along its fixed rig-space contact normal only when selected hand vertices cross their contact half-space. Keep wrist orientation and other local channels; at most four refreshed skin/reach steps, 0.1 mm reserve. Freeze the exact contact instant, outside-window and protected poses. Check original-reference pose limits and all original sampled rate caps. This is a pose-path proposal, not a native animation or continuous clearance proof.',
        reserve_m=.0001, maximum_steps=4, native_animation_exported=False, quality_approved=False))
    worlds = []; rows = []; original_worlds = []
    for i, (rig, ref, reader, reference, actor) in enumerate(zip(rigs, refs, readers, ref_readers, actors)):
        skin = BoundSkin(rig); ids = np.asarray(region['region_vertices'][i]); chain = donor['actors'][i]['nodes'][:3]
        layout = donor['actors'][i]; outward = np.asarray(target['normals'][i]); rig_outward = actor['rotation'].T@outward
        def surface(w): return skin.evaluate(w[None], np.zeros(len(ids), int), ids)@actor['rotation'].T+actor['translation']
        current_worlds = []; before_worlds = []; actor_rows = []
        for time in times:
            original = reader.sample(time); before_worlds.append(original)
            frozen = bool(time <= window[0] or time >= window[1] or time == event or any(a <= time <= b for a, b in protected))
            if frozen:
                current = original.copy(); excess = float(((surface(current)-midpoint)@outward).max()+clearance)
                report = dict(initial_excess_m=excess, final_excess_m=excess, total_retraction_m=0., selected_hand_plane_pass=excess <= 1e-8, frozen=True)
            else:
                current, report = retract(original, rig.parents, chain, surface, midpoint, outward, rig_outward, clearance_m=clearance)
                report['frozen'] = False
            local = local_transforms(current, rig.parents); original_local = local_transforms(original, rig.parents)
            ref_local = local_transforms(reference.sample(time), ref.parents); nodes = layout['nodes']
            angles = np.rad2deg(Rotation.from_matrix(ref_local[nodes, :3, :3].transpose(0, 2, 1)@local[nodes, :3, :3]).magnitude())
            limits_pass = bool(np.all(angles <= np.asarray(layout['original_budgets_degrees'])+1e-4))
            unchanged = [n for n in range(len(current)) if n not in chain]
            np.testing.assert_allclose(local[unchanged], original_local[unchanged], rtol=0, atol=1e-9)
            np.testing.assert_allclose(local[:, :3, 3], original_local[:, :3, 3], rtol=0, atol=1e-9)
            if frozen: np.testing.assert_array_equal(current, original)
            actor_rows.append(dict(time_s=float(time), original_pose_limits_pass=limits_pass, original_pose_angles_degrees=angles.tolist(), **report)); current_worlds.append(current)
        rows.append(actor_rows); worlds.append(np.array(current_worlds)); original_worlds.append(np.array(before_worlds))
        save(output/f'actor-{i}-path.json', actor_rows)
        print(dict(phase='hand_plane_path', actor=i, poses=len(times), retracted=sum(r['total_retraction_m'] > 0 for r in actor_rows),
            failed_pose_limits=sum(not r['original_pose_limits_pass'] for r in actor_rows), failed_plane=sum(not r['selected_hand_plane_pass'] for r in actor_rows)), flush=True)
    np.savez_compressed(output/'planned-worlds.npz', times=times, actor0=worlds[0], actor1=worlds[1])
    def payload(values):
        parts = [features(w, r.joints) for w, r in zip(values, refs)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ('positions', 'rotations')}
    raw = [np.array([reader.sample(t) for t in uniform]) for reader in ref_readers]
    caps = SampledMotionCaps(payload(raw), uniform, sq['original_bins_s']); actual = payload([w[np.searchsorted(times, uniform)] for w in worlds]); rates = []
    for kind, values, ceiling in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), measures(actual, caps.dt), caps.caps):
        excess = values-ceiling-caps.tolerance; rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    save(output/'rates.json', rates); observations = []
    for index, time in enumerate(guard):
        frame = int(np.searchsorted(times, time)); points = [r.vertices(w[frame])@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, worlds, actors)]
        surface_report = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces'])
        depths = [penetration(points[a], points[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in ((0, 1), (1, 0))]
        passed = not any(v for k, v in surface_report['counts'].items() if k != 'disjoint') and not any(surface_report['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8
        row = dict(time_s=float(time), surface=surface_report, depths=depths, inter_actor_pose_screen_pass=bool(passed)); observations.append(row)
        save(output/f'geometry-{index:02d}.json', row)
        print(dict(phase='path_geometry', completed=index+1, total=len(guard), passed=bool(passed)), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Changed method during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        poses_per_actor=len(times), original_pose_limits_pass=all(r['original_pose_limits_pass'] for actor in rows for r in actor),
        selected_hand_planes_pass=all(r['selected_hand_plane_pass'] for actor in rows for r in actor),
        original_motion_caps_pass=all(r['failed_rows'] == 0 for r in rates), failed_geometry_samples=sum(not o['inter_actor_pose_screen_pass'] for o in observations),
        maximum_vertex_depth_m=max(d['max_depth_m'] for o in observations for d in o['depths']),
        contact_pose_preserved_exact=True, native_animation_exported=False, continuous_collision_certified=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
