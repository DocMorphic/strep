"""Hash-bound, timed local finger-pose authoring on an existing rigged clip."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_loop import encode
from verify_rig_clearance import localize


def integer(value):return type(value) is int


def weight(frames,pose):
    f=np.arange(frames,dtype=float);a,b,c,d=(pose[k] for k in ['start_frame','full_start_frame','full_end_frame','end_frame'])
    attack=np.clip((f-a)/(b-a),0,1);release=np.clip((d-f)/(d-c),0,1)
    smooth=lambda x:x*x*(3-2*x)
    return np.minimum(smooth(attack),smooth(release))*pose['strength']


def validate(recipe,rig,source_hash):
    required={'schema','source_glb_sha256','frames','fps','hand_roots','poses','limits','provenance'}
    if not isinstance(recipe,dict) or set(recipe)!=required or recipe['schema']!='strep-hand-posture-v1':raise ValueError('Invalid posture recipe')
    if recipe['source_glb_sha256']!=source_hash:raise ValueError('Source animation changed')
    if recipe['fps']!=30 or not integer(recipe['frames']) or not 3<=recipe['frames']<=18000:raise ValueError('Invalid clock')
    if not isinstance(recipe['provenance'],str) or not 1<=len(recipe['provenance'])<=2000:raise ValueError('Name the authored pose provenance')
    roots=recipe['hand_roots']
    if not isinstance(roots,list) or not 1<=len(roots)<=2 or len(set(roots))!=len(roots) or any(not integer(n) or n not in rig.joints for n in roots):raise ValueError('Declare one or two mapped hand roots')
    limits=recipe['limits']
    if not isinstance(limits,dict) or set(limits)!={'rotation_degrees','correction_step_degrees'}:raise ValueError('Explicit edit budgets required')
    for k,maximum in [('rotation_degrees',90),('correction_step_degrees',5)]:
        v=limits[k]
        if type(v) not in (int,float) or not np.isfinite(v) or not 0<v<=maximum:raise ValueError('Invalid edit budget')
    poses=recipe['poses'];occupied={};ids=set();selected=set()
    if not isinstance(poses,list) or not 1<=len(poses)<=64:raise ValueError('Choose 1–64 posture intervals')
    for p in poses:
        keys={'id','hand_root','targets','start_frame','full_start_frame','full_end_frame','end_frame','strength'}
        if not isinstance(p,dict) or set(p)!=keys:raise ValueError('Invalid posture interval')
        if not isinstance(p['id'],str) or not 1<=len(p['id'])<=100 or p['id'] in ids:raise ValueError('Use unique posture IDs')
        ids.add(p['id'])
        a,b,c,d=(p[k] for k in ['start_frame','full_start_frame','full_end_frame','end_frame'])
        if not all(integer(n) for n in [a,b,c,d]) or not 0<=a<b<=c<d<recipe['frames']:raise ValueError('Invalid posture timing')
        if type(p['strength']) not in (int,float) or not np.isfinite(p['strength']) or not 0<=p['strength']<=1:raise ValueError('Invalid posture strength')
        if not integer(p['hand_root']) or p['hand_root'] not in roots:raise ValueError('Choose a declared hand root')
        if not isinstance(p['targets'],list) or not 1<=len(p['targets'])<=32:raise ValueError('Choose finger targets')
        seen=set()
        for target in p['targets']:
            if not isinstance(target,dict) or set(target)!={'node','rotation_xyzw'}:raise ValueError('Invalid rotation target')
            n=target['node']
            if not integer(n) or n not in rig.joints or n in seen or n in roots:raise ValueError('Invalid finger node')
            parent=rig.parents[n]
            while parent>=0 and parent!=p['hand_root']:parent=rig.parents[parent]
            if parent!=p['hand_root']:raise ValueError('Target is outside the declared hand')
            q=np.asarray(target['rotation_xyzw'],dtype=float)
            if q.shape!=(4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q)-1)>1e-5:raise ValueError('Target must be a unit quaternion')
            frames=set(range(a+1,d))
            if occupied.get(n,set())&frames:raise ValueError('Overlapping edits on the same finger')
            occupied.setdefault(n,set()).update(frames);seen.add(n);selected.add(n)
    return sorted(selected)


def author(local,parents,recipe):
    result=np.array(local,copy=True);edited=set();weights={}
    for pose in recipe['poses']:
        w=weight(len(local),pose);weights[pose['id']]=w
        for target in pose['targets']:
            node=target['node'];edited.add(node);desired=Rotation.from_quat(target['rotation_xyzw']).as_matrix()
            relative=local[:,node,:3,:3].transpose(0,2,1)@desired
            delta=Rotation.from_matrix(relative).as_rotvec()*w[:,None]
            active=w>0
            result[active,node,:3,:3]=local[active,node,:3,:3]@Rotation.from_rotvec(delta[active]).as_matrix()
    checks=[]
    for node in sorted(edited):
        delta=local[:,node,:3,:3].transpose(0,2,1)@result[:,node,:3,:3]
        angles=Rotation.from_matrix(delta).magnitude()
        steps=Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude()
        if angles.max()>np.radians(recipe['limits']['rotation_degrees'])+1e-8 or steps.max()>np.radians(recipe['limits']['correction_step_degrees'])+1e-8:raise ValueError('Authored posture exceeds edit budget')
        checks.append(dict(node=node,max_edit_degrees=float(np.degrees(angles).max()),max_correction_step_degrees=float(np.degrees(steps).max())))
    world=np.empty_like(result);depth=[]
    for n in range(len(parents)):
        d=0;p=parents[n]
        while p>=0:d+=1;p=parents[p]
        depth.append(d)
    for n in np.argsort(depth):world[:,n]=result[:,n] if parents[n]<0 else world[:,parents[n]]@result[:,n]
    return world,weights,checks


def run(source,recipe,output):
    source=Path(source).resolve();output=Path(output).resolve();rig=RigAsset.load(source);digest=sha256(source)
    selected=validate(recipe,rig,digest)
    sampler=AnimationSampler(rig.document,rig.binary,0);times=np.arange(recipe['frames'],dtype=np.float32)/30
    if abs(float(times[-1])-sampler.duration)>1e-5:raise ValueError('Recipe clock does not match the complete clip')
    original=np.array([sampler.sample(float(t)) for t in times]);local=localize(original,rig.parents)
    world,weights,checks=author(local,rig.parents,recipe)
    if output.exists():raise ValueError('Preserve existing output')
    output.mkdir(parents=True);shutil.copyfile(source,output/'input.glb');save(output/'posture.json',recipe)
    (output/'implementation').mkdir()
    sources=['hand_posture.py','rig_asset.py','rig_clip_import.py','rig_loop.py','verify_rig_clearance.py']
    for name in sources:shutil.copyfile(Path(__file__).parent/name,output/'implementation'/name)
    root=rig.skin.get('skeleton',rig.joints[0]);animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(selected)
    with threadpool_limits(limits=1):_,roundtrip=encode(rig,world,animated,root,output/'character.glb','Authored hand posture')
    decoded=RigAsset.load(output/'character.glb');other=AnimationSampler(decoded.document,decoded.binary,0)
    actual=np.array([other.sample(float(t)) for t in times]);new_local=localize(actual,rig.parents)
    untouched=[n for n in range(len(rig.parents)) if n not in selected]
    frozen=~np.any(np.stack(list(weights.values()))>0,axis=0)
    preservation=dict(unedited_local_max_error=float(np.abs(new_local[:,untouched]-local[:,untouched]).max()),
        all_local_translations_max_error=float(np.abs(new_local[:,:,:3,3]-local[:,:,:3,3]).max()),
        outside_intervals_world_max_error=float(np.abs(actual[frozen]-original[frozen]).max()),frozen_frames=int(frozen.sum()))
    if max(v for k,v in preservation.items() if k!='frozen_frames')>1e-5:raise ValueError('Protected motion changed')
    decoded_checks=[]
    for node in selected:
        delta=local[:,node,:3,:3].transpose(0,2,1)@new_local[:,node,:3,:3]
        angle=float(Rotation.from_matrix(delta).magnitude().max())
        step=float(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude().max())
        if angle>np.radians(recipe['limits']['rotation_degrees'])+1e-5 or step>np.radians(recipe['limits']['correction_step_degrees'])+1e-5:raise ValueError('Decoded posture exceeds edit budget')
        decoded_checks.append(dict(node=node,max_edit_degrees=float(np.degrees(angle)),max_correction_step_degrees=float(np.degrees(step))))
    if sha256(source)!=digest:raise ValueError('Input changed during authoring')
    report=dict(at=now(),source_glb_sha256=digest,glb_sha256=sha256(output/'character.glb'),frames=len(times),
        selected_nodes=selected,edit_checks=checks,decoded_edit_checks=decoded_checks,preservation=preservation,roundtrip=roundtrip,quality_approved=False,
        provenance='Authored local finger rotations, separate from model generation. Hand-root mapping and anatomical/contact validity require review.')
    save(output/'verification.json',report)
    save(output/'posture-events.json',dict(kind='authored_posture_intent',poses=recipe['poses'],contact_verified=False))
    save(output/'pipeline.json',dict(status='complete',quality_approved=False));return actual


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('recipe',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.source,read(a.recipe),a.output)
