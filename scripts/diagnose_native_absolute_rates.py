"""Read-only absolute-rate comparison against direct input or a matched alternative."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(study, output, baseline=None):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import features, measures
    from absolute_rate_peaks import compare
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh absolute-rate diagnostic output required')
    q, result = read(study/'request.json'), read(study/'result.json')
    if result['status'] != 'complete' or not result['native_animation_exported']:
        raise ValueError('Completed native exports required')
    files = dict(q['inputs']); files[str(study/'result.json')] = sha256(study/'result.json')
    for name, digest in result['outputs'].items():
        path = (study/name).resolve()
        if path.parent != study: raise ValueError('Escaping study output')
        files[str(path)] = digest
    for name, digest in q['implementation'].items():
        path = (study/'implementation'/name).resolve()
        if path.parent != study/'implementation': raise ValueError('Escaping method archive')
        files[str(path)] = digest
    compared_source = Path(q['source'])
    if baseline is not None:
        compared_source = Path(baseline).resolve()
        if compared_source == study: raise ValueError('Distinct completed comparison required')
        bq, br = read(compared_source/'request.json'), read(compared_source/'result.json')
        if br['status'] != 'complete' or not br['native_animation_exported']:
            raise ValueError('Completed native comparison exports required')
        if Path(bq['source']).resolve() != Path(q['source']).resolve() or bq['uniform_times_s'] != q['uniform_times_s']:
            raise ValueError('Matched source and audit clock required for alternative comparison')
        extra = dict(bq['inputs']); extra[str(compared_source/'result.json')] = sha256(compared_source/'result.json')
        for name, digest in br['outputs'].items():
            path = (compared_source/name).resolve()
            if path.parent != compared_source: raise ValueError('Escaping comparison output')
            extra[str(path)] = digest
        for name, digest in bq['implementation'].items():
            path = (compared_source/'implementation'/name).resolve()
            if path.parent != compared_source/'implementation': raise ValueError('Escaping comparison method')
            extra[str(path)] = digest
        for path, digest in extra.items():
            if path in files and files[path] != digest: raise ValueError('Conflicting bound comparison evidence')
            files[path] = digest
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Changed source evidence')
    times = np.asarray(q['uniform_times_s'], float)
    if times.ndim != 1 or len(times) < 3 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or not np.allclose(np.diff(times), times[1]-times[0], atol=1e-12, rtol=0):
        raise ValueError('Uniform original audit clock required')
    rows = []
    for actor in range(2):
        rates = []; identities = []
        for folder in (compared_source, study):
            path = folder/f'candidate-{actor}.glb'
            if files.get(str(path)) != sha256(path): raise ValueError('Unbound compared actor')
            rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
            identities.append([(n, rig.document['nodes'][n]['name']) for n in rig.joints])
            rates.append(measures(features(np.array([reader.sample(t) for t in times]), rig.joints), float(times[1]-times[0])))
        if identities[0] != identities[1]: raise ValueError('Compared joint identity changed')
        report = compare(*rates); report.update(actor=actor, joints=identities[0])
        for row in report['rates']: row['worst_joint'] = identities[0][row['worst_column']]
        rows.append(report)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(q['implementation']) | {'absolute_rate_peaks.py', Path(__file__).name}):
        methods[name] = sha256(ROOT/'scripts'/name); shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), source=str(study), comparison_baseline=str(compared_source), inputs=files, implementation=methods,
        times_s=times.tolist(), tolerance=1e-7, scope='Absolute per-joint rate peaks over the same uniform audit interval. Separate from excess over changing reference caps; no animation modification.'))
    save(output/'comparison.json', dict(actors=rows, absolute_peak_guards_pass=all(r['absolute_peak_guard_pass'] for r in rows), quality_approved=False))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Evidence changed during diagnosis')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Method changed during diagnosis')
    save(output/'result.json', dict(at=now(), status='complete', outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        animations_modified=False, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--baseline', type=Path, help='Optional completed alternative with the same source and audit clock')
    args = parser.parse_args(); run(args.study, args.output, args.baseline)
