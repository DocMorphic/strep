"""Bounded rigid-joint pose fit with explicit residuals and no quality promotion."""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def hierarchy_order(parents):
    parents=np.asarray(parents)
    if parents.ndim!=1 or not np.issubdtype(parents.dtype,np.integer) or np.any(parents< -1) or np.any(parents>=len(parents)):raise ValueError('Invalid parents')
    order=[];state=np.zeros(len(parents),dtype=int)
    def visit(node):
        if state[node]==1:raise ValueError('Cyclic hierarchy')
        if state[node]==2:return
        state[node]=1
        if parents[node]>=0:visit(int(parents[node]))
        state[node]=2;order.append(node)
    for node in range(len(parents)):visit(node)
    return order


def world_matrices(local,parents,order):
    world=np.empty_like(local)
    for node in order:world[node]=local[node] if parents[node]<0 else world[parents[node]]@local[node]
    return world


def solve(local,parents,targets,edit_limits_degrees,max_evaluations=200):
    local=np.asarray(local,dtype=float);parents=np.asarray(parents);order=hierarchy_order(parents)
    if local.shape!=(len(parents),4,4) or not np.isfinite(local).all() or not np.allclose(local[:,3],[0,0,0,1],atol=1e-8):raise ValueError('Finite affine local matrices required')
    rotations=local[:,:3,:3]
    if np.max(np.abs(rotations.transpose(0,2,1)@rotations-np.eye(3)))>1e-5 or np.max(np.abs(np.linalg.det(rotations)-1))>1e-5:raise ValueError('Rigid local rotations required')
    if not isinstance(edit_limits_degrees,dict) or not edit_limits_degrees:raise ValueError('Explicit edited joints required')
    nodes=list(edit_limits_degrees);limits=np.array(list(edit_limits_degrees.values()),dtype=float)
    if any(type(n) is not int or not 0<=n<len(parents) for n in nodes) or not np.isfinite(limits).all() or np.any(limits<=0) or np.any(limits>90):raise ValueError('Invalid edit limits')
    if not targets:raise ValueError('At least one target required')
    for target in targets:
        if set(target)!={'node','world_matrix','position_tolerance_m','rotation_tolerance_degrees'} or type(target['node']) is not int or not 0<=target['node']<len(parents):raise ValueError('Invalid target')
        m=np.asarray(target['world_matrix'],dtype=float)
        if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1],atol=1e-8):raise ValueError('Invalid target matrix')
        if not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3),atol=1e-5) or abs(np.linalg.det(m[:3,:3])-1)>1e-5:raise ValueError('Invalid target rotation')
        if any(type(target[k]) not in (int,float) or not np.isfinite(target[k]) or target[k]<=0 for k in ['position_tolerance_m','rotation_tolerance_degrees']):raise ValueError('Positive target tolerances required')
    bounds=np.repeat(np.radians(limits)/np.sqrt(3),3)
    def evaluate(x):
        changed=local.copy();changed[nodes,:3,:3]=local[nodes,:3,:3]@Rotation.from_rotvec(x.reshape(-1,3)).as_matrix()
        return changed,world_matrices(changed,parents,order)
    def residual(x):
        _,world=evaluate(x);values=[]
        for target in targets:
            current=world[target['node']];desired=np.asarray(target['world_matrix'])
            values.extend((current[:3,3]-desired[:3,3])*100)
            values.extend(Rotation.from_matrix(desired[:3,:3].T@current[:3,:3]).as_rotvec()*2)
        return np.r_[values,x*.02]
    result=least_squares(residual,np.zeros(len(bounds)),bounds=(-bounds,bounds),max_nfev=max_evaluations,ftol=1e-10,xtol=1e-10,gtol=1e-10)
    if not np.isfinite(result.x).all() or np.any(np.abs(result.x)>bounds+1e-10):raise ValueError('Solver exceeded hard parameter bounds')
    changed,world=evaluate(result.x);checks=[]
    for target in targets:
        current=world[target['node']];desired=np.asarray(target['world_matrix']);distance=float(np.linalg.norm(current[:3,3]-desired[:3,3]));angle=float(np.degrees(Rotation.from_matrix(desired[:3,:3].T@current[:3,:3]).magnitude()))
        checks.append(dict(node=target['node'],position_error_m=distance,rotation_error_degrees=angle,matched=distance<=target['position_tolerance_m'] and angle<=target['rotation_tolerance_degrees']))
    report=dict(solver_success=bool(result.success),status=int(result.status),evaluations=int(result.nfev),targets_matched=all(t['matched'] for t in checks),targets=checks,
        edited_nodes=nodes,rotation_vectors_rad=result.x.reshape(-1,3).tolist(),max_edit_degrees=np.degrees(np.linalg.norm(result.x.reshape(-1,3),axis=1)).tolist(),
        quality_approved=False,scope='Rigid-joint pose only. Conservative component boxes guarantee total local edit caps. No anatomy, surface contact, whole-motion or continuous-time approval. Infeasible residuals retained.')
    return changed,report
