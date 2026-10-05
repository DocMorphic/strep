"""Offline finite native grip/physics capture to editable prop GLBs.

Preserves source actors/geometry, exact clock evidence and physical failures.
No model, renderer, production skin query or anatomy/contact inference.
"""
import argparse,copy,hashlib,json,math,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from action_worker_lock import worker_lock
from process_monitor import kill_tree
from scene_prop_runtime import GDS,compile_request,entry_files,matrix
from native_scene_runtime import METHODS as NATIVE_METHODS,configure
from native_object_asset import ObjectAsset,stored_clock
from native_engine_clock import clock_wire
from gltf_tools import read_glb,write_glb,append_accessor
from object_release import ENGINE
from strep import ROOT,now,read,save,sha256,offline_environment

CAPTURE='godot_scene_prop_capture.gd'
IMPORT='godot_native_object_asset.gd'
ENGINE_SHA256='c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643'
POSE_LIMIT=3e-5
METHODS=tuple(dict.fromkeys(NATIVE_METHODS+GDS+(CAPTURE,IMPORT,'scene_prop_bake.py','scene_prop_runtime.py','scene_prop_ownership.py','primitive_penetration_bounds.py','process_monitor.py','object_release.py','release_geometry.py','release_colliders.py','moving_release_colliders.py','object_dynamics.py')))


def require(value,message):
    if not value:raise ValueError(message)


def member_hash(archive,name):
    h=hashlib.sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def load_package(source,project):
    """Whole verified extraction; only current SDK scripts may be executed."""
    with zipfile.ZipFile(source) as z:
        names=z.namelist();require(len(names)==len(set(n.casefold() for n in names)) and len(names)<512 and sum(i.file_size for i in z.infolist())<=1024**3,'Unique bounded complete runtime ZIP required')
        require(all(n and not PurePosixPath(n).is_absolute() and '\\' not in n and ':' not in n and all(p not in ('','.','..') for p in n.split('/')) for n in names),'Portable runtime paths required')
        m=json.loads(z.read('package.json'))
        require(m['schema']=='strep-scene-prop-runtime-package-v1' and m['status']=='complete' and set(names)==set(m['files_sha256'])|{'package.json'},'Complete native prop runtime package required')
        require(m['source_bytes_unchanged'] is True and all(m[k] is False for k in ('engine_executed','physics_verified','animation_quality_approved','release_approved')),'Original package scope required')
        require(set(m['runtime_methods_sha256'])==set(GDS),'Complete runtime methods required')
        for n,h in m['files_sha256'].items():require(member_hash(z,n)==h,'Runtime ZIP member changed')
        for n in GDS:require(m['runtime_methods_sha256'][n]==m['files_sha256']['ownership-v1/'+n]==sha256(ROOT/'scripts'/n),'Runtime script differs from trusted current SDK')
        require(hashlib.sha256(z.read('ownership-v1/ownership-authoring-request.json')).hexdigest()==m['ownership_request_sha256'],'Source authoring request changed')
        project.mkdir()
        for n in names:
            p=project/n;p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(n) as src,p.open('xb') as dst:shutil.copyfileobj(src,dst)
    original=read(project/'source-game-package.json')
    require(original['schema']=='strep-native-scene-game-package-v1' and original['original_selected'] is True and original['root_removed_from_character_clips'] is False
        and original['root_application_mode']=='reference-only-motion-remains-embedded','Original embedded game package required')
    require(all(original[k] is False for k in ('quality_approved','physics_verified','release_approved','animation_runtime_playback_verified')),'Original source approvals required')
    for n,h in original['files_sha256'].items():require(n in m['files_sha256'] and isinstance(h,str) and len(h)==64 and m['files_sha256'][n]==h,'Original source bytes differ')
    request=read(project/'ownership-v1/ownership-authoring-request.json')
    config,scene,times,events=configure(project,original,request['root_modes'])
    compiled=compile_request(request,config,scene,events,m['source_game_zip_sha256'])
    require(read(project/'ownership-v1/prop-runtime.json')==compiled,'Runtime bindings differ from bound authoring request')
    for n,text in entry_files(compiled['physics_fps']).items():require((project/n).read_text().replace('\r\n','\n')==text,'Runtime startup/rate differs')
    return m,original,compiled,scene,times,events


def validate_request(request,source_digest):
    require(isinstance(request,dict) and set(request)=={'schema','source_runtime_zip_sha256','parent_world_transform','floor'} and request['schema']=='strep-scene-prop-bake-request-v1','Exact explicit bake request required')
    require(request['source_runtime_zip_sha256']==source_digest,'Bake binds another runtime ZIP')
    matrix(request['parent_world_transform'])
    floor=request['floor'];require(isinstance(floor,dict) and set(floor)=={'enabled','height_m','friction','restitution'} and type(floor['enabled']) is bool,'Explicit floor settings required')
    for key,low,high in [('height_m',-10000,10000),('friction',0,1),('restitution',0,1)]:
        require(type(floor[key]) in (int,float) and np.isfinite(floor[key]) and low<=floor[key]<=high,'Finite bounded floor '+key+' required')
    return copy.deepcopy(request)


def physical_clock(duration,rate):
    require(type(rate) is int and rate in (60,120,240) and type(duration) in (int,float) and np.isfinite(duration) and duration>0,'Positive finite duration and supported physics rate required')
    last=math.ceil(duration*rate)
    while last/rate<duration:last+=1
    while last>0 and (last-1)/rate>=duration:last-=1
    require(1<=last<=14400,'Complete finite bake exceeds physics-step budget; no truncation')
    return np.arange(last+1,dtype='<f8')/rate


def decoded(value,count,label):
    require(isinstance(value,str) and len(value)==count*16,'Exact '+label+' Float64 bytes required')
    try:b=bytes.fromhex(value)
    except ValueError as exc:raise ValueError('Invalid '+label+' bytes') from exc
    require(b.hex()==value,'Canonical '+label+' bytes required')
    a=np.frombuffer(b,dtype='<f8');require(len(a)==count and np.isfinite(a).all(),'Finite '+label+' required');return a


def bits(time):return np.asarray([time],dtype='<f8').tobytes().hex()


def pose(value):
    t=decoded(value,16,'pose').reshape(4,4)
    require(np.array_equal(t[3],[0,0,0,1]) and abs(np.linalg.det(t[:3,:3])-1)<=POSE_LIMIT and abs(t[:3,:3].T@t[:3,:3]-np.eye(3)).max()<=POSE_LIMIT,'Rigid bounded captured pose required')
    return t


def grip_pose(scene,binding,prop,time):
    a=scene.actors[binding['actor']];p,r=a['placement'];place=np.eye(4);place[:3,:3]=r;place[:3,3]=p
    return place@a['sampler'].sample(time)[binding['joint_node']]@np.asarray(binding['prop_offsets'][prop])


def audit_capture(actual,compiled,scene,events,request,request_digest):
    clock=physical_clock(scene.duration,compiled['physics_fps']);source=np.minimum(clock,scene.duration)
    require(actual['schema']=='strep-scene-prop-capture-v1' and actual['request_sha256']==request_digest and actual['physics_fps']==compiled['physics_fps'] and actual['faults']==[],'Capture request/physics/fault mismatch')
    rows=actual['records'];require(len(rows)==len(clock),'Complete finite capture required')
    event_times=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    expected_events=[dict(id=e['id'],source_time_f64le=bits(event_times[e['sample_index']]),pose_time_f64le=bits(event_times[e['sample_index']])) for e in events['events'] if e['runtime_dispatch_allowed']]
    require(actual['events']==expected_events,'Complete exact native marker callback population required')
    planned=[]
    for g in compiled['ownership']['groups']:
        t=event_times[g['sample_index']];tick=int(np.searchsorted(clock,t))
        for tr in g['transitions']:
            ids=list(dict.fromkeys(c['event_id'] for c in tr['changes']))
            planned.append(dict(object=tr['object'],before=tr['before'],after=tr['after'],event_ids=ids,tick=tick,source_time_f64le=bits(t),application_time_f64le=bits(clock[tick]),last_grip_released=tr['last_grip_released']))
    require(len(actual['actions'])==len(planned),'Complete ownership application population required')
    applications=[]
    for action,expected in zip(actual['actions'],planned):
        require(set(action)==set(expected)|{'pose_f64le'} and all(action[k]==v for k,v in expected.items()),'Ownership application differs from native plan')
        require(type(action['tick']) is int and type(action['last_grip_released']) is bool,'Explicit captured application types required')
        pose(action['pose_f64le']);time=decoded(action['source_time_f64le'],1,'source time')[0];applied=decoded(action['application_time_f64le'],1,'application time')[0]
        applications.append({**expected,'application_delay_s':float(applied-time)})
    members={n:[] for n in compiled['props']};modes={n:'parked' for n in members};cursor=0;arrays={n:[] for n in scene.objects};held_error=0.;authored_error=0.;floor_depth={n:0. for n in scene.objects};orthogonal_error=0.
    parent=np.asarray(request['parent_world_transform']);allowed_contacts=set(compiled['props'])|({'floor'} if request['floor']['enabled'] else set())
    for index,row in enumerate(rows):
        require(type(row['tick']) is int and row['tick']==index and row['physics_time_f64le']==bits(clock[index]) and row['source_time_f64le']==row['pose_time_f64le']==bits(source[index]),'Exact shared physics/source pose clock required')
        require(set(row['actor_ids'])==set(scene.actors) and len(row['actor_ids'])==len(scene.actors) and set(row['props'])==set(scene.objects),'Complete actor/prop capture required')
        while cursor<len(planned) and planned[cursor]['tick']<=index:
            tr=planned[cursor];members[tr['object']]=tr['after'];modes[tr['object']]='held' if tr['after'] else 'released';cursor+=1
        require(row['members']==members and row['modes']==modes,'Captured ownership state differs')
        for n,obj in scene.objects.items():
            p=row['props'][n];t=pose(p['pose_f64le']);arrays[n].append(t)
            orthogonal_error=max(orthogonal_error,float(abs(t[:3,:3]-Rotation.from_matrix(t[:3,:3]).as_matrix()).max()))
            if compiled['object_modes'][n]=='authored':
                require(p['mode']=='authored' and p['contacts']==[],'Authored reference cannot claim body contacts')
                pos,rot=scene.object_poses(n,np.array([source[index]]));expected=np.eye(4);expected[:3,3]=pos[0];expected[:3,:3]=rot[0]
                authored_error=max(authored_error,float(abs(t-expected).max()))
            else:
                require(p['mode']==modes[n] and p['direct_state_class']=='JoltPhysicsDirectBodyState3D' and abs(p['step_s']-1/compiled['physics_fps'])<=1e-9,'Actual Jolt step/mode required')
                require(isinstance(p['contacts'],list) and set(p['contacts'])<=allowed_contacts,'Unknown captured collider')
                dynamic=modes[n]=='released';physics=compiled['props'][n]['physics']
                require(type(p['collision_layer']) is int and type(p['collision_mask']) is int and p['collision_layer']==(physics['collision_layer'] if dynamic else 0) and p['collision_mask']==(physics['collision_mask'] if dynamic else 0),'Captured collision mode differs')
                if modes[n]!='released':
                    expected=np.asarray(compiled['props'][n]['initial_pose']) if modes[n]=='parked' else grip_pose(scene,compiled['grip_bindings'][sorted(members[n])[0]],n,source[index])
                    held_error=max(held_error,float(abs(t-expected).max()))
            if request['floor']['enabled']:
                world=parent@t;rotation=Rotation.from_matrix(world[:3,:3]).as_matrix()
                depth=max(0.,request['floor']['height_m']-(world[1,3]-obj['geometry'].world_half_extents(rotation)[1]));floor_depth[n]=max(floor_depth[n],float(depth))
    require(held_error<=POSE_LIMIT and authored_error<=POSE_LIMIT,'Captured held/authored source poses differ beyond native bound')
    delay=max((a['application_delay_s'] for a in applications),default=0.)
    return dict(clock=clock_wire(clock),source_clock=clock_wire(source),samples=len(clock),applications=applications,
        maximum_application_delay_s=delay,exact_physical_event_timing_pass=delay==0.,held_pose_maximum_element_error=held_error,authored_pose_maximum_element_error=authored_error,
        floor_sampled_depth_max_m=floor_depth,floor_sampled_screen_pass=all(d<=.01 for d in floor_depth.values()) if request['floor']['enabled'] else None,
        floor_depth_uses_orthogonalized_observed_basis=True,maximum_pose_rotation_projection_error=orthogonal_error,
        continuous_collision_certified=False,physics_quality_approved=False,quality_approved=False,release_approved=False),{n:np.asarray(v) for n,v in arrays.items()}


def interpolated(times,poses,query):
    query=np.clip(np.asarray(query),times[0],times[-1]);p=poses[:,:3,3]
    return np.stack([np.interp(query,times,p[:,i]) for i in range(3)],axis=1),Slerp(times,Rotation.from_matrix(poses[:,:3,:3]))(query).as_matrix()


def export_bake(source_asset,path,clock,captured,modes):
    """Append physical TRS only; original mesh bytes and authored tracks survive."""
    old_doc,old_binary=read_glb(source_asset);old=ObjectAsset(source_asset);doc=copy.deepcopy(old_doc);binary=bytearray(old_binary);animation=doc['animations'][0];clocks={}
    require(set(captured)==set(old.objects)==set(modes),'Complete baked object population required')
    physical={n for n,v in modes.items() if v=='grip-physics'}
    animation['channels']=[c for c in animation['channels'] if doc['nodes'][c['target']['node']]['extras']['strep_object_id'] not in physical]
    for node,item in enumerate(doc['nodes']):
        n=item['extras']['strep_object_id']
        if n not in physical:continue
        stored,clocks[n]=stored_clock(clock);require(not clocks[n]['collision_groups'],'Complete physics clock cannot collapse in Float32')
        p,r=interpolated(clock,captured[n],stored);q=Rotation.from_matrix(r).as_quat()
        for i in range(1,len(q)):
            if q[i]@q[i-1]<0:q[i]*=-1
        item['translation']=p[0].astype('<f4').astype(float).tolist();item['rotation']=q[0].astype('<f4').astype(float).tolist()
        ti=append_accessor(doc,binary,stored,'SCALAR')
        for prop,values,kind in [('translation',p,'VEC3'),('rotation',q,'VEC4'),('scale',np.ones_like(p),'VEC3')]:
            sampler=len(animation['samplers']);animation['samplers'].append(dict(input=ti,output=append_accessor(doc,binary,values,kind),interpolation='LINEAR'));animation['channels'].append(dict(sampler=sampler,target=dict(node=node,path=prop)))
    doc.setdefault('extras',{}).update(strep_original_duration_s=old_doc.get('extras',{}).get('strep_source_duration_s'),strep_source_duration_s=float(clock[-1]),strep_bake_clock_scope='fixed-physics-boundaries; native event intent remains separate')
    write_glb(path,doc,binary);new_doc,new_binary=read_glb(path);require(new_binary[:len(old_binary)]==old_binary and new_doc['meshes']==old_doc['meshes'] and new_doc.get('materials')==old_doc.get('materials'),'Original mesh payload changed')
    asset=ObjectAsset(path);queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2]);checks={}
    for n in modes:
        expected=interpolated(clock,captured[n],queries) if n in physical else old.object_poses(n,queries)
        actual=asset.object_poses(n,queries);error=max(float(abs(a-b).max()) for a,b in zip(expected,actual))
        checks[n]=dict(samples=len(queries),maximum_pose_component_error=error,passed=error<=POSE_LIMIT,authored_channels_preserved=n not in physical)
    require(all(v['passed'] for v in checks.values()),'Decoded baked interpolation differs')
    return asset,dict(clock_storage=clocks,decoded_tracks=checks,original_mesh_payload_unchanged=True,quality_approved=False,release_approved=False)


def engine_run(project,script,request,output,log,timeout):
    with Path(log).open('w',encoding='utf8') as stream:
        p=subprocess.Popen([str(ENGINE),'--headless','--path',str(project),'--script',script,'--',str(Path(request).resolve()),str(Path(output).resolve())],stdout=stream,stderr=subprocess.STDOUT,env=offline_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        terminal=Path(str(log)+'.terminal.json')
        try:
            p.wait(timeout=timeout)
        except BaseException:
            if p.poll() is None:kill_tree(p.pid)
            p.wait();save(terminal,dict(pid=p.pid,exit_code=p.returncode,owned_tree_stopped=True));raise
        save(terminal,dict(pid=p.pid,exit_code=p.returncode,owned_tree_stopped=True))
    require(p.returncode==0,'Offline engine stage failed; raw output/log retained')
    return read(output)


def import_errors(imported,asset,queries):
    errors={}
    for mode in ('default-import','native-authoring'):
        require(set(imported[mode])==set(asset.objects),'Complete baked engine object import required');maximum=0.
        for n in asset.objects:
            rows=imported[mode][n];require(len(rows)==len(queries),'Complete baked engine sample population required')
            require([x['time_f64le'] for x in rows]==[bits(t) for t in queries],'Exact baked engine evaluation clock required')
            p,r=asset.object_poses(n,queries);actual_p=np.array([x['translation_m'] for x in rows]);actual_r=Rotation.from_quat([x['rotation_xyzw'] for x in rows]).as_matrix()
            require(np.isfinite(actual_p).all(),'Finite engine positions required')
            maximum=max(maximum,float(abs(actual_p-p).max()),float(abs(actual_r-r).max()))
        errors[mode]=maximum
    return errors


def audit_baked_motion(asset,queries,compiled,scene,applications,request):
    """Between-boundary grip/floor screens are separate from export fidelity."""
    members={n:[] for n in compiled['props']};cursor=0;held_position=0.;held_rotation=0.;floor_depth={n:0. for n in scene.objects}
    parent=np.asarray(request['parent_world_transform']);poses={n:asset.object_poses(n,queries) for n in scene.objects}
    for i,time in enumerate(queries):
        while cursor<len(applications) and decoded(applications[cursor]['application_time_f64le'],1,'application time')[0]<=time:
            a=applications[cursor];members[a['object']]=a['after'];cursor+=1
        for n,obj in scene.objects.items():
            p,r=poses[n];t=np.eye(4);t[:3,3]=p[i];t[:3,:3]=r[i]
            if n in members and members[n]:
                for grip in members[n]:
                    wanted=grip_pose(scene,compiled['grip_bindings'][grip],n,min(time,scene.duration))
                    held_position=max(held_position,float(np.linalg.norm(t[:3,3]-wanted[:3,3])))
                    held_rotation=max(held_rotation,float(Rotation.from_matrix(t[:3,:3]@wanted[:3,:3].T).magnitude()))
            if request['floor']['enabled']:
                world=parent@t;extent=obj['geometry'].world_half_extents(Rotation.from_matrix(world[:3,:3]).as_matrix())[1]
                floor_depth[n]=max(floor_depth[n],float(max(0.,request['floor']['height_m']-world[1,3]+extent)))
    plan=compiled['ownership']
    return dict(samples=len(queries),held_grip_position_error_max_m=held_position,held_grip_rotation_error_max_rad=held_rotation,
        held_grip_sampled_conditions_pass=held_position<=plan['position_tolerance_m'] and held_rotation<=plan['rotation_tolerance_rad'],
        floor_sampled_depth_max_m=floor_depth,floor_sampled_screen_pass=all(d<=.01 for d in floor_depth.values()) if request['floor']['enabled'] else None,
        includes_physics_midpoints_and_native_event_times=True,continuous_collision_certified=False,anatomical_contact_verified=False,quality_approved=False,release_approved=False)


def bake(source,request_path,output):
    source=Path(source).resolve();request_path=Path(request_path).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh bake output required')
    digest=sha256(source);request_bytes=request_path.read_bytes();request=validate_request(json.loads(request_bytes),digest)
    require(sha256(ENGINE)==ENGINE_SHA256,'Pinned headless engine changed')
    with worker_lock():
        output.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now()))
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};archive=output/'methods';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        shutil.copyfile(source,output/'source-runtime.zip');(output/'bake-request.json').write_bytes(request_bytes)
        try:
            project=output/'capture-project';m,original,compiled,scene,_,events=load_package(output/'source-runtime.zip',project)
            clock=physical_clock(scene.duration,compiled['physics_fps']);shutil.copyfile(archive/CAPTURE,project/'ownership-v1'/CAPTURE)
            capture_request=dict(asset_folder=str(project),config=compiled,parent_world_transform=request['parent_world_transform'],floor=request['floor'],last_tick=len(clock)-1)
            save(output/'capture-request.json',capture_request);save(output/'pipeline.json',dict(status='capturing',at=now()))
            actual=engine_run(project,'ownership-v1/'+CAPTURE,output/'capture-request.json',output/'capture.json',output/'capture.log',180)
            audit,poses=audit_capture(actual,compiled,scene,events,request,sha256(output/'capture-request.json'));save(output/'capture-audit.json',audit)
            assets=output/'assets';assets.mkdir();reference=assets/'reference';reference.mkdir()
            for n in list(original['files_sha256'])+['source-game-package.json']:
                dest=reference/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/n,dest)
            asset,storage=export_bake(project/'objects.glb',assets/'objects.glb',clock,poses,compiled['object_modes']);save(assets/'bake-storage.json',storage);save(assets/'bake-audit.json',audit)
            source_scene=read(project/'scene.json')
            actors={n:dict(**{**entry,'glb':'reference/'+entry['glb']},root_motion='original-embedded',end_policy='hold-original-end') for n,entry in source_scene['actors'].items()}
            save(assets/'composition.json',dict(schema='strep-baked-prop-composition-v1',duration_s=float(clock[-1]),source_duration_s=scene.duration,clock=audit['clock'],source_clock=audit['source_clock'],
                actors=actors,
                objects=dict(path='objects.glb',sha256=sha256(assets/'objects.glb'),modes=compiled['object_modes']),root_references='reference/root-motion.json',marker_intent='reference/events.json',contact_intent_scope='unchanged-authored-reference-only',
                parent_world_transform=request['parent_world_transform'],floor_world=request['floor'],quality_approved=False,release_approved=False))
            import_project=output/'import-project';import_project.mkdir();(import_project/'project.godot').write_text('config_version=5\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
            for n in (IMPORT,'native_engine_clock.gd'):shutil.copyfile(archive/n,import_project/n)
            queries=np.unique(np.r_[clock,(clock[:-1]+clock[1:])/2,np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')])
            payload=dict(asset_path=str(assets/'objects.glb'),resource_path=str(assets/'objects.res'),import_bake_fps=compiled['physics_fps'],payload=dict(channels=asset.channels,duration_s=float(clock[-1]),sample_times_s=queries.tolist(),sample_clock=clock_wire(queries)))
            diagnostic={**payload,'resource_path':str(output/'default-30fps-objects.res'),'import_bake_fps':30}
            save(output/'default-30fps-request.json',diagnostic)
            default=engine_run(import_project,IMPORT,output/'default-30fps-request.json',output/'default-30fps.json',output/'default-30fps.log',120)
            require(default['import_bake_fps']==30,'Default import diagnostic differs')
            default_errors=import_errors(default,asset,queries)
            save(output/'import-request.json',payload);imported=engine_run(import_project,IMPORT,output/'import-request.json',output/'import.json',output/'import.log',120)
            require(imported['import_bake_fps']==compiled['physics_fps'],'Configured GLB import rate differs')
            errors=import_errors(imported,asset,queries)
            require(all(v<=POSE_LIMIT for v in errors.values()),'Configured baked engine pose playback differs')
            save(assets/'import-audit.json',dict(samples=len(queries),maximum_component_error=errors,engine_sha256=ENGINE_SHA256,import_bake_fps=compiled['physics_fps'],engine_playback_verified=True,
                default_30fps_maximum_component_error=default_errors,default_30fps_import_pass=all(v<=POSE_LIMIT for v in default_errors.values()),pose_component_limit=POSE_LIMIT,quality_approved=False,release_approved=False))
            save(assets/'baked-motion-audit.json',audit_baked_motion(asset,queries,compiled,scene,audit['applications'],request))
            require(sha256(source)==sha256(output/'source-runtime.zip')==digest and request_path.read_bytes()==request_bytes,'Bake inputs changed')
            require(all(sha256(ROOT/'scripts'/n)==sha256(archive/n)==h for n,h in methods.items()),'Bake methods changed')
            require(all(sha256(project/n)==h for n,h in m['files_sha256'].items()),'Original runtime files changed')
            paths=[p for p in assets.rglob('*') if p.is_file()]
            require(len(paths)<512 and sum(p.stat().st_size for p in paths)<=1024**3,'Complete baked assets exceed portable package budget; no truncation')
            files={p.relative_to(assets).as_posix():sha256(p) for p in paths}
            manifest=dict(schema='strep-baked-prop-assets-v1',status='complete',at=now(),source_runtime_zip_sha256=digest,bake_request_sha256=sha256(output/'bake-request.json'),files_sha256=files,
                source_actors_unchanged=True,source_mesh_payload_unchanged=True,engine_import_verified=True,studio_selection_changed=False,original_selected=True,exact_physical_event_timing_pass=audit['exact_physical_event_timing_pass'],maximum_application_delay_s=audit['maximum_application_delay_s'],
                floor_sampled_screen_pass=audit['floor_sampled_screen_pass'],physics_quality_approved=False,animation_quality_approved=False,release_approved=False)
            save(assets/'package.json',manifest)
            with zipfile.ZipFile(output/'baked-assets.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
                for n in list(files)+['package.json']:z.write(assets/n,n)
            with zipfile.ZipFile(output/'baked-assets.zip') as z:
                require(set(z.namelist())==set(files)|{'package.json'} and all(member_hash(z,n)==h for n,h in files.items())
                    and z.read('package.json')==(assets/'package.json').read_bytes(),'Complete baked ZIP readback failed')
            result=dict(**manifest,package_sha256=sha256(output/'baked-assets.zip'),methods_sha256=methods,capture_sha256=sha256(output/'capture.json'),capture_audit_sha256=sha256(output/'capture-audit.json'),renderer_executed=False,human_reviewed=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=repr(exc),at=now()));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('request',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(bake(a.source,a.request,a.output)))
