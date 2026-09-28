"""Decoded splice/preservation oracle, raw-vs-output diagnostics and package checks."""
import io
import os
import json
import zipfile
import hashlib
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from urllib.request import urlopen
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from retarget_rig import calibration,resolve_profile
from gltf_tools import local_matrix


def localize(world,parents):
    local=world.copy()
    for node,parent in enumerate(parents):
        if parent>=0:local[:,node]=np.linalg.inv(world[:,parent])@world[:,node]
    return local


def verify(job,out):
    import torch
    from kimodo.skeleton import SOMASkeleton77,SOMASkeleton30
    folder=ROOT/'reports/rig-jobs'/job;edit=read(folder/'prompt-edit.json');report=read(folder/'input/report.json');result=read(folder/'result.json');a,b,k=(edit[x] for x in ('start_frame','last_frame','blend_frames'));n=b-a+1;frames=report['frames']
    source=RigAsset.load(folder/'input/character.glb');output=RigAsset.load(folder/'transfer/character.glb');reference=RigAsset.load(folder/'source/character.glb')
    sampler=AnimationSampler(source.document,source.binary,0);actual_sampler=AnimationSampler(output.document,output.binary,0)
    before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(frames)]);after=np.array([actual_sampler.sample(float(np.float32(f/30))) for f in range(frames)])
    profile=read(folder/'source/rig-profile.json');skeleton=SOMASkeleton77();mapping,offset=resolve_profile(reference,profile);corrections,scale,_=calibration(reference,mapping,skeleton,profile.get('axis_alignment_xyzw'))
    raw_path=folder/'generation/takes'/f'replacement-seed-{edit["seed"]}'/'motion.npz';raw=dict(np.load(raw_path,allow_pickle=False));aligned=dict(np.load(folder/'generation/aligned-generated.npz',allow_pickle=False));audit=read(folder/'transfer/prompt-edit-audit.json')
    origin=np.array(audit['origin_offset_m']);np.testing.assert_allclose(aligned['root_positions'],raw['root_positions']+origin,atol=1e-7)
    # Independently assemble mapped desired world rotations, reference helper locals and hips.
    world=np.empty((n,len(reference.parents),4,4));order=[]
    def depth(node):return 0 if reference.parents[node]<0 else depth(reference.parents[node])+1
    inverse={node:skeleton.bone_order_names.index(role) for role,node in mapping.items()}
    for node in sorted(range(len(reference.parents)),key=depth):
        parent=reference.parents[node];pw=np.broadcast_to(np.eye(4),(n,4,4)) if parent<0 else world[:,parent]
        local=(localize(before[a:b+1],source.parents)[:,node].copy()
               if audit.get('transfer_context',{}).get('source_context_preserved')
               else np.repeat(local_matrix(reference.document['nodes'][node])[None],n,axis=0))
        if node in inverse:
            desired=aligned['global_rot_mats'][:,inverse[node]]@corrections[node]
            local[:,:3,:3]=Rotation.from_matrix(np.linalg.inv(pw[:,:3,:3])@desired).as_matrix()
            if node==mapping['Hips']:local[:,:3,3]=(np.linalg.inv(pw)@np.c_[aligned['root_positions']*scale+offset,np.ones(n)][:,:,None])[:,:3,0]
        world[:,node]=pw@local
    before_local=localize(before,source.parents);raw_local=localize(world,source.parents);expected=before_local.copy();w=np.zeros(frames)
    for i in range(n):
        edge=min(i,n-1-i);u=min(1.,max(0.,(edge-1)/(k-2)));weight=u*u*(3-2*u);f=a+i;w[f]=weight
        expected[f,:,:3,3]=(1-weight)*before_local[f,:,:3,3]+weight*raw_local[i,:,:3,3]
        for node in range(len(source.parents)):
            expected[f,node,:3,:3]=Slerp([0,1],Rotation.from_matrix(np.array([before_local[f,node,:3,:3],raw_local[i,node,:3,:3]])))([weight]).as_matrix()[0]
    actual_local=localize(after,source.parents);local_error=float(np.abs(actual_local-expected).max());preserved=float(np.abs(after[w==0]-before[w==0]).max());assert max(local_error,preserved)<1e-5
    floor={};half={};step={}
    for label,rig,poses,sm in [('before',source,before,sampler),('after',output,after,actual_sampler)]:
        floor[label]=max(max(0.,-float(rig.vertices(p)[:,1].min())) for p in poses)
        half[label]=max(max(0.,-float(rig.vertices(sm.sample((f+.5)/30))[:,1].min())) for f in range(frames-1))
        loc=localize(poses,source.parents)[:,:,:3,:3];angle=np.degrees(Rotation.from_matrix((loc[:-1].transpose(0,1,3,2)@loc[1:]).reshape(-1,3,3)).magnitude()).reshape(frames-1,-1)
        step[label]=dict(max_degrees=float(angle.max()),edit_edge_max_degrees=float(angle[max(0,a-1):min(frames-1,a+k)].max()),return_edge_max_degrees=float(angle[max(0,b-k):min(frames-1,b+1)].max()))
    # SOMA30 FK comparison independent of adapter JSON loading.
    guide=dict(np.load(folder/'source/guide-motion.npz',allow_pickle=False));small=SOMASkeleton30();anchors=[0,1,n-2,n-1]
    positions=[]
    for data in [guide,raw]:
        local=small.from_SOMASkeleton77(torch.tensor(data['local_rot_mats'][anchors]));_,pos,_=small.fk(local,torch.tensor(data['root_positions'][anchors]));positions.append(pos.numpy())
    anchor_error=float(np.linalg.norm(positions[0]-positions[1],axis=-1).max());assert abs(anchor_error-audit['raw_anchor_audit']['guides'][0]['maximum']['joint_position_error_m'])<1e-5
    original_events=read(folder/'input/events.json') if (folder/'input/events.json').exists() else dict(events=[])
    events=read(folder/'transfer/events.json');assert len(events['events'])==len(original_events['events'])
    for old,new in zip(original_events['events'],events['events']):
        assert new['frame']==old['frame']
        if w[new['frame']]>0:assert new['requires_review']
        else:assert old==new
    root=read(folder/'transfer/root-motion.json');assert np.max(np.abs(np.array(root['positions_m'])-after[:,report['root_node'],:3,3]))<1e-5
    package=urlopen('http://127.0.0.1:8768'+result['package']).read();assert hashlib.sha256(package).hexdigest()==result['package_sha256']
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name!='README.txt':assert z.read(name)==(folder/name).read_bytes()
        entries=len(z.namelist())
    for v in result['variants'].values():assert hashlib.sha256(urlopen('http://127.0.0.1:8768'+v['glb']).read()).hexdigest()==v['sha256']
    record=read(raw_path.parent/'generation-record.json');assert record['npz_sha256']==sha256(raw_path)
    from audit_body_ground import measure
    from build_soma_preview import ASSET
    native_ground=measure(raw,dict(np.load(ASSET,allow_pickle=False)))
    save(out/(job+'-native-ground.json'),dict(**native_ground,raw_sha256=sha256(raw_path),skin_sha256=sha256(ASSET)))
    raw_target_floor=max(max(0.,-float(reference.vertices(p)[:,1].min())) for p in world)
    return dict(job=job,local_oracle_error=local_error,preserved_world_error=preserved,preserved_frames=int((w==0).sum()),floor_m=floor,half_frame_floor_m=half,raw_native_mesh_floor_m=native_ground['mesh_max_depth_m'],raw_retargeted_mesh_floor_m=raw_target_floor,rotation_steps=step,raw_anchor_error_m=anchor_error,raw_anchor_passed=audit['raw_anchor_audit']['numerical_screen_passed'],generation_seconds=record['generation_time_s'],package_entries=entries,raw_sha256=sha256(raw_path),output_sha256=sha256(folder/'transfer/character.glb'))


if __name__=='__main__':
    out=ROOT/'reports/prompt-edit-v1';checks={name:verify(job,out) for name,job in read(out/'cases.json').items()};manifest=[]
    for name,c in checks.items():
        folder=ROOT/'reports/rig-jobs'/c['job'];frames=read(folder/'transfer/report.json')['frames']
        for variant in ['input','transfer']:
            file=folder/variant/'character.glb';manifest.append(dict(id=name+'-'+variant,path=os.path.relpath(file,out).replace('\\','/'),sha256=sha256(file),frames=frames,fps=30))
    save(out/'manifest.json',dict(cases=manifest));save(out/'verification.json',dict(checks=checks,scope='Independent source-clock, per-node Slerp splice, preservation, raw anchor FK, integer/half-frame floor, joint-step diagnostics, root/events and all HTTP/archive bytes. Calibration shared with established rig adapter. No action/animator approval.'));print(json.dumps(checks))
