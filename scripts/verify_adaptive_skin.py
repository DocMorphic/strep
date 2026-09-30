"""Check retained crossing witnesses with independent barycentric feasibility."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from audit_interval_skin import load_protocol
from verify_triangle_scene import interior_witness
from convex_partner_surface import penetration


def run(study, protocol_path, output):
    study, protocol_path, output = map(lambda p: Path(p).resolve(), [study, protocol_path, output])
    if output.exists(): raise ValueError('Fresh verification directory required')
    result, request = read(study/'result.json'), read(study/'request.json')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(study/'request.json') or result['intervals_sha256'] != sha256(study/'intervals.json'):
        raise ValueError('Completed bound adaptive audit required')
    if request['inputs'].get(str(protocol_path)) != sha256(protocol_path) or read(protocol_path) != request['protocol']:
        raise ValueError('Exact bound protocol required')
    inputs = dict(request['inputs'])
    for name in ['result.json', 'request.json', 'intervals.json']: inputs[str(study/name)] = sha256(study/name)
    for name, digest in request['implementation'].items(): inputs[str(study/'implementation'/name)] = digest
    for name in ['audit_interval_skin.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']:
        if sha256(ROOT/'scripts'/name) != request['implementation'][name]: raise ValueError('Changed decoding method')
    def verify():
        for path, digest in inputs.items():
            if sha256(path) != digest: raise ValueError('Changed bound verification input: '+path)
    verify()
    protocol, _, intervals, names, actors = load_protocol(protocol_path)
    summaries = read(study/'intervals.json')
    if len(summaries) != len(intervals): raise ValueError('Complete root interval population required')
    output.mkdir(); (output/'implementation').mkdir()
    methods = ['verify_adaptive_skin.py', 'verify_triangle_scene.py', 'convex_partner_surface.py',
               'audit_interval_skin.py', 'skin_motion_bounds.py', 'swept_surface_boxes.py',
               'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    for name in methods:
        path = ROOT/'scripts'/name; inputs[str(path)] = sha256(path)
        shutil.copyfile(path, output/'implementation'/name)
    checks = []
    for index, (summary, interval) in enumerate(zip(summaries, intervals)):
        path = (study/summary['path']).resolve()
        if path.parent != study or sha256(path) != summary['sha256']: raise ValueError('Changed interval result')
        inputs[str(path)] = summary['sha256']; record = read(path); leaves = record['leaves']
        if [record['start_s'], record['end_s']] != interval.tolist() or not leaves:
            raise ValueError('Root interval mismatch')
        if (leaves[0]['start_s'] != interval[0] or leaves[-1]['end_s'] != interval[1]
                or any(row['start_s'] >= row['end_s'] for row in leaves)
                or any(a['end_s'] != b['start_s'] for a, b in zip(leaves[:-1], leaves[1:]))):
            raise ValueError('Incomplete terminal partition')
        for pose in record['poses']:
            if pose['outcome'] != 'crossing_observed': continue
            stamp = pose['time_s']; witness = pose['crossing_witness']
            if not interval[0] <= stamp <= interval[1]: raise ValueError('Witness outside requested interval')
            points = [actor['rig'].vertices(actor['sampler'].sample(stamp))@actor['rotation'].T+actor['translation'] for actor in actors]
            pair = [witness['left_triangle'], witness['right_triangle']]
            triangles = [p[actor['faces'][number]] for p, actor, number in zip(points, actors, pair)]
            proof = interior_witness(*triangles)
            passed = proof['feasible'] and proof['minimum_barycentric_weight'] > 1e-8 and proof['max_scaled_equality_error'] <= 1e-8
            depths = [penetration(points[a], points[b], actors[b]['faces']) for a, b in [(0, 1), (1, 0)]]
            checks.append(dict(interval=index, time_s=stamp, triangle_pair=pair, passed=passed, proof=proof,
                full_vertex_depths=depths,
                crossing_with_vertex_depth_at_most_1e_minus_8_m=bool(passed and max(row['max_depth_m'] for row in depths) <= 1e-8)))
            save(output/'checks.json', checks)
            print(dict(interval=index, time_s=stamp, passed=passed, vertex_depths_m=[d['max_depth_m'] for d in depths]), flush=True)
    if not checks: save(output/'checks.json', [])
    verify()
    save(output/'result.json', dict(at=now(), status='complete', inputs=inputs,
        checks_sha256=sha256(output/'checks.json'), checked_crossing_witnesses=len(checks),
        failed=sum(not row['passed'] for row in checks), all_root_partitions_complete=True,
        quality_approved=False, collision_free_certified=False,
        scope='Independent common strict-interior point for each retained first crossing witness, plus full-vertex depth at those same poses. Other counted crossings, false negatives, surface bounds, self-collision and full-clock quality are not certified.'))
    if any(not row['passed'] for row in checks): raise ValueError('Crossing witness failed independent verification')


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('protocol', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.study, args.protocol, args.output)
