"""Read-only acceleration-aware diagnosis of a saved stationary contact plan."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import scipy
from scipy.sparse import save_npz
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from contact_rate_feasibility import analyze
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from contact_timing_job import validate_options


def run(source, spec_path, reference_path, window, output):
    source, spec_path, reference_path, output = map(Path, [source, spec_path, reference_path, output])
    spec, reference = read(spec_path), read(reference_path)
    validate_options(dict(edit_window=window), spec, spec['frame_count'])
    pins = [(name, p) for name, entry in spec['regions'].items() if entry['mode'] == 'explicit' for p in entry['segments']]
    if any(type(p.get('vertex_id')) is not int or p['vertex_id'] < 0 for _, p in pins):
        raise ValueError('Saved material vertex bindings required')
    vertices = sorted({p['vertex_id'] for _, p in pins})
    rig = RigAsset.load(source);clock = AnimationSampler(rig.document, rig.binary, 0)
    frames = spec['frame_count']
    if abs(clock.duration-(frames-1)/30) > 1e-5:
        raise ValueError('Source export and declared frame count differ')
    inputs = {str(p.resolve()): sha256(p) for p in [source, spec_path, reference_path]}
    methods = {name: sha256(ROOT/'scripts'/name) for name in
        ['study_contact_rate_feasibility.py', 'contact_rate_feasibility.py', 'rig_asset.py',
         'rig_clip_import.py', 'gltf_tools.py', 'contact_timing_job.py', 'strep.py']}
    output.mkdir(parents=True, exist_ok=False);(output/'implementation').mkdir()
    for name in methods:shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'protocol.json', dict(inputs=inputs, implementation=methods, window=window,
        scipy_version=scipy.__version__, numpy_version=np.__version__, created_at=now(),
        source='Decoded GLB at every quarter frame; same full-mesh vertex sampler as exported contact audit.',
        diagnostic_row_reserve_m=1e-12, outside_position_budget_m=1e-6, pin_tolerance_m=.005,
        quality_approved=False))
    try:
        save(output/'pipeline.json', dict(status='sampling', at=now()))
        with threadpool_limits(limits=1):
            track = np.array([rig.vertices(clock.sample(i/120))[vertices] for i in range((frames-1)*4+1)])
            np.savez(output/'source-points.npz', vertices=vertices, positions=track)
            records=[]
            for index, vertex in enumerate(vertices):
                save(output/'pipeline.json', dict(status='linear_diagnosis', vertex=vertex, at=now()))
                point_pins = [p for _, p in pins if p['vertex_id'] == vertex]
                rows = [r for r in reference['rows'] if r['vertex_id'] == vertex]
                report, arrays = analyze(track[:, index], point_pins, rows, window)
                folder = output/str(vertex);folder.mkdir()
                save_npz(folder/'constraints.npz', arrays.pop('matrix'))
                np.savez(folder/'arrays.npz', **arrays)
                report.update(vertex_id=vertex, regions=sorted({name for name, p in pins if p['vertex_id'] == vertex}))
                save(folder/'report.json', report);records.append(report)
        for name, digest in inputs.items():
            if sha256(Path(name)) != digest:raise ValueError('Diagnostic input changed')
        for name, digest in methods.items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                raise ValueError('Diagnostic method changed')
        save(output/'pipeline.json', dict(status='complete', at=now()))
        result = dict(points=records, any_verified_conflict=any(r['any_verified_conflict'] for r in records),
            quality_approved=False, source_motion_changed=False,
            files={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()})
        save(output/'completion.json', result)
        return result
    except BaseException as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc), at=now()));raise


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--window', type=int, nargs=2, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'reports').resolve()):parser.error('Keep outputs under reports')
    with worker_lock():
        report = run(args.source, args.spec, args.reference, args.window, args.output)
    print(dict(any_verified_conflict=report['any_verified_conflict'], quality_approved=False))
