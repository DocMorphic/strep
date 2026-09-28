"""Bounded native SOMA pose targets, with source and failed candidates retained."""
import math
import re
import shutil
import uuid
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from strep import ROOT, save, sha256, now
from inspect_motion import validate_motion, skeleton_metadata

CHAINS={s+end:[s+a,s+b] for s in ['Left','Right'] for end,a,b in [('Hand','Arm','ForeArm'),('Foot','Leg','Shin')]}


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'motion','sha256','source_frame','effector','offset_m','max_edit_degrees'}:
        raise ValueError('Pose target requires a source motion/hash/frame, hand or foot, offset and edit budget')
    path=payload['motion']
    if not isinstance(path,str) or not path.startswith('reports/') or '\\' in path or '..' in path.split('/') or ':' in path or not path.endswith('.npz'):
        raise ValueError('Use a project report motion NPZ')
    source=(ROOT/path).resolve()
    if not source.is_relative_to((ROOT/'reports').resolve()) or not source.is_file() or source.stat().st_size>64*1024**2:
        raise ValueError('Source motion missing, outside reports, or larger than 64 MiB')
    if not isinstance(payload['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',payload['sha256']) or sha256(source)!=payload['sha256']:
        raise ValueError('Pose source checksum mismatch')
    if not isinstance(payload['effector'],str) or payload['effector'] not in CHAINS:raise ValueError('Choose a left/right hand or foot')
    offset=payload['offset_m'];budget=payload['max_edit_degrees']
    if not isinstance(offset,list) or len(offset)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in offset) or np.linalg.norm(offset)>.5:
        raise ValueError('Use a finite XYZ offset with length at most 0.5 metres')
    if type(budget) not in (int,float) or not math.isfinite(budget) or not 1<=budget<=90:raise ValueError('Rotation edit budget must be 1–90 degrees')
    with np.load(source,allow_pickle=False) as data:motion=dict(data)
    names,parents,_=validate_motion(motion,30);f=payload['source_frame']
    if len(names)!=77 or type(f) is not int or not 0<=f<len(motion['posed_joints']):raise ValueError('Choose a valid SOMA77 source frame')
    return source,motion,names,parents


def solve_pose(local,world,positions,parents,names,effector,target,budget_degrees):
    """Move a two-bone chain; preserve effector orientation and every other chain."""
    local=np.asarray(local,dtype=float);world=np.asarray(world,dtype=float);positions=np.asarray(positions,dtype=float)
    nodes=[names.index(n) for n in CHAINS[effector]];tip=names.index(effector)
    if parents[nodes[1]]!=nodes[0] or parents[tip]!=nodes[1]:raise ValueError('Unexpected SOMA chain hierarchy')
    offsets=np.zeros_like(positions)
    for i,p in enumerate(parents):
        if p>=0:offsets[i]=world[p].T@(positions[i]-positions[p])
    limit=np.deg2rad(budget_degrees)
    def fk(rotations):
        g=np.empty_like(rotations);p=np.empty_like(positions)
        for i,parent in enumerate(parents):
            if parent<0:g[i]=rotations[i];p[i]=positions[i]
            else:g[i]=g[parent]@rotations[i];p[i]=p[parent]+g[parent]@offsets[i]
        return g,p
    reference_world,_=fk(local)
    def evaluate(x):
        rotations=local.copy();rotations[nodes]=local[nodes]@Rotation.from_rotvec(x.reshape(2,3)).as_matrix()
        g,p=fk(rotations);rotations[tip]=np.linalg.solve(g[parents[tip]],reference_world[tip])
        g,p=fk(rotations)
        terminal=Rotation.from_matrix(local[tip].T@rotations[tip]).magnitude()
        return rotations,g,p,terminal
    def objective(x):
        _,_,p,_=evaluate(x)
        return float(np.sum((p[tip]-target)**2)+1e-7*np.dot(x,x))
    def bounds(x):
        terminal=evaluate(x)[3]
        return np.r_[limit**2-np.sum(x.reshape(2,3)**2,axis=1),limit**2-terminal**2]
    attempts=[];best=np.zeros(6);best_cost=objective(best)
    starts=[np.zeros(6)]
    for axis in range(3):
        for sign in [-1,1]:
            x=np.zeros(6);x[3+axis]=sign*min(.12,limit/3);starts.append(x)
    for start in starts:
        result=minimize(objective,start,method='SLSQP',bounds=[(-limit,limit)]*6,
            constraints=[dict(type='ineq',fun=bounds)],options=dict(maxiter=100,ftol=1e-12))
        feasible=bool(np.isfinite(result.x).all() and np.min(bounds(result.x))>=-1e-9)
        cost=objective(result.x) if feasible else None
        attempts.append(dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),feasible=feasible,cost=cost))
        if feasible and cost<best_cost:best=result.x.copy();best_cost=cost
        if np.linalg.norm(evaluate(best)[2][tip]-target)<=.001:break
    result,g,p,terminal=evaluate(best)
    edits=np.degrees(Rotation.from_matrix(local.transpose(0,2,1)@result).magnitude())
    error=float(np.linalg.norm(p[tip]-target));reached=error<=.005 and float(edits.max())<=budget_degrees+1e-5
    descendants={tip}
    for i,parent in enumerate(parents):
        if parent in descendants:descendants.add(i)
    changed=set(nodes)|descendants;fixed=[i for i in range(len(names)) if i not in changed]
    audit=dict(reached=reached,target_error_m=error,target_m=np.asarray(target).tolist(),actual_m=p[tip].tolist(),
        max_local_edit_degrees=float(edits.max()),budget_degrees=budget_degrees,
        changed_local_joints=[names[i] for i in nodes+[tip]],
        unchanged_joint_position_max_error_m=float(np.max(np.abs(p[fixed]-positions[fixed]))),
        effector_orientation_error_degrees=float(np.degrees(Rotation.from_matrix(world[tip].T@g[tip]).magnitude())),
        attempts=attempts,scope='One pose, relative rotation budget, not anatomical limits or collision/physical validation. Root and unedited chains preserved. No solver optimality claim.')
    return result,audit


def author(payload,output=None):
    source,motion,names,parents=validate(payload);f=payload['source_frame'];tip=names.index(payload['effector'])
    from kimodo.skeleton import SOMASkeleton77
    from correct_loops import assemble
    from build_soma_preview import ASSET,make_preview
    from gltf_tools import write_glb
    from audit_body_ground import measure
    skeleton=SOMASkeleton77();original=assemble(motion['local_rot_mats'][[f,f]],motion['root_positions'][[f,f]],np.zeros((2,6),dtype=bool),skeleton)
    if not np.allclose(original['posed_joints'][0],motion['posed_joints'][f],atol=1e-4,rtol=0) or not np.allclose(original['global_rot_mats'][0],motion['global_rot_mats'][f],atol=1e-4,rtol=0):raise ValueError('Source arrays disagree with SOMA kinematics')
    desired=original['posed_joints'][0,tip]+payload['offset_m']
    local,audit=solve_pose(original['local_rot_mats'][0],original['global_rot_mats'][0],original['posed_joints'][0],parents,names,payload['effector'],desired,payload['max_edit_degrees'])
    candidate=assemble(np.repeat(local[None],2,axis=0),original['root_positions'],original['foot_contacts'],skeleton)
    actual_error=float(np.linalg.norm(candidate['posed_joints'][0,tip]-desired))
    audit.update(actual_native_fk_target_error_m=actual_error,reached=bool(audit['reached'] and actual_error<=.005),created_at=now(),request=payload,source_sha256=sha256(source),author_sha256=sha256(Path(__file__)))
    # Two identical samples only satisfy the motion container format: this is a
    # static authored pose, never an interpolated action clip or contact label.
    folder=Path(output) if output else ROOT/'reports/pose-targets'/uuid.uuid4().hex
    folder.mkdir(parents=True,exist_ok=False);save(folder/'request.json',payload)
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',folder/'SOMA-preview-LICENSE.txt')
    skin=dict(np.load(ASSET,allow_pickle=False))
    for name,data in [('original',original),('candidate',candidate)]:
        np.savez_compressed(folder/(name+'.npz'),**data)
        doc,binary,_,_=make_preview(skin,data,np.zeros(3),repeat=False);write_glb(folder/(name+'.glb'),doc,binary)
        audit[name+'_floor_depth_m']=measure(data,skin)['mesh_max_depth_m']
    if sha256(source)!=payload['sha256']:raise ValueError('Source changed while authoring')
    audit['candidate_sha256']=sha256(folder/'candidate.npz');audit['source_frame']=f
    audit['contact_labels']='No inferred labels: all channels zero; original source stays untouched.'
    guide=None
    if audit['reached']:
        guide=dict(type='end-effector',joint_names=[payload['effector']],motion=(folder/'candidate.npz').relative_to(ROOT).as_posix(),sha256=audit['candidate_sha256'],source_frames=[0],frame_indices=[f])
    audit['guide']=guide;save(folder/'audit.json',audit)
    return dict(reached=audit['reached'],guide=guide,audit=audit,base='/files/'+folder.relative_to(ROOT/'reports').as_posix()+'/')
