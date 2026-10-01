"""Compare full-clip absolute joint peaks, independently of window-only caps."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from sampled_motion_caps import features, measures
from absolute_rate_peaks import compare


def run(studies, output):
    studies = [Path(p).resolve() for p in studies]; output = Path(output).resolve()
    if len(studies) != 3 or len(set(studies)) != 3 or output.exists() or output.parent != ROOT/'reports':
        raise ValueError('Input, minimal floor lift, smoothed lift and fresh reports output required')
    files = {}; requests = []
    def bind(path, digest):
        key = str(path.resolve())
        if key in files and files[key] != digest:
            raise ValueError('Conflicting motion evidence')
        files[key] = digest
    for study in studies:
        q, r = read(study/'request.json'), read(study/'result.json'); requests.append(q)
        if r['status'] != 'complete' or not r['native_animation_exported']:
            raise ValueError('Complete native exports required')
        for path, digest in q['inputs'].items(): bind(Path(path), digest)
        for name in ('request.json', 'result.json'): bind(study/name, sha256(study/name))
        for parent, entries in ((study, r['outputs']), (study/'implementation', q['implementation'])):
            for name, digest in entries.items():
                path = (parent/name).resolve()
                if path.parent != parent: raise ValueError('Escaping source evidence')
                bind(path, digest)
    contract = lambda q: [q[k] for k in ('target', 'event_time_s', 'window_s', 'original_bins_s')]
    if any(contract(q) != contract(requests[0]) for q in requests[1:]):
        raise ValueError('Matching motion/contact intent required')
    def unchanged():
        for path, digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed full-clip rate evidence')
    unchanged(); output.mkdir(); archive = output/'implementation'; archive.mkdir(); methods = {}
    for name in (Path(__file__).name, 'sampled_motion_caps.py', 'absolute_rate_peaks.py',
                 'rig_clip_import.py', 'rig_asset.py', 'gltf_tools.py', 'strep.py'):
        path = ROOT/'scripts'/name; methods[name] = sha256(path); shutil.copyfile(path, archive/name)
    save(output/'request.json', dict(at=now(), studies=[str(p) for p in studies], inputs=files,
        implementation=methods, fps=120,
        scope='Exact uniform 120Hz full-clip samples within native duration. Fractional tail is excluded from derivatives and reported; original window caps are unchanged, not extrapolated. Full-key/event/floor checks remain separate.'))
    rows = []
    for actor in (0, 1):
        rigs = [RigAsset.load(p/f'candidate-{actor}.glb') for p in studies]
        samplers = [AnimationSampler(r.document, r.binary, 0) for r in rigs]
        duration = samplers[0].duration
        if any(s.duration != duration for s in samplers[1:]) or any(not np.array_equal(r.joints, rigs[0].joints) for r in rigs[1:]):
            raise ValueError('Matching duration and joint population required')
        times = np.arange(int(np.floor(duration*120))+1)/120
        values = [measures(features(np.array([s.sample(float(t)) for t in times]), r.joints), 1/120)
                  for r, s in zip(rigs, samplers)]
        row = dict(actor=actor, samples=len(times), duration_s=duration, last_sample_time_s=float(times[-1]),
                   excluded_fractional_tail_s=duration-float(times[-1]),
                   joint_names=[rigs[0].document['nodes'][n]['name'] for n in rigs[0].joints],
                   minimal_vs_input=compare(values[0], values[1]),
                   smoothed_vs_input=compare(values[0], values[2]),
                   smoothed_vs_minimal=compare(values[1], values[2]), quality_approved=False)
        save(output/f'actor-{actor}.json', row); rows.append(row)
    unchanged()
    if any(sha256(ROOT/'scripts'/n) != d for n, d in methods.items()):
        raise ValueError('Full-rate method changed during diagnosis')
    result = dict(at=now(), status='complete', actors=rows, original_window_motion_caps_changed=False,
                  continuous_rate_certified=False, quality_approved=False)
    result['outputs'] = {p.name: sha256(p) for p in output.iterdir() if p.is_file()}
    save(output/'result.json', result)
    print([dict(actor=r['actor'], samples=r['samples'],
                full_clip_absolute_peak_guard_pass=r['smoothed_vs_input']['absolute_peak_guard_pass']) for r in rows], flush=True)


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path); parser.add_argument('studies', type=Path, nargs=3)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.studies, args.output)
