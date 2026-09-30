"""Independent selected-export angular evidence required before Studio publication."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from scalar_angular_replay import angular_replay


METHODS = ['verify_scene_pair_angular.py', 'scalar_angular_replay.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Preserve previous angular replay')
    result, request = read(study/'result.json'), read(study/'request.json')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Completed bound fit required')
    prepared_path = Path(request['prepared_request']).resolve(); prepared = read(prepared_path)
    if request['inputs'].get(str(prepared_path)) != sha256(prepared_path): raise ValueError('Original angular policy is unbound')
    files = {str(study/'result.json'):sha256(study/'result.json'), str(study/'request.json'):sha256(study/'request.json')}
    for path,digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Fitting input changed')
        files[path] = digest
    selected = result['selected']; trial = None
    if selected is not None:
        path = study/'trials.json'
        if sha256(path) != result['trials_sha256']: raise ValueError('Fitting trials changed')
        files[str(path)] = sha256(path)
        matches = [t for t in read(path) if t['folder'] == selected]
        if len(matches) != 1: raise ValueError('Distinct selected trial required')
        trial = matches[0]
        if [a['actor'] for a in trial['actors']] != list(prepared['actors']): raise ValueError('Matching ordered actors required')
    output.mkdir(); (output/'implementation').mkdir()
    for name in METHODS: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    methods = {n:sha256(output/'implementation'/n) for n in METHODS}
    protocol = dict(at=now(), study_request_sha256=sha256(study/'request.json'), study_result_sha256=sha256(study/'result.json'),
        selected=selected, inputs=files, implementation=methods, tolerance=1e-5, quality_approved=False)
    save(output/'request.json', protocol); reviews = []
    if trial is not None:
        times = np.asarray(prepared['sample_times_seconds']); knots = prepared['authored']['knots_s']
        for entry, (name, source) in zip(trial['actors'], prepared['actors'].items()):
            source_path = (prepared_path.parent/source['path']).resolve()
            target_path = (study/selected/entry['path']).resolve()
            if not source_path.is_relative_to(prepared_path.parent) or not target_path.is_relative_to(study): raise ValueError('Clip path escapes bound evidence')
            if sha256(source_path) != source['sha256'] or sha256(target_path) != entry['sha256']: raise ValueError('Angular replay clip changed')
            files[str(source_path)] = source['sha256']; files[str(target_path)] = entry['sha256']
            rigs = [RigAsset.load(p) for p in [source_path, target_path]]
            if rigs[0].joints != rigs[1].joints: raise ValueError('Angular replay joint population changed')
            rotations = []
            for rig in rigs:
                sampler = AnimationSampler(rig.document, rig.binary, 0)
                rotations.append(np.array([sampler.sample(t)[rig.joints, :3, :3] for t in times]))
            rates = angular_replay(*rotations, times, knots, tolerance=1e-5)
            reviews.append(dict(actor=name, source_sha256=source['sha256'], candidate_sha256=entry['sha256'],
                joints=len(rigs[0].joints), samples=len(times), rates=rates))
    save(output/'request.json', protocol)
    for path,digest in files.items():
        if sha256(path) != digest: raise ValueError('Angular input changed during replay')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Angular replay method changed')
    save(output/'verification.json', dict(at=now(), status='complete', selected=selected, request_sha256=sha256(output/'request.json'),
        actors=reviews, passed=bool(reviews) and all(v['exceeding_observations'] == 0 for r in reviews for v in r['rates'].values()),
        quality_approved=False, scope='Selected GLB replay using per-joint quaternion composition and immutable original-span caps. No collision, engine, visual or release approval.'))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('study', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    with threadpool_limits(limits=1): run(a.study, a.output)
