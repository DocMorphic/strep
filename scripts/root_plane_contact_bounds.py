"""Necessary per-pose vertical root intervals for floor and point contacts.

This retains every supplied vertex/contact. Nonempty intervals do not establish
a feasible clip: timing, interpolation, motion rates, other geometry and human
quality remain separate. Arithmetic is ordinary Float64, not interval-certified.
"""
import numpy as np


def translation_coefficients(rig,root):
    """Exact skin homogeneous response to world translation of a root subtree."""
    if type(root) is not int or root not in rig.joints:raise ValueError('Existing explicit skin root required')
    affected=np.zeros(len(rig.parents),bool)
    for node in range(len(rig.parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=rig.parents[ancestor]
        affected[node]=ancestor==root
    result=[]
    for primitive in rig.primitives:
        if primitive['joints'] is None:result.append(np.full(len(primitive['positions']),float(affected[primitive['node']])))
        else:
            points=np.c_[primitive['positions'],np.ones(len(primitive['positions']))]
            ids=primitive['joints'];homogeneous=np.einsum('nki,ni->nk',rig.inverse[ids][...,3,:],points)
            selected=affected[np.asarray(rig.joints)[ids]]
            result.append(np.sum(primitive['weights']*homogeneous*selected,axis=1))
    return np.concatenate(result),np.flatnonzero(affected)


def interval(heights,coefficients,*,floor_height_m,lower_m,upper_m,contacts=()):
    heights=np.asarray(heights,float);coefficients=np.asarray(coefficients,float)
    if heights.ndim!=1 or not len(heights) or coefficients.shape!=heights.shape or not np.isfinite(heights).all() or not np.isfinite(coefficients).all():
        raise ValueError('Complete finite vertex heights and vertical coefficients required')
    if any(type(v) not in (int,float) or not np.isfinite(v) for v in (floor_height_m,lower_m,upper_m)) or lower_m>upper_m:
        raise ValueError('Explicit finite ordered root interval and floor height required')
    lo=float(lower_m);hi=float(upper_m);lower_witness=dict(kind='root-budget',value_m=lo);upper_witness=dict(kind='root-budget',value_m=hi);conflicts=[]
    for i,(height,coefficient) in enumerate(zip(heights,coefficients)):
        if coefficient==0:
            if height<floor_height_m:conflicts.append(dict(kind='immovable-floor',vertex=i,height_m=float(height)))
            continue
        bound=float((floor_height_m-height)/coefficient)
        if coefficient>0 and bound>lo:lo=bound;lower_witness=dict(kind='floor',vertex=i,value_m=bound)
        if coefficient<0 and bound<hi:hi=bound;upper_witness=dict(kind='floor',vertex=i,value_m=bound)
    if not isinstance(contacts,(list,tuple)):raise ValueError('Explicit complete contact rows required')
    for row in contacts:
        if not isinstance(row,dict) or set(row)!={'id','error_m','coefficient','position_limit_m'}:raise ValueError('Explicit point-contact bound fields required')
        error=np.asarray(row['error_m'],float);a=row['coefficient'];radius=row['position_limit_m']
        if error.shape!=(3,) or not np.isfinite(error).all() or any(type(v) not in (int,float) or not np.isfinite(v) for v in (a,radius)) or radius<0:
            raise ValueError('Finite contact error, coefficient and nonnegative radius required')
        if a==0:
            if float(error@error)>radius**2:conflicts.append(dict(kind='immovable-contact',id=row['id']))
            continue
        remaining=float(radius**2-error[0]**2-error[2]**2)
        if remaining<0:conflicts.append(dict(kind='horizontal-contact',id=row['id']));continue
        span=np.sqrt(remaining);left,right=sorted((float((-error[1]-span)/a),float((-error[1]+span)/a)))
        if left>lo:lo=left;lower_witness=dict(kind='contact',id=row['id'],value_m=left)
        if right<hi:hi=right;upper_witness=dict(kind='contact',id=row['id'],value_m=right)
    if lo>hi:conflicts.append(dict(kind='empty-intersection',lower=lower_witness,upper=upper_witness))
    return dict(lower_m=lo,upper_m=hi,per_pose_interval_nonempty=not conflicts,
        lower_witness=lower_witness,upper_witness=upper_witness,conflicts=conflicts,vertices=len(heights),contacts=len(contacts),
        clip_feasibility_established=False,quality_approved=False,release_approved=False)
