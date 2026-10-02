"""Bake a reviewed same-character clip transition with explicit source clocks."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_contact_authoring import source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import authored_animation,append_accessor,write_glb,sample_animation


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'schema','label','clips','blend_frames','yaw_degrees'} or payload['schema']!='strep-rig-transition-v1':raise ValueError('Invalid transition recipe')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'])<=160:raise ValueError('Name the transition')
    if not isinstance(payload['clips'],list) or len(payload['clips'])!=2:raise ValueError('Choose two clips')
    snapshots=[]
    for c in payload['clips']:
        if not isinstance(c,dict) or set(c)!={'job','variant','glb_sha256','first_frame','last_frame'}:raise ValueError('Invalid source clip')
        s=source(c['job'],c['variant']);report=s[3]
        if c['glb_sha256']!=sha256(s[4]):raise ValueError('Transition source version changed')
        a,b=c['first_frame'],c['last_frame']
        if type(a) is not int or type(b) is not int or not 0<=a<b<report['frames']:raise ValueError('Choose a valid source range')
        snapshots.append(s)
    a,b=snapshots
    if a[2]['asset_id']!=b[2]['asset_id'] or a[3]['mapping']!=b[3]['mapping']:raise ValueError('Clips must use the same character and bone mapping')
    count=[c['last_frame']-c['first_frame']+1 for c in payload['clips']];k=payload['blend_frames']
    if type(k) is not int or not 3<=k<min(count):raise ValueError('Blend needs at least three frames and must be shorter than both source ranges')
    if sum(count)-k>901:raise ValueError('Joined clip must be at most 30 seconds')
    yaw=payload['yaw_degrees']
    if type(yaw) not in (int,float) or not np.isfinite(yaw) or abs(yaw)>180:raise ValueError('Heading adjustment must be within 180 degrees')
    return snapshots


def prepare(payload,folder):
    snapshots=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    for i,(old,_,request,report,glb) in enumerate(snapshots):
        dest=folder/('input' if i==0 else 'following');dest.mkdir()
        src=folder/'source' if i==0 else dest/'source'
        shutil.copytree(old/'source',src,ignore=shutil.ignore_patterns('implementation'))
        shutil.copyfile(glb,dest/'character.glb')
        metadata=glb.parent if (glb.parent/'inventory.json').exists() else old/'transfer'
        for name in ('inventory.json','rig-profile.json','contacts.json'):shutil.copyfile(metadata/name,dest/name)
        for name in ('events.json','contact-review.json'):
            if (metadata/name).exists():shutil.copyfile(metadata/name,dest/name)
        shutil.copyfile(glb.parent/'root-motion.json',dest/'root-motion.json')
        original='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
        report.update(source=str((src/original).resolve()),character=str((src/'character.glb').resolve()))
        if report.get('timeline_edited'):report['contact_annotations_file']=str((dest/'contacts.json').resolve())
        save(dest/'report.json',report)
        spec=old/'input/contact-spec.json' if payload['clips'][i]['variant']=='input' else old/'contact-spec.json'
        if spec.exists():shutil.copyfile(spec,dest/'contact-spec.json')
        from rig_contact_timing import snapshot,bind_inputs
        snapshot(glb,dest)
    save(folder/'transition.json',payload)
    history=folder/'source/transition-history'/folder.name;history.mkdir(parents=True)
    shutil.copytree(folder/'input',history/'input');shutil.copytree(folder/'following',history/'following');shutil.copyfile(folder/'transition.json',history/'transition.json')
    report=snapshots[0][3];original='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    request=dict(kind='transition',label=payload['label'],asset_id=snapshots[0][2]['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),source_kind=report.get('source_kind','soma_motion'),
        source_motion_sha256=sha256(folder/'source'/original),correct_contacts=False,recipe_sha256=sha256(folder/'transition.json'))
    bind_inputs(folder,request)
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def localize(world,parents):
    local=world.copy()
    for n,p in enumerate(parents):
        if p>=0:local[:,n]=np.linalg.inv(world[:,p])@world[:,n]
    return local


def compose(local,parents):
    def depth(n):return 0 if parents[n]<0 else depth(parents[n])+1
    world=np.empty_like(local)
    for n in sorted(range(len(parents)),key=depth):world[:,n]=local[:,n] if parents[n]<0 else world[:,parents[n]]@local[:,n]
    return world


def blend(a,b,weights):
    output=a.copy();output[:,:,:3,3]=(1-weights[:,None,None])*a[:,:,:3,3]+weights[:,None,None]*b[:,:,:3,3]
    qa=Rotation.from_matrix(a[:,:,:3,:3].reshape(-1,3,3));qb=Rotation.from_matrix(b[:,:,:3,:3].reshape(-1,3,3))
    delta=(qa.inv()*qb).as_rotvec().reshape(len(a),a.shape[1],3)
    output[:,:,:3,:3]=(qa*Rotation.from_rotvec((delta*weights[:,None,None]).reshape(-1,3))).as_matrix().reshape(a[:,:,:3,:3].shape)
    return output


def run(folder):
    folder=Path(folder);recipe=read(folder/'transition.json');request=read(folder/'request.json')
    from rig_contact_timing import verify_inputs,target_rows
    verify_inputs(folder,request)
    if sha256(folder/'transition.json')!=request['recipe_sha256']:raise ValueError('Transition recipe changed')
    rigs=[];reports=[];worlds=[];locals=[];frame_maps=[];animated=set()
    for i,name in enumerate(('input','following')):
        path=folder/name/'character.glb';c=recipe['clips'][i]
        if sha256(path)!=c['glb_sha256']:raise ValueError('Transition input changed')
        rig=RigAsset.load(path);rigs.append(rig);reports.append(read(folder/name/'report.json'))
        if reports[-1]['glb_sha256']!=c['glb_sha256'] or sha256(reports[-1]['source'])!=reports[-1]['source_sha256']:raise ValueError('Transition source provenance changed')
        sampler=AnimationSampler(rig.document,rig.binary,0);animated.update(c[0] for c in sampler.channels);frames=np.arange(c['first_frame'],c['last_frame']+1)
        world=np.array([sampler.sample(float(np.float32(f/30))) for f in frames]);worlds.append(world);frame_maps.append(frames)
    if rigs[0].parents!=rigs[1].parents:raise ValueError('Source hierarchies differ')
    root=reports[0]['root_node'];na,nb=map(len,worlds);k=recipe['blend_frames'];offset=na-k
    alignment=np.eye(4);alignment[:3,:3]=Rotation.from_euler('y',recipe['yaw_degrees'],degrees=True).as_matrix()
    delta=worlds[0][offset,root,:3,3]-alignment[:3,:3]@worlds[1][0,root,:3,3];delta[1]=0;alignment[:3,3]=delta
    original_b=localize(worlds[1],rigs[1].parents);aligned_b=original_b.copy();parent=rigs[1].parents[root]
    desired=alignment@worlds[1][:,root]
    aligned_b[:,root]=desired if parent<0 else np.linalg.inv(worlds[1][:,parent])@desired
    worlds[1]=compose(aligned_b,rigs[1].parents)
    locals=[localize(worlds[0],rigs[0].parents),aligned_b]
    u=np.linspace(0,1,k);weights=u*u*(3-2*u)
    local=np.concatenate([locals[0][:offset],blend(locals[0][offset:],locals[1][:k],weights),locals[1][k:]])
    world=compose(local,rigs[0].parents);n=len(world);times=np.arange(n,dtype=np.float32)/30
    doc,binary=copy.deepcopy(rigs[0].document),bytearray(rigs[0].binary);animation=authored_animation(recipe['label'])
    time_accessor=append_accessor(doc,binary,times,'SCALAR')
    from target_rig_contact import prepare_animated_node
    for node in sorted(animated|{root}):
        prepare_animated_node(doc,node);q=Rotation.from_matrix(local[:,node,:3,:3]).as_quat()
        for f in range(1,n):
            if q[f]@q[f-1]<0:q[f]*=-1
        for target,values,kind in [('translation',local[:,node,:3,3],'VEC3'),('rotation',q,'VEC4')]:
            output=append_accessor(doc,binary,values,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=target)))
            animation['samplers'].append(dict(input=time_accessor,output=output,interpolation='LINEAR'))
    doc['animations']=[animation];doc.setdefault('extras',{})['strep_transition']=dict(recipe_sha256=request['recipe_sha256'],source_glb_sha256=[c['glb_sha256'] for c in recipe['clips']])
    out=folder/'transfer';out.mkdir(exist_ok=False);write_glb(out/'character.glb',doc,binary);decoded=RigAsset.load(out/'character.glb')
    error=0.;skin_error=0.;floor=[]
    for f in range(n):
        actual=sample_animation(decoded.document,decoded.binary,0,f);points=decoded.vertices(actual)
        error=max(error,float(np.abs(actual-world[f]).max()));skin_error=max(skin_error,float(np.linalg.norm(points-rigs[0].vertices(world[f]),axis=1).max()));floor.append(max(0.,-float(points[:,1].min())))
    if max(error,skin_error)>1e-5:raise ValueError('Transition GLB roundtrip failed')
    clocks=[]
    for f in range(n):
        contributors=[]
        if f<na:contributors.append(dict(source=0,frame=int(frame_maps[0][f]),weight=float(1-weights[f-offset]) if f>=offset else 1.))
        if f>=offset:contributors.append(dict(source=1,frame=int(frame_maps[1][f-offset]),weight=float(weights[f-offset]) if f<na else 1.))
        clocks.append(contributors)
    from rig_contact_tracks import signals,ROLES
    loaded_signals=[signals(r) for r in reports];masks=[s[0] for s in loaded_signals];origins=[s[1] for s in loaded_signals];intervals=[];ambiguous=[]
    for role in ROLES:
        active=[]
        for f,contributors in enumerate(clocks):
            values=[bool(masks[c['source']][role][c['frame']]) for c in contributors if c['weight']>0]
            active.append(all(values))
            if len(set(values))>1:ambiguous.append(dict(frame=f,joint=role))
        edges=np.diff(np.r_[False,active,False].astype(int));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)
        intervals += [dict(joint=role,start_frame=int(a),end_frame_exclusive=int(b),start_seconds=a/30,end_seconds_exclusive=b/30,provenance='Conservative intersection of contributing source predictions; support unconfirmed') for a,b in zip(starts,ends)]
    save(out/'contacts.json',dict(origin='blended_source_predictions',source_origins=origins,intervals=intervals,provenance='Both positive-weight contributors must predict support during the blend. Missing annotations are unknown, not confirmation of no contact.',ambiguous_support_frames=ambiguous))
    authored=[]
    for i,name in enumerate(('input','following')):
        targets=target_rows(folder/name)
        if targets is None:targets=read(folder/name/'contact-review.json')['authored_targets'] if (folder/name/'contact-review.json').exists() else []
        for target_row in targets:
            source_weights={entry['frame']:entry['weight'] for entry in target_row['output_frames']}
            frames=[dict(frame=f,weight=entry['weight']*source_weights[entry['frame']]) for f,entries in enumerate(clocks) for entry in entries if entry['source']==i and entry['weight']>0 and source_weights.get(entry['frame'],0)>0]
            target=np.array(target_row['target_position_m'])
            if i:target=alignment[:3,:3]@target+alignment[:3,3]
            authored.append(dict(target_row,source=i,target_position_m=target.tolist(),output_frames=frames))
    save(out/'contact-review.json',dict(authored_targets=authored,ambiguous_support_frames=ambiguous,requires_review=True,scope='Source targets are remapped and retained for review; they are not fitted or promoted to verified contacts.'))
    save(out/'timeline.json',dict(fps=30,frames=n,blend_start_frame=offset,blend_last_frame=na-1,sources=recipe['clips'],contributors=clocks,second_alignment_matrix=alignment.tolist()))
    from rig_events import load as load_events,remap as remap_events
    save(out/'events.json',remap_events([load_events(folder/'input'),load_events(folder/'following')],clocks,[dict(name='transition_start',frame=offset,time_s=offset/30),dict(name='transition_end',frame=na-1,time_s=(na-1)/30)]))
    save(out/'root-motion.json',dict(space='Mapped pelvis world transform; second clip XZ aligned at overlap start, explicit yaw, original vertical placement retained',node=root,times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist()))
    for name in ('inventory.json','rig-profile.json'):shutil.copyfile(folder/'input'/name,out/name)
    np.savez_compressed(out/'target-transforms.npz',global_matrices=world,times_s=times)
    speed=np.diff(world[:,root,:3,3],axis=0)*30;acceleration=np.diff(speed,axis=0)*30
    mismatch=float(np.degrees(Rotation.from_matrix((np.linalg.inv(locals[0][offset:,:,:3,:3])@locals[1][:k,:,:3,:3]).reshape(-1,3,3)).magnitude()).max())
    audit=dict(created_at=now(),frames=n,blend_start_frame=offset,blend_last_frame=na-1,source_pose_disagreement_max_degrees=mismatch,
        floor_depth_max_m=max(floor),floor_failed_frames=sum(v>.005 for v in floor),root_speed_max_m_s=float(np.linalg.norm(speed,axis=1).max()),root_acceleration_max_m_s2=float(np.linalg.norm(acceleration,axis=1).max()),
        roundtrip_max_matrix_error=error,roundtrip_max_skin_error_m=skin_error,ambiguous_support_count=len(ambiguous),human_approved=False,
        scope='Baked smoothstep local-pose transition. Floor, root dynamics and support diagnostics; no claim of physical/action/contact correctness.')
    save(out/'transition-audit.json',audit)
    report=reports[0];report.update(frames=n,fps=30,glb_sha256=sha256(out/'character.glb'),timeline_edited=True,contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),
        animation_name=recipe['label'],last_key_time_s=float(times[-1]),target_mesh_floor_depth_max_m=max(floor),target_mesh_floor_frames_above_1cm=sum(v>.01 for v in floor),transition_sources=recipe['clips'])
    save(out/'report.json',report);return report,audit


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);run(p.parse_args().folder)
