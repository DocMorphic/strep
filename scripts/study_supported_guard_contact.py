"""Dual-peak guarded fit reserving headroom only on structurally mutable rate samples."""
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
    from contact_rate_path import ContactRatePath, ProjectedSkin
    from rotation_rate_support import SupportedDualRatePeakGuard, rate_support
    from elbow_swivel import descendants
    from scipy.optimize import minimize
    from functools import lru_cache
    from paired_approach_basis import BoundSkin
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    from palm_contact_region import rebind_surface_point
    from paired_temporal_neighbor import rotation_channels
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native path export required')
    sr, sq = read(source/'result.json'), read(source/'request.json')
    if not (sr['status'] == 'complete' and sr['contact_target_pass'] and sr['contact_mesh_screen_pass'] and sr['failed_geometry_samples'] == 0):
        raise ValueError('Clean source contact required; trajectory failures remain separate')
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
        if sha256(path) != digest: raise ValueError('Changed input')
    def bound(path):
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound evidence: '+str(path))
        return read(path)
    pose = sq; seen = set()
    while 'baseline' not in pose:
        path = Path(pose['source'])/'request.json'
        if path in seen or len(seen) >= 32: raise ValueError('Invalid provenance chain')
        seen.add(path); pose = bound(path)
    region = bound(Path(pose['source'])/'request.json'); donor = bound(Path(region['source'])/'request.json')
    baseline = Path(pose['baseline']); br = bound(baseline/'result.json')
    trial = next(t for t in bound(baseline/'trials.json') if t['folder'] == br['selected'])
    prepared, actors = load_actors(region['prepared']); target = sq['target']; contact = sq['selected_contact']
    for key in ('effector', 'target'): contact[key] = rebind_surface_point(contact[key], contact[key]['surface_vertex'])
    contact['tolerance_m'] = target['maximum_gap_m']
    event = sq['event_time_s']; window = sq['window_s']; protected = sq['protected_spans']
    guard, uniform = np.asarray(sq['guard_times_s']), np.asarray(sq['uniform_times_s'])
    rigs = []; refs = []; readers = []; ref_readers = []
    for i, entry in enumerate(trial['actors']):
        path = source/f'candidate-{i}.glb'; reference = baseline/br['selected']/entry['path']
        for p in (path, reference):
            if files.get(str(p)) != sha256(p): raise ValueError('Unbound rig or original reference')
        rigs.append(RigAsset.load(path)); refs.append(RigAsset.load(reference))
        readers.append(AnimationSampler(rigs[-1].document, rigs[-1].binary, 0)); ref_readers.append(AnimationSampler(refs[-1].document, refs[-1].binary, 0))
    plane_times = np.asarray(sq['plane_times_s'])
    full = np.unique(np.r_[plane_times, guard, uniform, event, window, 0., [r.duration for r in readers]])
    plane_frames = np.searchsorted(full, plane_times)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(sq['implementation']) | {'rate_peak_guard.py', 'sample_rate_peak_guard.py', 'absolute_rate_peaks.py', 'dual_rate_peak_guard.py', 'rotation_rate_support.py', 'study_supported_guard_contact.py'}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(source), inputs=files, implementation=methods,
        target=target, selected_contact=contact, event_time_s=event, window_s=window, protected_spans=protected,
        guard_times_s=guard.tolist(), uniform_times_s=uniform.tolist(), original_bins_s=sq['original_bins_s'],
        plane_times_s=plane_times.tolist(), solver_iterations=120, control_component_bound_radians=.15,
        minimum_hand_plane_clearance_m=.00045, authored_half_gap_m=target['separation_m']/2,
        rate_objective_scales=[1., 10., 3., 100.], proposal_plane_reserve_m=.000001,
        proposal_rate_formulation='Each time and affected subtree joint constrained by the minimum of frozen reference-excess and absolute peak envelopes. Acceptance checks every joint.',
        absolute_peak_guard_tolerance=1e-7, absolute_proposal_reserve_fraction=.1, absolute_proposal_reserve_scaled_maximum=1e-4,
        per_joint_peak_guard_tolerance=1e-7, proposal_peak_reserve_fraction=.1, proposal_peak_reserve_scaled_maximum=1e-4,
        policy='Matched continuation from the first completed rate fit. Keep original 45 degree joint budgets, contact target, 0.45 mm actual plane clearance and original rate caps. Add per-joint guards against increasing each original-cap excess peak, using the starting serialized clip, with 1e-7 numerical reporting allowance in each rate unit. Tighten proposal planes inward by 1 micrometre and positive peak deficits by min(10 percent, 1e-4 times rate scale); these reserves do not alter actual acceptance caps. Also freeze each absolute per-joint rate peak from the same source. Intersect the time-dependent excess envelope with that absolute envelope, with the same numerical allowance. Absolute proposal reserve is min(10 percent of absolute peak, 1e-4 times rate scale). Original caps remain separate. Proposal rate rows omit only structurally immutable samples: own-origin positions and rates whose complete native interpolation stencils are frozen. Final acceptance and independent decoding retain every joint/time bound. Source need only satisfy actual gates, not inward proposal reserves. Select only a serialized feasible objective improvement and audit decoded geometry and original rates. Preserve raw proposed controls even when every step is rejected.',
        quality_approved=False))
    decoded = []; clips = []; fits = []
    for i, (rig, ref, reader) in enumerate(zip(rigs, refs, readers)):
        nodes = donor['actors'][i]['nodes'][:3]
        edit = ContactRatePath(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in nodes], full, window, protected, event, (ref.document, ref.binary))
        actor = actors[i]; midpoint = np.asarray(target['midpoint_m']); outward = np.asarray(target['normals'][i])
        projection = ProjectedSkin(BoundSkin(rig), np.asarray(region['region_vertices'][i]), actor['rotation'].T@outward, (actor['translation']-midpoint)@outward)
        ref_world = np.array([ref_readers[i].sample(t) for t in uniform])
        actor_caps = SampledMotionCaps(features(ref_world, ref.joints), uniform, sq['original_bins_s'])
        uniform_frames = np.searchsorted(full, uniform); event_frame = int(np.searchsorted(full, event)); zero = np.zeros(edit.size)
        baseline_world = edit.world(zero, True); baseline_contact = baseline_world[event_frame]
        affected = descendants(rig.parents, nodes[0])
        if not np.all(affected[nodes]): raise ValueError('All controls must lie in the guarded subtree')
        columns = np.flatnonzero(affected[rig.joints])
        support = rate_support(rig.parents, rig.joints, edit.model.entries, uniform)
        peak_guard = SupportedDualRatePeakGuard(measures(features(baseline_world[uniform_frames], rig.joints), actor_caps.dt), actor_caps.caps, columns, support, cap_tolerance=actor_caps.tolerance)
        def evaluate(x, quantize=False, proposal=False):
            world = edit.world(x, quantize); values = measures(features(world[uniform_frames], rig.joints), actor_caps.dt)
            cost = sum(float(np.mean((np.maximum(v-c-actor_caps.tolerance, 0)/scale)**2)) for v, c, scale in zip(values, actor_caps.caps, (1., 10., 3., 100.)))
            excess = projection.evaluate(world[plane_frames]).max(axis=1)+.00045
            angles = edit.original_angles(x, quantize)
            constraints = np.r_[-(excess+(.000001 if proposal else 0))*1000, (45.-angles)/45., (peak_guard.sample_margins(values, proposal=True) if proposal else peak_guard.margins(values))]
            return cost, constraints, float(np.abs(world[event_frame]-baseline_contact).max()), excess
        @lru_cache(maxsize=128)
        def cached(key):
            x = np.frombuffer(key, dtype=float); cost, constraints, _, _ = evaluate(x, proposal=True)
            return cost+1e-6*float(x@x), constraints
        initial_cost, initial_constraints, _, _ = evaluate(zero, True)
        if initial_constraints.min() < -1e-8: raise ValueError('Initial serialized path violates actual constraints')
        history = []
        def callback(x):
            cost, constraints = cached(np.asarray(x, float).tobytes()); history.append(dict(objective=cost, minimum_constraint=float(constraints.min())))
            if len(history)%10 == 0: print(dict(phase='supported_guarded_fit', actor=i, iteration=len(history), objective=cost, minimum_constraint=float(constraints.min())), flush=True)
        fit = minimize(lambda x: cached(np.asarray(x, float).tobytes())[0], zero, method='SLSQP',
            bounds=[(-.15, .15)]*edit.size,
            constraints=[dict(type='ineq', fun=lambda x: cached(np.asarray(x, float).tobytes())[1])], callback=callback,
            options=dict(maxiter=120, ftol=1e-10, eps=1e-5))
        selected = zero; fraction = 0.; attempts = []
        for factor in 2.**(-np.arange(9)):
            proposed = fit.x*factor; cost, constraints, drift, excess = evaluate(proposed, True)
            feasible = bool(constraints.min() >= 0 and drift <= 1e-6)
            attempts.append(dict(fraction=float(factor), objective=cost, minimum_constraint=float(constraints.min()), contact_matrix_drift=drift, feasible=feasible))
            if feasible and cost < initial_cost-1e-10: selected = proposed; fraction = float(factor); break
        final_cost, constraints, drift, excess = evaluate(selected, True)
        report = dict(actor=i, solver_success=bool(fit.success), solver_message=str(fit.message), iterations=int(fit.nit), evaluations=int(fit.nfev),
            initial_objective=initial_cost, selected_objective=final_cost, selected_fraction=fraction, controls=selected.tolist(),
            proposal_joint_columns=columns.tolist(), proposal_sample_rows=sum(int(m.sum()) for m in support),
            immutable_sample_rows=[int(m.size-m.sum()) for m in support],
            proposed_controls=fit.x.tolist(), history=history, serialized_attempts=attempts, contact_matrix_drift=drift, minimum_constraint=float(constraints.min()),
            peak_guard=peak_guard.report(measures(features(edit.world(selected, True)[uniform_frames], rig.joints), actor_caps.dt)),
            plane_clearance_pass=bool(np.all(excess <= 1e-8)),
            authored_half_gap_plane_pass=bool(np.all(excess-.00045+target['separation_m']/2 <= 1e-8)), quality_approved=False)
        fits.append(report); save(output/f'actor-{i}-fit.json', report)
        print(dict(phase='supported_guarded_selected', actor=i, initial=initial_cost, selected=final_cost, fraction=fraction), flush=True)
        path = output/f'candidate-{i}.glb'
        if fraction: edit.export(selected, path)
        else: shutil.copyfile(source/path.name, path)
        asset = RigAsset.load(path); current = AnimationSampler(asset.document, asset.binary, 0)
        world = np.array([current.sample(t) for t in full]); before = np.array([reader.sample(t) for t in full])
        frozen = (full <= window[0]) | (full >= window[1])
        for a, b in protected: frozen |= (full >= a) & (full <= b)
        np.testing.assert_array_equal(world[frozen], before[frozen])
        event_index = int(np.searchsorted(full, event)); error = float(np.max(np.abs(world[event_index]-before[event_index])))
        if error > 1e-6: raise ValueError('Decoded contact drift exceeds matrix tolerance')
        assert len(current.channels) == len(reader.channels)
        for a, b in zip(current.channels, reader.channels):
            assert a[:2] == b[:2] and a[4] == b[4]; np.testing.assert_array_equal(a[2], b[2])
            if a[1] != 'rotation' or a[0] not in nodes: np.testing.assert_array_equal(a[3], b[3])
        original_channels, channels = rotation_channels(ref.document, ref.binary), rotation_channels(asset.document, asset.binary); angles = []
        for node, budget in zip(donor['actors'][i]['nodes'], donor['actors'][i]['original_budgets_degrees']):
            angle = float(np.rad2deg((Rotation.from_quat(original_channels[node][2]).inv()*Rotation.from_quat(channels[node][2])).magnitude()).max())
            if angle > budget+1e-4: raise ValueError('Decoded original native edit budget exceeded')
            angles.append(angle)
        decoded_peak_guard = peak_guard.report(measures(features(world[uniform_frames], rig.joints), actor_caps.dt))
        if not decoded_peak_guard['dual_peak_guard_pass']: raise ValueError('Independent decode regressed an absolute or reference-excess joint peak')
        decoded.append(world); clips.append(dict(path=path.name, sha256=sha256(path), contact_matrix_drift=error,
            per_joint_peak_guard=decoded_peak_guard,
            original_edit_angles_degrees=angles, native_clocks_unselected_channels_outside_window_protected_poses_exact=True))
    def payload(values):
        parts = [features(w, r.joints) for w, r in zip(values, refs)]
        return {k: np.concatenate([p[k] for p in parts], axis=1) for k in ('positions', 'rotations')}
    raw = [np.array([r.sample(t) for t in uniform]) for r in ref_readers]
    caps = SampledMotionCaps(payload(raw), uniform, sq['original_bins_s']); actual = payload([w[np.searchsorted(full, uniform)] for w in decoded]); rates = []
    for kind, values, ceiling in zip(('position_speed', 'position_acceleration', 'angular_speed', 'angular_acceleration'), measures(actual, caps.dt), caps.caps):
        excess = values-ceiling-caps.tolerance; rates.append(dict(kind=kind, failed_rows=int(np.count_nonzero(excess > 0)), maximum_excess=float(excess.max())))
    observations = []; contact_check = None; floor = []
    for index, time in enumerate(guard):
        frame = int(np.searchsorted(full, time)); points = [r.vertices(w[frame])@a['rotation'].T+a['translation'] for r, w, a in zip(rigs, decoded, actors)]
        surface = audit(points[0], actors[0]['faces'], points[1], actors[1]['faces'])
        depths = [penetration(points[a], points[b], actors[b]['faces'], tolerance_m=1e-8) for a, b in ((0, 1), (1, 0))]
        passed = not any(v for k, v in surface['counts'].items() if k != 'disjoint') and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8
        row = dict(time_s=float(time), surface=surface, depths=depths, inter_actor_pose_screen_pass=bool(passed)); observations.append(row)
        if time == event:
            centers = []; normals = []
            for i, (p, a) in enumerate(zip(points, actors)):
                v = (contact['effector'] if i == 0 else contact['target'])['surface_vertex']; patch = a['faces'][np.any(a['faces'] == v, axis=1)]
                c, n = palm_geometry(p, patch, v); centers.append(c); normals.append(n)
            contact_check = measure(centers, normals, target); row['contact'] = contact_check
        save(output/f'geometry-{index:02d}.json', row)
        before = [r.vertices(reader.sample(time))@a['rotation'].T+a['translation'] for r, reader, a in zip(rigs, readers, actors)]
        floor.append(dict(time_s=float(time), source_m=[max(0., -float(p[:, 1].min())) for p in before], exported_m=[max(0., -float(p[:, 1].min())) for p in points]))
        print(dict(phase='supported_guarded_geometry', completed=index+1, total=len(guard), passed=bool(passed)), flush=True)
    save(output/'decoded.json', dict(clips=clips, contact=contact_check, motion_rates=rates)); save(output/'floor.json', floor)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed input during study')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Changed method during study')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        contact_target_pass=contact_check['contact_target_pass'], contact_mesh_screen_pass=next(o['inter_actor_pose_screen_pass'] for o in observations if o['time_s'] == event),
        guard_samples=len(guard), failed_geometry_samples=sum(not o['inter_actor_pose_screen_pass'] for o in observations),
        maximum_vertex_depth_m=max(d['max_depth_m'] for o in observations for d in o['depths']),
        original_motion_caps_pass=all(r['failed_rows'] == 0 for r in rates), native_animation_exported=True,
        proposal_plane_clearance_pass=all(r['plane_clearance_pass'] for r in fits),
        authored_half_gap_planes_pass=all(r['authored_half_gap_plane_pass'] for r in fits),
        accepted_actor_updates=sum(r['selected_fraction'] > 0 for r in fits),
        per_joint_peak_guards_pass=all(c['per_joint_peak_guard']['per_joint_peak_guard_pass'] for c in clips),
        absolute_peak_guards_pass=all(c['per_joint_peak_guard']['absolute_peak_guard']['absolute_peak_guard_pass'] for c in clips),
        dual_peak_guards_pass=all(c['per_joint_peak_guard']['dual_peak_guard_pass'] for c in clips),
        continuous_collision_certified=False, selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.source, args.output)
