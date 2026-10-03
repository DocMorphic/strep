"""CPU Godot proof for saved native resources in embedded/extracted root modes.

Fresh output, exact original keys/clock, whole skeleton and raw imported skin.
No model generation, geometry requery, GPU readback, physics or event dispatch.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now,offline_environment
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_engine_clock import clock_wire,clock_echo_matches
from native_scene_imported_skin import ImportedSceneSkin
from native_engine_contacts import matrices
from native_scene_engine import POSE_TOLERANCE,SKIN_POSITION_TOLERANCE,METHODS as SCENE_METHODS
from native_godot_payload import payload

METHODS=tuple(dict.fromkeys(SCENE_METHODS+('godot_native_root_adapter.gd','godot_native_root_audit.gd','native_godot_preview.gd',
    'native_engine_clock.gd','audit_native_root_runtime.py','native_scene_imported_skin.py',
    'native_engine_contacts.py','native_support_skin.py','native_support_clock.py','rig_asset.py',
    'native_godot_payload.py','native_engine_clock.py')))


def validate(rig,index,root,times,placement):
    if type(index) is not int or type(root) is not int or root not in rig.joints: raise ValueError('Explicit animation and skin root joint required')
    sampler=NativeSupportSampler(rig.document,rig.binary,index)
    native=payload(rig,sampler,'') # Existing supported native channel contract.
    times=np.asarray(times,dtype='<f8');clock_wire(times)
    if times[-1]!=sampler.duration or any(not np.isin(c['times_s'],times).all() for c in native['channels']):
        raise ValueError('Complete duration and every original native key required')
    descendants=[]
    for node in rig.joints:
        parent=node
        while parent>=0 and parent!=root: parent=rig.parents[parent]
        if parent==root:descendants.append(node)
    if set(descendants)!=set(rig.joints):raise ValueError('Extraction root must contain the entire skeleton, including unweighted gameplay bones')
    if not rig.primitives or any(p['joints'] is None for p in rig.primitives):raise ValueError('Whole skinned character required; static accessories unsupported')
    placement=np.asarray(placement,dtype='<f8')
    if (placement.shape!=(4,4) or not np.isfinite(placement).all() or not np.array_equal(placement[3],[0,0,0,1])
            or abs(np.linalg.det(placement[:3,:3])-1)>1e-5 or abs(placement[:3,:3].T@placement[:3,:3]-np.eye(3)).max()>1e-5):
        raise ValueError('Finite proper rigid actor placement required')
    return sampler,times,placement


def evaluate(rig,sampler,times,placement,actual):
    if actual['duration_s']!=sampler.duration:raise ValueError('Saved native resource duration changed')
    skin=ImportedSceneSkin(rig,actual)
    expected=placement@np.array([sampler.sample(float(t))[rig.joints] for t in times])
    arrays={'times_s':times,'source_world':expected};checks={}
    for mode in ('embedded','extracted'):
        frames=actual[mode]
        if len(frames)!=len(times) or any(not clock_echo_matches(t,f['time_s']) for t,f in zip(times,frames)):
            raise ValueError('Complete unchanged native runtime clock required')
        # ImportedSceneSkin.bone_map maps observed bone order to source order.
        world=matrices([f['bones'] for f in frames])[:,np.argsort(skin.bone_map)]
        if world.shape!=expected.shape:raise ValueError('Complete runtime joint population required')
        arrays[mode+'_world']=world
        arrays[mode+'_actor']=matrices([f['actor_world'] for f in frames])
        arrays[mode+'_root']=matrices([f['root_motion'] for f in frames])
        arrays[mode+'_delta']=matrices([f['root_delta'] for f in frames])
        arrays[mode+'_root_in_actor']=matrices([f['root_in_actor'] for f in frames])
        checks[mode]=dict(maximum_pose_element_error=float(abs(world-expected).max()))
    drift=float(abs(arrays['extracted_root_in_actor']-arrays['extracted_root_in_actor'][0]).max())
    parity=float(abs(arrays['embedded_world']-arrays['extracted_world']).max())
    skin_error=0.0
    # Every imported vertex, with RAW imported weights/binds, unchanged population.
    for embedded,extracted in zip(arrays['embedded_world'],arrays['extracted_world']):
        skin_error=max(skin_error,float(np.linalg.norm(skin.vertices(embedded)-skin.vertices(extracted),axis=1).max()))
    actor_expected=placement@arrays['extracted_root']
    actor_error=float(abs(arrays['extracted_actor']-actor_expected).max())
    embedded_actor_error=float(abs(arrays['embedded_actor']-placement).max())
    delta=np.concatenate([np.eye(4)[None],np.linalg.inv(arrays['extracted_root'][:-1])@arrays['extracted_root'][1:]])
    delta_error=float(abs(delta-arrays['extracted_delta']).max())
    previews=actual['preview'];indices=[]
    for frame in previews:
        matches=[i for i,t in enumerate(times) if clock_echo_matches(t,frame['time_s'])]
        if len(matches)!=1:raise ValueError('Preview must retain an exact native-clock sample')
        indices.append(matches[0])
    preview_world=matrices([f['bones'] for f in previews])[:,np.argsort(skin.bone_map)]
    preview_error=float(abs(preview_world-arrays['extracted_world'][indices]).max())
    arrays['preview_times_s']=times[indices];arrays['preview_world']=preview_world
    # Check native resource keys against supplied source, not a freshly written resource.
    native=payload(rig,sampler,'');observed=actual['channels']
    if len(observed)!=len(native['channels']):raise ValueError('Saved native channel population changed')
    value_error=0.0
    for source,target in zip(native['channels'],observed):
        if (target['type']!={'translation':1,'rotation':2,'scale':3}[source['path']]
                or target['path'].rsplit(':',1)[-1]!=source['bone']
                or np.asarray(target['times_s']).shape!=np.asarray(source['times_s']).shape
                or not np.array_equal(target['times_s'],source['times_s'])):raise ValueError('Saved native key population, bone or times changed')
        values=np.asarray(source['values']);found=np.asarray(target['values'])
        if source['path']=='rotation':values=values/np.linalg.norm(values,axis=1)[:,None]
        if found.shape!=values.shape or not np.isfinite(found).all():raise ValueError('Complete finite saved native key values required')
        value_error=max(value_error,float(abs(found-values).max()))
    result=dict(samples=len(times),bones=len(rig.joints),vertices=len(skin.nodes),imported_skin=skin.report,
        pose=checks,maximum_mode_pose_difference=parity,maximum_mode_skin_position_difference_m=skin_error,
        maximum_extracted_root_drift=drift,maximum_actor_application_error=actor_error,
        maximum_embedded_actor_drift=embedded_actor_error,maximum_root_delta_error=delta_error,
        maximum_preview_pose_difference=preview_error,maximum_native_key_value_difference=value_error,
        pose_limit=POSE_TOLERANCE,skin_position_limit_m=SKIN_POSITION_TOLERANCE,
        invalid_clocks_reject_without_mutation=actual['invalid_rejected'],
        malformed_bindings_reject_without_mutation=actual['malformed_bindings_rejected'],malformed_bindings=actual['malformed_bindings'])
    result['sampled_runtime_conditions_pass']=bool(max([c['maximum_pose_element_error'] for c in checks.values()]+[parity,drift,actor_error,embedded_actor_error,delta_error,preview_error])<=POSE_TOLERANCE
        and skin_error<=SKIN_POSITION_TOLERANCE and value_error<=1e-6 and actual['invalid_rejected'] is True
        and actual['malformed_bindings_rejected'] is True and actual['malformed_bindings']>=7)
    return result,arrays


def run(glb,animation_resource,index,root,times,output,*,placement=None,engine=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh native root runtime output required')
    glb=Path(glb).resolve();resource=Path(animation_resource).resolve()
    rig=RigAsset.load(glb);sampler,times,placement=validate(rig,index,root,times,np.eye(4) if placement is None else placement)
    engine=Path(engine or ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe').resolve()
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (glb,resource,engine)}
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir();project=output/'project';project.mkdir();archive=output/'implementation';archive.mkdir()
        save(output/'pipeline.json',dict(status='running',original_selected=True,quality_approved=False))
        try:
            shutil.copyfile(glb,output/'character.glb');shutil.copyfile(resource,output/'animation.res')
            for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,archive/n)
            for n in ('godot_native_root_adapter.gd','godot_native_root_audit.gd','native_godot_preview.gd','native_engine_clock.gd'):shutil.copyfile(archive/n,project/n)
            (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native root audit"\n',encoding='utf8')
            request=dict(glb=str(output/'character.glb'),animation_resource=str(output/'animation.res'),animation_index=index,
                root_bone=rig.document['nodes'][root]['name'],clock=clock_wire(times),placement=placement.tolist())
            save(output/'request.json',request)
            with (output/'engine.log').open('w',encoding='utf8') as log:
                process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','res://godot_native_root_audit.gd','--',str(output/'request.json'),str(output/'engine.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300,env=offline_environment())
            if process.returncode or not (output/'engine.json').is_file():raise ValueError('Actual native root engine audit failed; see preserved engine.log')
            result,arrays=evaluate(rig,sampler,times,placement,read(output/'engine.json'))
            for path,digest in bindings.items():
                if sha256(path)!=digest:raise ValueError('Original runtime input changed')
            if sha256(output/'character.glb')!=bindings[str(glb)] or sha256(output/'animation.res')!=bindings[str(resource)]:raise ValueError('Runtime snapshot changed')
            for name,digest in methods.items():
                if sha256(archive/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Runtime implementation changed during study')
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                if set(stored.files)!=set(arrays) or any(stored[n].dtype!=v.dtype or stored[n].shape!=v.shape or stored[n].tobytes()!=v.tobytes() for n,v in arrays.items()):raise ValueError('Complete Float64 runtime observation transport changed')
            result.update(at=now(),schema='strep-native-root-runtime-audit-v1',status='complete',engine=read(output/'engine.json')['engine'],
                input_sha256=bindings,implementation_sha256=methods,request_sha256=sha256(output/'request.json'),
                raw_engine_sha256=sha256(output/'engine.json'),observations_sha256=sha256(output/'observations.npz'),
                executed_script_sha256={n:sha256(project/n) for n in ('godot_native_root_adapter.gd','godot_native_root_audit.gd','native_godot_preview.gd','native_engine_clock.gd')},
                source_bytes_unchanged=True,arrays_roundtrip_exact=True,original_selected=True,
                quality_approved=False,physics_verified=False,release_approved=False,gpu_render_checked=False,
                scope='Finite saved native resources, absolute authored clock, whole skeleton and complete raw imported CPU skin in embedded/extracted modes. No events, scene-object playback, blending, loops, physics or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',sampled_runtime_conditions_pass=result['sampled_runtime_conditions_pass'],original_selected=True,quality_approved=False));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request');parser.add_argument('output');args=parser.parse_args()
    value=read(args.request);print(run(value['glb'],value['animation_resource'],value['animation_index'],value['root_node'],value['times_s'],args.output,placement=value.get('placement'),engine=value.get('engine')))
