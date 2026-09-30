"""Bound and subdivide explicit intervals in two saved actor clips."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from audit_interval_skin import load_protocol
from adaptive_surface_intervals import audit


def adapter(actor):
    def vertices(time):
        return actor['rig'].vertices(actor['sampler'].sample(time))@actor['rotation'].T+actor['translation']
    def interval(start, end):
        value = actor['bound'].interval(start, end)
        value['center_vertices'] = value['center_vertices']@actor['rotation'].T+actor['translation']
        return value
    return dict(faces=actor['faces'], vertices=vertices, interval=interval)


def run(protocol_path, output, max_depth=6, max_intervals=127):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh output directory required')
    if type(max_depth) is not int or not 0 <= max_depth <= 20 or type(max_intervals) is not int or not 1 <= max_intervals <= 4095:
        raise ValueError('Valid explicit depth and interval budgets required')
    protocol, inputs, intervals, names, actors = load_protocol(protocol_path)
    if len(actors) != 2: raise ValueError('Two placed actor clips required')
    actors = [adapter(actor) for actor in actors]
    methods = ['audit_adaptive_skin.py', 'audit_interval_skin.py', 'adaptive_surface_intervals.py',
        'skin_motion_bounds.py', 'swept_surface_boxes.py', 'triangle_crossing.py',
        'convex_partner_surface.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    output.mkdir(); (output/'implementation').mkdir(); digests = {}
    for name in methods:
        path = ROOT/'scripts'/name; digests[name] = sha256(path)
        shutil.copyfile(path, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=digests, protocol=protocol,
        max_depth=max_depth, max_intervals_per_root=max_intervals, tolerance_m=1e-8, quality_approved=False))
    results = []
    for index, (start, end) in enumerate(intervals):
        def progress(node):
            save(output/'progress.json', dict(at=now(), root=index, **node))
            print(dict(root=index, depth=node['depth'], outcome=node['outcome']), flush=True)
        value = audit(*actors, float(start), float(end), max_depth=max_depth,
                      max_intervals=max_intervals, observe=progress)
        name = f'interval-{index:03d}.json'; save(output/name, value)
        results.append(dict(start_s=float(start), end_s=float(end), path=name, sha256=sha256(output/name),
            outcome=value['outcome'], leaf_counts=value['leaf_counts'], evaluated_intervals=value['evaluated_intervals'],
            inspected_poses=len(value['poses']), entire_partition_has_surface_bounds=value['entire_partition_has_surface_bounds']))
        save(output/'intervals.json', results)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Bound input changed during adaptive audit')
    for name, digest in digests.items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
            raise ValueError('Adaptive audit implementation changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        intervals_sha256=sha256(output/'intervals.json'), intervals=len(results), actors=names,
        collision_free_certified=False, quality_approved=False,
        scope='Complete partitions of requested intervals only. Crossing or interior-vertex observations are local witnesses; surface bounds and sampled containment do not certify continuous volumetric clearance, self-collision or animation quality. Budget leaves remain unresolved.'))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--max-depth', type=int, default=6)
    parser.add_argument('--max-intervals', type=int, default=127)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1):
        run(args.protocol, args.output, args.max_depth, args.max_intervals)
