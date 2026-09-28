"""Refine a feasible pose using the full per-joint rotation-vector norm budget."""
import copy
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from bounded_pose_ik import solve as box_solve,hierarchy_order,world_matrices


def solve(local,parents,targets,edit_limits_degrees,max_evaluations=200):
    initial,baseline=box_solve(local,parents,targets,edit_limits_degrees,max_evaluations)
    local=np.asarray(local,dtype=float);parents=np.asarray(parents);order=hierarchy_order(parents)
    nodes=baseline['edited_nodes'];radii=np.radians([edit_limits_degrees[n] for n in nodes]);start=np.asarray(baseline['rotation_vectors_rad']).ravel()
    def evaluate(x):
        candidate=local.copy();candidate[nodes,:3,:3]=local[nodes,:3,:3]@Rotation.from_rotvec(x.reshape(-1,3)).as_matrix()
        world=world_matrices(candidate,parents,order);values=[];checks=[]
        for target in targets:
            current=world[target['node']];desired=np.asarray(target['world_matrix']);p=current[:3,3]-desired[:3,3];r=Rotation.from_matrix(desired[:3,:3].T@current[:3,:3]).as_rotvec()
            values.extend(p*100);values.extend(r*2);distance=float(np.linalg.norm(p));angle=float(np.degrees(np.linalg.norm(r)))
            checks.append(dict(node=target['node'],position_error_m=distance,rotation_error_degrees=angle,matched=distance<=target['position_tolerance_m'] and angle<=target['rotation_tolerance_degrees']))
        residual=np.r_[values,x*.02]
        return candidate,checks,float(residual@residual)
    def slack(x):return 1-np.sum(x.reshape(-1,3)**2,axis=1)/radii**2
    def jacobian(x):
        jac=np.zeros((len(nodes),len(x)))
        for i in range(len(nodes)):jac[i,3*i:3*i+3]=-2*x[3*i:3*i+3]/radii[i]**2
        return jac
    initial_cost=evaluate(start)[2]
    result=minimize(lambda x:evaluate(x)[2],start,method='SLSQP',jac='3-point',bounds=list(zip(-np.repeat(radii,3),np.repeat(radii,3))),
        constraints=[dict(type='ineq',fun=slack,jac=jacobian)],options=dict(maxiter=max_evaluations,ftol=1e-12))
    finite=np.isfinite(result.x).all();feasible=finite and np.all(np.linalg.norm(result.x.reshape(-1,3),axis=1)<=radii+1e-8)
    candidate,checks,cost=evaluate(result.x) if finite else (None,[],float('inf'))
    # Retain the previous feasible result on regressions or numerical failure.
    accepted=bool(feasible and cost<=initial_cost+1e-12 and (not baseline['targets_matched'] or all(c['matched'] for c in checks)))
    report=copy.deepcopy(baseline)
    report['box_initializer']=copy.deepcopy(baseline)
    report['norm_refinement']=dict(solver_success=bool(result.success),status=int(result.status),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev),
        candidate_feasible=bool(feasible),candidate_targets=checks,initial_squared_residual=initial_cost,candidate_squared_residual=cost if finite else None,accepted=accepted)
    if accepted:
        report.update(solver_success=bool(result.success),status=int(result.status),evaluations=int(result.nfev),targets_matched=all(c['matched'] for c in checks),targets=checks,
            rotation_vectors_rad=result.x.reshape(-1,3).tolist(),max_edit_degrees=np.degrees(np.linalg.norm(result.x.reshape(-1,3),axis=1)).tolist())
        initial=candidate
    report['scope']='Rigid-joint pose fit with exact per-joint rotation-vector norm constraints. Feasible box initializer retained if refinement violates budgets, regresses cost or loses an already matched target. No anatomy, surface contact, motion or global-optimality certificate.'
    return initial,report
