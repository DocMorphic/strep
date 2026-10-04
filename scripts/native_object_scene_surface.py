"""Audit explicit surface-facing conditions on a bound imported object scene."""
import argparse
from pathlib import Path
import shutil

import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_object_bounded_scene import METHODS as BOUND_METHODS, SCHEMA as BOUND_SCHEMA, _validate_handoff
from native_object_scene_engine import load
from native_surface_contact import METHODS as SURFACE_METHODS, evaluate, policy_for

SCHEMA = 'strep-native-object-scene-surface-v1'
METHODS = tuple(dict.fromkeys(BOUND_METHODS + SURFACE_METHODS + ('native_object_scene_surface.py',)))


class ImportedContactScene:
    """Point and normal measurements must use the same imported observations."""
    def __init__(self, scene, actor, objects):
        self.scene = scene
        self.actor = actor
        self.objects_provider = objects
        self.actors = scene.actors
        self.rows = scene.rows
        self.object_poses = objects.object_poses

    def evaluate(self):
        return self.scene.evaluate(actor_points=self.actor.actor_points,
                                   object_poses=self.objects_provider.object_poses)

    def check_inputs(self):
        self.scene.check_inputs()


def bound_scene(folder):
    with worker_lock(), threadpool_limits(limits=1):
        return _bound_scene(folder)


def _bound_scene(folder):
    """Caller holds the single-worker lock for this complete producer check."""
    folder = Path(folder).resolve()
    result = read(folder/'result.json')
    request = read(folder/'request.json')
    if (read(folder/'pipeline.json')['status'] != 'complete' or result['status'] != 'complete'
            or result['schema'] != BOUND_SCHEMA or request['schema'] != BOUND_SCHEMA):
        raise ValueError('Complete bounded imported scene required')
    if set(result['implementation_sha256']) != set(BOUND_METHODS):
        raise ValueError('Complete bounded scene methods required')
    for name, digest in result['implementation_sha256'].items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(folder/'implementation'/name) != digest:
            raise ValueError('Bounded scene method changed')
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(result['files_sha256']) | {'result.json', 'pipeline.json'}:
        raise ValueError('Complete bounded scene file inventory required')
    for name, digest in result['files_sha256'].items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder) or sha256(path) != digest:
            raise ValueError('Bounded scene file changed or escaped output')
    if request['bindings'] != result['bindings']:
        raise ValueError('Bounded scene input receipts differ')
    for path, digest in result['bindings'].items():
        if sha256(path) != digest: raise ValueError('Bounded scene input changed')
    if not result['original_selected'] or any(result[k] is not False for k in
            ('quality_approved', 'training_admitted', 'release_approved')):
        raise ValueError('Unapproved original-retained development scene required')
    _, handoff_times = _validate_handoff(Path(request['fit']), Path(request['handoff']), Path(request['engine']))
    scene, geometry_policy, actor, providers, times, bindings = load(
        Path(request['contacts']), Path(request['policy']), folder/'actor-engine',
        Path(request['handoff'])/'candidate-engine')
    combined = read(folder/'combined/result.json')
    replay = read(folder/'verification/result.json')
    if (read(folder/'combined/pipeline.json')['status'] != 'complete'
            or read(folder/'verification/pipeline.json')['status'] != 'complete'
            or combined['status'] != 'complete' or replay['status'] != 'complete'):
        raise ValueError('Complete combined scene and replay required')
    if (not np.array_equal(times, handoff_times) or len(times) != request['samples']
            or len(times) != result['samples'] or len(times) != combined['samples'] or len(times) != replay['samples']
            or combined['source_bindings_sha256'] != bindings):
        raise ValueError('Complete original producer population and clock required')
    if (not replay['all_replayed_observations_exact']
            or replay['recorded_sampled_conditions_pass'] != combined['all_sampled_conditions_pass']
            or combined['all_sampled_conditions_pass'] != result['combined_scene_conditions_pass']):
        raise ValueError('Exact saved scene replay required')
    expected_replay = bool(replay['all_replayed_observations_exact'] and replay['recorded_sampled_conditions_pass'])
    expected_scene = bool(result['object_handoff_conditions_pass'] and result['combined_scene_conditions_pass'] and expected_replay)
    if (result['object_handoff_conditions_pass'] is not True
            or result['saved_scene_replay_pass'] != expected_replay
            or result['bounded_scene_conditions_pass'] != expected_scene):
        raise ValueError('Bounded scene aggregate differs from retained handoff and replay')
    return request, result, scene, actor, providers, times


def run(folder, surface_policy, output):
    folder, surface_policy, output = [Path(p).resolve() for p in (folder, surface_policy, output)]
    if output.exists() or output.is_relative_to(folder):
        raise ValueError('Fresh surface audit output outside the original scene required')
    with worker_lock(), threadpool_limits(limits=1):
        request, original, scene, actor, providers, times = _bound_scene(folder)
        contacts_digest = sha256(request['contacts'])
        policy = read(surface_policy)
        policy_for(policy, scene, contacts_digest)
        inputs = {str(folder/'result.json'): sha256(folder/'result.json'), str(surface_policy): sha256(surface_policy)}
        methods = {name: sha256(ROOT/'scripts'/name) for name in METHODS}
        output.mkdir(parents=True)
        (output/'implementation').mkdir()
        for name in METHODS: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
        shutil.copyfile(surface_policy, output/'surface-policy.json')
        save(output/'request.json', dict(schema=SCHEMA, at=now(), inputs_sha256=inputs,
            implementation_sha256=methods, bound_scene=str(folder), contacts_sha256=contacts_digest,
                scene_samples=len(times), new_authored_conditions=True))
        try:
            reports = {}; arrays = {}
            for mode, provider in providers.items():
                save(output/'pipeline.json', dict(status='processing', stage='imported-surface-contacts',
                    mode=mode, original_selected=True))
                imported = ImportedContactScene(scene, actor, provider)
                report, values = evaluate(imported, policy, contacts_digest,
                    actor_vertices=actor.actor_vertices, object_poses=provider.object_poses)
                report.update(measurement_source='Complete imported CPU skin and actual saved object Animation-resource poses',
                    actual_imported_observations_used=True, loaded_skin_weights_normalized=False)
                reports[mode] = report
                save(output/(mode+'-surface.json'), report)
                arrays.update({mode+'_'+name: value for name, value in values.items()})
            np.savez_compressed(output/'observations.npz', **arrays)
            _bound_scene(folder)
            if any(sha256(path) != digest for path, digest in inputs.items()):
                raise ValueError('Surface audit input changed')
            if sha256(output/'surface-policy.json') != inputs[str(surface_policy)]:
                raise ValueError('Archived surface policy changed')
            for name, digest in methods.items():
                if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                    raise ValueError('Surface audit method changed')
            passed = reports['native-authoring']['surface_contacts_pass']
            result = dict(schema=SCHEMA, at=now(), status='complete', scene_samples=len(times),
                inputs_sha256=inputs, implementation_sha256=methods,
                contact_samples={mode: {c['id']: len(c['samples']) for c in value['contacts']}
                    for mode, value in reports.items()},
                surface_actor_pose_queries={mode: value['actor_pose_queries'] for mode, value in reports.items()},
                original_sampled_scene_conditions_pass=original['bounded_scene_conditions_pass'],
                surface_conditions_pass={mode: value['surface_contacts_pass'] for mode, value in reports.items()},
                sampled_scene_and_surface_conditions_pass=bool(original['bounded_scene_conditions_pass'] and passed),
                new_authored_conditions=True, actual_imported_observations_used=True,
                loaded_skin_weights_normalized=False, original_selected=True, anatomical_review_pending=True,
                normal_winding_epoch='Original actor triangle winding at the measured imported positions; complete imported triangle correspondence is checked by the bound scene.',
                geometry_queries_rerun=False, gpu_render_checked=False, physics_verified=False,
                real_time_playback_verified=False, continuous_collision_certified=False,
                quality_approved=False, training_admitted=False, release_approved=False,
                files_sha256={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*')
                    if p.is_file() and p not in (output/'result.json', output/'pipeline.json')},
                scope='Additional explicit winding-normal opposition and facing-side conditions at every original contact clock. '
                    'Imported contact points and normals share the same raw imported skin/object observations. '
                    'No anatomical identification, force, geometry requery, continuous collision or human-quality approval.')
            save(output/'result.json', result)
            save(output/'pipeline.json', dict(status='complete', original_selected=True))
            return result
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc), original_selected=True))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scene', 'surface_policy', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args(); run(args.scene, args.surface_policy, args.output)
