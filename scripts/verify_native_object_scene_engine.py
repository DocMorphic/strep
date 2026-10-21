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
from native_scene_geometry import faces_for, policy_for, SELF_METHOD, CONTAINMENT_METHOD
from engine_contact_sampling import contract_sha256
from native_observation_archive import verify as verify_transport

FILES = ('default-import-contacts.json', 'native-authoring-contacts.json',
         'geometry.json', 'geometry-observations.npz', 'geometry-observations.npz.receipt.json', 'observations.npz')


def self_surface_reductions(sample, topology, tolerance):
    """Reduce retained self-surface evidence; do not claim to repeat queries."""
    audits = sample.get('self_surfaces')
    require(isinstance(audits, dict) and set(audits) == set(topology), 'Complete self-surface actor population required')
    eligible = True
    for name, audit in audits.items():
        shape = topology[name]
        require(audit['schema'] == 'strep-native-self-surface-v1' and audit['status'] == 'complete'
            and audit['method'] == SELF_METHOD and audit['complete_triangle_population'] is True
            and audit['vertices'] == shape['vertices'] and audit['triangles'] == shape['faces']
            and audit['faces_sha256'] == shape['faces_sha256'] and audit['tolerance_m'] == tolerance,
            'Matching complete self-surface topology and method required')
        counts = audit['counts']; pairs = audit['candidate_pairs']
        require(type(pairs) is int and 0 <= pairs <= audit['maximum_pairs']
            and all(type(n) is int and n >= 0 for n in counts.values()) and sum(counts.values()) == pairs,
            'Complete self-surface pair counts required')
        records = audit['records']; seen = set(); proper = 0; ambiguous = False
        require(isinstance(records, list) and len(records) <= audit['maximum_records'], 'Complete self-surface records required')
        for row in records:
            left, right = row['left_triangle'], row['right_triangle']
            require(type(left) is int and type(right) is int and 0 <= left < right < shape['faces']
                and (left, right) not in seen, 'Distinct original self-surface pairs required')
            seen.add((left, right)); kind = row['kind']
            require(kind in ('proper_crossing', 'coplanar_or_near_parallel_overlap', 'boundary_or_near_contact'),
                'Explicit self-surface relation required')
            if kind == 'proper_crossing':
                length = row['overlap_length_m']
                require(type(length) in (int, float) and np.isfinite(length) and length > 0, 'Positive self-crossing interval required')
                proper += 1
            else:
                ambiguous = True
        require(proper == counts.get('proper_crossing', 0)
            and audit['has_observed_transverse_crossings'] is bool(proper)
            and audit['has_ambiguous_surface_records'] is ambiguous, 'Self-surface reductions differ')
        require(audit['degenerate_faces'] == sample['degenerate_faces'][name], 'Self-surface degenerate population differs')
        clean = not records and not audit['degenerate_faces']
        state = sample['volumes'][name]
        available = bool(state['watertight'] and state['winding_consistent'] and state['outward_positive_volume'] and clean)
        require(state['self_intersection_checked'] is True and state['self_surface_method'] == SELF_METHOD
            and state['containment_blocked_by_self_geometry'] is (not clean)
            and state['containment_available'] is available, 'Self-surface containment eligibility differs')
        require(audit['self_collision_free_certified'] is False and audit['quality_approved'] is False,
            'Self-surface evidence cannot certify motion')
        eligible &= clean
    return eligible


def ray_consensus_reduction(ray,resolved,counts):
    require(type(ray) is bool and type(resolved) is bool and isinstance(counts,list) and len(counts)==3
        and all(isinstance(pair,list) and len(pair)==2
            and all(type(n) is int and n>=0 for n in pair) for pair in counts), 'Six explicit nonnegative ray hit counts required')
    parity=[n%2 for pair in counts for n in pair]
    agrees=all(p==parity[0] for p in parity)
    require(resolved is agrees and ray is (agrees and parity[0]==1), 'Ray consensus reduction differs')


def containment_state(distance, ray, winding, tolerance, *, unsigned=None, ray_resolved=True):
    require(type(distance) in (int, float) and np.isfinite(distance) and type(ray) is bool
        and type(winding) in (int, float) and np.isfinite(winding), 'Complete finite containment consensus observations required')
    # A zero sign in the pinned nearest-normal implementation can erase the
    # unsigned magnitude. Older center records cannot distinguish that from
    # an actual surface point. Both possible outcomes remain non-passing.
    if unsigned is None and distance == 0: return 'near-surface-or-unresolved'
    unsigned = abs(distance) if unsigned is None else unsigned
    require(type(unsigned) in (int, float) and np.isfinite(unsigned) and unsigned >= 0, 'Finite nearest distance required')
    if unsigned <= tolerance: return 'near-surface'
    require(type(ray_resolved) is bool,'Explicit ray consensus resolution required')
    if not ray_resolved:return 'unresolved'
    if distance > tolerance and ray and abs(winding - 1) <= 1e-5: return 'inside'
    if distance < -tolerance and not ray and abs(winding) <= 1e-5: return 'outside'
    return 'unresolved'


def partner_containment_reduction(row, target_available, source_vertices, limit, tolerance):
    require(type(row['available']) is bool, 'Explicit partner availability required')
    if not target_available:
        require(row['available'] is False and set(row) == {'source', 'target', 'available'},
            'Ineligible partner target cannot have depth observations')
        return
    require(row['containment_method'] == CONTAINMENT_METHOD and row['count_tolerance_m'] == max(limit, 1e-12)
        and row['vertices_checked'] == source_vertices, 'Complete versioned partner query required')
    queried = row['queried_vertices']; unresolved = row['unresolved_vertices']
    require(type(queried) is int and 0 <= queried <= source_vertices and isinstance(unresolved, list)
        and len(unresolved) <= queried, 'Bounded unresolved partner population required')
    seen = set()
    for observation in unresolved:
        vertex = observation['vertex']
        require(type(vertex) is int and 0 <= vertex < source_vertices and vertex not in seen, 'Distinct unresolved source vertices required')
        seen.add(vertex)
        ray_consensus_reduction(observation['ray_inside'],observation['ray_resolved'],observation['ray_hit_counts'])
        status = containment_state(observation['signed_distance_m'], observation['ray_inside'], observation['winding'],
            tolerance, unsigned=observation['unsigned_distance_m'],ray_resolved=observation['ray_resolved'])
        require(status in ('near-surface', 'unresolved') and observation['state'] == status, 'Unresolved partner observation differs')
    require(row['available'] is (not unresolved), 'Partner availability differs from consensus evidence')
    if unresolved:
        require(not any(key in row for key in ('max_depth_m', 'vertices_over_tolerance', 'deepest_vertex')),
            'Unresolved partner query cannot report a depth reduction')
    else:
        depth = row['max_depth_m']; count = row['vertices_over_tolerance']; vertex = row['deepest_vertex']
        require(type(depth) in (int, float) and np.isfinite(depth) and depth >= 0
            and type(count) is int and 0 <= count <= queried, 'Invalid partner depth')
        require((depth == 0 and vertex is None) or (depth > 0 and type(vertex) is int and 0 <= vertex < source_vertices),
            'Invalid deepest partner vertex')


def geometry_reductions(scene, policy, digest, times, report, saved):
    """Check every declared population and saved triangle-array reduction.

    Containment and partner query outputs remain retained measurements, not
    independently re-queried geometry. No decision flags are trusted alone.
    """
    required, populations, _ = policy_for(policy, scene, digest)
    require(np.isin(required, times).all(), 'Geometry clock missing from engine observations')
    times = required  # Explicit policies may declare fewer times than contact sampling.
    require(report['schema'] == 'strep-native-scene-geometry-result-v1' and report['status'] == 'complete', 'Complete geometry required')
    require(report.get('self_surface_method') == SELF_METHOD, 'Versioned self-surface evidence required')
    require(report.get('containment_method') == CONTAINMENT_METHOD, 'Versioned containment evidence required')
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
        self_clean = self_surface_reductions(sample, report['topology'], tolerance)
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
                require(containment['containment_method'] == CONTAINMENT_METHOD, 'Versioned center containment required')
                ray_consensus_reduction(containment['ray_inside'],containment['ray_resolved'],containment['ray_hit_counts'])
                status = containment_state(distance, containment['ray_inside'], containment['winding'], tolerance,
                    unsigned=containment['unsigned_center_distance_m'],ray_resolved=containment['ray_resolved'])
                if status == 'near-surface-or-unresolved':
                    require(containment['status'] in ('near-surface', 'unresolved'), 'Zero signed center distance cannot establish containment')
                    status = containment['status']
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
                partner_containment_reduction(d, sample['volumes'][d['target']]['containment_available'],
                    report['topology'][d['source']]['vertices'], limit, tolerance)
            passed = bool(not row['surface']['records'] and not sample['degenerate_faces'][left]
                and not sample['degenerate_faces'][right] and all(d['available'] and d['max_depth_m'] <= limit for d in depths))
            require(row['passed'] is passed, 'Partner decision differs')
        for row in sample['world_planes']:
            require(np.isfinite(row['maximum_depth_m']) and row['maximum_depth_m'] >= 0
                    and type(row['peak_vertex']) is int and row['peak_vertex'] in faces[row['actor']], 'Invalid plane reduction')
            require(row['passed'] is bool(row['maximum_depth_m'] <= limit and not sample['degenerate_faces'][row['actor']]), 'Plane decision differs')
        conditions = sample['actor_objects'] + sample['actor_pairs'] + sample['world_planes']
        passed = bool(conditions and all(r['passed'] for r in conditions) and not any(sample['degenerate_faces'].values()) and self_clean)
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
            geometry_report = read(combined_dir/'geometry.json')
            require(sha256(combined_dir/'geometry-observations.npz')==geometry_report['observations_sha256']
                and sha256(combined_dir/'geometry-observations.npz.receipt.json')==geometry_report['observation_receipt_sha256'],
                'Combined geometry transport changed')
            transport = verify_transport(combined_dir/'geometry-observations.npz')
            with np.load(combined_dir/'geometry-observations.npz', allow_pickle=False) as saved:
                geometry = geometry_reductions(scene, policy, sha256(contacts), times, geometry_report, saved)
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
                recorded_sampled_conditions_pass=passed, geometry_reductions=geometry, geometry_transport=transport, source_bindings_sha256=bindings,
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
