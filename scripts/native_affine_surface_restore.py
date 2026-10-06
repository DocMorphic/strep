"""Bounded surface improvement along a feasible affine segment.

This returns local guidance, never decoded motion or geometry approval. Callers
must provide the complete original norm/surface populations, depth witnesses
and the intersection of their authored/trust/certificate delta boxes.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows


def restore(native,native_jac,gaps,surface_jac,depth_ids,anchor,target,lower,upper,
            *,depth_limit,depth_bound,clearance=0.,scale=.005,iterations=32):
    anchor,target,lower,upper=[np.asarray(a,float).copy() for a in (anchor,target,lower,upper)]
    if (anchor.ndim!=1 or not len(anchor) or any(a.shape!=anchor.shape or not np.isfinite(a).all() for a in (target,lower,upper))
            or not np.isfinite(anchor).all() or np.any(lower>upper)
            or any(np.any(a<lower) or np.any(a>upper) for a in (anchor,target))):
        raise ValueError('Complete finite endpoints inside the original delta box required')
    if (not isinstance(native,NormRows) or any(not np.isfinite(a).all() for a in (native.vectors,native.caps,native.scales))
            or np.any(native.scales<=0)):
        raise ValueError('Original finite native norm rows required')
    gaps=np.asarray(gaps,float);nj=sparse.csr_matrix(native_jac,copy=True);sj=sparse.csr_matrix(surface_jac,copy=True)
    if (gaps.ndim!=1 or not len(gaps) or not np.isfinite(gaps).all()
            or nj.shape!=(native.vectors.size,len(anchor)) or sj.shape!=(len(gaps),len(anchor))
            or not np.isfinite(nj.data).all() or not np.isfinite(sj.data).all()):
        raise ValueError('Complete matching finite affine populations required')
    ids=np.asarray(depth_ids)
    if (ids.ndim!=1 or (len(ids) and (ids.dtype.kind not in 'iu' or np.any(ids<0) or np.any(ids>=len(gaps)) or len(np.unique(ids))!=len(ids)))):
        raise ValueError('Distinct original depth witness indices required')
    ids=ids.astype(int)
    if (any(type(a) not in (int,float) or not np.isfinite(a) or a<0 for a in (depth_limit,depth_bound,clearance))
            or type(scale) not in (int,float) or not np.isfinite(scale) or scale<=0
            or type(iterations) is not int or not 1<=iterations<=64):
        raise ValueError('Finite original bounds, positive scale and bounded iteration count required')
    probes=[]
    def check(point,fraction):
        with np.errstate(over='ignore',invalid='ignore'):
            residual=native.residual(nj,point);full=(clearance-gaps-sj@point)/scale
            depth=(-gaps[ids]-sj[ids]@point-depth_limit)/scale
        finite=bool(np.isfinite(residual).all() and np.isfinite(full).all() and np.isfinite(depth).all())
        row=dict(fraction=float(fraction),finite=finite,passed=False)
        if finite:
            row.update(native_excess=float(residual.max()),depth_deficit=float(max(0.,depth.max())) if len(ids) else 0.,
                       surface_excess=float(max(0.,full.max())))
            row['passed']=bool(np.all(point>=lower) and np.all(point<=upper)
                               and row['native_excess']<=0. and row['depth_deficit']<=depth_bound)
        probes.append(row);return row
    first=check(anchor,0.)
    if not first['passed']:raise ValueError('Strictly native/depth feasible original anchor required')
    last=check(target,1.);low,high=0.,1.;selected=anchor.copy();selected_row=first
    if last['passed']:low=1.;selected=target.copy();selected_row=last
    else:
        # Along this segment every norm sublevel and affine depth halfspace is
        # convex; their intersection containing zero is an interval. Measure
        # the complete populations at every probe, without relying on status.
        for _ in range(iterations):
            fraction=(low+high)/2.;point=(1.-fraction)*anchor+fraction*target;row=check(point,fraction)
            if row['passed']:low=fraction;selected=point;selected_row=row
            else:high=fraction
    improved=selected_row['surface_excess']<first['surface_excess']
    if not improved:low=0.;selected=anchor.copy();selected_row=first
    return selected,dict(status='RestoredSurfaceDirection' if improved else 'NoSurfaceImprovement',
        fraction=low,bracket_upper=high,probes=probes,selected=selected_row,anchor=first,target=last,
        complete_native_norm_rows=len(native.caps),complete_surface_rows=len(gaps),depth_witness_rows=len(ids),
        original_native_caps_scales_unchanged=True,native_check_tolerance=0.,depth_bound=depth_bound,
        quality_approved=False,release_approved=False,
        scope='Bounded segment search with strict complete affine native checks and original depth priority. '
              'No global optimality, decoded native, nonlinear geometry, engine or motion-quality certificate.')
