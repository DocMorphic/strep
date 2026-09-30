"""Immutable saved-scene release requests and a supervised local bake worker."""
import argparse
import copy
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from scene_constraints import sample_object,pose
from object_release import release_request,simulate,bake
from action_worker_lock import worker_lock
from object_geometry import scene_geometry
from release_geometry import body_geometry,geometry_fields,primitive_gap,floor_gaps

JOBS=ROOT/'reports/scene-release-jobs'


def name_check(name):
    if not isinstance(name,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',name) or name.upper() in ['CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]]:raise ValueError('Unsafe actor/object identifier')


def source_metadata(url,*,allow_native_runs=False,allow_actor_only=False,frame_limits=(4,900)):
    from action_studio_server import allowed_file
    if not isinstance(url,str) or not url.startswith('/files/') or '?' in url or '#' in url:raise ValueError('Select a saved scene')
    path=allowed_file(url)
    if path is None or path.suffix!='.json' or not path.is_file():raise ValueError('Saved scene not found')
    initial_hash=sha256(path);bundle=read(path)
    if sha256(path)!=initial_hash:raise ValueError('Scene changed while reading')
    scene=bundle.get('scene')
    if not isinstance(scene,dict) or scene.get('fps')!=30 or scene.get('schema_version')!=1:raise ValueError('Saved 30fps scene required')
    frames=scene.get('frame_count')
    if not isinstance(frame_limits,tuple) or len(frame_limits)!=2 or any(type(n) is not int for n in frame_limits) or not 3<=frame_limits[0]<=frame_limits[1]<=901:
        raise ValueError('Invalid source frame limits')
    if type(frames)!=int or not frame_limits[0]<=frames<=frame_limits[1]:raise ValueError(f'Scene must contain {frame_limits[0]}–{frame_limits[1]} frames')
    base=None
    for parent in path.parents:
        if parent==ROOT/'reports':break
        manifest=parent/'manifest.json'
        if manifest.exists() and any((parent/value).resolve()==path.resolve() for s in read(manifest).get('scenes',[]) for value in s.get('variants',{}).values()):base=parent;break
    if base is None:raise ValueError('Scene is not registered in its saved collection')
    if not isinstance(scene.get('actors'),dict) or not 1<=len(scene['actors'])<=4:raise ValueError('Scene needs one to four native actors')
    if not isinstance(scene.get('objects'),dict) or not (0 if allow_actor_only else 1)<=len(scene['objects'])<=8:raise ValueError('Scene object count is unsupported')
    files={path:sha256(path)}
    for name,entry in scene['actors'].items():
        name_check(name);pose(entry['transform'])
        motion=(ROOT/entry['motion']).resolve();glb=(base/entry['preview_glb']).resolve()
        motion_roots=[(ROOT/'reports').resolve()]+([(ROOT/'runs').resolve()] if allow_native_runs else [])
        if not any(motion.is_relative_to(r) for r in motion_roots) or motion.suffix!='.npz' or not glb.is_relative_to(base.resolve()) or glb.suffix!='.glb':raise ValueError('Scene asset escapes saved collection')
        for asset in [motion,glb]:files[asset]=sha256(asset)
        with np.load(motion,allow_pickle=False) as arrays:
            if arrays['posed_joints'].shape!=(frames,77,3) or arrays['global_rot_mats'].shape!=(frames,77,3,3):raise ValueError('Release currently requires native 77-joint scene actors')
    for name,obj in scene['objects'].items():
        name_check(name);sample_object(obj,frames)
        geometry=scene_geometry(obj);dimensions=geometry.local_size()
        if min(dimensions)<.01 or max(dimensions)>10:raise ValueError('Primitive dimensions/diameter must be 0.01–10 metres')
    license_path=base/'SOMA-preview-LICENSE.txt'
    if not license_path.exists():license_path=ROOT/'vendor/kimodo/LICENSE'
    for asset in [path.parent/'events.json',license_path]:
        if asset.exists():files[asset]=sha256(asset)
    revision=hashlib.sha256(json.dumps({p.relative_to(ROOT).as_posix():v for p,v in files.items()},sort_keys=True).encode()).hexdigest()
    return dict(path=path,base=base,bundle=bundle,files=files,revision=revision)


def metadata(url):
    source=source_metadata(url);scene=source['bundle']['scene']
    return dict(source_url=url,revision=source['revision'],frames=scene['frame_count'],objects=list(scene['objects']),
        earliest_release={name:max([2]+[c['end_frame']+1 for c in scene['contacts'] if c.get('target',{}).get('space')=='object' and c['target'].get('object')==name]) for name in scene['objects']},
        supported='Saved native humanoid scenes; box/sphere release against floor, static primitives or prescribed moving primitives (Jolt). Prescribed objects retain authored motion and do not react to impacts. Optional actor proxies do not produce actor response.')


def validate(payload):
    keys={'source_url','revision','object','release_frame','mass_kg','friction','restitution','label'}
    if not isinstance(payload,dict) or not keys<=set(payload) or set(payload)-keys-{'collision_mode','actor_collision_mode'}:raise ValueError('Invalid release fields')
    mode=payload.get('collision_mode','floor_only')
    if mode not in ['floor_only','static_scene','moving_scene']:raise ValueError('Unknown collision mode')
    actor_mode=payload.get('actor_collision_mode','none')
    if actor_mode not in ['none','convex_skin']:raise ValueError('Unknown actor collision mode')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'].strip())<=100:raise ValueError('Name must contain 1–100 characters')
    source=source_metadata(payload['source_url'])
    if payload['revision']!=source['revision']:raise ValueError('Saved scene or assets changed; reload before release')
    scene=source['bundle']['scene'];name=payload['object']
    if not isinstance(name,str) or name not in scene['objects']:raise ValueError('Select a saved primitive object')
    if type(payload['mass_kg']) not in (int,float) or not .05<=payload['mass_kg']<=2000:raise ValueError('Mass must be 0.05–2000 kg')
    release=payload['release_frame']
    if type(release)!=int or not 2<=release<scene['frame_count']-1:raise ValueError('Release needs two incoming frames and an output tail')
    if any(c.get('target',{}).get('space')=='object' and c['target'].get('object')==name and c['end_frame']>=release for c in scene['contacts']):raise ValueError('Release conflicts with a saved contact window; choose a frame after its end')
    p,r=sample_object(scene['objects'][name],scene['frame_count'])
    track=dict(fps=30,object=name,**geometry_fields(scene['objects'][name]),positions_m=p.tolist(),rotations_xyzw=Rotation.from_matrix(r).as_quat().tolist())
    geometry=body_geometry(track)
    request=release_request(track,release,mass_kg=payload['mass_kg'],friction=payload['friction'],restitution=payload['restitution'])
    if mode=='static_scene':
        from release_colliders import compile_colliders,box_separation
        request['static_colliders']=compile_colliders(scene,name,release,friction=payload['friction'],restitution=payload['restitution'])
        for collider in request['static_colliders']:
            if primitive_gap(geometry,p[release],r[release],body_geometry(collider),collider['position_m'],Rotation.from_quat(collider['rotation_xyzw']).as_matrix()) < -.001:
                raise ValueError('Released object overlaps static collider '+collider['id']+' at release; choose a clear pose')
    if mode=='moving_scene':
        from moving_release_colliders import compile_moving
        from release_colliders import box_separation
        request['backend']='Jolt Physics'
        request['moving_colliders']=compile_moving(scene,name,release,physics_fps=request['physics_fps'],friction=payload['friction'],restitution=payload['restitution'])
        for collider in request['moving_colliders']:
            if primitive_gap(geometry,p[release],r[release],body_geometry(collider),collider['positions_m'][1],Rotation.from_quat(collider['rotations_xyzw'][1]).as_matrix()) < -.001:
                raise ValueError('Released object overlaps moving collider '+collider['id']+' at release; choose a clear pose')
    if actor_mode=='convex_skin':
        from actor_collision_proxies import compile_actor_proxies
        from convex_colliders import ConvexBoxTest,ConvexSphereTest
        proxies,calibration=compile_actor_proxies(scene,source['base'],release,physics_fps=request['physics_fps'],friction=payload['friction'],restitution=payload['restitution'])
        for collider in proxies:
            center=np.array(collider['positions_m'][1]);rotation=Rotation.from_quat(collider['rotations_xyzw'][1]).as_matrix()
            gap=ConvexBoxTest(collider['points_m']).gap(p[release],r[release],geometry.dimensions,center,rotation) if geometry.shape=='box' else ConvexSphereTest(collider['points_m']).gap(p[release],geometry.dimensions[0],center,rotation)
            if gap < -.001:
                raise ValueError('Released object overlaps body proxy '+collider['id']+' at release; retain or revise the authored pose')
        request['backend']='Jolt Physics';request['moving_colliders']=request.get('moving_colliders',[])+proxies
        source['actor_proxy_calibration']=calibration
    return source,track,request


def prepare(payload,folder):
    source,track,physics=validate(payload);folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    original=source['bundle'];bundle=copy.deepcopy(original)
    (folder/'source').mkdir()
    shutil.copyfile(source['path'],folder/'source/original-bundle.json')
    if sha256(folder/'source/original-bundle.json')!=source['files'][source['path']]:raise ValueError('Scene changed during snapshot')
    for name,entry in bundle['scene']['actors'].items():
        for field,original_path,filename in [('motion',ROOT/entry['motion'],'motion.npz'),('preview_glb',source['base']/entry['preview_glb'],'actor.glb')]:
            target=folder/'source/actors'/name/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original_path,target)
            if sha256(target)!=source['files'][original_path.resolve()]:raise ValueError('Source changed during snapshot')
            entry[field]=target.relative_to(ROOT if field=='motion' else folder).as_posix()
    events_path=source['path'].parent/'events.json'
    if events_path.exists():
        shutil.copyfile(events_path,folder/'source/events.json')
        if sha256(folder/'source/events.json')!=source['files'].get(events_path):raise ValueError('Events changed during snapshot')
    else:
        from package_generated_scenes import contact_events
        save(folder/'source/events.json',contact_events(bundle['scene']))
    license_path=source['base']/'SOMA-preview-LICENSE.txt'
    if not license_path.exists():license_path=ROOT/'vendor/kimodo/LICENSE'
    shutil.copyfile(license_path,folder/'source/LICENSE.txt')
    if sha256(folder/'source/LICENSE.txt')!=source['files'][license_path]:raise ValueError('License changed during snapshot')
    save(folder/'source/bundle.json',bundle);save(folder/'source/object-track.json',track)
    if 'actor_proxy_calibration' in source:save(folder/'source/actor-proxies.json',source['actor_proxy_calibration'])
    snapshot=folder/'source/implementation';snapshot.mkdir()
    for name in ['scene_release_job.py','scene_object_export.py','object_geometry_mesh.py','object_release.py','godot_object_release.gd','scene_constraints.py','object_geometry.py','audit_scene_orientation.py',
                 'strep.py','object_dynamics.py','gltf_tools.py','package_generated_scenes.py','inspect_motion.py','floor_contact.py','palm_contacts.py','build_soma_preview.py','release_colliders.py','moving_release_colliders.py',
                 'convex_colliders.py','actor_collision_proxies.py','rig_asset.py','rig_clip_import.py','scene_runtime.py','godot_scene_clock.gd','release_geometry.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    files={p.relative_to(folder).as_posix():sha256(p) for p in (folder/'source').rglob('*') if p.is_file()}
    save(folder/'request.json',dict(authored=payload,physics=physics,files=files,created_at=now()))
    save(folder/'pipeline.json',dict(status='starting',stage='Prepared immutable scene'))


def run(folder):
    from scene_constraints import evaluate
    from scene_object_export import export_objects
    from build_soma_preview import ASSET
    from audit_scene_orientation import audit
    folder=Path(folder).resolve()
    try:
        with worker_lock():
            import os,psutil
            save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
            request=read(folder/'request.json');payload=request['authored'];release=payload['release_frame'];name=payload['object']
            for filename,digest in request['files'].items():
                if sha256(folder/filename)!=digest:raise ValueError('Saved input changed')
            for script in (folder/'source/implementation').iterdir():
                if sha256(ROOT/'scripts'/script.name)!=sha256(script):raise ValueError('Release implementation changed after preparation')
            save(folder/'pipeline.json',dict(status='processing',stage='Simulating released object'))
            original=read(folder/'source/bundle.json');track=read(folder/'source/object-track.json')
            simulation=simulate(request['physics'],folder/'simulation');candidate=bake(track,release,request['physics'],simulation)
            result=copy.deepcopy(original);scene=result['scene'];scene['id']=payload['label'].strip()
            scene['objects'][name]['keyframes']=[dict(frame=i,translation_m=p,rotation_xyzw=q) for i,(p,q) in enumerate(zip(candidate['positions_m'],candidate['rotations_xyzw']))]
            scene['objects'][name]['trajectory_provenance']=candidate['provenance']
            count=len(request['physics'].get('static_colliders',[]));moving_count=len(request['physics'].get('moving_colliders',[]))
            actor_mode=payload.get('actor_collision_mode','none')
            scene['review_note']=f"Authored release at frame {release}: {payload['mass_kg']:g} kg, friction {payload['friction']:g}, bounce {payload['restitution']:g}. Hypothetical physical properties; floor and {count} static and {moving_count} prescribed colliders. Prescribed colliders keep authored motion and do not react to impacts. Body proxy mode: {actor_mode}. Convex skin envelopes are approximate; inspect calibration distances and retained skin/contact failures. No actor response or animator approval."
            save(folder/'pipeline.json',dict(status='processing',stage='Auditing contacts and exporting scene'))
            skin=dict(np.load(ASSET,allow_pickle=False));result['evaluation']=evaluate(scene,skin)
            orientation=audit(scene,skin);save(folder/'orientation-audit.json',orientation)
            save(folder/'input.json',original);save(folder/'candidate.json',result);save(folder/'object-track.json',candidate)
            events=read(folder/'source/events.json')
            # A dynamics-start marker does not rewrite historical grasp/release
            # annotations, nor assert that the hand contact was successful.
            events['events'].append(dict(type='dynamic_release_start',object=name,frame=release,time_s=release/30,provenance='Authored bake request'))
            save(folder/'events.json',events)
            export_objects(original['scene'],folder/'input-objects.glb');export_objects(scene,folder/'objects.glb')
            obs=simulation['observations'];p=np.array([o['position_m'] for o in obs]);r=Rotation.from_quat([o['rotation_xyzw'] for o in obs]).as_matrix()
            bottom=floor_gaps(body_geometry(track),p,r);contacts=[o['tick'] for o in obs if 'floor' in o['contact_colliders']]
            floor_depth=float(max(0.,-bottom.min()));gap=float(abs(bottom[-1]));speed=float(np.linalg.norm(obs[-1]['linear_velocity_m_s']))
            release_audit=dict(release_frame=release,simulated_floor_depth_max_m=floor_depth,final_floor_gap_m=gap,final_speed_m_s=speed,
                first_floor_contact_source_frame=release+contacts[0]*30/request['physics']['physics_fps'] if contacts else None,
                floor_screens_passed=floor_depth<=.01 and gap<=.01 and speed<=.1,physics_approval=None,
                scope='Floor proximity/settling screens only; a primitive resting on a scene surface may correctly remain above the floor. Rolling or bouncing actions need different acceptance criteria. Inspect separate scene-collision screens. No actor or animator approval.')
            from release_colliders import audit_collisions
            release_audit['scene_collisions']=audit_collisions(request['physics'],obs,release)
            release_audit['collision_mode']=payload.get('collision_mode','floor_only')
            release_audit['actor_collision_mode']=actor_mode
            if (folder/'source/actor-proxies.json').exists():
                calibration=read(folder/'source/actor-proxies.json')
                release_audit['actor_proxy_calibration']=[{k:v for k,v in row.items() if k!='parts_geometry'} for row in calibration['actors']]
            save(folder/'release-audit.json',release_audit)
            portable=copy.deepcopy(scene)
            for entry in portable['actors'].values():entry['motion']=str(Path(entry['motion']).relative_to(folder.relative_to(ROOT))).replace('\\','/')
            portable['objects_glb']='objects.glb';save(folder/'portable-scene.json',portable)
            from scene_runtime import write as write_scene_runtime
            write_scene_runtime(folder)
            items=[dict(id=kind,label=payload['label'].strip()+' · '+label,variants=dict(palm=kind+'.json'),
                review_note=scene['review_note'] if kind=='candidate' else 'Preserved input scene.',
                downloads=[dict(label='Scene package · ZIP',path='scene-animation.zip'),dict(label='Object GLB',path='objects.glb' if kind=='candidate' else 'input-objects.glb'),dict(label='Events',path='events.json')],
                **(dict(release_file='release-audit.json',orientation_file='orientation-audit.json',**(dict(actor_proxy_file='source/actor-proxies.json') if actor_mode=='convex_skin' else {})) if kind=='candidate' else {})) for kind,label in [('input','Input'),('candidate','Release candidate')]]
            save(folder/'manifest.json',dict(scenes=items,assets={entry['preview_glb']:dict(sha256=sha256(folder/entry['preview_glb'])) for entry in scene['actors'].values()}))
            paths=[p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in ('.json','.glb','.npz','.txt','.md','.gd','.py') and p.name not in ['worker.json','pipeline.json','manifest.json'] and 'project' not in p.parts]
            with zipfile.ZipFile(folder/'scene-animation.zip','w',zipfile.ZIP_DEFLATED) as archive:
                for path in paths:archive.write(path,path.relative_to(folder).as_posix())
                archive.writestr('README.txt','GODOT-SCENES.md describes the included shared-clock loader, scene-runtime.json and godot_scene_clock.gd. It owns all actor/object animation tracks and their authored event notifications. Load objects.glb and each source/actors/<id>/actor.glb on the same 30fps clock; apply actor placements from portable-scene.json once. Object tracks already use scene coordinates. Preserve constant scale tracks (disable remove immutable tracks in Godot import) to avoid quaternion-to-Euler fallback. This is a baked animation, with no runtime physics required; do not also drive baked objects with live physics. See request.json for explicit backend, floor/static/prescribed-primitive colliders and material assumptions. No actor response, human balance or animator approval.\n')
            with zipfile.ZipFile(folder/'scene-animation.zip') as archive:
                assert archive.testzip() is None
            save(folder/'result.json',dict(status='ready_for_review',collection=folder.relative_to(ROOT/'reports').as_posix(),quality_approved=False,package_sha256=sha256(folder/'scene-animation.zip')))
            save(folder/'pipeline.json',dict(status='complete',stage='Ready for review',finished_at=now()))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);args=parser.parse_args();run(args.folder)
