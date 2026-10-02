"""Immutable trim, retime and local pose curves on a selected target-rig clip."""
import copy
import math
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_contact_authoring import source
from rig_clip_import import AnimationSampler
from gltf_tools import authored_animation,append_accessor,write_glb,sample_animation


def timeline(edit,frames):
    if set(edit)!={'schema','glb_sha256','label','start_frame','last_frame','speed','poses'} or edit['schema']!='strep-rig-clip-edit-v1':
        raise ValueError('Invalid clip edit recipe')
    a,b,speed=edit['start_frame'],edit['last_frame'],edit['speed']
    if type(a) is not int or type(b) is not int or not 0<=a<b<frames:raise ValueError('Choose at least two source frames within the clip')
    if type(speed) not in (int,float) or not math.isfinite(speed) or not .25<=speed<=4:raise ValueError('Speed must be between 0.25 and 4')
    spans=max(1,int(math.floor((b-a)/speed+.5)))
    if spans>900:raise ValueError('Edited clip must be at most 30 seconds')
    if not isinstance(edit['label'],str) or not 1<=len(edit['label'])<=160:raise ValueError('Name the edited clip')
    return np.linspace(a,b,spans+1),dict(source_start_frame=a,source_last_frame=b,requested_speed=speed,effective_speed=(b-a)/spans,frames=spans+1,fps=30,duration_s=spans/30)


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'source_job','variant','edit'}:raise ValueError('Choose a source clip, version and edit recipe')
    previous,result,request,report,glb=source(payload['source_job'],payload['variant']);edit=payload['edit']
    if not isinstance(edit,dict) or edit.get('glb_sha256')!=sha256(glb):raise ValueError('Edit recipe belongs to a different clip version')
    frames,clock=timeline(edit,report['frames']);rig=RigAsset.load(glb);poses=edit['poses']
    if not isinstance(poses,list) or len(poses)>24:raise ValueError('Use up to 24 pose adjustments')
    for i,pose in enumerate(poses):
        if not isinstance(pose,dict) or set(pose)!={'node','start_frame','peak_frame','end_frame','rotation_degrees'}:raise ValueError('Invalid pose adjustment')
        n=pose['node'];a,c,b=(pose[k] for k in ('start_frame','peak_frame','end_frame'))
        if type(n) is not int or n not in rig.joints:raise ValueError('Choose a skin bone for the pose adjustment')
        ancestor=n
        while ancestor>=0 and ancestor!=report['root_node']:ancestor=rig.parents[ancestor]
        if ancestor<0:raise ValueError('Pose bone must descend from the mapped pelvis')
        if any(type(v) is not int for v in (a,c,b)) or not 0<=a<c<b<report['frames']:raise ValueError('Pose frames must satisfy start < peak < end within the source clip')
        if b<=edit['start_frame'] or a>=edit['last_frame']:raise ValueError('Pose adjustment lies outside the trimmed clip')
        angles=pose['rotation_degrees']
        if not isinstance(angles,list) or len(angles)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>90 for v in angles):raise ValueError('Use three finite local XYZ angles within 90 degrees')
        if np.degrees(Rotation.from_euler('xyz',angles,degrees=True).magnitude())>90+1e-6:raise ValueError('Combined local rotation must not exceed 90 degrees')
        if any(p['node']==n and max(p['start_frame'],a)<min(p['end_frame'],b) for p in poses[:i]):raise ValueError('Overlapping pose adjustments on the same bone are ambiguous')
    return previous,request,report,glb,copy.deepcopy(edit)


def remap_intervals(intervals,source_frames):
    """Discrete contact membership uses the same source-frame clock as geometry."""
    out=[];dropped=[]
    for index,entry in enumerate(intervals):
        active=(source_frames>=entry['start_frame']-1e-9)&(source_frames<entry['end_frame_exclusive']-1e-9)
        ids=np.flatnonzero(active)
        if not len(ids):dropped.append(index);continue
        mapped=copy.deepcopy(entry);a,b=int(ids[0]),int(ids[-1])+1
        mapped.update(start_frame=a,end_frame_exclusive=b)
        if 'start_seconds' in mapped:mapped['start_seconds']=a/30
        if 'end_seconds_exclusive' in mapped:mapped['end_seconds_exclusive']=b/30
        out.append(mapped)
    return out,dropped


def envelope(pose,frame):
    a,c,b=(pose[k] for k in ('start_frame','peak_frame','end_frame'))
    if frame<=a or frame>=b:return 0.
    u=(frame-a)/(c-a) if frame<=c else (b-frame)/(b-c)
    return u*u*(3-2*u)


def prepare(payload,folder):
    previous,original,report,glb,edit=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    dest=folder/'input';dest.mkdir();shutil.copyfile(glb,dest/'character.glb')
    metadata=glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json'):shutil.copyfile(metadata/name,dest/name)
    for name in ('events.json','timeline.json','contact-review.json'):
        if (metadata/name).exists():shutil.copyfile(metadata/name,dest/name)
    shutil.copyfile(glb.parent/'root-motion.json',dest/'root-motion.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((dest/'contacts.json').resolve())
    save(dest/'report.json',report)
    prior_spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if prior_spec.exists():shutil.copyfile(prior_spec,dest/'contact-spec.json')
    from rig_contact_timing import snapshot,bind_inputs
    snapshot(glb,dest)
    save(folder/'clip-edit.json',edit)
    request=dict(kind='clip_edit',label=edit['label'],asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),
        source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/source_name),correct_contacts=False,
        source_job=previous.name,input_variant=payload['variant'],input_glb_sha256=sha256(glb),edit_sha256=sha256(folder/'clip-edit.json'))
    bind_inputs(folder,request)
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def run(folder):
    folder=Path(folder);request=read(folder/'request.json');edit=read(folder/'clip-edit.json');input=folder/'input/character.glb';report=read(folder/'input/report.json')
    from rig_contact_timing import verify_inputs,retime as retime_contact_timing
    verify_inputs(folder,request)
    if sha256(input)!=request['input_glb_sha256'] or sha256(folder/'clip-edit.json')!=request['edit_sha256']:raise ValueError('Clip edit snapshot changed')
    source_frames,clock=timeline(edit,report['frames']);rig=RigAsset.load(input);sampler=AnimationSampler(rig.document,rig.binary,0)
    source_times=(source_frames/30).astype(np.float32).astype(float);world=np.array([sampler.sample(t) for t in source_times]);local=world.copy()
    for n,p in enumerate(rig.parents):
        if p>=0:local[:,n]=np.linalg.inv(world[:,p])@world[:,n]
    original_local=local.copy();curves=[]
    for pose in edit['poses']:
        weights=np.array([envelope(pose,f) for f in source_frames]);delta=Rotation.from_euler('xyz',pose['rotation_degrees'],degrees=True).as_rotvec()
        local[:,pose['node'],:3,:3]=local[:,pose['node'],:3,:3]@Rotation.from_rotvec(weights[:,None]*delta).as_matrix()
        curves.append(dict(node=pose['node'],weights=weights.tolist(),max_rotation_degrees=float(np.degrees(np.linalg.norm(delta))*weights.max())))
    def depth(n):return 0 if rig.parents[n]<0 else 1+depth(rig.parents[n])
    after=np.empty_like(local)
    for n in sorted(range(len(rig.parents)),key=depth):after[:,n]=local[:,n] if rig.parents[n]<0 else after[:,rig.parents[n]]@local[:,n]
    document,binary=copy.deepcopy(rig.document),bytearray(rig.binary);animation=authored_animation(edit['label']);times=np.arange(len(source_frames),dtype=np.float32)/30
    time_accessor=append_accessor(document,binary,times,'SCALAR');animated={c[0] for c in sampler.channels}|{p['node'] for p in edit['poses']}
    from target_rig_contact import prepare_animated_node
    for n in sorted(animated):
        prepare_animated_node(document,n);q=Rotation.from_matrix(local[:,n,:3,:3]).as_quat()
        for f in range(1,len(q)):
            if q[f]@q[f-1]<0:q[f]*=-1
        for path,values,kind in [('translation',local[:,n,:3,3],'VEC3'),('rotation',q,'VEC4')]:
            acc=append_accessor(document,binary,values,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=n,path=path)))
            animation['samplers'].append(dict(input=time_accessor,output=acc,interpolation='LINEAR'))
    document['animations']=[animation];document.setdefault('extras',{})['strep_clip_edit']=dict(input_sha256=sha256(input),recipe_sha256=sha256(folder/'clip-edit.json'),timeline=clock)
    out=folder/'transfer';out.mkdir(exist_ok=False);write_glb(out/'character.glb',document,binary);decoded=RigAsset.load(out/'character.glb');matrix_error=skin_error=0.;floor=[];before_floor=[]
    for f,expected in enumerate(after):
        found=sample_animation(decoded.document,decoded.binary,0,f);points=decoded.vertices(found)
        matrix_error=max(matrix_error,float(np.abs(found-expected).max()));skin_error=max(skin_error,float(np.linalg.norm(points-rig.vertices(expected),axis=1).max()))
        floor.append(max(0.,-float(points[:,1].min())));before_floor.append(max(0.,-float(rig.vertices(world[f])[:,1].min())))
    if max(matrix_error,skin_error)>1e-5:raise ValueError('Edited animation failed transform/skin export verification')
    annotations=read(folder/'input/contacts.json');annotations['intervals'],dropped=remap_intervals(annotations['intervals'],source_frames)
    annotations.setdefault('origin','none_supplied' if report.get('source_kind')=='gltf_animation' else 'source_model_predictions')
    annotations['timeline_provenance']='Intervals resampled using the exact source-frame mapping; original prediction/authorship provenance retained. Support must be reviewed after pose/time edits.'
    save(out/'contacts.json',annotations)
    dropped_events=[];event_retiming=None
    if (folder/'input/events.json').exists():
        from rig_event_retime import retime
        events,event_retiming=retime(read(folder/'input/events.json'),source_frames,sha256(input))
        dropped_events=event_retiming['dropped_event_indices']
        save(out/'events.json',events)
    if (folder/'input/contact-review.json').exists():
        review=read(folder/'input/contact-review.json')
        for target in review['authored_targets']:
            old=target['output_frames'];weights=np.zeros(report['frames'])
            for entry in old:weights[entry['frame']]=entry['weight']
            sampled=np.interp(source_frames,np.arange(report['frames']),weights)
            target['output_frames']=[dict(frame=i,weight=float(w)) for i,w in enumerate(sampled) if w>0]
        ambiguous=[]
        for entry in review.get('ambiguous_support_frames',[]):
            for f in np.flatnonzero((source_frames>=entry['frame'])&(source_frames<entry['frame']+1)):
                ambiguous.append({**entry,'frame':int(f)})
        review.update(ambiguous_support_frames=ambiguous,retiming='Source contribution weights sampled on the new clock; original review retained under input/. Targets unchanged in world space. Prior ambiguity flags remapped, not reevaluated; support remains unconfirmed.')
        save(out/'contact-review.json',review)
    if (folder/'input/contact-spec.json').exists():
        spec=read(folder/'input/contact-spec.json');spec['contacts'],dropped_authored=remap_intervals(spec['contacts'],source_frames)
        spec.update(frames=len(times),glb_sha256=sha256(out/'character.glb'),provenance=spec['provenance'][:1600]+' Retimed to this clip; targets retained in world space and need review after edits.')
        save(folder/'contact-spec.json',spec)
        retime_contact_timing(folder/'input',out,spec,dropped_authored)
    else:dropped_authored=[]
    root=report['root_node'];save(out/'root-motion.json',dict(space='Edited mapped pelvis world transform; original world placement retained',node=root,times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
    for name in ('inventory.json','rig-profile.json'):shutil.copyfile(folder/'input'/name,out/name)
    np.savez_compressed(out/'target-transforms.npz',global_matrices=after,times_s=times,source_frames=source_frames)
    save(out/'timeline.json',dict(**clock,source_frames=source_frames.tolist(),source_times_s=source_times.tolist(),input_frames=report['frames'],input_sha256=sha256(input),input_variant=request['input_variant']))
    check=dict(created_at=now(),source_glb_sha256=sha256(input),glb_sha256=sha256(out/'character.glb'),recipe_sha256=sha256(folder/'clip-edit.json'),timeline=clock,pose_curves=curves,
        max_local_translation_change_m=float(np.abs(local[:,:,:3,3]-original_local[:,:,:3,3]).max()),floor_before_pose_max_m=max(before_floor),floor_after_pose_max_m=max(floor),floor_failed_frames=sum(v>.005 for v in floor),
        roundtrip_max_matrix_error=matrix_error,roundtrip_max_skin_error_m=skin_error,dropped_annotation_indices=dropped,dropped_authored_contact_indices=dropped_authored,dropped_event_indices=dropped_events,event_retiming=event_retiming,
        scope='Source-frame sampling, smooth local pose rotation curves, root tracks and discrete contact remapping. Timing changes alter dynamics; no physical, semantic, continuous-collision or animator approval.',human_approved=False)
    save(out/'clip-edit-audit.json',check)
    report.update(frames=len(times),fps=30,glb_sha256=sha256(out/'character.glb'),timeline_edited=True,contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),
        target_mesh_floor_depth_max_m=max(floor),target_mesh_floor_frames_above_1cm=sum(v>.01 for v in floor),edit_parent_glb_sha256=sha256(input))
    report.update(last_key_time_s=float(times[-1]),animation_name=edit['label'],edited_duration_s=clock['duration_s'])
    save(out/'report.json',report);return report,check
