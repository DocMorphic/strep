"""Package explicit source-bound grip/physics bindings around a native game ZIP.

All original clips/resources/contact intent remain unchanged. Packaging does not
run a model, simulate physics, inspect production skin, or approve motion quality.
"""
import argparse,copy,hashlib,json,shutil,zipfile
from pathlib import Path
import numpy as np
from action_worker_lock import worker_lock
from native_scene_runtime import package_members,configure
from scene_prop_ownership import compile_plan,name,require
from primitive_penetration_bounds import rigid
from strep import ROOT,now,read,save,sha256
from prop_runtime_collision import profile_document,project_lines

GDS=('godot_scene_prop_runtime.gd','godot_scene_prop_boot.gd','godot_scene_prop_owner.gd','godot_scene_prop_body.gd',
     'godot_native_scene_loader.gd','godot_native_scene_player.gd','godot_native_root_adapter.gd',
     'godot_native_object_player.gd','godot_scene_game_events.gd','native_engine_clock.gd','native_godot_preview.gd')


def scalar(value,low,high,label):
    require(type(value) in (int,float) and np.isfinite(value) and low<=value<=high,'Finite bounded '+label+' required')
    return float(value)


def matrix(value):
    require(isinstance(value,list) and len(value)==4 and all(isinstance(row,list) and len(row)==4 for row in value),'Explicit 4x4 offset required')
    require(all(type(x) in (int,float) for row in value for x in row),'Numeric offset required')
    t=np.asarray(value,dtype=float);require(np.isfinite(t).all() and np.array_equal(t[3],[0,0,0,1]),'Rigid homogeneous offset required')
    rigid(t[:3,:3]);return t.tolist()


def entry_files(physics_fps,collision_profile=None):
    """Canonical startup files, also checked against completed Studio downloads."""
    return {
        'ownership-v1/scene.tscn':'[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://ownership-v1/godot_scene_prop_boot.gd" id="1"]\n[node name="Strep" type="Node3D"]\nscript = ExtResource("1")\n',
        'project.godot':'config_version=5\n[application]\nconfig/name="Strep explicit prop runtime"\nrun/main_scene="res://ownership-v1/scene.tscn"\n[physics]\ncommon/physics_ticks_per_second='+str(physics_fps)+'\n3d/physics_engine="Jolt Physics"\n'+project_lines(collision_profile,physics_fps)+'[rendering]\nrenderer/rendering_method="gl_compatibility"\n'}


def compile_request(request,config,scene,events,source_digest):
    fields={'schema','source_game_zip_sha256','root_modes','object_modes','grips','commands','physics','physics_fps','history_capacity'}
    require(isinstance(request,dict) and fields<=set(request) and set(request)<=fields|{'position_tolerance_m','rotation_tolerance_rad','collision_profile'}
        and request['schema']=='strep-scene-prop-runtime-request-v1','Complete explicit prop runtime request required')
    require(request['source_game_zip_sha256']==source_digest,'Request binds another source game ZIP')
    expected_modes={a['id']:'extracted' if a['extract'] else 'embedded' for a in config['actors']}
    require(request['root_modes']==expected_modes,'Explicit matching mode for every source actor required')
    require(type(request['physics_fps']) is int and request['physics_fps'] in (60,120,240),'Explicit 60/120/240 physics rate required')
    require(type(request['history_capacity']) is int and 2<=request['history_capacity']<=3600,'Bounded history capacity required')
    modes=request['object_modes'];require(isinstance(modes,dict) and set(modes)==set(scene.objects) and all(v in ('authored','grip-physics') for v in modes.values()),'Explicit ownership mode for every source prop required')
    require(isinstance(config.get('objects'),dict) and set(config['objects']['names'])==set(scene.objects),'Complete matching native source prop population required')
    selected=sorted(n for n,v in modes.items() if v=='grip-physics');require(selected,'Choose at least one physical prop')
    grips=request['grips'];require(isinstance(grips,dict) and grips,'Explicit joint bindings required')
    simplified={};bindings={}
    for key,g in grips.items():
        name(key);require(isinstance(g,dict) and set(g)=={'actor','joint_node','prop_offsets'} and g['actor'] in scene.actors,'Exact source actor/joint/offset binding required')
        actor=scene.actors[g['actor']];rig=actor['rig'];node=g['joint_node']
        require(type(node) is int and node in rig.joints,'Choose an existing skin joint; no bone-name guessing')
        bone=rig.document['nodes'][node].get('name')
        require(isinstance(bone,str) and bone and ':' not in bone and '/' not in bone and sum(rig.document['nodes'][n].get('name')==bone for n in rig.joints)==1,'Unique plain source bone name required')
        offsets=g['prop_offsets'];require(isinstance(offsets,dict) and offsets and set(offsets)<=set(selected),'Offsets must bind physical source props')
        simplified[key]={'actor':g['actor']}
        asset=next(e['asset'] for e in config['actors'] if e['id']==g['actor'])
        bindings[key]=dict(actor=g['actor'],joint_node=node,bone=bone,character_glb_sha256=asset['sha256'],
            animation_index=actor['animation_index'],prop_offsets={n:matrix(v) for n,v in offsets.items()})
    options={k:request[k] for k in ('position_tolerance_m','rotation_tolerance_rad') if k in request}
    plan=compile_plan(events,selected,simplified,request['commands'],**options)
    for key,b in bindings.items():
        needed={c['object'] for c in request['commands'] if c['grip']==key}
        require(set(b['prop_offsets'])==needed,'Complete exact prop offset population for every commanded grip required')
    physics=request['physics'];require(isinstance(physics,dict) and set(physics)==set(selected),'Physical settings for every dynamic prop required')
    props={}
    for key in selected:
        p=physics[key];require(isinstance(p,dict) and set(p)=={'mass_kg','friction','restitution','linear_damping','angular_damping','collision_layer','collision_mask'},'Explicit complete prop physics settings required')
        mass=scalar(p['mass_kg'],.001,10000,'mass');checked={'mass_kg':mass}
        for k,upper in [('friction',1),('restitution',1),('linear_damping',100),('angular_damping',100)]:checked[k]=scalar(p[k],0,upper,k)
        for k in ('collision_layer','collision_mask'):
            require(type(p[k]) is int and 0<=p[k]<=2**32-1,'Explicit collision bitfield required');checked[k]=p[k]
        geometry=scene.objects[key]['geometry'];pos,rot=scene.object_poses(key,np.array([0.]))
        t=np.eye(4);t[:3,:3]=rot[0];t[:3,3]=pos[0]
        props[key]=dict(geometry=geometry.record(),initial_pose=matrix(t.tolist()),inertia_diagonal=np.diag(geometry.uniform_inertia(mass)).tolist(),physics=checked)
    result=dict(schema='strep-scene-prop-runtime-v1',native_scene=copy.deepcopy(config),object_modes=copy.deepcopy(modes),grip_bindings=bindings,
                ownership=plan,props=props,physics_fps=request['physics_fps'],history_capacity=request['history_capacity'],
                source_game_zip_sha256=source_digest,source_contacts_apply_to='unchanged-authored-reference-only',
                source_bytes_unchanged=True,physics_verified=False,animation_quality_approved=False,release_approved=False)
    if 'collision_profile' in request:result['collision_profile']=profile_document(request['collision_profile'],request['physics_fps'])
    return result


def package(source,request_path,output):
    source=Path(source).resolve();request_path=Path(request_path).resolve();output=Path(output).resolve()
    require(not output.exists(),'Fresh prop runtime output required')
    request_bytes=request_path.read_bytes();request=json.loads(request_bytes);source_digest=sha256(source)
    require(isinstance(request,dict),'Explicit authoring request object required')
    with worker_lock():
        with zipfile.ZipFile(source) as archive:manifest=package_members(archive)
        output.mkdir(parents=True);project=output/'project';project.mkdir()
        save(output/'pipeline.json',dict(status='packaging',at=now()))
        try:
            shutil.copyfile(source,output/'source-game-assets.zip');require(sha256(output/'source-game-assets.zip')==source_digest,'Source snapshot changed')
            with zipfile.ZipFile(output/'source-game-assets.zip') as archive:
                require(package_members(archive)==manifest,'Source package snapshot changed')
                for n in archive.namelist():
                    dest=project/('source-game-package.json' if n=='package.json' else n);dest.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(n) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
            config,scene,_,events=configure(project,manifest,request.get('root_modes',{}))
            compiled=compile_request(request,config,scene,events,source_digest)
            runtime=project/'ownership-v1';runtime.mkdir()
            methods={n:sha256(ROOT/'scripts'/n) for n in GDS}
            for n in GDS:shutil.copyfile(ROOT/'scripts'/n,runtime/n)
            save(runtime/'prop-runtime.json',compiled)
            (runtime/'ownership-authoring-request.json').write_bytes(request_bytes)
            require(not (project/'project.godot').exists(),'Original package project entry conflicts with prop runtime')
            for n,text in entry_files(compiled['physics_fps'],compiled.get('collision_profile')).items():(project/n).write_bytes(text.encode('utf8'))
            require(sha256(source)==source_digest and request_path.read_bytes()==request_bytes,'Source/request changed during packaging')
            require(all(sha256(project/n)==h for n,h in manifest['files_sha256'].items()),'Original source entry changed')
            require(all(sha256(ROOT/'scripts'/n)==sha256(runtime/n)==h for n,h in methods.items()),'Runtime implementation changed')
            files={p.relative_to(project).as_posix():sha256(p) for p in project.rglob('*') if p.is_file()}
            require(len(files)<512 and sum(p.stat().st_size for p in project.rglob('*') if p.is_file())<=1024**3,'Complete packaged source exceeds budget; no subset emitted')
            result=dict(schema='strep-scene-prop-runtime-package-v1',status='complete',at=now(),files_sha256=files,source_game_zip_sha256=source_digest,
                        ownership_request_sha256=hashlib.sha256(request_bytes).hexdigest(),runtime_methods_sha256=methods,source_bytes_unchanged=True,
                        engine_executed=False,physics_verified=False,animation_quality_approved=False,release_approved=False)
            save(project/'package.json',result)
            with zipfile.ZipFile(output/'prop-runtime-assets.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
                for n in list(files)+['package.json']:archive.write(project/n,n)
            with zipfile.ZipFile(output/'prop-runtime-assets.zip') as archive:
                require(set(archive.namelist())==set(files)|{'package.json'},'Complete packaged ZIP required')
                for n,h in {**files,'package.json':sha256(project/'package.json')}.items():
                    digest=hashlib.sha256()
                    with archive.open(n) as f:
                        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
                    require(digest.hexdigest()==h,'Packaged bytes changed')
            result.update(package_sha256=sha256(output/'prop-runtime-assets.zip'))
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),at=now()));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('request');parser.add_argument('output')
    args=parser.parse_args();package(args.source,args.request,args.output)
