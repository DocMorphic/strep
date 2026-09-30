"""Read-only projection refinement on declared saved-clip intervals."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from audit_interval_skin import load_protocol
from audit_adaptive_skin import adapter
from swept_triangle_separation import audit


def run(protocol_path, output, candidate_limit=20000):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh projection audit required')
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 1000000:
        raise ValueError('One to one million candidate pairs required')
    protocol, inputs, intervals, names, actors = load_protocol(protocol_path)
    if len(actors) != 2: raise ValueError('Two placed actors required')
    actors = [adapter(actor) for actor in actors]
    methods = ['audit_swept_triangle_separation.py', 'swept_triangle_separation.py',
        'audit_adaptive_skin.py', 'adaptive_surface_intervals.py', 'triangle_crossing.py',
        'convex_partner_surface.py', 'audit_interval_skin.py', 'skin_motion_bounds.py',
        'swept_surface_boxes.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    output.mkdir(); (output/'implementation').mkdir(); digests = {}
    for name in methods:
        path = ROOT/'scripts'/name; digests[name] = sha256(path)
        shutil.copyfile(path, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=digests,
        protocol=protocol, candidate_limit=candidate_limit, tolerance_m=1e-8, quality_approved=False))
    rows = []
    for start, end in intervals:
        bound = [actor['interval'](float(start), float(end)) for actor in actors]
        value = audit(bound[0], actors[0]['faces'], bound[1], actors[1]['faces'], candidate_limit=candidate_limit)
        rows.append(value); save(output/'intervals.json', rows)
        print(dict(interval=[float(start), float(end)], outcome=value['outcome'],
            candidates=value['candidate_pairs'], checked=value['checked_pairs']), flush=True)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Projection input changed')
    for name, digest in digests.items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
            raise ValueError('Projection method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        intervals_sha256=sha256(output/'intervals.json'), intervals=len(rows), actors=names,
        collision_free_certified=False, quality_approved=False,
        scope='Fixed-axis sufficient surface separation only, under supplied native-motion bounds. No animation edit, new sampling/containment screen, adaptive traversal, full-clock or quality approval.'))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--candidate-limit', type=int, default=20000); args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.protocol, args.output, args.candidate_limit)
