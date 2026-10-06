"""Read-only bridge source diagnosis with full frozen poses and exact witnesses.

Bind a completed reserve-guided correction, derive the existing tangent guards,
compare every frozen native geometry sample, and independently check all proper
crossing records at explicitly chosen frozen times. This does not replay the
optimizer or its external parent graph, certify an entire collision-free scene,
or modify any source clip, permission, acceptance limit, or release decision.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from exact_triangle_crossing_witness import witness, verify as verify_witness
from native_geometry_failure_profile import summarize, editable, SCOPE_SCHEMA
from native_scene_contacts import SceneContacts
from native_scene_geometry import faces_for, evaluate, METHODS as GEOMETRY_METHODS
from strep import ROOT, read, save, sha256, now

SCHEMA = 'strep-native-geometry-source-blocker-audit-v1'
METHODS = tuple(dict.fromkeys(GEOMETRY_METHODS + ('native_transition_scene_fit.py',
    'native_geometry_failure_profile.py', 'exact_triangle_crossing_witness.py', 'native_geometry_source_blockers.py')))


def require(value, message):
    if not value: raise ValueError(message)


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def scope_for(recipe, source, source_result, digest):
    """Match existing bridge-only permission and tangent-guard construction."""
    actors = {name: None for name in source.actors}
    require(recipe['schema'] == 'strep-native-transition-scene-fit-v1' and recipe['actors']
        and not set(recipe['actors'])-set(actors), 'Existing nonempty bridge actor permissions required')
    for name, permission in recipe['actors'].items():
        require(same(permission['window_s'], source_result['bridge_interval_s']), 'Window differs from sealed source bridge')
        start, end = permission['window_s']; guards = []
        require(isinstance(permission['protected_s'], list) and permission['tracks'], 'Explicit protected ranges/tracks required')
        for track in permission['tracks']:
            found = [c for c in source.actors[name]['sampler'].channels if c[:2] == (track['node'], track['path'])]
            require(len(found) == 1, 'Existing unique selected source channel required')
            clock = found[0][2]; lo, hi = np.searchsorted(clock, [start, end])
            require(hi < len(clock) and clock[lo] == start and clock[hi] == end and hi-lo >= 4,
                'Native source bridge requires endpoints, tangent guards and interior keys')
            guards += [[start, float(clock[lo+1])], [float(clock[hi-1]), end]]
        actors[name] = dict(window_s=copy.deepcopy(permission['window_s']),
            protected_s=copy.deepcopy(permission['protected_s'])+guards)
    return dict(schema=SCOPE_SCHEMA, geometry_sha256=digest, actors=actors, object_motion_editable=False, planes_editable=False)


def face_primitive(topology, face):
    found = [p for p in topology['primitives'] if p['first_face'] <= face < p['first_face']+p['faces']]
    require(len(found) == 1, 'Exact existing topology face identity required')
    return dict(node=found[0]['node'], primitive=found[0]['primitive'], face_in_primitive=face-found[0]['first_face'])


def tree(base):
    return {str(p.resolve()): sha256(p) for p in Path(base).rglob('*') if p.is_file()}


def run(correction, output, witness_times_s, *, imported_geometry=None):
    correction, output = Path(correction).resolve(), Path(output).resolve()
    require(not output.exists(), 'Fresh source-blocker audit output required')
    require(isinstance(witness_times_s, list) and witness_times_s and all(type(t) in (int,float)
        and np.isfinite(t) for t in witness_times_s) and len(set(witness_times_s)) == len(witness_times_s),
        'Explicit unique finite witness times required')
    recipe = read(correction/'recipe.json'); prepared = read(correction/'prepared.json')
    sealed = read(correction/'result.json')
    require(sealed['schema'] == prepared['schema'] == 'strep-native-transition-contact-fit-v1'
        and sealed['status'] == 'complete' and sha256(correction/'result.json') == read(correction/'completion.json')['result_sha256']
        and sha256(correction/'prepared.json') == sealed['prepared_sha256'], 'Completed byte-bound correction required')
    for key, folder in (('files_sha256',correction),('probe_files_sha256',correction/'probes'),('candidate_files_sha256',correction/'candidate')):
        expected_files = sealed[key]
        for name, digest in expected_files.items():
            path = (folder/name).resolve()
            require(path.is_relative_to(folder) and sha256(path) == digest, 'Sealed correction artifact changed')
        if folder != correction:
            require(set(tree(folder)) == {str((folder/name).resolve()) for name in expected_files}, 'Complete sealed artifact population required')
    for name, digest in prepared['implementation_sha256'].items():
        require(sha256(ROOT/'scripts'/name) == digest and sha256(correction/'implementation'/name) == digest,
            'Original numerical implementation differs from its archive')
    require(sha256(correction/'recipe.json') == prepared['recipe_sha256'], 'Sealed correction recipe changed')
    source_folder = (Path(prepared['recipe_base'])/recipe['source']['folder']).resolve()
    require(not output.is_relative_to(correction) and not output.is_relative_to(source_folder), 'Separate audit output required')
    require(sha256(source_folder/'result.json') == recipe['source']['result_sha256'], 'Sealed source result changed')
    for name, digest in prepared['original_files_sha256'].items():
        require(sha256(source_folder/name) == digest, 'Original correction input changed: '+name)
    candidate_folder = correction/'candidate'
    source_spec, candidate_spec = read(source_folder/'scene.json'), read(candidate_folder/'scene.json')
    source, candidate = SceneContacts(source_spec, source_folder), SceneContacts(candidate_spec, candidate_folder)
    expected = copy.deepcopy(source_spec)
    for name, actor in source.actors.items():
        entry = candidate_spec['actors'][name]
        expected['actors'][name].update(glb=entry['glb'], sha256=entry['sha256'], animation_index=len(actor['rig'].document['animations']))
        changed = candidate.actors[name]['rig']
        require(changed.binary[:len(actor['rig'].binary)] == actor['rig'].binary
            and same(changed.document['animations'][:-1], actor['rig'].document['animations']), 'Original clip library/payload changed')
        require(np.array_equal(faces_for(actor['rig'])[0], faces_for(changed)[0]), 'Original face identity changed')
    require(same(expected, candidate_spec), 'Candidate changes original object/contact/placement intent')
    geometry_path = candidate_folder/'geometry.json'; geometry = read(geometry_path); geometry_digest = sha256(geometry_path)
    require(same(geometry['limits'], recipe['geometry']['limits']), 'Original geometry acceptance changed')
    scope = scope_for(recipe, source, read(source_folder/'result.json'), geometry_digest)
    profile = summarize(geometry, scope, geometry_digest)
    times = geometry['times_s']
    require(all(t in times and all(not editable(scope, name, t) for name in source.actors) for t in witness_times_s),
        'Witness times must be existing geometry samples frozen for every actor')
    input_hashes = {**tree(correction), **tree(source_folder)}
    if imported_geometry is not None:
        imported_geometry = Path(imported_geometry).resolve(); input_hashes[str(imported_geometry)] = sha256(imported_geometry)
    methods = {name:sha256(ROOT/'scripts'/name) for name in METHODS}
    with worker_lock(), threadpool_limits(limits=1):
        output.mkdir(parents=True)
        (output/'implementation').mkdir()
        for name in methods: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        save(output/'inputs.json', input_hashes); save(output/'native-scope.json', scope); save(output/'native-profile.json', profile)
        save(output/'pipeline.json', dict(status='processing', phase='complete-frozen-native-sample-comparison', at=now()))
        try:
            imported_profile = None
            if imported_geometry is not None:
                imported_scope = copy.deepcopy(scope); imported_scope['geometry_sha256'] = sha256(imported_geometry)
                imported_report = read(imported_geometry)
                require(same(imported_report['limits'], geometry['limits']) and same(imported_report['topology'], geometry['topology']),
                    'Imported diagnostic topology/acceptance differs')
                imported_profile = summarize(imported_report, imported_scope, imported_scope['geometry_sha256'])
                save(output/'imported-scope.json', imported_scope); save(output/'imported-profile.json', imported_profile)
            arrays = {}; frozen = {}
            for name, actor in source.actors.items():
                clock = [t for t in times if not editable(scope, name, t)]
                sw, cw, sv, cv = [], [], [], []
                for t in clock:
                    worlds = [scene.actors[name]['sampler'].sample(float(t)) for scene in (source, candidate)]
                    vertices = []
                    for scene, world in zip((source,candidate), worlds):
                        entry = scene.actors[name]; p, r = entry['placement']
                        vertices.append(entry['rig'].vertices(world) @ r.T+p)
                    sw.append(worlds[0]); cw.append(worlds[1]); sv.append(vertices[0]); cv.append(vertices[1])
                values = [np.asarray(v) for v in (clock,sw,cw,sv,cv)]
                for label, value in zip(('times_s','source_worlds','candidate_worlds','source_vertices','candidate_vertices'), values):
                    arrays[name+'_'+label] = value
                frozen[name] = dict(samples=len(clock), worlds_byte_equal=values[1].tobytes()==values[2].tobytes(),
                    vertices_byte_equal=values[3].tobytes()==values[4].tobytes(),
                    maximum_world_component_error=float(abs(values[1]-values[2]).max()),
                    maximum_vertex_component_error_m=float(abs(values[3]-values[4]).max()))
                save(output/'pipeline.json', dict(status='processing', phase='frozen-actor-complete', actor=name, samples=len(clock), at=now()))
            np.savez(output/'frozen-observations.npz', **arrays)
            selected_times = sorted(set([0., source.duration]+witness_times_s))
            save(output/'pipeline.json', dict(status='processing', phase='representative-all-face-geometry-recomputation', times_s=selected_times, at=now()))
            recomputed = {}
            for label, scene in (('source',source), ('candidate',candidate)):
                digest = sha256((source_folder if label == 'source' else candidate_folder)/'scene.json')
                policy = dict(schema='strep-native-scene-geometry-v1',contacts_sha256=digest,**copy.deepcopy(recipe['geometry']))
                policy['clock'] = dict(mode='explicit',times_s=selected_times)
                report, observations = evaluate(scene, policy, digest)
                save(output/(label+'-representative-policy.json'), policy)
                save(output/(label+'-representative-geometry.json'), report)
                np.savez(output/(label+'-representative-observations.npz'), **observations)
                recomputed[label] = report
            exact = []
            for time in witness_times_s:
                original_sample = next(s for s in geometry['samples'] if s['time_s'] == time)
                for pair in original_sample['actor_pairs']:
                    left, right = pair['actors']
                    records = [r for r in pair['surface']['records'] if r['kind'] == 'proper_crossing']
                    require(records, 'Selected frozen witness time lacks a reported proper crossing')
                    for record in records:
                        entry = dict(time_s=time,actors=pair['actors'],left_triangle=record['left_triangle'],right_triangle=record['right_triangle'],
                            primitive_identity=[face_primitive(geometry['topology'][n], record[k]) for n,k in ((left,'left_triangle'),(right,'right_triangle'))])
                        for label, scene in (('source',source),('candidate',candidate)):
                            triangles = []
                            for name, face_key in ((left,'left_triangle'),(right,'right_triangle')):
                                actor = scene.actors[name]; p, r = actor['placement']
                                vertices = actor['rig'].vertices(actor['sampler'].sample(time)) @ r.T+p
                                triangles.append(vertices[faces_for(actor['rig'])[0][record[face_key]]])
                            entry[label] = verify_witness(witness(*triangles))
                        exact.append(entry)
            save(output/'exact-crossing-witnesses.json', dict(witness_times_s=witness_times_s, all_reported_proper_records_at_selected_times=exact))
            unchanged = all(tree(base) == {p:h for p,h in input_hashes.items() if Path(p).is_relative_to(base)} for base in (correction,source_folder))
            require(unchanged and all(sha256(p) == h for p,h in input_hashes.items()), 'Audit input bytes/population changed')
            require(all(sha256(ROOT/'scripts'/n) == h and sha256(output/'implementation'/n) == h for n,h in methods.items()), 'Audit methods changed')
            equal = all(v['worlds_byte_equal'] and v['vertices_byte_equal'] for v in frozen.values())
            proved = bool(exact and all(e['source']['strict_interior_crossing_proved'] and e['candidate']['strict_interior_crossing_proved'] for e in exact))
            files = {p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p.name != 'pipeline.json'}
            result = dict(schema=SCHEMA,status='complete',at=now(),inputs_sha256=input_hashes,implementation_sha256=methods,files_sha256=files,
                native_samples=profile['samples'],imported_samples=None if imported_profile is None else imported_profile['samples'],
                native_counts=profile['counts'],imported_counts=None if imported_profile is None else imported_profile['counts'],
                frozen_pose_skin_comparison=frozen,complete_frozen_sample_equality=equal,
                representative_geometry_times_s=selected_times,original_limits_unchanged=True,
                representative_source_geometry_pass=recomputed['source']['sampled_conditions_pass'],
                representative_candidate_geometry_pass=recomputed['candidate']['sampled_conditions_pass'],
                exact_witness_pairs=len(exact),all_selected_source_candidate_witnesses_proved=proved,
                source_phase_crossing_blocker_proved=bool(equal and proved and profile['source_window_blockers_present']),
                full_collision_clock_recomputed=False,optimizer_or_external_parent_graph_replayed=False,
                imported_diagnostics_recomputed=False,quality_approved=False,release_approved=False,
                runtime=dict(python=sys.version,numpy=np.__version__),
                scope='Complete saved native/imported diagnostics classified separately; every frozen native pose and skin vertex compared. '
                    'All face/pair/object conditions recomputed only at selected representative times plus clip endpoints. Every saved proper-crossing '
                    'record at requested frozen times receives an independent rational witness on source and candidate represented triangles. '
                    'No optimizer replay, complete native/imported collision recomputation, continuous-time certificate, anatomy, physics, rendered/GPU or human approval.')
            save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete',at=now()))
            return result
        except BaseException as exc:
            save(output/'pipeline.json', dict(status='failed',error=str(exc),at=now())); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('correction',type=Path); parser.add_argument('output',type=Path)
    parser.add_argument('--witness-time',type=float,action='append',required=True)
    parser.add_argument('--imported-geometry',type=Path)
    args = parser.parse_args()
    result = run(args.correction,args.output,args.witness_time,imported_geometry=args.imported_geometry)
    print(json.dumps({k:result[k] for k in ('status','native_samples','imported_samples','exact_witness_pairs','source_phase_crossing_blocker_proved')},indent=2))
