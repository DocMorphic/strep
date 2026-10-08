"""Full sampled scene geometry from immutable simultaneous engine observations.

Reuse the original complete clock and raw skins, never reimport or substitute
source poses. Native triangle/volume checks keep their original semantics.
"""
import argparse
import re
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from native_scene_imported_skin import ImportedSceneSkin
from native_engine_contacts import matrices
from native_engine_clock import check_clock_wire
from scene_import_clock import verify_scene
from native_scene_geometry import evaluate_to_archive, METHODS as GEOMETRY_METHODS
from native_scene_engine import METHODS as ENGINE_METHODS
from object_geometry import scene_geometry

METHODS = tuple(dict.fromkeys(ENGINE_METHODS + GEOMETRY_METHODS +
    ('imported_scene_geometry.py', 'scene_import_clock.py')))


class ImportedGeometryScene:
    def __init__(self, source_scene, request, observed):
        if source_scene.get('schema_version') != 1 or source_scene.get('fps') != 30:
            raise ValueError('Original 30fps scene schema required')
        self.times = np.asarray(request['sample_times_s'], float)
        check_clock_wire(request['sample_clock'], self.times)
        if request['frames'] != len(self.times) or source_scene['frame_count'] != request['source_frame_count']:
            raise ValueError('Unchanged complete source and imported clock required')
        if source_scene['id'] != request['id'] or set(source_scene['actors']) != set(request['actors']):
            raise ValueError('Unchanged scene identity and actor population required')
        self.duration = float(self.times[-1]); self.rows = []
        self.source_scene = source_scene; self.actors = {}; self.objects = {}
        self.skins = {}; self.observed = observed; self.transforms = {}; self.worlds = {}
        actors = {}; objects = {}; self.inputs = {}
        for name, entry in request['actors'].items():
            if entry['transform'] != source_scene['actors'][name]['transform']:
                raise ValueError('Actor placement differs from bound source scene')
            path = Path(entry['path']); self.inputs[str(path)] = sha256(path)
            rig = RigAsset.load(path)
            if len(rig.document.get('animations', [])) != 1:
                raise ValueError('One original exported animation required')
            sampler = AnimationSampler(rig.document, rig.binary, 0, max_duration_s=None)
            pose = entry['transform']; actors[name] = (rig, sampler, pose)
            p = np.asarray(pose['translation_m'], float)
            r = Rotation.from_quat(pose['rotation_xyzw']).as_matrix()
            self.actors[name] = dict(rig=rig, sampler=sampler, placement=(p, r))
            transform = np.eye(4); transform[:3, :3] = r; transform[:3, 3] = p
            self.transforms[name] = transform
        if source_scene['objects']:
            path = Path(request['objects_glb']); self.inputs[str(path)] = sha256(path)
            document, binary = read_glb(path)
            sampler = AnimationSampler(document, binary, 0, max_duration_s=None)
            for name, descriptor in source_scene['objects'].items():
                found = [i for i, n in enumerate(document['nodes']) if n.get('extras', {}).get('strep_object_id') == name]
                if len(found) != 1: raise ValueError('One bound exported object node required')
                objects[name] = (sampler, found[0])
                self.objects[name] = dict(geometry=scene_geometry(descriptor))
        self.pose_report = verify_scene(request, observed, actors, objects)
        if not self.pose_report['all_precision_screens_passed']:
            raise ValueError('Complete source-bound pose screens must pass before geometry replay')
        for name, (rig, _, _) in actors.items():
            skin = ImportedSceneSkin(rig, observed['actors'][name]); self.skins[name] = skin
            self.worlds[name] = matrices([frame[name] for frame in observed['frames']])
        self.object_tracks = {}; self.object_projection_errors = {}
        for name in self.objects:
            values = matrices([frame[name] for frame in observed['object_frames']])
            rotation = Rotation.from_matrix(values[:, :3, :3]).as_matrix()
            drift = float(abs(rotation - values[:, :3, :3]).max())
            if drift > 1e-5: raise ValueError('Object rigid-basis projection exceeds its pose screen')
            self.object_projection_errors[name] = drift
            self.object_tracks[name] = (values[:, :3, 3], rotation)

    def indices(self, times):
        values = np.asarray(times, float); found = np.searchsorted(self.times, values)
        if np.any(found >= len(self.times)) or not np.array_equal(self.times[found], values):
            raise ValueError('Geometry requested a clock sample missing from engine observations')
        return found

    def actor_vertices(self, name, time):
        skin = self.skins[name]; frame = int(self.indices([time])[0])
        observed = self.worlds[name][frame]
        world = np.empty_like(observed); world[skin.bone_map] = observed
        native = np.linalg.inv(self.transforms[name]) @ world
        p, r = self.actors[name]['placement']
        return skin.vertices(native) @ r.T + p

    def object_poses(self, name, times):
        ids = self.indices(times); p, r = self.object_tracks[name]
        return p[ids], r[ids]


def geometry_policy(value, scene, digest):
    if (not isinstance(value, dict) or set(value) != {'schema', 'producer_result_sha256', 'limits', 'planes'}
            or value['schema'] != 'strep-imported-scene-geometry-policy-v1'
            or value['producer_result_sha256'] != digest):
        raise ValueError('Geometry policy must bind this exact terminal engine result')
    return dict(schema='strep-native-scene-geometry-v1', contacts_sha256=digest,
                clock=dict(mode='explicit', times_s=scene.times.tolist()),
                limits=value['limits'], planes=value['planes'])


def load_producer(source):
    source = Path(source).resolve(); result = read(source / 'result.json')
    if (read(source / 'pipeline.json')['status'] != 'complete' or result['status'] != 'complete'
            or not result.get('imported_skin_measurements') or not result['all_precision_screens_passed']):
        raise ValueError('Terminal simultaneous imported-skin scene observations required')
    for filename, key in [('request.json', 'request_sha256'), ('engine-output.json', 'engine_output_sha256')]:
        if sha256(source / filename) != result[key]: raise ValueError('Producer observation file changed')
    for name, digest in result['implementation_sha256'].items():
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or sha256(source / 'implementation' / name) != digest:
            raise ValueError('Producer implementation snapshot changed')
    bindings = dict(result['inputs_sha256'])
    for path, digest in bindings.items():
        if sha256(path) != digest: raise ValueError('Producer input changed since import')
    request = read(source / 'request.json'); observed = read(source / 'engine-output.json')
    if ([s['id'] for s in request['scenes']] != [s['id'] for s in observed['scenes']]
            or [s['id'] for s in result['rows']] != [s['id'] for s in request['scenes']]):
        raise ValueError('Complete unchanged producer scene population required')
    for row in result['rows']:
        m = row['skin_measurements']
        for path_key, hash_key in [('path', 'sha256'), ('observations_path', 'observations_sha256')]:
            path = (source / m[path_key]).resolve()
            if not path.is_relative_to(source) or sha256(path) != m[hash_key]:
                raise ValueError('Producer skin receipt changed')
    bindings.update({str(source / name): sha256(source / name) for name in
                     ('result.json', 'request.json', 'engine-output.json', 'pipeline.json')})
    return result, request, observed, bindings


def run(source, policy_path, output, *, scene_ids=None):
    source, policy_path, output = map(lambda p: Path(p).resolve(), (source, policy_path, output))
    if output.exists(): raise ValueError('Fresh imported geometry output required')
    with worker_lock(), threadpool_limits(limits=1):
        producer, request, observed, bindings = load_producer(source)
        digest = sha256(source / 'result.json'); value = read(policy_path)
        bindings[str(policy_path)] = sha256(policy_path)
        ids = [s['id'] for s in request['scenes']]
        if len(set(ids)) != len(ids): raise ValueError('Distinct producer scene IDs required')
        selected = ids if scene_ids is None else scene_ids
        if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(ids):
            raise ValueError('Explicit existing distinct geometry scene IDs required')
        manifests = [Path(p) for p in producer['inputs_sha256'] if Path(p).name == 'manifest.json']
        if len(manifests) != 1: raise ValueError('One original bound scene manifest required')
        manifest_path = manifests[0]; manifest = read(manifest_path)
        methods = {name: sha256(ROOT / 'scripts' / name) for name in METHODS}
        output.mkdir(parents=True); implementation = output / 'implementation'; implementation.mkdir()
        for name in METHODS: shutil.copyfile(ROOT / 'scripts' / name, implementation / name)
        save(output / 'policy.json', value)
        save(output / 'pipeline.json', dict(status='processing', producer_result_sha256=digest))
        rows = []
        try:
            for item, actual in zip(request['scenes'], observed['scenes']):
                if item['id'] not in selected: continue
                entries = [s for s in manifest['scenes'] if s['id'] == item['id']]
                if len(entries) != 1: raise ValueError('One original scene record required')
                path = (manifest_path.parent / entries[0]['variants']['palm']).resolve()
                if str(path) not in bindings: raise ValueError('Scene record not bound by original producer')
                scene = ImportedGeometryScene(read(path)['scene'], item, actual)
                if any(bindings.get(p) != h for p, h in scene.inputs.items()):
                    raise ValueError('Geometry asset missing from exact producer input bindings')
                policy = geometry_policy(value, scene, digest)
                # Current independent pose/skin checks are rerun against raw
                # observations; the producer's old method version need not be
                # silently rebound to current source.
                report, archive = evaluate_to_archive(scene, policy, digest,
                    output / f'geometry-{len(rows)}.npz',
                    lambda progress: save(output / 'pipeline.json', dict(scene_id=item['id'], **progress)),
                    actor_vertices=scene.actor_vertices, object_poses=scene.object_poses)
                report.update(scene_id=item['id'], imported_skins={n: s.report for n, s in scene.skins.items()},
                    pose_check=scene.pose_report, actor_placement_applied_after_skin=True,
                    object_raw_basis_projection_errors=scene.object_projection_errors,
                    measurement_source='Bound raw simultaneous engine poses and skin; all source triangles, imported actor/prop clock unchanged', **archive)
                filename = f'geometry-{len(rows)}.json'; save(output / filename, report)
                rows.append(dict(id=item['id'], path=filename, sha256=sha256(output / filename),
                    samples=len(scene.times), sampled_conditions_pass=report['sampled_conditions_pass']))
            if any(sha256(p) != h for p, h in bindings.items()): raise ValueError('Geometry replay input changed')
            if any(sha256(ROOT / 'scripts' / n) != h or sha256(implementation / n) != h for n, h in methods.items()):
                raise ValueError('Geometry replay method changed')
            result = dict(status='complete', at=now(), rows=rows, inputs_sha256=bindings, implementation_sha256=methods,
                producer_result_sha256=digest, selected_scene_ids=selected,
                sampled_conditions_pass=all(r['sampled_conditions_pass'] for r in rows),
                collision_verified=False, continuous_collision_certified=False, quality_approved=False, release_approved=False)
            save(output / 'result.json', result); save(output / 'pipeline.json', dict(status='complete'))
            return result
        except Exception as error:
            save(output / 'pipeline.json', dict(status='failed', error=str(error), completed_scenes=rows)); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'policy', 'output'): parser.add_argument(name)
    parser.add_argument('--scene-id', action='append')
    args = parser.parse_args(); result = run(args.source, args.policy, args.output, scene_ids=args.scene_id)
    print(dict(scenes=len(result['rows']), sampled_geometry_pass=result['sampled_conditions_pass'], release_approved=False), flush=True)
