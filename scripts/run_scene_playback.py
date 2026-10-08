"""Sample every placed actor and exported prop together on a dense Godot clock."""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from scene_object_export import export_objects
from scene_import_clock import shared_clock, verify_scene
from native_engine_clock import clock_wire
from scene_import_measurements import measure, scalar
from native_scene_engine import METHODS as NATIVE_METHODS

METHODS = tuple(dict.fromkeys(NATIVE_METHODS + ('run_scene_playback.py', 'scene_import_clock.py', 'native_engine_clock.py',
           'godot_scene_import_audit.gd', 'rig_asset.py', 'rig_clip_import.py',
           'gltf_tools.py', 'scene_object_export.py', 'scene_constraints.py',
           'object_geometry.py', 'object_geometry_mesh.py', 'inspect_motion.py',
           'strep.py', 'action_worker_lock.py', 'scene_import_measurements.py')))


def bound_asset_digest(assets, relative_path):
    matches = [entry['sha256'] for key, entry in assets.items()
               if entry.get('file', key) == relative_path]
    if len(matches) != 1:
        raise ValueError('Exactly one declared preview asset binding required')
    return matches[0]


def run(source, output, *, rate_hz=120, scene_ids=None, engine=None,
        measure_skin=False, floor_y_m=0., penetration_limit_m=.005):
    source, output = Path(source).resolve(), Path(output).resolve()
    if type(measure_skin) is not bool:
        raise ValueError('Explicit boolean imported skin measurement option required')
    scalar(floor_y_m, 'declared floor height', -1e6, 1e6)
    scalar(penetration_limit_m, 'vertex penetration screen', 0., 1.)
    if output.exists():
        raise ValueError('Fresh playback evidence destination required')
    engine = (Path(engine).resolve() if engine else
              ROOT / '.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe')
    with worker_lock(), threadpool_limits(limits=1):
        manifest_path = source / 'manifest.json'
        manifest = read(manifest_path)
        selected = manifest['scenes']
        all_ids = [item['id'] for item in selected]
        if not all_ids or len(set(all_ids)) != len(all_ids):
            raise ValueError('Nonempty distinct scene population required')
        if scene_ids is not None:
            if not scene_ids or len(set(scene_ids)) != len(scene_ids) or not set(scene_ids) <= set(all_ids):
                raise ValueError('Explicit distinct existing scene IDs required')
            selected = [item for item in selected if item['id'] in scene_ids]
        bindings = {str(manifest_path): sha256(manifest_path), str(engine): sha256(engine)}
        methods = {name: sha256(ROOT / 'scripts' / name) for name in METHODS}
        prepared = []
        for item in selected:
            scene_path = (source / item['variants']['palm']).resolve()
            if not scene_path.is_relative_to(source):
                raise ValueError('Scene file escapes source bundle')
            scene = read(scene_path)['scene']
            if scene['id'] != item['id'] or scene['fps'] != 30 or not scene['actors']:
                raise ValueError('Matching nonempty 30fps source scene required')
            bindings[str(scene_path)] = sha256(scene_path)
            actors = {}; entries = {}
            for name, actor in scene['actors'].items():
                glb = (source / actor['preview_glb']).resolve()
                motion = (ROOT / actor['motion']).resolve()
                if (not glb.is_relative_to(source) or not motion.is_relative_to(ROOT)
                        or sha256(glb) != bound_asset_digest(manifest['assets'], actor['preview_glb'])
                        or sha256(motion) != actor['source_sha256']):
                    raise ValueError('Unchanged bound actor GLB and raw motion required')
                rig = RigAsset.load(glb)
                if len(rig.document.get('animations', [])) != 1:
                    raise ValueError('Exactly one explicit exported actor animation required')
                sampler = AnimationSampler(rig.document, rig.binary, 0, max_duration_s=None)
                actors[name] = (rig, sampler, actor['transform'])
                entries[name] = dict(path=str(glb), transform=actor['transform'])
                bindings.update({str(glb): sha256(glb), str(motion): sha256(motion)})
            # Validate clocks before creating the output or launching the engine.
            shared_clock(scene['frame_count'], rate_hz, [a[1] for a in actors.values()])
            prepared.append((scene, actors, entries))
        output.mkdir(parents=True)
        save(output / 'pipeline.json', dict(status='processing', quality_approved=False))
        try:
            implementation = output / 'implementation'; implementation.mkdir()
            for name in METHODS:
                shutil.copyfile(ROOT / 'scripts' / name, implementation / name)
            request = dict(scenes=[]); objects_by_scene = {}
            for index, (scene, actors, entries) in enumerate(prepared):
                objects = {}; extra = {}
                if scene['objects']:
                    path = output / f'objects-{index}.glb'
                    export_objects(scene, path)
                    document, binary = read_glb(path)
                    sampler = AnimationSampler(document, binary, 0, max_duration_s=None)
                    objects = {name: (sampler, next(i for i, n in enumerate(document['nodes'])
                               if n.get('extras', {}).get('strep_object_id') == name)) for name in scene['objects']}
                    extra = dict(objects_glb=str(path), object_names=list(objects))
                    bindings[str(path)] = sha256(path)
                times = shared_clock(scene['frame_count'], rate_hz,
                                     [a[1] for a in actors.values()] + ([sampler] if objects else []))
                request['scenes'].append(dict(id=scene['id'], frames=len(times),
                    source_frame_count=scene['frame_count'], sample_times_s=times.tolist(),
                    sample_clock=clock_wire(times), actors=entries, audit_actor_skin=measure_skin, **extra))
                objects_by_scene[scene['id']] = objects
            save(output / 'request.json', request)
            save(output / 'protocol.json', dict(at=now(), inputs_sha256=bindings,
                 implementation_sha256=methods, rate_hz=rate_hz, measure_imported_skin=measure_skin,
                 declared_floor_y_m=floor_y_m, vertex_penetration_limit_m=penetration_limit_m,
                 clock='Complete shared uniform clock plus every actual stored actor/object key; exact deduplication only',
                 quality_approved=False))
            project = output / 'project'; project.mkdir()
            (project / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep synchronized playback"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf8')
            shutil.copyfile(implementation / 'godot_scene_import_audit.gd', project / 'audit.gd')
            with (output / 'engine.log').open('w', encoding='utf8') as log:
                completed = subprocess.run([str(engine), '--headless', '--path', str(project), '--script',
                    'audit.gd', '--', str(output / 'request.json'), str(output / 'engine-output.json')],
                    stdout=log, stderr=subprocess.STDOUT, timeout=300,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if completed.returncode:
                raise RuntimeError('Godot playback failed; retained engine log')
            report = read(output / 'engine-output.json')
            if [s['id'] for s in report['scenes']] != [s['id'] for s in request['scenes']]:
                raise ValueError('Complete unchanged observed scene population required')
            rows = []
            for index, (item, actual, (scene, actors, _)) in enumerate(zip(request['scenes'], report['scenes'], prepared)):
                row = dict(id=item['id'], **verify_scene(item, actual, actors, objects_by_scene[item['id']]))
                if measure_skin:
                    measurements, arrays = measure(scene, item, actual, actors, objects_by_scene[item['id']],
                        floor_y_m=floor_y_m, penetration_limit_m=penetration_limit_m)
                    path = output / f'measurements-{index}.npz'
                    np.savez_compressed(path, **arrays)
                    save(output / f'measurements-{index}.json', measurements)
                    row['skin_measurements'] = dict(path=f'measurements-{index}.json',
                        sha256=sha256(output / f'measurements-{index}.json'),
                        observations_path=path.name, observations_sha256=sha256(path),
                        point_contact_samples_passed=measurements['point_contact_samples_passed'],
                        authored_requirements_fully_measured=measurements['authored_requirements_fully_measured'])
                rows.append(row)
            for path, digest in bindings.items():
                if sha256(path) != digest:
                    raise ValueError('Playback input changed during audit')
            for name, digest in methods.items():
                if sha256(ROOT / 'scripts' / name) != digest or sha256(implementation / name) != digest:
                    raise ValueError('Playback implementation changed during audit')
            result = dict(at=now(), status='complete', engine=report['engine'], rows=rows,
                inputs_sha256=bindings, implementation_sha256=methods,
                engine_output_sha256=sha256(output / 'engine-output.json'),
                request_sha256=sha256(output / 'request.json'),
                all_precision_screens_passed=all(r['all_precision_screens_passed'] for r in rows),
                quality_approved=False, release_approved=False, imported_skin_measurements=measure_skin,
                scope='All actors and separately exported object GLBs present together; shared absolute manual seek, actual player clocks and every placed bone/object transform. Independent source local-track interpolation and hierarchy composition. Optional bound imported-skin point-contact and complete-vertex penetration diagnostics are saved separately. No full triangle/partner collision, GPU rendering, runtime physics/events or naturalness approval.')
            save(output / 'result.json', result)
            save(output / 'pipeline.json', dict(status='complete', quality_approved=False))
            return result
        except Exception as error:
            save(output / 'pipeline.json', dict(status='failed', error=str(error), quality_approved=False))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source'); parser.add_argument('output')
    parser.add_argument('--rate-hz', type=int, default=120)
    parser.add_argument('--scene-id', action='append'); parser.add_argument('--engine')
    parser.add_argument('--measure-skin', action='store_true')
    parser.add_argument('--floor-y-m', type=float, default=0.)
    parser.add_argument('--penetration-limit-m', type=float, default=.005)
    args = parser.parse_args()
    result = run(args.source, args.output, rate_hz=args.rate_hz, scene_ids=args.scene_id, engine=args.engine,
                 measure_skin=args.measure_skin, floor_y_m=args.floor_y_m, penetration_limit_m=args.penetration_limit_m)
    summary = dict(scenes=len(result['rows']), pose_screens_passed=result['all_precision_screens_passed'])
    if args.measure_skin:
        summary['point_contact_samples_passed'] = all(r['skin_measurements']['point_contact_samples_passed'] for r in result['rows'])
    print(summary, flush=True)
