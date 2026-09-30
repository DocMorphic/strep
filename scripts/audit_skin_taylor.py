"""Compare motion balls with synchronized Taylor bounds on saved GLB intervals."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from strep import ROOT, save, sha256, now
from audit_interval_skin import load_protocol
from skin_taylor_bounds import SkinTaylorBounds
from swept_triangle_separation import audit


def placed_bound(actor, start, end):
    value = actor['bound'].interval(start, end)
    value['center_vertices'] = value['center_vertices']@actor['rotation'].T+actor['translation']
    value['center_velocities'] = value['center_velocities']@actor['rotation'].T
    return value


def run(protocol_path, output, candidate_limit=20000):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh Taylor audit output required')
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 1000000:
        raise ValueError('Valid explicit candidate budget required')
    protocol, inputs, intervals, names, actors = load_protocol(protocol_path)
    if len(actors) != 2: raise ValueError('Two placed actors required')
    for actor in actors: actor['bound'] = SkinTaylorBounds(actor['rig'], actor['sampler'])
    # Fail before starting if any interval crosses a velocity discontinuity.
    for start, end in intervals:
        for actor in actors:
            if np.any((actor['bound'].knots > start) & (actor['bound'].knots < end)):
                raise ValueError('Protocol intervals must split at native knots')
    methods = ['audit_skin_taylor.py', 'skin_taylor_bounds.py', 'skin_motion_bounds.py',
        'audit_interval_skin.py', 'swept_triangle_separation.py', 'swept_surface_boxes.py',
        'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    output.mkdir(); (output/'implementation').mkdir(); digests = {}
    for name in methods:
        path = ROOT/'scripts'/name; digests[name] = sha256(path)
        shutil.copyfile(path, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=digests, protocol=protocol,
        replay_samples_per_actor_interval=17, candidate_limit=candidate_limit, tolerance_m=1e-8, quality_approved=False))
    rows = []; started = time.perf_counter()
    for index, (start, end) in enumerate(intervals):
        bounds = []; observations = []
        for name, actor in zip(names, actors):
            value = placed_bound(actor, float(start), float(end)); maximum = 0.
            for stamp in np.linspace(start, end, 17):
                points = actor['rig'].vertices(actor['sampler'].sample(float(stamp)))@actor['rotation'].T+actor['translation']
                predicted = value['center_vertices']+(stamp-value['center_s'])*value['center_velocities']
                error = np.linalg.norm(points-predicted, axis=1)
                if np.any(error > value['remainder_radius_m']): raise ValueError('Actual skin exceeded Taylor remainder')
                maximum = max(maximum, float((error/value['remainder_radius_m']).max()))
            observations.append(dict(actor=name, vertices=len(value['radius_m']), decoded_replay_samples=17,
                maximum_observed_remainder_ratio=maximum, all_replayed_vertices_inside=True,
                maximum_remainder_radius_m=float(value['remainder_radius_m'].max()),
                maximum_original_radius_m=float(value['radius_m'].max())))
            bounds.append(value)
        compared = {model: audit(bounds[0], actors[0]['faces'], bounds[1], actors[1]['faces'],
            candidate_limit=candidate_limit, motion_model=model) for model in ('balls', 'taylor')}
        if compared['balls']['candidate_pairs'] != compared['taylor']['candidate_pairs']:
            raise ValueError('Matched broad-phase candidates changed')
        rows.append(dict(start_s=float(start), end_s=float(end), actors=observations, comparisons=compared))
        save(output/'intervals.json', rows)
        print(dict(interval=index, time=[float(start), float(end)], candidates=compared['taylor']['candidate_pairs'],
            balls=compared['balls']['outcome'], taylor=compared['taylor']['outcome']), flush=True)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Taylor audit input changed')
    for name, digest in digests.items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
            raise ValueError('Taylor audit method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        intervals_sha256=sha256(output/'intervals.json'), intervals=len(rows), elapsed_s=time.perf_counter()-started,
        actor_pose_replays=17*2*len(rows), collision_free_certified=False, quality_approved=False,
        scope='Matched saved-clip projection comparison and decoded skin replay only. Sample containment of Taylor remainders is not a continuous proof. No new collision/containment observations, animation edits, self-collision or release approval.'))


if __name__ == '__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--candidate-limit', type=int, default=20000); args = parser.parse_args()
    with worker_lock(), threadpool_limits(limits=1): run(args.protocol, args.output, args.candidate_limit)
