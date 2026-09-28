"""Experimental whole-surface clearance with bounded pelvis lift and limb anchors.

Root XZ and orientation remain fixed. This is a kinematic floor correction,
not a balance/dynamics solver. Contact candidates come from geometry, not text.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from floor_contact import Surface, reconstruct, smooth_lift, correct as limb_correct
from correct_stance import knee_target, swing
from inspect_motion import validate_motion
from audit_body_ground import measure

CONFIG=dict(max_root_lift_m=.22,clearance_m=.002,iterations=5,
            anchor_full_height_m=.012,anchor_fade_height_m=.08,
            minimum_body_depth_m=.01,max_spine_pitch_degrees=20)


def anchor_weights(base,surface):
    weights={}
    for name in surface.regions:
        heights=surface.heights(base,name)
        u=np.clip((CONFIG['anchor_fade_height_m']-heights)/
                  (CONFIG['anchor_fade_height_m']-CONFIG['anchor_full_height_m']),0,1)
        weights[name]=u*u*(3-2*u)
    return weights


def anchored_lift(base,lift,weights,parents,names,target_lifts=None,spine_clearance=None):
    local=base['local_rot_mats'].astype(float).copy()
    shifted={k:v.copy() for k,v in base.items()}
    shifted['root_positions'][:,1]+=lift
    # reconstruct uses global positions only to recover rest offsets.
    result=reconstruct(shifted,local,parents)
    if spine_clearance is not None:
        joint=names.index('Spine1');arms=[names.index('LeftArm'),names.index('RightArm')]
        for f in range(len(local)):
            amount=min(lift[f]*max(weights['LeftHand'][f],weights['RightHand'][f]),max(0,spine_clearance[f]-.04))
            if amount<1e-8:continue
            vector=base['posed_joints'][f,arms].mean(0)-base['posed_joints'][f,joint]
            length=np.linalg.norm(vector);horizontal=vector.copy();horizontal[1]=0
            if np.linalg.norm(horizontal)<1e-6:continue
            target=horizontal/np.linalg.norm(horizontal)*np.sqrt(max(1e-10,length**2-(vector[1]-amount)**2))
            target[1]=np.clip(vector[1]-amount,-length+.00001,length-.00001)
            rv=Rotation.from_matrix(swing(vector,target)).as_rotvec();angle=np.linalg.norm(rv)
            rv*=min(1,np.deg2rad(CONFIG['max_spine_pitch_degrees'])/max(angle,1e-10))
            desired=Rotation.from_rotvec(rv).as_matrix()@base['global_rot_mats'][f,joint]
            local[f,joint]=result['global_rot_mats'][f,parents[joint]].T@desired
        result=reconstruct(shifted,local,parents)
    errors={}
    for region,weight in weights.items():
        end=names.index(region);middle=parents[end];start=parents[middle]
        errors[region]=[]
        for f,w in enumerate(weight):
            height=0 if target_lifts is None else target_lifts[region][f]
            if lift[f]*w+height<1e-9 and spine_clearance is None:
                errors[region].append(0.);continue
            p=result['posed_joints'][f];r=result['global_rot_mats'][f]
            a,b,c=p[[start,middle,end]].astype(float)
            target=base['posed_joints'][f,end].astype(float)+np.array([0,lift[f]*(1-w)+height,0])
            nb,nc,error=knee_target(a,b,c,target)
            ra=swing(b-a,nb-a)@r[start];rb=swing(c-b,nc-nb)@r[middle]
            local[f,start]=r[parents[start]].T@ra
            local[f,middle]=ra.T@rb
            local[f,end]=rb.T@base['global_rot_mats'][f,end]
            errors[region].append(float(error))
        result=reconstruct(shifted,local,parents)
    return result,errors


def refine(base,skin):
    names,parents,_=validate_motion(base,30);surface=Surface(skin)
    before=measure(base,skin)
    if before['mesh_max_depth_m']<=CONFIG['minimum_body_depth_m']:
        return {k:v.copy() for k,v in base.items()},dict(config=CONFIG,applied=False,root_lift_m=[0.]*len(base['root_positions']))
    weights=anchor_weights(base,surface);lift=np.zeros(len(base['root_positions']))
    target_lifts={k:np.maximum(0,CONFIG['clearance_m']-surface.heights(base,k)) for k in surface.regions}
    excluded=np.concatenate(list(surface.regions.values()))
    body_indices=np.setdiff1d(np.arange(len(surface.points)),excluded)
    dominant=surface.indices[np.arange(len(surface.indices)),surface.weights.argmax(1)]
    torso_indices=np.flatnonzero(np.isin(dominant,[names.index(n) for n in ['Spine1','Spine2','Chest','Neck1','Neck2','Head']]))
    spine_clearance=np.array([surface.vertices(r,p,torso_indices)[:,1].min() for r,p in zip(base['global_rot_mats'],base['posed_joints'])])
    result=base;errors={};history=[]
    for _ in range(CONFIG['iterations']):
        measured=measure(result,skin)
        required=np.array([max(0,-surface.vertices(r,p,body_indices)[:,1].min()) for r,p in zip(result['global_rot_mats'],result['posed_joints'])])
        required=np.where(required>.001,required+CONFIG['clearance_m'],0.)
        lift=smooth_lift(lift+required,CONFIG['max_root_lift_m'])
        result,errors=anchored_lift(base,lift,weights,parents,names,target_lifts,spine_clearance)
        history.append(dict(max_depth_before_m=measured['mesh_max_depth_m'],max_requested_lift_m=float(lift.max())))
    # This network-derived auxiliary path no longer describes the edited root.
    # Core export arrays are sufficient; do not carry stale model features.
    result.pop('smooth_root_pos',None)
    return result,dict(config=CONFIG,applied=True,root_lift_m=lift.tolist(),anchor_weights={k:v.tolist() for k,v in weights.items()},
                       reach_errors_m=errors,iterations=history,omitted_auxiliary_fields=['smooth_root_pos'],
                       scope='Vertical pelvis edit with original moving end-effector trajectories retained near the floor. Does not remove existing sliding or infer certified contacts.')


def correct(source,skin):
    base,limb_recipe=limb_correct(source,skin)
    result,body_recipe=refine(base,skin)
    return result,dict(limb=limb_recipe,body=body_recipe)
