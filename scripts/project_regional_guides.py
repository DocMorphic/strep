"""Project explicitly alternative regional guides onto source-bounded arms."""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from rigid_contact_placement import bounded


def rigid_wrist_target(wrist_position,wrist_rotation,anchor,matrix,point):
    return matrix@(wrist_position-anchor)+point,matrix@wrist_rotation


def run(source,output):
    torch.set_num_threads(2);source,output=Path(source).resolve(),Path(output).resolve()
    rp,rr=read(source/'protocol.json'),read(source/'result.json')
    if rr['status']!='complete' or rr['protocol_sha256']!=sha256(source/'protocol.json'):raise ValueError('Complete matching guide study required')
    for path,digest in rp['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Guide input changed')
    for name,digest in rp['methods'].items():
        if sha256(source/'implementation'/name)!=digest:raise ValueError('Guide method snapshot changed')
    hand_protocol=read(ROOT/rp['source']/'protocol.json');prior=read(ROOT/hand_protocol['study']/'protocol.json')
    p=RegionalPoseProblem(ROOT/prior['fit'],prior['frame']);base=np.array(hand_protocol['seed_parameters'])
    inputs=dict(rp['inputs']);inputs.update({str(source/n):sha256(source/n) for n in ['protocol.json','result.json']})
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    settings=dict(evaluations=160,seconds_per_hand=60.,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3),
        position_scale_m=.001,orientation_scale=.01,regularization=1e-6,reach_position_m=.0001,reach_rotation_degrees=.1)
    protocol=dict(at=now(),source=source.relative_to(ROOT).as_posix(),inputs=inputs,methods={q.name:sha256(q) for q in snap.iterdir()},settings=settings,
        selection='Project rank zero per hand under the frozen guide-study ranking. Combine only disjoint arm/finger parameter blocks; independently audit original and alternative guides.',
        scope='Alternative guide vertices, unchanged original patch faces/normals/targets/numeric gates and source-relative rotation norms. One native pose only; no anatomical, self-collision, balance, temporal, force or clip approval.',quality_approved=False)
    save(output/'protocol.json',protocol);hands=[];used=set();combined=base.copy();alternative=copy.copy(p);alternative.regions=copy.deepcopy(p.regions)
    for hand in ['LeftHand','RightHand']:
        if not rr['ranked'][hand]:raise ValueError('No passing alternative for '+hand)
        row=rr['ranked'][hand][0];shape=rp['shapes'][row['shape_index']]
        if not row['alternative_condition_passed'] or shape['hand']!=hand:raise ValueError('Invalid ranked candidate')
        seed=np.array(shape['parameters']);anchor=row['anchor'];region=next(r for r in p.regions if r['anchor']==shape['original_anchor'])
        before,motion=p.independent(seed);vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);wrist=p.names.index(hand)
        matrix=np.array(shape['orientations'][row['orientation_index']]['rotation']);point=region['target']-row['placement_gap_m']*region['normal']
        position,target_rotation=rigid_wrist_target(motion['posed_joints'][0,wrist],motion['global_rot_mats'][0,wrist],vertices[anchor],matrix,point)
        prefix=hand.removesuffix('Hand');joints=[prefix+n for n in ['Shoulder','Arm','ForeArm','Hand']]
        slots=np.array([p.lookup[p.names.index(n)] for n in joints]);columns=np.array([3*i+k for i in slots for k in range(3)])
        finger_slots=[i for i,j in enumerate(p.editable) if p.names[j].startswith(hand) and p.names[j]!=hand]
        merge_columns=np.r_[columns,[3*i+k for i in finger_slots for k in range(3)]].astype(int)
        if used.intersection(merge_columns):raise ValueError('Arm/finger parameter blocks overlap')
        used.update(merge_columns);frozen=np.setdiff1d(np.arange(p.dim),columns)
        np.testing.assert_array_equal(seed[np.setdiff1d(np.arange(p.dim),merge_columns)],base[np.setdiff1d(np.arange(p.dim),merge_columns)])
        limits=p.limits[slots];scaled=seed[columns].reshape(-1,3)/limits[:,None]
        if np.any(np.sum(scaled**2,axis=1)>=1):raise ValueError('Interior bounded arm seed required')
        initial=(scaled/np.sqrt(1-np.sum(scaled**2,axis=1))[:,None]).ravel()
        hp=copy.copy(p);hp.indices=p.indices[:1];hp.bind=p.bind[:1];hp.weights=p.weights[:1]
        folder=output/hand;folder.mkdir();started=time.monotonic();peak=0;last=initial.copy();cache=None;history=[]
        def parameters(raw):return p.t(seed).index_copy(0,torch.as_tensor(columns),bounded(raw.reshape(-1,3),p.t(limits)[:,None]).reshape(-1))
        def geometry(raw):
            rotations,positions,_,_=hp.fk(parameters(raw))
            return torch.cat([(positions[wrist]-p.t(position))/settings['position_scale_m'],((rotations[wrist]-p.t(target_rotation))/settings['orientation_scale']).reshape(-1)])
        def pair(raw):
            nonlocal last,cache,peak
            if cache is not None and np.array_equal(raw,cache[0]):return cache[1:]
            peak=max(peak,psutil.Process().memory_info().rss)
            if time.monotonic()-started>settings['seconds_per_hand'] or peak>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:
                raise TimeoutError('Bounded arm projection resource guard')
            variable=p.t(raw).requires_grad_();values=geometry(variable)
            jac=np.array([torch.autograd.grad(v,variable,retain_graph=True)[0].detach().numpy() for v in values])
            residual=np.r_[values.detach().numpy(),settings['regularization']*(raw-initial)]
            jac=np.r_[jac,settings['regularization']*np.eye(len(raw))];last=raw.copy()
            history.append(dict(evaluation=len(history)+1,squared_residual=float(residual@residual)))
            cache=raw.copy(),residual,jac;return residual,jac
        _,jac=pair(initial);direction=np.random.default_rng(441).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-6
        with torch.no_grad():fd=((geometry(p.t(initial+h*direction))-geometry(p.t(initial-h*direction)))/(2*h)).numpy()
        np.testing.assert_allclose(jac[:12]@direction,fd,atol=2e-5,rtol=2e-4);derivative_error=float(abs(jac[:12]@direction-fd).max());status='complete'
        try:
            fit=least_squares(lambda raw:pair(raw)[0],initial,jac=lambda raw:pair(raw)[1],max_nfev=settings['evaluations'],ftol=1e-11,xtol=1e-11,gtol=1e-11)
            last=fit.x;solver=dict(success=bool(fit.success),message=str(fit.message),evaluations=int(fit.nfev))
        except TimeoutError as exc:status='interrupted_resource_guard';solver=dict(success=False,message=str(exc))
        physical=parameters(p.t(last)).detach().numpy();np.testing.assert_array_equal(physical[frozen],seed[frozen])
        audit,motion=p.independent(physical)
        if not audit['bounds_passed']:raise ValueError('Original rotation norms failed')
        reach_position=float(np.linalg.norm(motion['posed_joints'][0,wrist]-position))
        reach_rotation=float(np.rad2deg(np.linalg.norm(Rotation.from_matrix(target_rotation.T@motion['global_rot_mats'][0,wrist]).as_rotvec())))
        reached=reach_position<=settings['reach_position_m'] and reach_rotation<=settings['reach_rotation_degrees']
        np.savez(folder/'pose.npz',**motion)
        record=dict(hand=hand,status=status,solver=solver,source_rank=row,parameters=physical.tolist(),seed_parameters=seed.tolist(),raw_parameters=last.tolist(),
            arm_columns=columns.tolist(),merge_columns=merge_columns.tolist(),target_wrist_position=position.tolist(),target_wrist_rotation=target_rotation.tolist(),
            reach_position_m=reach_position,reach_rotation_degrees=reach_rotation,target_reached=bool(reached),original_condition_audit=audit,
            derivative_error=derivative_error,seconds=time.monotonic()-started,peak_rss_bytes=peak,history=history,pose_sha256=sha256(folder/'pose.npz'),quality_approved=False)
        save(folder/'result.json',record);hands.append(record);combined[merge_columns]=physical[merge_columns]
        alt_region=next(r for r in alternative.regions if r['id']==region['id']);alt_region['anchor']=anchor;alt_region['local_anchor']=int(np.flatnonzero(alt_region['ids']==anchor)[0])
        print(dict(hand=hand,reached=reached,position_error_m=reach_position,rotation_error_degrees=reach_rotation),flush=True)
    original_audit,motion=p.independent(combined);alternative_audit,alt_motion=alternative.independent(combined)
    for key in motion:np.testing.assert_array_equal(motion[key],alt_motion[key])
    np.testing.assert_array_equal(combined[np.setdiff1d(np.arange(p.dim),list(used))],base[np.setdiff1d(np.arange(p.dim),list(used))])
    np.savez(output/'pose.npz',**motion)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Projection input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Projection method changed')
    result=dict(at=now(),status='complete',parameters=combined.tolist(),original_condition_audit=original_audit,alternative_condition_audit=alternative_audit,
        both_targets_reached=all(h['target_reached'] for h in hands),alternative_pose_passed=bool(all(h['target_reached'] for h in hands) and alternative_audit['pose_witness_passed']),
        hand_results={h['hand']:sha256(output/h['hand']/'result.json') for h in hands},protocol_sha256=sha256(output/'protocol.json'),pose_sha256=sha256(output/'pose.npz'),quality_approved=False)
    save(output/'result.json',result);print(result,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.source,args.output)
