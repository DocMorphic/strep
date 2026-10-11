"""Necessary adjacent-key speed bounds for source-relative rotation edits.

This does not prescribe a human speed threshold, modify clips, or prove that an
admitted trajectory is feasible. Limits, when provided, belong to the author.
Validated matrices are explicitly projected onto SO(3) for this calculation.
"""
import numpy as np

MAX_MATRICES=1000000
ANGULAR_RESERVE_DEGREES=1e-7


def numeric(value,label):
    if isinstance(value,(list,tuple)):
        def check(items):
            for item in items:
                if isinstance(item,(list,tuple)):check(item)
                elif isinstance(item,(bool,np.bool_)):raise ValueError('Numeric '+label+' required')
        check(value)
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or not np.isfinite(raw).all():raise ValueError('Finite numeric '+label+' required')
    return raw.astype(float,copy=False)


def assess(rotations,times_s,edit_caps_degrees,*,speed_limits_degrees_per_second=None):
    r=numeric(rotations,'rotation matrices');times=numeric(times_s,'times')
    if r.ndim!=4 or r.shape[2:]!=(3,3) or not 2<=r.shape[0]<=20000 or not 1<=r.shape[1]<=512 or r.shape[0]*r.shape[1]>MAX_MATRICES:
        raise ValueError('Bounded complete [frames,joints,3,3] rotation population required')
    frames,joints=r.shape[:2]
    if times.shape!=(frames,) or times[0]<0 or np.any(np.diff(times)<=0):raise ValueError('Complete strictly increasing nonnegative times required')
    drift=float(np.max(abs(r.swapaxes(-1,-2)@r-np.eye(3))))
    determinant_error=float(np.max(abs(np.linalg.det(r)-1)))
    if max(drift,determinant_error)>1e-10:raise ValueError('Proper rigid rotation matrices required')
    caps=numeric(edit_caps_degrees,'edit caps')
    if caps.shape==(joints,):caps=np.broadcast_to(caps,(frames,joints))
    if caps.shape!=(frames,joints) or np.any(caps<0) or np.any(caps>180):raise ValueError('Explicit 0-180 degree cap for every frame/joint required')
    limits=None
    if speed_limits_degrees_per_second is not None:
        limits=numeric(speed_limits_degrees_per_second,'speed limits')
        if limits.shape!=(joints,) or np.any(limits<0):raise ValueError('Explicit nonnegative speed limit per joint required')
    # Projection is declared rather than silently treating drifted matrices as
    # exact rotations. Rejected reflections/scales never reach this operation.
    u,_,vt=np.linalg.svd(r);projected=u@vt
    if np.any(np.linalg.det(projected)<=0):raise ValueError('Proper rotation projection required')
    relative=projected[:-1].swapaxes(-1,-2)@projected[1:]
    skew=np.stack([relative[...,2,1]-relative[...,1,2],relative[...,0,2]-relative[...,2,0],relative[...,1,0]-relative[...,0,1]],axis=-1)/2
    cosine=np.clip((np.trace(relative,axis1=-2,axis2=-1)-1)/2,-1,1)
    angle=np.rad2deg(np.arctan2(np.linalg.norm(skew,axis=-1),cosine))
    dt=np.diff(times)[:,None]
    lower_angle=np.maximum(0.,angle-caps[:-1]-caps[1:]-ANGULAR_RESERVE_DEGREES)
    with np.errstate(over='raise',divide='raise',invalid='raise'):
        try:lower_rate=lower_angle/dt
        except FloatingPointError as error:raise ValueError('Finite representable rotation speed bounds required') from error
    excluded=np.zeros((frames-1,joints),bool) if limits is None else lower_rate>limits[None,:]
    peak=np.unravel_index(np.argmax(lower_rate),lower_rate.shape)
    witnesses=[]
    # Keep a compact maximum-deficit witness per joint; the returned complete
    # bounds retain every neighboring-key comparison for caller-side archives.
    if limits is not None:
        for joint in np.flatnonzero(excluded.any(axis=0)):
            interval=int(np.argmax(lower_rate[:,joint]-limits[joint]))
            witnesses.append(dict(joint=int(joint),interval=interval,times_s=times[interval:interval+2].tolist(),
                original_angle_degrees=float(angle[interval,joint]),edit_caps_degrees=caps[interval:interval+2,joint].tolist(),
                conservative_minimum_speed_degrees_per_second=float(lower_rate[interval,joint]),
                requested_maximum_speed_degrees_per_second=float(limits[joint])))
    return lower_rate,dict(schema='strep-temporal-rotation-bounds-v1',status='excluded' if excluded.any() else 'assessed',
        frames=frames,joints=joints,neighbor_comparisons=(frames-1)*joints,all_neighbors_assessed=True,
        author_speed_limits_provided=limits is not None,speed_limits_proven_incompatible=bool(excluded.any()),
        excluded_neighbor_comparisons=int(excluded.sum()),witnesses=witnesses,
        maximum_minimum_speed_degrees_per_second=float(lower_rate[peak]),maximum_interval=int(peak[0]),maximum_joint=int(peak[1]),
        reference_rotation_projection_max_element_change=float(np.max(abs(projected-r))),
        angular_reserve_degrees=ANGULAR_RESERVE_DEGREES,source_changed=False,
        anatomical_speed_threshold_calibrated=False,continuous_time_verified=False,quality_approved=False,release_approved=False,
        scope='Triangle-inequality necessary lower bounds on SO(3) geodesic speed between every adjacent original key, after explicitly recorded projection. Caps are local rotation norm balls relative to those projected references. Limits are authored, not calibrated physiology or project release thresholds. Non-exclusion is not global trajectory feasibility; it does not check translation, contacts, dynamics, interpolation or engine behavior.')
