"""Replay refreshed bindings, exact exports and full sampled clearance comparison."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from coupled_pair_problem import PairProblem
from coupled_continuation_checkpoint import checkpoint
from coupled_continuation_policy import acceptance
from study_paired_guarded_temporal import decoded
from paired_temporal_neighbor import placed_joint_positions, rotation_channels
from gltf_tools import read_glb
from rig_asset import RigAsset
from verify_paired_stage_rates import verify_rates


def run(study, witnesses, geometry, output):
    study, geometry, output = (Path(p).resolve() for p in (study, geometry, output))
    if output.exists():
        raise ValueError('Preserve earlier refreshed-pair replay')
    request, result = read(study/'request.json'), read(study/'result.json')
    if result['status'] != 'complete' or result['selected'] is None or result['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Completed selected comparison required')
    problem = PairProblem(witnesses); state = checkpoint(request['start'])
    source_geometry = Path(request['starting_geometry'])
    inputs = {**request['inputs'], **problem.inputs}
    for name in ['request.json', 'result.json', 'start-review.json', 'manifest.json']:
        inputs[str(study/name)] = sha256(study/name)
    for name, key in [('bindings.npz', 'bindings_sha256'), ('solver.json', 'solver_sha256'), ('trials.json', 'trials_sha256')]:
        inputs[str(study/name)] = result[key]
    solver = read(study/'solver.json'); inputs[str(study/'linearization.npz')] = solver['linearization_sha256']
    np.testing.assert_array_equal(solver['base_controls'], state['controls'])
    step = np.array(solver['step'])
    if np.rad2deg(np.linalg.norm(step.reshape(-1, 3), axis=1)).max() > .2+1e-7:
        raise ValueError('Step exceeds unchanged knot trust radius')
    with np.load(study/'bindings.npz', allow_pickle=False) as saved:
        bindings = dict(saved)
    with np.load(study/'linearization.npz', allow_pickle=False) as saved:
        linear = dict(saved)
    center = read(Path(request['reserve'])/'result.json')
    with np.load(center['center_linearization_path'], allow_pickle=False) as previous:
        for key in ['vectors', 'jacobians', 'radii', 'kinds']:
            np.testing.assert_array_equal(linear[key], previous[key])
    rows = read(source_geometry/'samples.json')['rows']
    caps = np.array([.005 if r['candidate_depth_m'] <= .005 else max(.005, r['source_depth_m']) for r in rows])
    np.testing.assert_array_equal(caps, request['depth_caps_m'])
    np.testing.assert_array_equal([r['frame'] for r in rows], request['frames'])
    cap_map = dict(zip(request['frames'], caps)); records = [r for g in problem.groups for r in g['rows']]
    frame_ids = np.array([r['frame'] for r in records])
    row_caps = np.array([cap_map[r['frame']] for r in records])
    np.testing.assert_array_equal(row_caps, linear['depth_caps'])
    inside = np.concatenate([bindings[f'{n}_signed_depth'] for n in range(2)]) > 0
    if int(inside.sum()) != result['penetrating_norm_rows']:
        raise ValueError('Refreshed inside population changed')
    for n, group in enumerate(problem.groups):
        np.testing.assert_array_equal(group['ids'], bindings[f'{n}_ids'])
        np.testing.assert_array_equal([r['frame'] for r in group['rows']], bindings[f'{n}_frames'])
    triangles = np.concatenate([bindings[f'{n}_triangles'] for n in range(2)])
    bary = np.concatenate([bindings[f'{n}_bary'] for n in range(2)])
    normals = np.concatenate([bindings[f'{n}_normals'] for n in range(2)])
    original_positions = []
    for actor in problem.actors:
        doc, world = decoded(actor['source'])
        original_positions.append(placed_joint_positions(world, doc['skins'][0]['joints'], actor['rotation'], actor['translation']))
    trials = read(study/'trials.json'); initial = read(study/'start-review.json')
    entries = [initial]+trials
    if len(trials) != result['trial_count'] or not trials or trials[-1] != result['selected']:
        raise ValueError('Trial selection/history differs')
    inputs[str(source_geometry/'samples.json')] = sha256(source_geometry/'samples.json')
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Replay input changed')
    output.mkdir(); shutil.copyfile(__file__, output/'implementation.py')
    total_peaks = 0; peak_error = 0.; vector_error = 0.; point_error = 0.; decisions = []
    starting_depths = None
    for index, entry in enumerate(entries):
        controls = state['controls'] if index == 0 else state['controls']+step*entry['factor']
        if index:
            if entry['factor'] != request['line_factors'][index-1]:
                raise ValueError('Line search order differs')
            np.testing.assert_array_equal(controls, entry['controls'])
        reconstructed = output/f'reconstructed-{index}'; reconstructed.mkdir()
        worlds = []; rigs = []; replayed_failures = []; replayed_edits = []
        for actor_number, (actor, part, check) in enumerate(zip(problem.actors, np.split(controls, [problem.sizes[0]]), entry['actors'])):
            path = study/check['path']; inputs[str(path)] = check['sha256']
            actor['model'].export(part, reconstructed/path.name)
            if sha256(path) != check['sha256'] or sha256(reconstructed/path.name) != check['sha256']:
                raise ValueError('Cumulative controls fail exact GLB reconstruction')
            rig = RigAsset.load(path); doc, world = decoded(path); rigs.append(rig); worlds.append(world)
            names = [doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
            positions = placed_joint_positions(world, doc['skins'][0]['joints'], actor['rotation'], actor['translation'])
            rate_path = path.parent/(actor['name']+'-rates.json'); inputs[str(rate_path)] = check['rates_sha256']
            rates = read(rate_path)
            count, error = verify_rates(original_positions[actor_number], positions, rates, names)
            total_peaks += count; peak_error = max(peak_error, error)
            failures = sum(row['change'] > 1e-5 for metric in ['speed', 'acceleration'] for window in rates[metric]['windows'] for row in window['joints'])
            if failures != check['rate_failures']:
                raise ValueError('Replayed motion failure count differs')
            replayed_failures.append(failures)
            ref_doc, ref_binary = read_glb(actor['reference']); reference = rotation_channels(ref_doc, ref_binary)
            actual_doc, actual_binary = read_glb(path); actual = rotation_channels(actual_doc, actual_binary)
            maximum = max(float(np.rad2deg((Rotation.from_quat(reference[node][2]).inv()*Rotation.from_quat(q)).magnitude()).max()) for node, (_, _, q) in actual.items())
            np.testing.assert_allclose(maximum, check['maximum_original_edit_degrees'], atol=1e-10, rtol=0)
            replayed_edits.append(maximum)
        parent = (study/entry['actors'][0]['path']).parent
        vector_path = parent/'witness-vectors.npz'; inputs[str(vector_path)] = entry['witness_vectors_sha256']
        with np.load(vector_path, allow_pickle=False) as saved:
            expected = saved['vectors']
        if index == 0:
            fresh = bindings
        else:
            path = parent/'fresh-surface.npz'; inputs[str(path)] = entry['fresh_surface_sha256']
            with np.load(path, allow_pickle=False) as saved:
                fresh = dict(saved)
        for n in range(2):
            for key in ['ids', 'frames']:
                np.testing.assert_array_equal(fresh[f'{n}_{key}'], bindings[f'{n}_{key}'])
        fresh_triangles = np.concatenate([fresh[f'{n}_triangles'] for n in range(2)])
        fresh_bary = np.concatenate([fresh[f'{n}_bary'] for n in range(2)])
        fresh_points = np.concatenate([fresh[f'{n}_points'] for n in range(2)])
        fresh_closest = np.concatenate([fresh[f'{n}_closest'] for n in range(2)])
        signed = np.concatenate([fresh[f'{n}_signed_depth'] for n in range(2)])
        values = np.empty_like(expected)
        for frame in request['frames']:
            points = [rig.vertices(world[int(round(frame*4))]) @ actor['rotation'].T+actor['translation'] for rig, world, actor in zip(rigs, worlds, problem.actors)]
            for i in np.flatnonzero(frame_ids == frame):
                row = records[i]; p = points[row['source']][row['vertex']]
                target = sum(w*points[row['target']][v] for w, v in zip(bary[i], triangles[i]))
                values[i] = p-target
                closest = sum(w*points[row['target']][v] for w, v in zip(fresh_bary[i], fresh_triangles[i]))
                np.testing.assert_allclose(p, fresh_points[i], atol=1e-10, rtol=0)
                np.testing.assert_allclose(closest, fresh_closest[i], atol=1e-10, rtol=0)
                np.testing.assert_allclose(np.linalg.norm(p-closest), abs(signed[i]), atol=1e-8, rtol=0)
                point_error = max(point_error, float(np.abs(p-fresh_points[i]).max()), float(np.abs(closest-fresh_closest[i]).max()))
        np.testing.assert_allclose(values, expected, atol=1e-10, rtol=0)
        vector_error = max(vector_error, float(np.abs(values-expected).max()))
        fixed_excess = max(0., np.r_[np.linalg.norm(values[inside], axis=1)-row_caps[inside], -np.sum(values*normals, axis=1)-row_caps].max())
        depths = np.array([max(0., signed[frame_ids == frame].max(initial=0.)) for frame in request['frames']])
        if starting_depths is None:
            starting_depths = depths
        subset_excess = max(0., (depths-caps).max())
        np.testing.assert_allclose([depths.max(), subset_excess, fixed_excess],
            [entry['actual_subset']['candidate_peak_m'], entry['actual_subset']['maximum_cap_excess_m'], entry['surface']['maximum_cap_excess_m']], atol=1e-10, rtol=0)
        if index:
            decision = acceptance(float(starting_depths.max()), float(depths.max()), float(max(fixed_excess, subset_excess)),
                replayed_failures, replayed_edits, [c['preservation']['original_finger_limits_passed'] for c in entry['actors']])
            if decision['accepted'] != entry['decision']['accepted'] or decision['reasons'] != entry['decision']['reasons']:
                raise ValueError('Replayed trial acceptance differs')
            if index < len(entries)-1 and decision['accepted']:
                raise ValueError('Continued after accepting a trial')
            decisions.append(decision)
    np.testing.assert_array_equal(result['total_controls'], result['selected']['controls'])
    gr, gp = read(geometry/'verification.json'), read(geometry/'request.json')
    if gr['request_sha256'] != sha256(geometry/'request.json') or gr['samples_sha256'] != sha256(geometry/'samples.json') or gr['samples'] != 57 or gr['fresh_directional_queries'] != 114:
        raise ValueError('Complete final mesh audit required')
    for check in result['selected']['actors']:
        path = study/'candidate'/(check['actor']+'.glb')
        if gp['inputs'].get(str(path)) != check['sha256']:
            raise ValueError('Final geometry belongs to another pair')
    candidate_rows = read(geometry/'samples.json')['rows']
    np.testing.assert_array_equal([r['frame'] for r in candidate_rows], request['frames'])
    start_full = np.array([r['candidate_depth_m'] for r in rows]); final_full = np.array([r['candidate_depth_m'] for r in candidate_rows])
    if np.any(depths > final_full+1e-8):
        raise ValueError('Selected-vertex depth contradicts complete final audit')
    comparison = dict(start_peak_m=float(start_full.max()), candidate_peak_m=float(final_full.max()),
        improvement_m=float(start_full.max()-final_full.max()), start_screen_failures=int(np.sum(start_full > .005)),
        candidate_screen_failures=int(np.sum(final_full > .005)), protected_clear_times=int(np.sum(start_full <= .005)),
        lost_clearances_strict=int(np.sum((start_full <= .005) & (final_full > .005))),
        lost_clearances_over_1e_6=int(np.sum((start_full <= .005) & (final_full > .005001))),
        maximum_cap_excess_m=float(max(0., (final_full-caps).max())), cap_failures_over_1e_6=int(np.sum(final_full-caps > 1e-6)),
        depth_increases_vs_start_over_1e_6=int(np.sum(final_full-start_full > 1e-6)),
        maximum_depth_increase_vs_start_m=float((final_full-start_full).max()),
        maximum_floor_increase_vs_start_m=max(max(r['floor_depth_m'])-max(s['floor_depth_m']) for s, r in zip(rows, candidate_rows)))
    comparison['sampled_geometry_policy_passed'] = comparison['improvement_m'] >= 1e-6 and comparison['cap_failures_over_1e_6'] == 0 and comparison['maximum_floor_increase_vs_start_m'] <= 1e-6
    for name in ['request.json', 'samples.json', 'verification.json']:
        inputs[str(geometry/name)] = sha256(geometry/name)
    for path, digest in {**inputs, **gp['inputs']}.items():
        if sha256(path) != digest:
            raise ValueError('Input changed during independent replay')
    save(output/'verification.json', dict(at=now(), inputs=inputs, implementation_sha256=sha256(__file__),
        exact_reconstructed_exports=2*len(entries), trial_decisions=decisions, replayed_peak_values=total_peaks,
        maximum_rate_replay_error=peak_error, full_skin_witness_vectors=len(records)*len(entries), maximum_vector_error_m=vector_error,
        maximum_fresh_point_error_m=point_error, comparison=comparison, quality_approved=False,
        scope='Exact cumulative-control export reconstruction, original motion center, all trial rate tables and full CPU-skin fixed/fresh point reconstruction. Stored signed distances determine trial decisions; complete independently queried final mesh evidence determines the sampled clearance-policy result. No continuous collision or naturalness certification.'))
    print(dict(comparison=comparison, replayed_peak_values=total_peaks, maximum_vector_error_m=vector_error), flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['study', 'witnesses', 'geometry', 'output']:
        p.add_argument(name, type=Path)
    args = p.parse_args()
    with threadpool_limits(limits=1):
        run(args.study, args.witnesses, args.geometry, args.output)
