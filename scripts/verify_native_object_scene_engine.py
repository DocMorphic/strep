"""Replay combined engine skin/contact observations and saved geometry reductions.

This is a read-only evidence check. It does not repeat geometry queries, run an
engine, render, establish reviewer independence, or approve motion quality.
"""
import argparse
import hashlib
from itertools import combinations
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_object_scene_engine import load, method_bindings, require, METHODS
from native_scene_engine import SKIN_POSITION_TOLERANCE
from native_object_asset import POSITION_LIMIT_M, BASIS_LIMIT
from native_scene_geometry import faces_for, policy_for
from engine_contact_sampling import contract_sha256

FILES = ('default-import-contacts.json', 'native-authoring-contacts.json',
         'geometry.json', 'geometry-observations.npz', 'observations.npz')


def geometry_reductions(scene, policy, digest, times, report, saved):
    """Check every declared population and saved triangle-array reduction.

    Containment and partner query outputs remain retained measurements, not
    independently re-queried geometry. No decision flags are trusted alone.
    """
    required, populations, _ = policy_for(policy, scene, digest)
    require(np.isin(required, times).all(), 'Geometry clock missing from engine observations')
    times = required  # Explicit policies may declare fewer times than contact sampling.
    require(report['schema'] == 'strep-native-scene-geometry-result-v1' and report['status'] == 'complete', 'Complete geometry required')
    require(report['times_s'] == times.tolist() and len(report['samples']) == len(times), 'Complete geometry samples required')
    require(report['limits'] == policy['limits'] and report['declared_planes'] == list(policy['planes']), 'Geometry policy differs')
    require(report['clock_mode'] == policy['clock']['mode'] and report['frame_contract_sha256'] == contract_sha256(), 'Geometry frame contract differs')
    expected_populations = [dict(id=p['id'], rate_hz=p['rate_hz'], phase_offset_frames=p['phase_offset_frames'], times_s=p['times_s'].tolist()) for p in populations]
    require(report['frame_populations'] == expected_populations, 'Geometry frame populations differ')
    faces = {}
    for name, actor in scene.actors.items():
        faces[name], primitives = faces_for(actor['rig'])
        topology = dict(vertices=sum(len(p['positions']) for p in actor['rig'].primitives), faces=len(faces[name]),
            faces_sha256=hashlib.sha256(faces[name].astype('<i8').tobytes()).hexdigest(), primitives=primitives)
        require(report['topology'].get(name) == topology, 'Geometry topology differs')
    require(set(report['topology']) == set(scene.actors), 'Geometry actor population differs')
    require(np.array_equal(saved['times_s'], times), 'Saved geometry clock differs')
    expected = {'times_s'}; overall = True; observations = 0; maximum = 0.
    object_pairs = [(a, o) for a in scene.actors for o in scene.objects]
    actor_pairs = [list(p) for p in combinations(scene.actors, 2)]
    plane_pairs = [(a, p) for a in scene.actors for p in policy['planes']]
    limit = policy['limits']['penetration_m']; tolerance = policy['limits']['surface_tolerance_m']
    for i, sample in enumerate(report['samples']):
        require(sample['time_s'] == times[i], 'Geometry sample time differs')
        require(set(sample['volumes']) == set(sample['degenerate_faces']) == set(scene.actors), 'Complete actor states required')
        require([(r['actor'], r['object']) for r in sample['actor_objects']] == object_pairs, 'Complete actor/object population required')
        require([r['actors'] for r in sample['actor_pairs']] == actor_pairs, 'Complete partner population required')
        require([(r['actor'], r['plane']) for r in sample['world_planes']] == plane_pairs, 'Complete plane population required')
        for name, indices in sample['degenerate_faces'].items():
            require(isinstance(indices, list) and all(type(j) is int and 0 <= j < len(faces[name]) for j in indices)
                    and len(indices) == len(set(indices)), 'Invalid degenerate face population')
        for row in sample['actor_objects']:
            prefix = f'frame_{i}_{row["actor"]}_{row["object"]}'
            names = [prefix + suffix for suffix in ('_depth_lower_m', '_depth_upper_m', '_witness_world_m')]
            expected.update(names); low, high, witnesses = [saved[n] for n in names]; count = len(faces[row['actor']])
            require(low.shape == high.shape == (count,) and witnesses.shape == (count, 3), 'Complete triangle observations required')
            require(np.isfinite(low).all() and np.isfinite(high).all() and np.isfinite(witnesses).all()
                    and (low >= 0).all() and (high >= low).all(), 'Invalid triangle observations')
            peak = int(low.argmax())
            require(row['total_faces'] == count and row['peak_lower_face'] == peak
                    and row['maximum_depth_lower_m'] == float(low.max()) and row['maximum_depth_upper_m'] == float(high.max())
                    and row['peak_lower_witness_world_m'] == witnesses[peak].tolist(), 'Triangle reductions differ')
            require(row['primitive_bounding_radius_m'] == scene.objects[row['object']]['geometry'].bounding_radius(), 'Object geometry differs')
            require(type(row['candidate_faces']) is int and 0 <= row['candidate_faces'] <= count
                    and np.isfinite(row['floating_reserve_m']) and row['floating_reserve_m'] >= 0, 'Invalid query summary')
            containment = row['containment']; distance = containment['signed_center_distance_m']
            if sample['volumes'][row['actor']]['containment_available']:
                require(distance is not None and np.isfinite(distance), 'Missing containment observation')
                status = 'inside' if distance > tolerance else ('outside' if distance < -tolerance else 'near-surface')
            else:
                require(distance is None, 'Unavailable containment has a distance'); status = 'unavailable'
            require(containment['status'] == status, 'Containment reduction differs')
            passed = bool(high.max() <= limit and not sample['degenerate_faces'][row['actor']] and status == 'outside')
            require(row['passed'] is passed, 'Actor/object decision differs')
            observations += 1; maximum = max(maximum, float(high.max()))
        for row in sample['actor_pairs']:
            left, right = row['actors']; depths = row['vertex_containment']
            require([(d['source'], d['target']) for d in depths] == [(left, right), (right, left)], 'Complete partner containment required')
            for d in depths:
                require(d['available'] is sample['volumes'][d['target']]['containment_available'], 'Partner availability differs')
                if d['available']:
                    require(d['count_tolerance_m'] == max(limit, 1e-12) and np.isfinite(d['max_depth_m']) and d['max_depth_m'] >= 0, 'Invalid partner depth')
            passed = bool(not row['surface']['records'] and not sample['degenerate_faces'][left]
                and not sample['degenerate_faces'][right] and all(d['available'] and d['max_depth_m'] <= limit for d in depths))
            require(row['passed'] is passed, 'Partner decision differs')
        for row in sample['world_planes']:
            require(np.isfinite(row['maximum_depth_m']) and row['maximum_depth_m'] >= 0
                    and type(row['peak_vertex']) is int and row['peak_vertex'] in faces[row['actor']], 'Invalid plane reduction')
            require(row['passed'] is bool(row['maximum_depth_m'] <= limit and not sample['degenerate_faces'][row['actor']]), 'Plane decision differs')
        conditions = sample['actor_objects'] + sample['actor_pairs'] + sample['world_planes']
        passed = bool(conditions and all(r['passed'] for r in conditions) and not any(sample['degenerate_faces'].values()))
        require(sample['conditions_available'] is bool(conditions) and sample['passed'] is passed, 'Sample decision differs')
        overall &= passed
    require(set(saved.files) == expected, 'Saved geometry population differs')
    require(report['sampled_conditions_pass'] is overall, 'Geometry decision differs')
    return dict(samples=len(times), actor_object_observations=observations, maximum_depth_upper_m=maximum,
                passed=overall, geometry_queries_rerun=False)


def run(contacts, policy_path, actor_dir, object_dir, combined_dir, output):
    combined_dir, output = [Path(p).resolve() for p in (combined_dir, output)]
    require(not output.exists(), 'Fresh verification output required')
    with worker_lock(), threadpool_limits(limits=1):
        require(read(combined_dir/'pipeline.json')['status'] == 'complete', 'Combined producer must be terminal')
        result = read(combined_dir/'result.json'); require(result['status'] == 'complete', 'Complete combined result required')
        method_bindings(combined_dir, result, METHODS)
        require(set(result['files_sha256']) == set(FILES), 'Complete combined receipts required')
        receipts = {str(combined_dir/n): sha256(combined_dir/n) for n in FILES + ('result.json', 'pipeline.json')}
        for n in FILES: require(receipts[str(combined_dir/n)] == result['files_sha256'][n], 'Combined file changed: '+n)
        scene, policy, actor, providers, times, bindings = load(contacts, policy_path, actor_dir, object_dir)
        require(result['source_bindings_sha256'] == bindings and result['samples'] == len(times), 'Combined source binding differs')
        output.mkdir(parents=True); shutil.copyfile(__file__, output/'verifier.py')
        try:
            arrays = {'times_s': times}; skin = {}; reports = {}; objects = {}
            save(output/'pipeline.json', dict(status='processing', stage='replay-full-skin-and-contacts', original_selected=True))
            for name, entry in scene.actors.items():
                p, r = entry['placement']; values = []
                for t in times:
                    native = entry['rig'].vertices(entry['sampler'].sample(float(t))) @ r.T + p
                    values.append(float(np.linalg.norm(actor.actor_vertices(name, float(t)) - native, axis=1).max()))
                arrays[name+'_skin_errors_m'] = np.asarray(values)
                skin[name] = dict(maximum_position_error_m=max(values), limit_m=SKIN_POSITION_TOLERANCE, passed=max(values)<=SKIN_POSITION_TOLERANCE)
            require(skin == result['skin_errors'] and actor.reports == result['actor_pose_reports'], 'Imported skin/pose reports differ')
            for mode, provider in providers.items():
                report, data = scene.evaluate(actor_points=actor.actor_points, object_poses=provider.object_poses)
                report.update(loaded_skin_weights_normalized=False, measurement_source='Complete imported CPU skin and actual saved object Animation resource poses')
                require(report == read(combined_dir/(mode+'-contacts.json')), 'Replayed contact report differs')
                reports[mode] = report; arrays.update({mode+'_'+k: v for k,v in data.items()}); objects[mode] = {}
                for name in scene.objects:
                    p,r=scene.object_poses(name,times); q,s=provider.object_poses(name,times)
                    position=float(np.linalg.norm(q-p,axis=1).max()); basis=float(abs(s-r).max())
                    objects[mode][name]=dict(maximum_position_error_m=position, maximum_basis_error=basis, passed=position<=POSITION_LIMIT_M and basis<=BASIS_LIMIT)
            require(objects == result['object_pose_reports'] and {m:r['passed'] for m,r in reports.items()} == result['contacts_pass'], 'Object/contact decisions differ')
            with np.load(combined_dir/'observations.npz', allow_pickle=False) as saved:
                require(set(saved.files) == set(arrays), 'Complete replay observations required')
                for n,v in arrays.items(): require(np.array_equal(v,saved[n]), 'Replayed observations differ: '+n)
            with np.load(combined_dir/'geometry-observations.npz', allow_pickle=False) as saved:
                geometry = geometry_reductions(scene, policy, sha256(contacts), times, read(combined_dir/'geometry.json'), saved)
            native,_ = scene.evaluate()
            passed = bool(native['passed'] and reports['native-authoring']['passed'] and geometry['passed']
                and all(r['pose_samples_pass'] for r in actor.reports.values()) and all(r['passed'] for r in skin.values())
                and all(r['passed'] for r in objects['native-authoring'].values()))
            require(result['source_contacts_pass'] is native['passed'] and result['geometry_pass'] is geometry['passed']
                    and result['all_sampled_conditions_pass'] is passed, 'Combined decision differs')
            scene.check_inputs(); load(contacts,policy_path,actor_dir,object_dir); method_bindings(combined_dir,result,METHODS)
            for p,h in {**bindings,**receipts}.items(): require(sha256(p)==h, 'Verification input changed')
            require(sha256(__file__)==sha256(output/'verifier.py'), 'Verifier changed')
            verified = dict(at=now(), status='complete', samples=len(times), all_replayed_observations_exact=True,
                recorded_sampled_conditions_pass=passed, geometry_reductions=geometry, source_bindings_sha256=bindings,
                combined_files_sha256=receipts, producer_implementation_sha256=result['implementation_sha256'],
                verifier_sha256=sha256(__file__), original_selected=True, quality_approved=False, training_admitted=False,
                release_approved=False, gpu_render_checked=False, physics_verified=False, real_time_playback_verified=False,
                scope='Replay all imported skin/contact/object pose observations and complete saved geometry reductions. Geometry query/containment/partner/plane measurements are not independently rerun. No human-quality or release approval.')
            save(output/'result.json',verified); save(output/'pipeline.json',dict(status='complete',original_selected=True)); return verified
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True)); raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('contacts','policy','actor_engine','object_engine','combined_engine','output'): parser.add_argument(n,type=Path)
    a=parser.parse_args(); run(a.contacts,a.policy,a.actor_engine,a.object_engine,a.combined_engine,a.output)
