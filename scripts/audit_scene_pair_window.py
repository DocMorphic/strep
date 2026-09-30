"""Bind native-key immobility to completed source collision observations."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from paired_window_feasibility import fixed_collision_floor


def run(study, output):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native-window audit required')
    request, _, files = load_bound_study(study)
    _, actors = load_actors(Path(request['prepared_request']).parent)
    samples = [read(study/'source'/name) for name in read(study/'source-index.json')]
    result = fixed_collision_floor([a['model'] for a in actors], samples)
    output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in sorted(set(request['implementation']) | {'audit_scene_pair_window.py', 'paired_window_feasibility.py', 'diagnose_scene_pair_limits.py'}):
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name); methods[name] = sha256(output/'implementation'/name)
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, implementation=methods, quality_approved=False))
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Window-audit input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Window-audit method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'), **result))
    print({k:v for k,v in result.items() if k != 'fixed_samples'}, flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.study, args.output)
