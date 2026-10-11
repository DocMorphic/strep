"""Conditional rigid-distance exclusion for rotation-only pose targets.

Distance is invariant when no editable rotation can move exactly one endpoint
around a third pivot. Endpoint/common-ancestor rotations preserve distance.
Non-exclusion is not feasibility; translations and other edit modes are outside
this preflight. Near-rigid input drift receives a conservative numerical guard.
"""
import numpy as np


def preflight(local,parents,targets,edited_nodes):
    local=np.asarray(local,dtype=float);parents=np.asarray(parents)
    if (parents.ndim!=1 or parents.dtype.kind not in 'iu' or not 1<=len(parents)<=512
            or np.any(parents< -1) or np.any(parents>=len(parents))):raise ValueError('Bounded valid pose hierarchy required')
    if local.shape!=(len(parents),4,4) or not np.isfinite(local).all() or not np.allclose(local[:,3],[0,0,0,1],atol=1e-12,rtol=0):
        raise ValueError('Complete finite affine local poses required')
    if (not isinstance(targets,(list,tuple)) or not 1<=len(targets)<=256
            or not isinstance(edited_nodes,(list,tuple))
            or any(type(n) is not int or not 0<=n<len(parents) for n in edited_nodes)
            or len(set(edited_nodes))!=len(edited_nodes)):
        raise ValueError('Explicit bounded targets and distinct edited nodes required')
    goal=[]
    for target in targets:
        if (not isinstance(target,dict) or set(target)!={'node','world_matrix','position_tolerance_m','rotation_tolerance_degrees'}
                or type(target['node']) is not int or not 0<=target['node']<len(parents)):
            raise ValueError('Complete explicit target required')
        m=np.asarray(target['world_matrix'],dtype=float)
        if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1],atol=1e-12,rtol=0):raise ValueError('Finite affine target required')
        if any(type(target[k]) not in (int,float) or not np.isfinite(target[k]) or target[k]<=0
               for k in ('position_tolerance_m','rotation_tolerance_degrees')):raise ValueError('Positive target tolerances required')
        goal.append(m[:3,3])
    world=np.empty_like(local);ancestors={};state=np.zeros(len(parents),dtype=int)
    def visit(n):
        if state[n]==1:raise ValueError('Cyclic pose hierarchy')
        if state[n]==2:return
        state[n]=1;p=int(parents[n])
        if p<0:world[n]=local[n];ancestors[n]=set()
        else:visit(p);world[n]=world[p]@local[n];ancestors[n]=ancestors[p]|{p}
        state[n]=2
    for n in range(len(parents)):visit(n)
    rotation=local[:,:3,:3];drift=float(np.max(abs(rotation.swapaxes(-1,-2)@rotation-np.eye(3))))
    determinant=float(np.max(abs(np.linalg.det(rotation)-1)))
    assessed=drift<=1e-12 and determinant<=1e-12
    extent=max(1.,float(np.max(abs(world[:,:3,3]))),float(np.max(abs(local[:,:3,3]))),float(np.max(np.abs(goal))))
    guard=1e-9+len(parents)**2*extent*(128*np.finfo(float).eps+4*max(drift,determinant))
    pairs=[];skipped=0;edits=set(edited_nodes)
    if assessed:
        for i,a in enumerate(targets):
            for j in range(i+1,len(targets)):
                b=targets[j];n,m=a['node'],b['node']
                pivots=(ancestors[n]^ancestors[m])-{n,m}
                if edits&pivots:skipped+=1;continue
                actual=float(np.linalg.norm(world[n,:3,3]-world[m,:3,3]));desired=float(np.linalg.norm(goal[i]-goal[j]))
                discrepancy=abs(actual-desired);allowed=a['position_tolerance_m']+b['position_tolerance_m']
                pairs.append(dict(target_indices=[i,j],nodes=[n,m],invariant_distance_m=actual,requested_distance_m=desired,
                    minimum_sum_position_error_m=discrepancy,minimum_max_endpoint_error_m=discrepancy/2,
                    allowed_sum_position_error_m=float(allowed),numerical_guard_m=guard,
                    excluded=bool(discrepancy>allowed+guard)))
    return dict(schema='strep-pose-length-preflight-v1',status='assessed' if assessed else 'not_assessed_nonrigid_drift',
        position_targets_excluded=any(p['excluded'] for p in pairs),pairs=pairs,skipped_variable_distance_pairs=skipped,
        rotation_orthogonality_max_error=drift,numerical_guard_m=guard,
        non_exclusion_proves_feasibility=False,quality_approved=False,release_approved=False,
        scope='Conditional numerical distance exclusion with fixed local translations and only declared local rotations editable. Endpoint/common-ancestor rotations allowed. Other intermediate rotations, translation/length edits and surface contacts require different analysis. Orientation tolerances, caps, dynamics and whole-motion feasibility not certified.')
