"""Full-row affine feasibility restoration toward an aggregate-loss proposal."""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows

POSTCHECK=1e-8


def restore(system,jacobian,anchor,target,lower,upper,*,hard_rows,iterations=32,maximum_nonzeros=6000000):
    anchor,target,lower,upper=[np.asarray(v,float).copy() for v in (anchor,target,lower,upper)]
    if (not isinstance(system,NormRows) or any(not np.isfinite(v).all() for v in (system.vectors,system.caps,system.scales)) or np.any(system.scales<=0) or anchor.ndim!=1 or not len(anchor)
            or any(v.shape!=anchor.shape or not np.isfinite(v).all() for v in (anchor,target,lower,upper))
            or np.any(lower>upper) or any(np.any(v<lower) or np.any(v>upper) for v in (anchor,target))
            or type(hard_rows) is not int or not 0<=hard_rows<=len(system.caps)
            or type(iterations) is not int or not 1<=iterations<=64
            or type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=6000000):
        raise ValueError('Complete finite endpoints, original delta boxes and bounded complete-row search required')
    jac=sparse.csr_matrix(jacobian,copy=True)
    if jac.shape!=(system.vectors.size,len(anchor)) or not np.isfinite(jac.data).all() or jac.nnz>maximum_nonzeros:raise ValueError('Complete finite Jacobian within the declared budget required; no subset returned')
    probes=[]
    def check(point,fraction):
        residual=system.residual(jac,point);finite=bool(np.isfinite(residual).all())
        row=dict(fraction=float(fraction),finite=finite,passed=False)
        if finite:
            row.update(maximum_hard_excess=float(residual[:hard_rows].max()) if hard_rows else 0.,failed_hard_rows=int((residual[:hard_rows]>POSTCHECK).sum()),positive_soft_sum=float(np.maximum(residual[hard_rows:],0).sum()))
            row['passed']=bool(row['failed_hard_rows']==0 and np.all(point>=lower) and np.all(point<=upper))
        probes.append(row);return row
    first=check(anchor,0.)
    if not first['passed']:raise ValueError('Anchor must pass every original hard affine row and delta box')
    last=check(target,1.);low=0.;high=1.;point=anchor.copy();selected=first
    if last['passed']:low=1.;point=target.copy();selected=last
    else:
        # Every complete norm sublevel and box is convex along this segment.
        # Re-evaluate all rows at each probe, including numerically marginal ones.
        for _ in range(iterations):
            fraction=(low+high)/2.;candidate=(1.-fraction)*anchor+fraction*target;row=check(candidate,fraction)
            if row['passed']:low=fraction;point=candidate;selected=row
            else:high=fraction
    reserve=128*(len(system.caps)+3*len(anchor)+4)*np.finfo(float).eps*max(1.,first['positive_soft_sum'],selected['positive_soft_sum'])
    gain=first['positive_soft_sum']-selected['positive_soft_sum'];improved=bool(low>0 and gain>reserve)
    if not improved:point=anchor.copy();selected=first;low=0.
    return point,dict(status='RestoredAggregateDirection' if improved else 'NoAggregateImprovement',fraction=low,bracket_upper=high,
        anchor=first,target=last,selected=selected,probes=probes,proposed_segment_gain=gain,positive_soft_sum_gain=gain if improved else 0.,arithmetic_gain_reserve=reserve,
        hard_rows=hard_rows,total_rows=len(system.caps),hard_postcheck_tolerance=POSTCHECK,original_caps_scales_unchanged=True,
        original_selected=True,quality_approved=False,release_approved=False,
        scope='Bounded segment toward a proposed point with full affine hard checks and measured aggregate-loss improvement. '
        'Uses the existing 1e-8 affine postcheck only; actual original-bound decoded acceptance remains mandatory. '
        'No global or segment-loss optimum, mesh, continuous-time, engine or motion-quality certificate.')
