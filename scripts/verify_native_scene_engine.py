"""Replay one complete native scene engine study in either playback mode.

Actor, object, partner, contact, raw skin, plane and archive populations remain
complete. Saved triangle geometry reductions are replayed without rerunning
triangle queries. Shared pose/contact decoding is evidence consistency, not
independent geometry mathematics, runtime playback or animation approval.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for, faces_for
from native_scene_engine import EngineObservations, sample_times, METHODS, SKIN_POSITION_TOLERANCE
from native_engine_clock import check_clock_wire
from native_godot_payload import payload
from native_object_scene_engine import method_bindings, require
from native_observation_archive import verify as verify_transport
from verify_native_object_scene_engine import geometry_reductions

FILES = ('result.json', 'pipeline.json', 'request.json', 'raw-engine-receipt.json',
         'engine-output.json', 'engine.log', 'native-observations.npz',
         'imported-contact-observations.npz', 'geometry.json',
         'geometry-observations.npz', 'geometry-observations.npz.receipt.json')
VERIFIER_METHODS = tuple(dict.fromkeys(METHODS + (
    'verify_native_scene_engine.py', 'native_object_scene_engine.py',
    'verify_native_object_scene_engine.py', 'native_observation_archive.py')))


def load(contacts, policy_path, actor_dir):
    contacts, policy_path, actor_dir = [Path(p).resolve() for p in (contacts, policy_path, actor_dir)]
    require(read(actor_dir/'pipeline.json')['status'] == 'complete', 'Complete actor producer required')
    result = read(actor_dir/'result.json')
    require(result['status'] == 'complete' and result['schema'] == 'strep-native-scene-engine-v1', 'Complete native actor result required')
    require(result['original_selected'] is True and all(result[k] is False for k in (
        'gpu_skin_verified','physics_playback_verified','gameplay_event_playback_verified',
        'continuous_collision_certified','quality_approved','training_admitted','release_approved')), 'Original unapproved actor evidence required')
    spec = read(contacts); scene = SceneContacts(spec, contacts.parent); policy = read(policy_path)
    policy_for(policy, scene, sha256(contacts))
    request = read(actor_dir/'request.json'); receipt = read(actor_dir/'raw-engine-receipt.json')
    require(request['inputs_sha256'] == result['inputs_sha256'] and request['implementation_sha256'] == result['implementation_sha256'], 'Actor request binding changed')
    require(result['inputs_sha256'].get(str(contacts)) == sha256(contacts)
            and result['inputs_sha256'].get(str(policy_path)) == sha256(policy_path), 'Exact contacts and policy required')
    mode = result['playback_mode']
    require(mode in ('import', 'native-authoring') and request['playback_mode'] == mode
            and request['objects'] == spec['objects'], 'Complete scene and explicit playback mode required')
    require(sha256(actor_dir/'request.json') == receipt['request_sha256']
            and sha256(actor_dir/'engine-output.json') == receipt['engine_output_sha256'] == result['engine_output_sha256'], 'Raw actor receipt differs')
    require(sha256(actor_dir/'raw-engine-receipt.json') == result['raw_engine_receipt_sha256'], 'Actor receipt changed')
    require(receipt['returncode'] == 0 and receipt['engine_executable_sha256'] == request['engine_sha256'] == result['engine_executable_sha256'], 'Executed actor engine differs')
    require(sha256(actor_dir/'engine.log') == receipt['engine_log_sha256'], 'Actor engine log changed')
    for filename, key in (('native-observations.npz', 'native_observations_sha256'),
                          ('imported-contact-observations.npz', 'imported_contact_observations_sha256'), ('geometry.json', 'geometry_sha256')):
        require(sha256(actor_dir/filename) == result[key], 'Actor observation changed: '+filename)
    geometry = read(actor_dir/'geometry.json')
    require(sha256(actor_dir/'geometry-observations.npz') == geometry['observations_sha256']
            and sha256(actor_dir/'geometry-observations.npz.receipt.json') == geometry['observation_receipt_sha256'], 'Actor geometry transport changed')
    method_bindings(actor_dir, result, METHODS)
    source_inputs = {str(contacts): sha256(contacts), str(policy_path): sha256(policy_path), **scene.inputs}
    engine_inputs = {p: h for p, h in result['inputs_sha256'].items() if p not in source_inputs}
    require(len(engine_inputs) == 1 and next(iter(engine_inputs.values())) == result['engine_executable_sha256']
            and result['inputs_sha256'] == {**source_inputs, **engine_inputs}, 'Complete scene assets and one engine binding required')
    for path, digest in result['inputs_sha256'].items(): require(sha256(path) == digest, 'Actor producer input changed')
    require(set(result['source_snapshots']) == set(source_inputs), 'Complete actor snapshots required')
    for path, snapshot in result['source_snapshots'].items():
        saved = (actor_dir/snapshot['path']).resolve()
        require(saved.is_relative_to(actor_dir) and sha256(path) == sha256(saved) == snapshot['sha256'], 'Actor snapshot changed')
    scripts = {'godot_native_scene_audit.gd', 'native_godot_tracks.gd', 'native_godot_preview.gd', 'native_engine_clock.gd'}
    require(set(receipt['executed_scripts_sha256']) == scripts, 'Complete executed actor scripts required')
    for name, digest in receipt['executed_scripts_sha256'].items():
        require(digest == result['implementation_sha256'][name]
                and sha256(actor_dir/'project'/('audit.gd' if name == 'godot_native_scene_audit.gd' else name)) == digest, 'Executed actor script changed')
    resources = result.get('animation_resources_sha256', {})
    require(set(resources) == (set(scene.actors) if mode == 'native-authoring' else set())
            and resources == receipt['animation_resources_sha256'], 'Complete mode-specific animation resources required')
    for name, digest in resources.items(): require(sha256(actor_dir/(name+'-animation.res')) == digest, 'Scene resource changed')
    times = np.asarray(request['sample_times_s'], dtype='<f8'); check_clock_wire(request['sample_clock'], times)
    _, native_arrays = scene.evaluate()
    require(np.array_equal(times, sample_times(scene, native_arrays, policy, sha256(contacts))), 'Complete original actor/contact/geometry clock required')
    require([c['id'] for c in request['cases']] == list(scene.actors), 'Complete original actor selection required')
    for case in request['cases']:
        source_path = str((contacts.parent / spec['actors'][case['id']]['glb']).resolve())
        saved_path = (actor_dir / result['source_snapshots'][source_path]['path']).resolve()
        require(case['animation_index'] == spec['actors'][case['id']]['animation_index']
                and Path(case['path']).resolve() == saved_path
                and sha256(case['path']) == spec['actors'][case['id']]['sha256'], 'Scene source selection differs')
        if mode == 'native-authoring':
            require(Path(case['animation_output']).resolve() == actor_dir/(case['id']+'-animation.res'), 'Scene authoring resource differs')
            entry = scene.actors[case['id']]
            require(case['native_payload'] == payload(entry['rig'], entry['sampler'], spec['actors'][case['id']]['sha256']),
                    'Complete source-derived native payload required')
        else: require('animation_output' not in case and 'native_payload' not in case, 'Import-only case cannot claim native authoring')
    actual = read(actor_dir/'engine-output.json'); require(actual['engine'] == result['engine'], 'Engine version differs')
    actor = EngineObservations(scene, actual, request['cases'], times)
    bindings = {str(contacts): sha256(contacts), str(policy_path): sha256(policy_path)}
    bindings.update({str(actor_dir/n): sha256(actor_dir/n) for n in FILES})
    bindings.update({str(actor_dir/(n+'-animation.res')): h for n,h in resources.items()})
    return scene, policy, actor, times, bindings


def exact_arrays(path, arrays):
    with np.load(path, allow_pickle=False) as stored:
        require(set(stored.files) == set(arrays), 'Complete replay array population required')
        for name, value in arrays.items():
            require(stored[name].dtype == value.dtype and stored[name].shape == value.shape
                    and stored[name].tobytes() == value.tobytes(), 'Replay array differs: '+name)


def run(contacts, policy_path, actor_dir, output):
    actor_dir = Path(actor_dir).resolve(); output = Path(output).resolve()
    require(not output.exists(), 'Fresh actor replay output required')
    with worker_lock(), threadpool_limits(limits=1):
        scene, policy, actor, times, bindings = load(contacts, policy_path, actor_dir)
        result = read(actor_dir/'result.json'); output.mkdir(parents=True)
        save(output/'pipeline.json', dict(status='processing', original_selected=True))
        try:
            shutil.copyfile(__file__, output/'verifier.py')
            verifier_methods = {name: sha256(ROOT/'scripts'/name) for name in VERIFIER_METHODS}
            implementation = output/'implementation'; implementation.mkdir()
            for name, digest in verifier_methods.items():
                shutil.copyfile(ROOT/'scripts'/name, implementation/name)
                require(sha256(implementation/name) == digest, 'Verifier method changed while freezing')
            native, arrays = scene.evaluate(); skin = {}; plane_observations = 0
            geometry_report = read(actor_dir/'geometry.json')
            required = policy_for(policy, scene, sha256(contacts))[0]
            require(geometry_report['times_s'] == required.tolist() and len(geometry_report['samples']) == len(required), 'Complete original geometry clock required')
            geometry_samples = dict(zip(required, geometry_report['samples']))
            for name, entry in scene.actors.items():
                p, r = entry['placement']; values = []; faces, _ = faces_for(entry['rig']); used = np.unique(faces)
                for t in times:
                    measured = actor.actor_vertices(name, float(t))
                    values.append(float(np.linalg.norm(measured-(entry['rig'].vertices(entry['sampler'].sample(float(t))) @ r.T+p), axis=1).max()))
                    if t in geometry_samples:
                        sample = geometry_samples[t]; triangles = measured[faces]
                        degenerate = np.flatnonzero(np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
                            <= policy['limits']['surface_tolerance_m']**2).tolist()
                        require(sample['degenerate_faces'][name] == degenerate, 'Replayed posed triangle degeneracy differs')
                        for plane_name, plane in policy['planes'].items():
                            rows = [row for row in sample['world_planes'] if row['actor'] == name and row['plane'] == plane_name]
                            require(len(rows) == 1, 'Complete posed actor/plane population required')
                            distances = measured @ np.array(plane['normal_world'])-plane['offset_m']; peak = int(used[distances[used].argmin()])
                            depth = max(0.,-float(distances[peak]))
                            require(rows[0]['peak_vertex'] == peak and rows[0]['maximum_depth_m'] == depth, 'Replayed world-plane observation differs')
                            plane_observations += 1
                errors = np.array(values)
                maximum = 0.; peak = None
                for t, error in zip(times, errors):
                    if error > maximum: maximum, peak = float(error), float(t)
                arrays[name+'_skin_errors_m'] = errors
                skin[name] = dict(maximum_engine_native_vertex_error_m=maximum, peak_time_s=peak,
                    tolerance_m=SKIN_POSITION_TOLERANCE, position_samples_pass=bool(maximum <= SKIN_POSITION_TOLERANCE))
            exact_arrays(actor_dir/'native-observations.npz', arrays)
            imported, imported_arrays = scene.evaluate(actor_points=actor.actor_points, object_poses=actor.object_poses)
            imported.update(loaded_skin_weights_normalized=False, measurement_source='Raw imported skin and object poses')
            exact_arrays(actor_dir/'imported-contact-observations.npz', imported_arrays)
            require(native == result['native_contacts'] and imported == result['imported_contacts']
                    and skin == result['skin_errors'] and actor.reports == result['actors'] and actor.object_report == result['objects'], 'Replayed actor/contact reports differ')
            transport = verify_transport(actor_dir/'geometry-observations.npz')
            with np.load(actor_dir/'geometry-observations.npz', allow_pickle=False) as stored:
                geometry = geometry_reductions(scene, policy, sha256(contacts), times, geometry_report, stored)
            decisions = dict(imported_pose_samples_pass=all(r['pose_samples_pass'] for r in actor.reports.values()),
                imported_object_pose_samples_pass=all(r['pose_samples_pass'] for r in actor.object_report.values()), imported_contact_samples_pass=imported['passed'],
                imported_skin_position_samples_pass=all(r['position_samples_pass'] for r in skin.values()),
                all_sampled_conditions_available=True, imported_geometry_samples_pass=geometry['passed'])
            passed = bool(native['passed'] and all(decisions.values()))
            require(all(result[k] is v for k,v in decisions.items()) and result['all_sampled_conditions_pass'] is passed
                    and result['samples'] == len(times), 'Actor sampled decision differs')
            load(contacts, policy_path, actor_dir); scene.check_inputs()
            require(all(sha256(p) == h for p,h in bindings.items()) and sha256(__file__) == sha256(output/'verifier.py'), 'Actor replay input/method changed')
            require(all(sha256(ROOT/'scripts'/name) == sha256(implementation/name) == digest
                        for name, digest in verifier_methods.items()), 'Verifier dependency changed during replay')
            verified = dict(schema='strep-native-scene-replay-v1', playback_mode=result['playback_mode'], at=now(), status='complete', samples=len(times),
                all_replayed_observations_exact=True, recorded_sampled_conditions_pass=passed,
                geometry_reductions=geometry, geometry_transport=transport, source_bindings_sha256=bindings,
                world_plane_observations_replayed=plane_observations, posed_triangle_degeneracy_replayed=True,
                producer_files_sha256=bindings, producer_implementation_sha256=result['implementation_sha256'],
                verifier_sha256=sha256(__file__), original_selected=True, quality_approved=False,
                verifier_implementation_sha256=verifier_methods,
                training_admitted=False, release_approved=False,
                scope='Complete selected-mode actor/object pose, raw imported skin/contact replay, world-plane/degeneracy replay and saved actor/object/partner geometry reductions. Shared producer pose/contact decoding; no independent triangle-depth or partner containment requery, GPU rendering, physics, real-time playback, human quality or release approval.')
            save(output/'result.json', verified); save(output/'pipeline.json', dict(status='complete', original_selected=True)); return verified
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc), original_selected=True)); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contacts', 'policy', 'scene_engine', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args(); run(args.contacts, args.policy, args.scene_engine, args.output)
