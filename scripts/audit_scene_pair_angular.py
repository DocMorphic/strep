"""Supplement retained paired trials with independent world angular-rate evidence."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from joint_angular_rates import compare_angular_rates


def run(audit, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    audit, output = Path(audit).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh angular audit required')
    complete = read(audit/'result.json'); request = read(audit/'request.json')
    if complete['status'] != 'complete': raise ValueError('Completed export audit required')
    files = {str(audit/'result.json'): sha256(audit/'result.json')}
    for name in ['request', 'trials']:
        path = audit/(name+'.json')
        if sha256(path) != complete[name+'_sha256']: raise ValueError('Export audit changed')
        files[str(path)] = sha256(path)
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Export audit input changed')
        files[path] = digest
    for name in ['rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py']:
        if sha256(ROOT/'scripts'/name) != request['implementation'][name]: raise ValueError('Export decoder changed')
    refined = read(Path(request['refinement'])/'request.json'); study = read(Path(refined['study'])/'request.json')
    prepared_path = Path(study['prepared_request']); prepared = read(prepared_path)
    if files.get(str(prepared_path)) != sha256(prepared_path): raise ValueError('Original clocks are not bound')
    times = np.asarray(prepared['sample_times_seconds']); knots = prepared['authored']['knots_s']; actors = {}
    for name, entry in prepared['actors'].items():
        path = (prepared_path.parent/entry['path']).resolve()
        if not path.is_relative_to(prepared_path.parent) or sha256(path) != entry['sha256']: raise ValueError('Original actor changed')
        files[str(path)] = entry['sha256']; rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        rotations = np.array([sampler.sample(t)[rig.joints, :3, :3] for t in times])
        actors[name] = dict(rig=rig, rotations=rotations, names=[rig.document['nodes'][n]['name'] for n in rig.joints])
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in ['audit_scene_pair_angular.py', 'joint_angular_rates.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    trials = []
    for index, trial in enumerate(read(audit/'trials.json')):
        if [a['actor'] for a in trial['actors']] != list(actors): raise ValueError('Trial actor order differs')
        records = []
        for record in trial['actors']:
            path = (audit/f'trial-{index}'/record['path']).resolve()
            if path.parent != audit/f'trial-{index}' or sha256(path) != record['sha256']: raise ValueError('Trial export changed')
            files[str(path)] = record['sha256']; source = actors[record['actor']]
            rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
            for field in ['nodes', 'skins']:
                if rig.document[field] != source['rig'].document[field]: raise ValueError('Trial changed rig identity')
            rotations = np.array([sampler.sample(t)[rig.joints, :3, :3] for t in times])
            rates = compare_angular_rates(source['rotations'], rotations, times, knots, source['names'],
                speed_tolerance=1e-5, acceleration_tolerance=1e-5)
            records.append(dict(actor=record['actor'], rates=rates))
        trials.append(dict(index=index, factor=trial['factor'], actors=records, positional_preliminary_pass=trial['preliminary_checks_pass']))
        save(output/'trials.json', trials)
        print(dict(factor=trial['factor'], angular_exceedances=[{k:v['exceeding_observations'] for k,v in a['rates'].items()} for a in records]), flush=True)
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Angular audit input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Angular audit method changed')
    save(output/'request.json', dict(at=now(), export_audit=str(audit), inputs=files, implementation=methods,
        sample_times_seconds=times.tolist(), original_knots_seconds=knots, tolerances=dict(speed_rad_s=1e-5, acceleration_rad_s2=1e-5),
        scope='World-frame interval rotation logs and finite differences at 120 Hz. Original per-joint/span maxima; thresholds are declared diagnostic numerical comparisons, not validated naturalness or physiological limits. Position-only fitter is unchanged; this audit cannot grant approval.', quality_approved=False))
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        trials_sha256=sha256(output/'trials.json'), quality_approved=False))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('audit', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.audit, args.output)
