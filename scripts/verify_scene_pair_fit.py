"""Independent GLB replay of every attempted scene-derived paired correction."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from gltf_tools import read_glb
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from timed_rotation_edit import TimedRotationEdit


def rate_check(source, candidate, times, knots, tolerance=1e-5):
    """Replay every joint/stencil; no reuse of the fitter's active-row policy."""
    if not np.allclose(np.diff(times), times[1]-times[0], atol=1e-12, rtol=0):
        raise ValueError('Uniform replay clock required')
    failures = 0; checked = 0; maximum = 0.; peaks = []
    for order in [1, 2]:
        original = np.linalg.norm(np.diff(source, n=order, axis=0)/(times[1]-times[0])**order, axis=2)
        edited = np.linalg.norm(np.diff(candidate, n=order, axis=0)/(times[1]-times[0])**order, axis=2)
        clock = (times[:-order]+times[order:])/2
        edges = np.r_[-np.inf, knots[1:-1], np.inf]
        for index, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
            mask = (clock >= left) & (clock < right)
            if not mask.any(): continue
            cap = original[mask].max(axis=0); excess = edited[mask]-cap
            failures += int((excess > tolerance).sum()); checked += excess.size
            maximum = max(maximum, float(excess.max()))
            peaks.append(dict(order=order, span=index, source=cap.tolist(), candidate=edited[mask].max(axis=0).tolist()))
    return dict(failures=failures, checked=checked, maximum_excess=maximum, peaks=peaks)


def trial_controls(trial, actors):
    if [a['name'] for a in actors] != [r['actor'] for r in trial['actors']]:
        raise ValueError('Replay actor population or order differs')
    controls = np.asarray(trial['controls'], float)
    if controls.shape != (sum(a['model'].size for a in actors),) or not np.isfinite(controls).all():
        raise ValueError('Complete finite controls for every replay actor required')
    return controls


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    result, request = read(study/'result.json'), read(study/'request.json')
    if output.exists(): raise ValueError('Preserve earlier independent replay')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Completed bound study required')
    for name in ['source-index', 'linearization', 'solver', 'manifest', 'trials']:
        filename = name+('.npz' if name == 'linearization' else '.json')
        digest = result.get(name.replace('-', '_')+'_sha256')
        if digest is not None and sha256(study/filename) != digest: raise ValueError('Study artifact changed: '+name)
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Study input changed')
    for name, digest in request['implementation'].items():
        if sha256(study/'implementation'/name) != digest: raise ValueError('Study snapshot changed')
    prepared = Path(request['prepared_request']); record = read(prepared); authored = record['authored']
    times = np.asarray(record['sample_times_seconds']); knots = np.asarray(authored['knots_s'])
    samples = []
    for name, digest in read(study/'source-index.json').items():
        if sha256(study/'source'/name) != digest: raise ValueError('Source geometry changed')
        samples.append(read(study/'source'/name))
    if [s['sample'] for s in samples] != list(range(len(times))) or not np.array_equal([s['time_s'] for s in samples], times):
        raise ValueError('Geometry population differs from original request')
    output.mkdir(); implementation = output/'implementation'; implementation.mkdir()
    methods = ['verify_scene_pair_fit.py', 'timed_rotation_edit.py', 'rig_asset.py', 'rig_clip_import.py',
               'paired_temporal_neighbor.py', 'paired_guarded_temporal.py', 'gltf_tools.py', 'strep.py',
               'refined_reserve_inputs.py', 'bound_evidence.py', 'diagnose_scene_pair_refinement.py',
               'diagnose_scene_pair_limits.py', 'coupled_pair_proposal.py']
    for name in methods: shutil.copyfile(ROOT/'scripts'/name, implementation/name)
    protocol = dict(at=now(), study_request_sha256=sha256(study/'request.json'), study_result_sha256=sha256(study/'result.json'),
        implementation={n: sha256(implementation/n) for n in methods}, quality_approved=False)
    save(output/'request.json', protocol); actors = []; gaps = [[], []]; skin_errors = []
    for index, (name, entry) in enumerate(record['actors'].items()):
        path = prepared.parent/entry['path']; rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        worlds = np.array([sampler.sample(t) for t in times]); placement = entry['placement']
        rotation = Rotation.from_quat(placement['rotation_xyzw']).as_matrix(); shift = np.asarray(placement['translation_m'])
        model = TimedRotationEdit(rig.document, rig.binary, authored['actors'][name]['joints'], times, authored['window_s'],
            record['protected_seconds'], knots=knots, limit_degrees=authored['limit_degrees'])
        actors.append(dict(name=name, model=model, rig=rig, world=worlds, rotation=rotation, shift=shift))
    if request.get('curve_actors') is not None:
        from refined_reserve_inputs import install_refined_models
        install_refined_models(actors, request['curve_actors'])
    # The outer `knots` remain the immutable prepared bins, regardless of the
    # denser reconstruction basis installed above.
    # Full CPU skinning reconstructs every retained source point/target point.
    for sample in samples:
        index = sample['sample']; points = [a['rig'].vertices(a['world'][index])@a['rotation'].T+a['shift'] for a in actors]
        for direction in sample['directions']:
            s, t = direction['source'], direction['target']
            for row in direction['records']:
                p = points[s][row['vertex']]; q = np.asarray(row['barycentric'])@points[t][row['target_vertices']]
                gap = float((p-q)@row['normal']); gaps[s].append(gap)
                skin_errors.append(max(float(np.abs(p-row['source_position_m']).max()), float(np.abs(q-row['target_position_m']).max())))
                if abs(gap-row['gap_m']) > 1e-8: raise ValueError('Full-skin source witness mismatch')
    with np.load(study/'linearization.npz', allow_pickle=False) as linear:
        np.testing.assert_allclose(np.concatenate(gaps), linear['gaps'], atol=1e-8, rtol=0)
    trials = read(study/'trials.json') if result['trials'] else []; reviews = []
    for trial in trials:
        all_controls = trial_controls(trial, actors)
        folder = output/trial['folder']; folder.mkdir(); offset = 0; records = []
        for index, (actor, report) in enumerate(zip(actors, trial['actors'])):
            model = actor['model']; controls = all_controls[offset:offset+model.size]; offset += model.size
            path = study/trial['folder']/report['path']
            if sha256(path) != report['sha256']: raise ValueError('Trial actor changed')
            reconstructed = folder/f'actor-{index}.glb'; model.export(controls, reconstructed)
            if sha256(reconstructed) != report['sha256']: raise ValueError('Controls do not reconstruct actual export')
            doc, binary = read_glb(path); sampler = AnimationSampler(doc, binary, 0); joints = actor['rig'].joints
            world = np.array([sampler.sample(t) for t in times]); source = actor['world']
            positions = lambda w: w[:, joints][:, :, :3, 3]@actor['rotation'].T+actor['shift']
            rates = rate_check(positions(source), positions(world), times, knots)
            if rates['failures'] != report['rate_failures']: raise ValueError('Independent rate-failure count differs')
            original = rotation_channels(model.document, model.binary); changed = rotation_channels(doc, binary)
            maximum = 0.
            for node, (_, clock, q) in original.items():
                np.testing.assert_array_equal(clock, changed[node][1])
                entry = next((e for e in model.entries if e['node'] == node), None)
                frozen = np.arange(len(clock)) if entry is None else np.setdiff1d(np.arange(len(clock)), entry['ids'])
                np.testing.assert_array_equal(q[frozen], changed[node][2][frozen])
                maximum = max(maximum, float(np.rad2deg((Rotation.from_quat(q).inv()*Rotation.from_quat(changed[node][2])).magnitude()).max()))
            if abs(maximum-report['maximum_edit_degrees']) > 1e-10: raise ValueError('Original edit report differs')
            records.append(dict(actor=actor['name'], exact_export_reconstruction=True, rates=rates, maximum_edit_degrees=maximum))
        geometry = trial['geometry']
        if geometry:
            path = study/trial['folder']/'geometry.json'
            if sha256(path) != geometry['geometry_sha256']: raise ValueError('Export geometry changed')
            rows = read(path)
            if len(rows) != len(samples): raise ValueError('Incomplete exported geometry')
            for row, source in zip(rows, samples):
                if row['sample'] != source['sample'] or row['time_s'] != source['time_s']: raise ValueError('Geometry clock differs')
                start = max(d['maximum_depth_m'] for d in source['directions'])
                depth = max(d['max_depth_m'] for d in row['directions'])
                np.testing.assert_allclose([row['source_depth_m'], row['candidate_depth_m'], row['cap_excess_m']],
                    [start, depth, max(0., depth-max(.005, start))], atol=1e-12, rtol=0)
        reviews.append(dict(folder=trial['folder'], actors=records, quality_approved=False))
    save(output/'verification.json', dict(at=now(), request_sha256=sha256(output/'request.json'), trials=reviews,
        reconstructed_exports=sum(len(r['actors']) for r in reviews), rate_observations=sum(a['rates']['checked'] for r in reviews for a in r['actors']),
        full_skin_witnesses=len(skin_errors), maximum_full_skin_point_error=max(skin_errors, default=0.), quality_approved=False,
        scope='Independent scalar GLB replay of all attempted exports and all joint rate stencils; exact export reconstruction and full-skin source witness checks. Geometry report bindings and arithmetic checked, not a second signed-distance implementation or a release approval.'))
    print(dict(status='complete', trials=len(reviews), witnesses=len(skin_errors)), flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('study', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    with threadpool_limits(limits=1): run(a.study, a.output)
