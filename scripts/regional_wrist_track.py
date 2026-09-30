"""Frame-local native geometry and source-bounded moving wrist projection."""
import copy
import numpy as np
import torch
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from rigid_contact_placement import bounded
from region_grasp_track import arm_columns
from scene_solver_context import context_primitives
from joint_continuity import rotation_residual


def frame_problem(reference,frame,scene,anchors,contacts=True):
    if type(frame) is not int or not 0<=frame<len(reference.base['root_positions']):raise ValueError('Native frame required')
    p=copy.copy(reference);p.frame=frame;p.initial=p.t(p.base['local_rot_mats'][frame]);p.root=p.t(p.base['root_positions'][frame])
    offsets=np.zeros((len(p.parents),3))
    for j,parent in enumerate(p.parents):
        if parent>=0:offsets[j]=p.base['global_rot_mats'][frame,parent].T@(p.base['posed_joints'][frame,j]-p.base['posed_joints'][frame,parent])
    p.offsets=p.t(offsets);p.objects=[(g,o['id'],p.t(o['positions_m'][frame])[None],p.t(o['rotations'][frame])[None]) for g,o in context_primitives(p.context)]
    p.regions=copy.deepcopy(reference.regions) if contacts else []
    for r in p.regions:
        c=next(c for c in scene['contacts'] if c['id']==r['id']);g,_,position,rotation=next(o for o in p.objects if o[1]==c['target']['object'])
        r['position']=position.numpy()[0];r['rotation']=rotation.numpy()[0];r['target']=r['position']+r['rotation']@c['target']['point_m']
        r['normal']=-r['rotation']@g.local_surface_normal(c['target']['point_m'])
        r['anchor']=anchors[r['id']];r['local_anchor']=int(np.flatnonzero(r['ids']==r['anchor'])[0])
    return p


def fixed_finger_parameters(problem,reference_parameters,reference_local):
    values=np.array(reference_parameters).copy()
    locked=[j for j,n in enumerate(problem.names) if 'Hand' in n and n not in ['LeftHand','RightHand'] and j not in problem.editable]
    if np.any(np.isin(problem.indices,locked)&(problem.skin['lbs_weights']>0)):
        raise ValueError('Uneditable hand nodes influence skin; fixed hand shape unsupported')
    slots=[i for i,j in enumerate(problem.editable) if 'Hand' in problem.names[j] and problem.names[j] not in ['LeftHand','RightHand']]
    joints=[problem.editable[i] for i in slots]
    angles=Rotation.from_matrix(problem.base['local_rot_mats'][problem.frame,joints].transpose(0,2,1)@reference_local[joints]).as_rotvec()
    if np.any(np.linalg.norm(angles,axis=1)>problem.limits[slots]+1e-9):raise ValueError('Fixed hand shape exceeds original frame-local finger budgets')
    for slot,angle in zip(slots,angles):values[3*slot:3*slot+3]=angle
    return values


def project(problem,fixed,initial_angles,targets,guard,maximum_evaluations=100,check_derivative=False,previous_local=None,continuity_weight=0.):
    if type(continuity_weight) not in [int,float] or not np.isfinite(continuity_weight) or continuity_weight<0:
        raise ValueError('Finite nonnegative continuity weight required')
    if (previous_local is None)!=(continuity_weight==0):raise ValueError('Physical continuity requires prior rotations and a positive weight')
    if previous_local is not None and (np.asarray(previous_local).shape!=problem.initial.shape or not np.isfinite(previous_local).all()):
        raise ValueError('Previous local rotation layout changed')
    if previous_local is not None:previous_local=np.asarray(previous_local)
    columns,limits=arm_columns(problem);scaled=np.asarray(initial_angles).reshape(-1,3)/limits[:,None]
    arm_joints=np.array(problem.editable)[columns.reshape(-1,3)[:,0]//3]
    if np.any(np.sum(scaled**2,axis=1)>=1):raise ValueError('Interior bounded arm initialization required')
    initial=(scaled/np.sqrt(1-np.sum(scaled**2,axis=1))[:,None]).ravel()
    hp=copy.copy(problem);hp.indices=problem.indices[:1];hp.bind=problem.bind[:1];hp.weights=problem.weights[:1]
    def physical(raw):return problem.t(fixed).index_copy(0,torch.as_tensor(columns),bounded(raw.reshape(-1,3),problem.t(limits)[:,None]).reshape(-1))
    def geometry(raw):
        rotations,positions,_,_=hp.fk(physical(raw));values=[]
        for hand,target in targets.items():
            wrist=problem.names.index(hand)
            values.extend([(positions[wrist]-problem.t(target['position']))/.001,((rotations[wrist]-problem.t(target['rotation']))/.01).reshape(-1)])
        return torch.cat(values)
    def preference(raw):
        if previous_local is None:return 1e-6*(raw-problem.t(initial))
        theta=physical(raw)[columns].reshape(-1,3)
        return rotation_residual(problem.initial[arm_joints],theta,problem.t(previous_local[arm_joints]),continuity_weight)
    class Reached(Exception):pass
    cache=None;last=initial.copy();evaluations=0;early=False
    def pair(raw):
        nonlocal cache,last,evaluations
        if cache is not None and np.array_equal(cache[0],raw):return cache[1:]
        guard();variable=problem.t(raw).requires_grad_();values=geometry(variable);array=values.detach().numpy()
        last=raw.copy();evaluations+=1
        # Numerical target stopping only. Independent serialized contact/bounds
        # determine pose acceptance; this does not waive any geometry condition.
        if early and all(np.linalg.norm(row[:3])<.001 and np.linalg.norm(row[3:])<.001 for row in array.reshape(-1,12)):
            raise Reached()
        all_values=torch.cat([values,preference(variable)])
        jac=np.array([torch.autograd.grad(v,variable,retain_graph=True)[0].detach().numpy() for v in all_values])
        residual=all_values.detach().numpy()
        cache=raw.copy(),residual,jac;return residual,jac
    derivative_error=None
    if check_derivative:
        _,jac=pair(initial);direction=np.random.default_rng(549).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-6
        with torch.no_grad():
            plus=problem.t(initial+h*direction);minus=problem.t(initial-h*direction)
            fd=((torch.cat([geometry(plus),preference(plus)])-torch.cat([geometry(minus),preference(minus)]))/(2*h)).numpy()
        np.testing.assert_allclose(jac@direction,fd,atol=2e-5,rtol=2e-4);derivative_error=float(abs(jac@direction-fd).max())
    early=True;cache=None;status='complete'
    try:
        fitted=least_squares(lambda raw:pair(raw)[0],initial,jac=lambda raw:pair(raw)[1],max_nfev=maximum_evaluations,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        last=fitted.x;solver=dict(termination='scipy',success=bool(fitted.success),message=str(fitted.message),evaluations=int(fitted.nfev))
    except Reached:solver=dict(termination='numerical_wrist_targets_reached',success=None,evaluations=evaluations)
    except TimeoutError as exc:status='interrupted_resource_guard';solver=dict(termination='resource_guard',success=False,message=str(exc),evaluations=evaluations)
    return physical(problem.t(last)).detach().numpy(),dict(status=status,solver=solver,raw_parameters=last.tolist(),derivative_error=derivative_error)
