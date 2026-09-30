"""Explicit constant vertical placement edit with a continuous primitive bound.

Preserves trajectory velocities, rotations and local material grips. This is an
authored scene edit, not collision response or automatic grasp adaptation.
"""
import copy
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scene_constraints import sample_object,pose
from object_geometry import scene_geometry
from release_geometry import floor_gaps


def floor_lower_bound(obj,frames,floor_height_m=0.,substeps=4):
    if not np.isfinite(floor_height_m) or type(substeps)!=int or not 1<=substeps<=120:raise ValueError('Invalid floor sampling controls')
    sample_object(obj,frames);geometry=scene_geometry(obj);keys=obj['keyframes'];bounds=[]
    for a,b in zip(keys,keys[1:]):
        p,r=pose(a);q,s=pose(b);angle=float((Rotation.from_matrix(s)*Rotation.from_matrix(r).inv()).magnitude())
        endpoints=floor_gaps(geometry,np.array([p,q]),np.array([r,s]),floor_height_m)
        if geometry.shape=='sphere' or angle<1e-12:
            lower=float(endpoints.min());margin=0.;samples=2
        else:
            intervals=(b['frame']-a['frame'])*substeps;u=np.linspace(0.,1.,intervals+1)
            positions=p[None]+u[:,None]*(q-p);rotations=Slerp([0.,1.],Rotation.from_matrix([r,s]))(u).as_matrix()
            # Every time is within half a sample interval of a sampled time.
            # Any rigid primitive point moves by at most radius * angular displacement.
            radius=geometry.bounding_radius()
            margin=(abs(float(q[1]-p[1]))+radius*angle)/(2*intervals)
            lower=float(floor_gaps(geometry,positions,rotations,floor_height_m).min()-margin);samples=len(u)
        bounds.append(dict(start_frame=a['frame'],end_frame=b['frame'],lower_bound_m=lower,between_sample_bound_m=margin,samples=samples))
    if not bounds:
        p,r=pose(keys[0]);bounds=[dict(start_frame=0,end_frame=frames-1,lower_bound_m=float(floor_gaps(geometry,p[None],r[None],floor_height_m)[0]),between_sample_bound_m=0.,samples=1)]
    return dict(lower_bound_m=min(b['lower_bound_m'] for b in bounds),segments=bounds,
        method='Exact endpoint minimum for spheres or constant orientation; conservative translation/rotation Lipschitz bound for SLERP primitive segments.')


def place_above_floor(obj,frames,*,clearance_m=.002,max_shift_m=.2,floor_height_m=0.):
    if any(type(x) not in (int,float) or not np.isfinite(x) for x in [clearance_m,max_shift_m]) or clearance_m<0 or max_shift_m<0:
        raise ValueError('Nonnegative finite placement controls required')
    before=floor_lower_bound(obj,frames,floor_height_m);shift=max(0.,clearance_m-before['lower_bound_m'])
    if shift>max_shift_m+1e-12:raise ValueError('Required object placement exceeds vertical edit budget')
    result=copy.deepcopy(obj)
    for key in result['keyframes']:key['translation_m'][1]+=shift
    after=floor_lower_bound(result,frames,floor_height_m)
    if after['lower_bound_m']<clearance_m-1e-10:raise ValueError('Object placement floor bound failed')
    return result,dict(vertical_shift_m=shift,clearance_m=clearance_m,max_shift_m=max_shift_m,floor_height_m=floor_height_m,before=before,after=after,
        scope='Constant authored object translation, preserving rotations, local grips, timing and velocity. Actor motion is unchanged and grip fitting must be reevaluated. No inter-object collision, attachment, physical reaction or human approval.')
