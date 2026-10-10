"""Source-capped pose fitting that favors continuity with a previous local pose.

Wrist/other rigid-node targets are soft residuals. Actual skin contacts, temporal
limits, collision and human quality require separate evaluation of the clip.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from bounded_pose_ik import hierarchy_order,world_matrices


def _rigid(value,label):
    value=np.asarray(value,dtype=float)
    if (value.shape[-2:]!=(4,4) or not np.isfinite(value).all()
            or not np.allclose(value[...,3,:],[0,0,0,1],atol=1e-8,rtol=0)):
        raise ValueError('Finite affine '+label+' required')
    rotation=value[...,:3,:3]
    if (not np.allclose(rotation.swapaxes(-1,-2)@rotation,np.eye(3),atol=1e-5,rtol=0)
            or not np.allclose(np.linalg.det(rotation),1,atol=1e-5,rtol=0)):
        raise ValueError('Proper rigid '+label+' required')
    return value


def solve(local,parents,targets,edit_limits_degrees,previous,max_evaluations=200,
          *,source_weight=.002,continuation_weight=.02):
    """Fit one pose with explicit source caps and previous-local rotation weights.

    Translation and nonselected local matrices are copied from current source.
    Previous rotations initialize the fit after projection inside source caps;
    previous translations are never copied. The fallback is that projected
    initialization, whose target residuals remain reported even if unmatched.
    """
    parents=np.asarray(parents);order=hierarchy_order(parents)
    local=_rigid(local,'source local transforms');previous=_rigid(previous,'previous local transforms')
    if local.shape!=(len(parents),4,4) or previous.shape!=local.shape:
        raise ValueError('Matching complete source/previous node populations required')
    if (not isinstance(edit_limits_degrees,dict) or not edit_limits_degrees
            or any(type(n) is not int or not 0<=n<len(parents) for n in edit_limits_degrees)):
        raise ValueError('Explicit existing edited nodes required')
    nodes=list(edit_limits_degrees);limits=list(edit_limits_degrees.values())
    if any(type(v) not in (int,float) or not np.isfinite(v) or not 0<v<=90 for v in limits):
        raise ValueError('Finite positive source rotation caps up to 90 degrees required')
    if type(max_evaluations) is not int or not 1<=max_evaluations<=1000:
        raise ValueError('Explicit bounded solver iterations from 1 to 1000 required')
    if any(type(v) not in (int,float) or not np.isfinite(v) or not 0<=v<=1 for v in [source_weight,continuation_weight]):
        raise ValueError('Finite explicit rotation weights from zero to one required')
    if not isinstance(targets,list) or not targets:
        raise ValueError('At least one explicit rigid-node target required')
    for target in targets:
        if (not isinstance(target,dict) or set(target)!={'node','world_matrix','position_tolerance_m','rotation_tolerance_degrees'}
                or type(target['node']) is not int or not 0<=target['node']<len(parents)):
            raise ValueError('Complete existing rigid-node target required')
        if _rigid(target['world_matrix'],'target transform').shape!=(4,4):
            raise ValueError('Single rigid target transform required')
        if any(type(target[k]) not in (int,float) or not np.isfinite(target[k]) or target[k]<=0
               for k in ['position_tolerance_m','rotation_tolerance_degrees']):
            raise ValueError('Finite positive target reporting tolerances required')
    radii=np.radians(limits)
    seed=Rotation.from_matrix(local[nodes,:3,:3].transpose(0,2,1)@previous[nodes,:3,:3]).as_rotvec()
    lengths=np.linalg.norm(seed,axis=1);seed*=np.minimum(1.,radii*.999999/np.maximum(lengths,1e-30))[:,None]
    start=seed.ravel();reference_previous=previous[nodes,:3,:3]
    def evaluate(x):
        candidate=local.copy();candidate[nodes,:3,:3]=local[nodes,:3,:3]@Rotation.from_rotvec(x.reshape(-1,3)).as_matrix()
        world=world_matrices(candidate,parents,order);values=[];checks=[]
        for target in targets:
            current=world[target['node']];desired=np.asarray(target['world_matrix']);p=current[:3,3]-desired[:3,3];r=Rotation.from_matrix(desired[:3,:3].T@current[:3,:3]).as_rotvec()
            values.extend(p*100);values.extend(r*2);distance=float(np.linalg.norm(p));angle=float(np.degrees(np.linalg.norm(r)))
            checks.append(dict(node=target['node'],position_error_m=distance,rotation_error_degrees=angle,matched=distance<=target['position_tolerance_m'] and angle<=target['rotation_tolerance_degrees']))
        previous_delta=Rotation.from_matrix(reference_previous.transpose(0,2,1)@candidate[nodes,:3,:3]).as_rotvec()
        residual=np.r_[values,x*source_weight,previous_delta.ravel()*continuation_weight]
        if not np.isfinite(residual).all():raise ValueError('Finite transformed pose residuals required')
        return candidate,checks,float(residual@residual)
    def slack(x):return 1-np.sum(x.reshape(-1,3)**2,axis=1)/radii**2
    def jacobian(x):
        jac=np.zeros((len(nodes),len(x)))
        for i in range(len(nodes)):jac[i,3*i:3*i+3]=-2*x[3*i:3*i+3]/radii[i]**2
        return jac
    initial_cost=evaluate(start)[2]
    result=minimize(lambda x:evaluate(x)[2],start,method='SLSQP',jac='3-point',bounds=list(zip(-np.repeat(radii,3),np.repeat(radii,3))),constraints=[dict(type='ineq',fun=slack,jac=jacobian)],options=dict(maxiter=max_evaluations,ftol=1e-12))
    finite=np.isfinite(result.x).all();feasible=finite and np.all(np.linalg.norm(result.x.reshape(-1,3),axis=1)<=radii+1e-8)
    candidate,checks,cost=evaluate(result.x) if finite else (None,[],float('inf'))
    accepted=bool(feasible and cost<=initial_cost+1e-12)
    chosen=result.x if accepted else start;candidate,checks,cost=evaluate(chosen)
    report=dict(solver_success=bool(result.success),status=int(result.status),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev),edited_nodes=nodes,rotation_vectors_rad=chosen.reshape(-1,3).tolist(),initial_rotation_vectors_rad=seed.tolist(),max_edit_degrees=np.degrees(np.linalg.norm(chosen.reshape(-1,3),axis=1)).tolist(),targets=checks,targets_matched=all(c['matched'] for c in checks),initial_squared_residual=initial_cost,final_squared_residual=cost,optimized_candidate_accepted=accepted,source_regularization_weight=source_weight,previous_local_rotation_weight=continuation_weight,source_cap_allowance_rad=1e-8,quality_approved=False,release_approved=False,scope='Explicit source-relative norm caps and protected source locals/translations, previous-local-pose initialization/regularization. Soft rigid-node residuals; actual skin/contact/temporal acceptance belongs to separate replay. No anatomy, full-motion or global-optimality certificate.')
    return candidate,report
