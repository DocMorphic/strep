"""Generic humanoid loop extraction with cycle transforms and repeated seam evidence."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_contact_authoring import source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize,compose,blend
from gltf_tools import authored_animation,append_accessor,write_glb,sample_animation


def validate(payload):
    keys={'schema','label','job','variant','glb_sha256','start_frame','period_frames','blend_frames','turn_degrees'}
    if not isinstance(payload,dict) or not keys<=set(payload) or set(payload)-keys-{'root_mode'} or payload['schema']!='strep-rig-loop-v1':raise ValueError('Invalid loop recipe')
    if payload.get('root_mode','travel') not in ('travel','in_place'):raise ValueError('Choose traveling or in-place root motion')
    snapshot=source(payload['job'],payload['variant']);report=snapshot[3]
    if payload['glb_sha256']!=sha256(snapshot[4]):raise ValueError('Loop source changed')
    a,p,k=(payload[n] for n in ('start_frame','period_frames','blend_frames'))
    if any(type(n) is not int for n in (a,p,k)) or not 0<=a or not 4<=k<p or a+p+k>report['frames']:raise ValueError('Choose a cycle longer than its blend and leave blend frames after the cycle')
    if p>900:raise ValueError('A cycle must be at most 30 seconds')
    turn=payload['turn_degrees']
    if type(turn) not in (int,float) or not np.isfinite(turn) or abs(turn)>180:raise ValueError('Cycle turn must be within 180 degrees')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'])<=160:raise ValueError('Name the loop')
    return snapshot


def prepare(payload,folder):
    previous,_,original,report,glb=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'));dest=folder/'input';dest.mkdir();shutil.copyfile(glb,dest/'character.glb')
    metadata=glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (metadata/name).exists():shutil.copyfile(metadata/name,dest/name)
    shutil.copyfile(glb.parent/'root-motion.json',dest/'root-motion.json')
    original_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/original_name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((dest/'contacts.json').resolve())
    save(dest/'report.json',report)
    spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if spec.exists():shutil.copyfile(spec,dest/'contact-spec.json')
    from rig_contact_timing import snapshot,bind_inputs
    snapshot(glb,dest)
    save(folder/'loop.json',payload)
    history=folder/'source/loop-history'/folder.name;history.mkdir(parents=True);shutil.copytree(dest,history/'input');shutil.copyfile(folder/'loop.json',history/'loop.json')
    request=dict(kind='loop',label=payload['label'],asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/original_name),correct_contacts=False,recipe_sha256=sha256(folder/'loop.json'))
    bind_inputs(folder,request)
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def place(world,parents,root,transform):
    result=world.copy()
    for node in range(len(parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=parents[ancestor]
        if ancestor==root:result[:,node]=transform@world[:,node]
    return result


def encode(rig,world,animated,root,path,label):
    local=localize(world,rig.parents);doc,binary=copy.deepcopy(rig.document),bytearray(rig.binary);times=np.arange(len(world),dtype=np.float32)/30
    animation=authored_animation(label);time=append_accessor(doc,binary,times,'SCALAR')
    from target_rig_contact import prepare_animated_node
    for node in sorted(animated|{root}):
        prepare_animated_node(doc,node);q=Rotation.from_matrix(local[:,node,:3,:3]).as_quat()
        for f in range(1,len(q)):
            if q[f]@q[f-1]<0:q[f]*=-1
        for target,values,kind in [('translation',local[:,node,:3,3],'VEC3'),('rotation',q,'VEC4')]:
            output=append_accessor(doc,binary,values,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=target)));animation['samplers'].append(dict(input=time,output=output,interpolation='LINEAR'))
    doc['animations']=[animation];write_glb(path,doc,binary);decoded=RigAsset.load(path);error=skin=0.;depth=[]
    for f in range(len(world)):
        actual=sample_animation(decoded.document,decoded.binary,0,f);points=decoded.vertices(actual)
        error=max(error,float(np.abs(actual-world[f]).max()));skin=max(skin,float(np.linalg.norm(points-rig.vertices(world[f]),axis=1).max()));depth.append(max(0.,-float(points[:,1].min())))
    if max(error,skin)>1e-5:raise ValueError('Loop transform/skin roundtrip failed')
    return times,dict(matrix_error=error,skin_error_m=skin,floor_depth_max_m=max(depth),floor_failed_frames=sum(v>.005 for v in depth),floor_frames_above_1cm=sum(v>.01 for v in depth))


def assemble(raw,parents,root,recipe):
    """Assemble P phases plus terminal phase zero from P+K source samples."""
    p,k=recipe['period_frames'],recipe['blend_frames']
    cycle=np.eye(4);cycle[:3,:3]=Rotation.from_euler('y',recipe['turn_degrees'],degrees=True).as_matrix()
    destination=raw[p,root,:3,3] if recipe.get('root_mode','travel')=='travel' else raw[0,root,:3,3]
    delta=destination-cycle[:3,:3]@raw[0,root,:3,3];delta[1]=0;cycle[:3,3]=delta
    tail=place(raw[p:p+k],parents,root,np.linalg.inv(cycle));head=localize(raw[:p],parents)
    # Keep the first two continuation samples unchanged, preserving source seam velocities.
    u=np.clip((np.arange(k)-1)/(k-2),0,1);w=u*u*(3-2*u);head[:k]=blend(localize(tail,parents),head[:k],w)
    world=compose(head,parents);terminal=place(world[:1],parents,root,cycle)
    return np.concatenate([world,terminal]),cycle,w


def run(folder):
    folder=Path(folder);recipe=read(folder/'loop.json');request=read(folder/'request.json');report=read(folder/'input/report.json');path=folder/'input/character.glb'
    from rig_contact_timing import verify_inputs,target_rows
    verify_inputs(folder,request)
    if sha256(path)!=recipe['glb_sha256'] or sha256(folder/'loop.json')!=request['recipe_sha256'] or sha256(report['source'])!=report['source_sha256']:raise ValueError('Loop snapshot changed')
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0);a,p,k=(recipe[n] for n in ('start_frame','period_frames','blend_frames'));root=report['root_node']
    raw=np.array([sampler.sample(float(np.float32(f/30))) for f in range(a,a+p+k)])
    single,cycle,w=assemble(raw,rig.parents,root,recipe);world=single[:-1]
    repeated=np.concatenate([place(world,rig.parents,root,np.linalg.matrix_power(cycle,c)) for c in range(3)]+[place(world[:1],rig.parents,root,np.linalg.matrix_power(cycle,3))])
    clocks=[]
    for f in range(p):
        clocks.append([dict(frame=a+p+f,weight=float(1-w[f]),cycle_offset=-1),dict(frame=a+f,weight=float(w[f]),cycle_offset=0)] if f<k else [dict(frame=a+f,weight=1.,cycle_offset=0)])
    def contributors(count):
        return [[{**entry,'cycle_offset':entry['cycle_offset']+f//p} for entry in clocks[f%p]] for f in range(count)]
    from rig_contact_tracks import signals,ROLES
    masks,origin=signals(report)
    targets=[]
    stored=target_rows(folder/'input')
    if stored is not None:targets=stored
    elif (folder/'input/contact-review.json').exists():targets=read(folder/'input/contact-review.json')['authored_targets']
    audits={}
    for name,poses in [('transfer',single),('repeated',repeated)]:
        out=folder/name;out.mkdir(exist_ok=False);times,audit=encode(rig,poses,{c[0] for c in sampler.channels},root,out/'character.glb',recipe['label']+(' · 3 cycles' if name=='repeated' else ''))
        audits[name]=audit;clock=contributors(len(poses));intervals=[];ambiguous=[]
        for role in ROLES:
            active=[]
            for f,entries in enumerate(clock):
                v=[bool(masks[role][c['frame']]) for c in entries if c['weight']>0];active.append(all(v))
                if len(set(v))>1:ambiguous.append(dict(frame=f,joint=role))
            edges=np.diff(np.r_[False,active,False].astype(int))
            intervals.extend(dict(joint=role,start_frame=int(b),end_frame_exclusive=int(e),start_seconds=b/30,end_seconds_exclusive=e/30,provenance='Intersection of loop source predictions; not verified support') for b,e in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
        save(out/'contacts.json',dict(origin='loop_source_predictions',source_origin=origin,intervals=intervals,ambiguous_support_frames=ambiguous,provenance='Missing annotations are unknown. Loop blending can invalidate support.'))
        authored=[]
        for t in targets:
            weights={e['frame']:e['weight'] for e in t['output_frames']};groups={}
            for f,entries in enumerate(clock):
                for c in entries:
                    weight=c['weight']*weights.get(c['frame'],0)
                    if weight>0:groups.setdefault(c['cycle_offset'],[]).append(dict(frame=f,weight=weight))
            for offset,frames in groups.items():
                matrix=np.linalg.matrix_power(cycle,offset);position=matrix[:3,:3]@t['target_position_m']+matrix[:3,3]
                authored.append(dict(t,target_position_m=position.tolist(),output_frames=frames,source_cycle_offset=offset))
        save(out/'contact-review.json',dict(authored_targets=authored,ambiguous_support_frames=ambiguous,requires_review=True,scope='Targets follow cycle placement and source weights; not fitted or confirmed.'))
        save(out/'timeline.json',dict(period_frames=p,fps=30,frames=len(poses),contributors=clock,cycle_transform=cycle.tolist(),source_glb_sha256=recipe['glb_sha256'],terminal_sample='Last frame duplicates phase zero at the next cycle placement; duration is period_frames/30.'))
        from rig_events import load as load_events,remap as remap_events
        save(out/'events.json',remap_events([load_events(folder/'input')],clock,[dict(name='cycle_boundary',frame=f,time_s=f/30) for f in range(p,len(poses),p)]))
        save(out/'root-motion.json',dict(node=root,space='Mapped pelvis world transform; accumulate cycle_transform at each wrap; do not replay world root from zero',times_s=times.tolist(),positions_m=poses[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(poses[:,root,:3,:3]).as_quat().tolist(),cycle_transform=cycle.tolist()))
        for file in ('inventory.json','rig-profile.json'):shutil.copyfile(folder/'input'/file,out/file)
        rep=copy.deepcopy(report);rep.update(frames=len(poses),fps=30,glb_sha256=sha256(out/'character.glb'),timeline_edited=True,contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),animation_name=recipe['label'],last_key_time_s=float(times[-1]),target_mesh_floor_depth_max_m=audit['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=audit['floor_frames_above_1cm'])
        save(out/'report.json',rep)
    # Compare the repeated seam with the untouched continuation at source end.
    seam_expected=raw[p-1:p+2];seam_actual=repeated[p-1:p+2]
    seam_error=float(np.abs(seam_expected-seam_actual).max())
    velocity=np.diff(repeated[:,root,:3,3],axis=0)*30
    local=localize(repeated,rig.parents);angles=np.degrees(Rotation.from_matrix((np.linalg.inv(local[:-1,:,:3,:3])@local[1:,:,:3,:3]).reshape(-1,3,3)).magnitude()).reshape(len(repeated)-1,-1)
    audit=dict(created_at=now(),period_frames=p,blend_frames=k,cycle_transform=cycle.tolist(),exports=audits,source_seam_transform_error=seam_error,root_speed_max_m_s=float(np.linalg.norm(velocity,axis=1).max()),root_acceleration_max_m_s2=float(np.linalg.norm(np.diff(velocity,axis=0)*30,axis=1).max()),local_rotation_step_max_degrees=float(angles.max()),seam_rotation_step_max_degrees=float(angles[[p-1,p,2*p-1,2*p]].max()),human_approved=False,scope='Three accumulated cycles with exact terminal closure; source seam continuity and sampled floor/dynamics diagnostics. Not naturalness, contact, physical or loop-suitability approval.')
    save(folder/'transfer/loop-audit.json',audit)
    from rig_runtime_cycle import write as write_runtime
    try:write_runtime(folder/'transfer')
    except ValueError as exc:save(folder/'transfer/runtime-unavailable.json',dict(reason=str(exc)))
    return read(folder/'transfer/report.json'),audit
