"""Headless imported actor/prop observations for arbitrary native scene contacts.

Complete raw imported skin functions and triangles are checked before CPU skin
reconstruction. Import-only and native-resource authoring seeks stay distinct.
This does not use GPU mesh baking, rendering, physics or runtime event playback.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import scipy
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256
from native_scene_contacts import SceneContacts
from native_scene_geometry import evaluate as geometry_audit, policy_for, METHODS as GEOMETRY_METHODS
from native_scene_imported_skin import ImportedSceneSkin
from native_engine_contacts import imported_world, matrices
from native_engine_clock import clock_echo_matches
from native_godot_payload import payload

METHODS = tuple(dict.fromkeys(GEOMETRY_METHODS + ('native_scene_engine.py','native_scene_imported_skin.py',
    'native_engine_contacts.py','native_engine_clock.py','native_godot_payload.py','godot_native_scene_audit.gd',
    'native_godot_tracks.gd','native_godot_preview.gd','native_review_support.py','native_support_spec.py',
    'native_leg_floor.py','native_foot_plant.py','native_contact_diagnostics.py','contact_rate_path.py',
    'contact_locked_native.py','timed_rotation_edit.py','elbow_swivel.py','two_bone_waypoint.py',
    'native_leg_smoothing.py','absolute_rate_peaks.py')))
POSE_TOLERANCE = 1e-4
OBJECT_TOLERANCE = 1e-6
SKIN_POSITION_TOLERANCE = 1e-4


def sample_times(scene, contact_arrays, policy=None, digest=None):
    clocks = [np.array([0.,scene.duration])]
    clocks += [v for k,v in contact_arrays.items() if k.endswith('_times_s')]
    if policy is not None: clocks.append(policy_for(policy,scene,digest)[0])
    return np.unique(np.concatenate(clocks))


class EngineObservations:
    def __init__(self, scene, actual, cases, times):
        self.scene = scene; self.times = np.asarray(times,float); self.skins = {}; self.worlds = {}; self.objects = {}; self.reports = {}
        if ([c['id'] for c in actual['cases']] != [c['id'] for c in cases]
                or [o['id'] for o in actual['objects']] != list(scene.objects)):
            raise ValueError('Complete unchanged engine actor/object population required')
        for observed, case in zip(actual['cases'],cases):
            name = case['id']; actor = scene.actors[name]
            if (observed['path'] != case['path'] or observed['animation_index'] != actor['animation_index']
                    or observed['original_animation_count'] != len(actor['rig'].document['animations'])):
                raise ValueError('Engine selected another source file or animation')
            skin = ImportedSceneSkin(actor['rig'],observed)
            world = imported_world(observed,self.times,skin.bone_map)
            expected = np.array([actor['sampler'].sample(float(t))[actor['rig'].joints] for t in self.times])
            error = float(abs(world-expected).max())
            duration_error = abs(float(observed['duration_s'])-scene.duration)
            if not np.isfinite(duration_error): raise ValueError('Finite imported duration required')
            self.skins[name] = skin; self.worlds[name] = world
            self.reports[name] = dict(samples=len(times),maximum_pose_element_error=error,duration_error_s=duration_error,
                loop_mode=observed['loop_mode'], selected_animation=observed['selected_animation'],
                animation_index=observed['animation_index'], imported_skin=skin.report,
                pose_samples_pass=bool(error<=POSE_TOLERANCE and duration_error<=1e-6 and observed['loop_mode']==0))
        self.object_report = {}
        for observed in actual['objects']:
            name = observed['id']; frames = observed['frames']
            if len(frames)!=len(times): raise ValueError('Missing engine object poses')
            if any(not clock_echo_matches(t,f['requested_time_s']) for t,f in zip(self.times,frames)):
                raise ValueError('Engine object clock differs')
            world = matrices([f['matrix'] for f in frames]); q = np.asarray([f['rotation_xyzw'] for f in frames],float)
            if q.shape != (len(times),4) or not np.isfinite(q).all() or np.any(abs(np.linalg.norm(q,axis=1)-1)>1e-6):
                raise ValueError('Unit-range finite imported object rotations required')
            # Analytic primitive queries require a proper rigid rotation. Retain
            # the raw matrix and report the normalization/projection difference.
            r = Rotation.from_quat(q).as_matrix(); p = world[:,:3,3]
            projection_error = float(abs(world[:,:3,:3]-r).max())
            native_p,native_r = scene.object_poses(name,self.times)
            position_error = float(np.linalg.norm(p-native_p,axis=1).max())
            rotation_error = float(abs(r-native_r).max())
            self.objects[name] = (p,r)
            self.object_report[name] = dict(samples=len(times),maximum_position_error_m=position_error,
                maximum_basis_error=rotation_error,maximum_raw_basis_projection_error=projection_error,
                raw_quaternion_normalization_error=float(abs(np.linalg.norm(q,axis=1)-1).max()),
                pose_samples_pass=bool(max(position_error,rotation_error,projection_error)<=OBJECT_TOLERANCE))

    def indices(self,times):
        values = np.asarray(times,float); index = np.searchsorted(self.times,values)
        if np.any(index>=len(self.times)) or not np.array_equal(self.times[index],values):
            raise ValueError('Missing exact declared imported clock sample')
        return index

    def actor_points(self,name,ids,times):
        actor = self.scene.actors[name]; p,r = actor['placement']; skin = self.skins[name]
        return np.array([skin.vertices(self.worlds[name][i],ids) @ r.T + p for i in self.indices(times)])

    def actor_vertices(self,name,time):
        return self.actor_points(name,np.arange(len(self.skins[name].nodes)),[time])[0]

    def object_poses(self,name,times):
        p,r = self.objects[name]; index = self.indices(times); return p[index],r[index]


def run(contacts_path,output,*,geometry_policy=None,engine=None,playback_mode='import'):
    if playback_mode not in ('import','native-authoring'): raise ValueError('Explicit import or native-authoring mode required')
    contacts_path,output = Path(contacts_path).resolve(),Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native scene engine output required')
    engine = Path(engine).resolve() if engine is not None else ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    with worker_lock(),threadpool_limits(limits=1):
        bindings = {str(contacts_path):sha256(contacts_path),str(engine):sha256(engine)}
        spec = read(contacts_path); scene = SceneContacts(spec,contacts_path.parent); bindings.update(scene.inputs)
        policy = None
        if geometry_policy is not None:
            geometry_policy = Path(geometry_policy).resolve(); bindings[str(geometry_policy)] = sha256(geometry_policy)
            policy = read(geometry_policy); policy_for(policy,scene,bindings[str(contacts_path)])
        native_contacts,native_arrays = scene.evaluate()
        times = sample_times(scene,native_arrays,policy,bindings[str(contacts_path)])
        methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True); project = output/'project'; project.mkdir(); archive = output/'implementation'; archive.mkdir()
        for n in methods: shutil.copyfile(ROOT/'scripts'/n,archive/n)
        snapshots = {}
        for i,(path,h) in enumerate(bindings.items()):
            if path==str(engine): continue  # Hash the executable; never duplicate its payload.
            dest = output/'input'/f'{i}{Path(path).suffix}'; dest.parent.mkdir(exist_ok=True); shutil.copyfile(path,dest)
            if sha256(dest)!=h: raise ValueError('Engine input snapshot differs')
            snapshots[path] = dict(path=dest.relative_to(output).as_posix(),sha256=h)
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native scene audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        for n in ('godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd'):
            shutil.copyfile(ROOT/'scripts'/n,project/('audit.gd' if n=='godot_native_scene_audit.gd' else n))
        cases = []
        for name,actor in scene.actors.items():
            original = (contacts_path.parent/spec['actors'][name]['glb']).resolve()
            case = dict(id=name,path=str(output/snapshots[str(original)]['path']),animation_index=actor['animation_index'])
            if playback_mode=='native-authoring':
                case.update(native_payload=payload(actor['rig'],actor['sampler'],sha256(original)),
                    animation_output=str(output/(name+'-animation.res')))
            cases.append(case)
        request = dict(cases=cases,sample_times_s=times.tolist(),objects=spec['objects'],playback_mode=playback_mode,
            engine_sha256=bindings[str(engine)],inputs_sha256=bindings,implementation_sha256=methods,
            pose_tolerance=POSE_TOLERANCE,object_pose_tolerance=OBJECT_TOLERANCE,
            skin_position_tolerance_m=SKIN_POSITION_TOLERANCE,
            imported_weight_normalization=False,physics_playback_verified=False,gpu_skin_verified=False)
        save(output/'request.json',request); save(output/'pipeline.json',dict(status='processing',stage='engine-import'))
        try:
            with (output/'engine.log').open('w') as log:
                finished = subprocess.run([str(engine),'--headless','--path',str(project),'--script','audit.gd','--',
                    str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,
                    timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if finished.returncode: raise ValueError('Native scene engine import failed; inspect engine.log')
            raw_digest = sha256(output/'engine-output.json')
            executed_scripts = {n:sha256(project/('audit.gd' if n=='godot_native_scene_audit.gd' else n))
                for n in ('godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd')}
            if any(h!=methods[n] for n,h in executed_scripts.items()): raise ValueError('Executed engine script changed')
            save(output/'raw-engine-receipt.json',dict(returncode=finished.returncode,engine_executable_sha256=bindings[str(engine)],
                request_sha256=sha256(output/'request.json'),engine_output_sha256=raw_digest,
                engine_log_sha256=sha256(output/'engine.log'),executed_scripts_sha256=executed_scripts,
                animation_resources_sha256={} if playback_mode=='import' else {c['id']:sha256(c['animation_output']) for c in cases}))
            actual = read(output/'engine-output.json')
            save(output/'pipeline.json',dict(status='processing',stage='imported-bindings'))
            observed = EngineObservations(scene,actual,cases,times)
            skin_errors = {}
            for name,actor in scene.actors.items():
                maximum = 0.; peak = None; errors = []
                for i,time in enumerate(times):
                    p,r = actor['placement']; expected = actor['rig'].vertices(actor['sampler'].sample(float(time))) @ r.T+p
                    measured = observed.actor_vertices(name,float(time))
                    error = float(np.linalg.norm(measured-expected,axis=1).max()); errors.append(error)
                    if error>maximum: maximum,peak = error,float(time)
                    if i%100==0: save(output/'pipeline.json',dict(status='processing',stage='full-imported-skin',actor=name,
                        completed_samples=i,total_samples=len(times)))
                skin_errors[name] = dict(maximum_engine_native_vertex_error_m=maximum,peak_time_s=peak,
                    tolerance_m=SKIN_POSITION_TOLERANCE,position_samples_pass=bool(maximum<=SKIN_POSITION_TOLERANCE))
                native_arrays[name+'_skin_errors_m'] = np.array(errors)
            imported_contacts,imported_arrays = scene.evaluate(actor_points=observed.actor_points,object_poses=observed.object_poses)
            imported_contacts.update(loaded_skin_weights_normalized=False,measurement_source='Raw imported skin and object poses')
            geometry = None
            if policy is not None:
                save(output/'pipeline.json',dict(status='processing',stage='imported-scene-geometry'))
                geometry,geometry_arrays = geometry_audit(scene,policy,bindings[str(contacts_path)],
                    actor_vertices=observed.actor_vertices,object_poses=observed.object_poses)
                np.savez_compressed(output/'geometry-observations.npz',**geometry_arrays)
                geometry.update(imported_triangle_identity_checked=True,
                    measurement_source='Imported CPU skin and engine Node3D prop transforms; authored placements after skin',
                    observations_sha256=sha256(output/'geometry-observations.npz'))
                save(output/'geometry.json',geometry)
            if any(sha256(p)!=h for p,h in bindings.items()): raise ValueError('Native scene engine source changed')
            if sha256(output/'engine-output.json')!=raw_digest: raise ValueError('Raw imported engine observations changed')
            if any(sha256(output/e['path'])!=e['sha256'] for e in snapshots.values()): raise ValueError('Engine source snapshot changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):
                raise ValueError('Native scene engine implementation changed')
            for n in ('godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd'):
                target = project/('audit.gd' if n=='godot_native_scene_audit.gd' else n)
                if sha256(target)!=methods[n]: raise ValueError('Executed engine script changed')
            np.savez_compressed(output/'native-observations.npz',**native_arrays)
            np.savez_compressed(output/'imported-contact-observations.npz',**imported_arrays)
            result = dict(schema='strep-native-scene-engine-v1',status='complete',engine=actual['engine'],
                engine_executable_sha256=bindings[str(engine)],playback_mode=playback_mode,samples=len(times),
                actors=observed.reports,objects=observed.object_report,skin_errors=skin_errors,
                native_contacts=native_contacts,imported_contacts=imported_contacts,
                imported_pose_samples_pass=all(r['pose_samples_pass'] for r in observed.reports.values()),
                imported_object_pose_samples_pass=all(r['pose_samples_pass'] for r in observed.object_report.values()),
                imported_contact_samples_pass=imported_contacts['passed'],
                imported_skin_position_samples_pass=all(r['position_samples_pass'] for r in skin_errors.values()),
                all_sampled_conditions_available=geometry is not None,
                all_sampled_conditions_pass=bool(geometry is not None and geometry['sampled_conditions_pass'] and native_contacts['passed']
                    and imported_contacts['passed'] and all(r['pose_samples_pass'] for r in observed.reports.values())
                    and all(r['pose_samples_pass'] for r in observed.object_report.values())
                    and all(r['position_samples_pass'] for r in skin_errors.values())),
                imported_geometry_samples_pass=None if geometry is None else geometry['sampled_conditions_pass'],
                geometry_sha256=None if geometry is None else sha256(output/'geometry.json'),
                source_snapshots=snapshots,inputs_sha256=bindings,implementation_sha256=methods,
                engine_output_sha256=sha256(output/'engine-output.json'),
                raw_engine_receipt_sha256=sha256(output/'raw-engine-receipt.json'),
                native_observations_sha256=sha256(output/'native-observations.npz'),
                imported_contact_observations_sha256=sha256(output/'imported-contact-observations.npz'),
                runtime=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__),
                original_selected=True,gpu_skin_verified=False,physics_playback_verified=False,
                gameplay_event_playback_verified=False,continuous_collision_certified=False,
                quality_approved=False,training_admitted=False,release_approved=False,
                scope='Actual headless selected-animation import, joint scrubs, raw imported triangle/skin data and '
                    'Node3D rigid object pose samples. CPU skin reconstruction uses unnormalized imported weights, '
                    'with authored actor placements applied after skin. Native-authoring uses the separately '
                    'exported/reloaded native Animation resource and authoring seek, not real-time playback. '
                    'No GPU buffers, rendering, physics, event playback, continuous collision or human quality approval.')
            if playback_mode=='native-authoring': result['animation_resources_sha256'] = {c['id']:sha256(c['animation_output']) for c in cases}
            save(output/'result.json',result); save(output/'pipeline.json',dict(status='complete',original_selected=True)); return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True)); raise


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('contacts',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--geometry-policy',type=Path); p.add_argument('--engine',type=Path)
    p.add_argument('--playback-mode',choices=['import','native-authoring'],default='import')
    a=p.parse_args();run(a.contacts,a.output,geometry_policy=a.geometry_policy,engine=a.engine,playback_mode=a.playback_mode)
