"""Sampled rigid-object inverse-dynamics diagnostic, not a contact-force solver.

World positions must be centers of mass. Rotations map body axes into world.
No smoothing, inferred contacts, character inertias or automatic quality approval.
"""
import numpy as np
from scipy.spatial.transform import Rotation


def finite_array(value,shape,label):
    try:result=np.asarray(value,dtype=float)
    except (TypeError,ValueError) as exc:raise ValueError('Invalid '+label) from exc
    if result.shape!=shape or not np.isfinite(result).all():raise ValueError('Invalid '+label)
    return result


def uniform_box_inertia(mass_kg,size_m):
    if type(mass_kg) not in (int,float) or not np.isfinite(mass_kg) or mass_kg<=0:
        raise ValueError('Mass must be a positive finite value in kg')
    size=finite_array(size_m,(3,),'box size')
    if np.any(size<=0):raise ValueError('Box dimensions must be positive metres')
    return np.diag(mass_kg*(np.sum(size**2)-size**2)/12)


def diagnose(positions_m,rotations_xyzw,*,fps,mass_kg,inertia_body_kg_m2,
             gravity_m_s2,phases):
    if type(fps) not in (int,float) or not np.isfinite(fps) or fps<=0:raise ValueError('Invalid fps')
    if type(mass_kg) not in (int,float) or not np.isfinite(mass_kg) or mass_kg<=0:raise ValueError('Invalid mass')
    try:frames=len(positions_m)
    except TypeError as exc:raise ValueError('Invalid positions') from exc
    if frames<3:raise ValueError('Need at least three samples')
    p=finite_array(positions_m,(frames,3),'positions')
    q=finite_array(rotations_xyzw,(frames,4),'quaternions')
    if not np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-6,rtol=0):raise ValueError('Quaternions must be unit length')
    inertia=finite_array(inertia_body_kg_m2,(3,3),'inertia')
    if not np.allclose(inertia,inertia.T,atol=1e-12,rtol=0):raise ValueError('Inertia must be symmetric')
    eigen=np.linalg.eigvalsh(inertia)
    if np.min(eigen)<=0 or eigen[-1]>eigen[0]+eigen[1]+1e-12:raise ValueError('Unphysical inertia')
    try:gravity=np.asarray(gravity_m_s2,dtype=float)
    except (TypeError,ValueError) as exc:raise ValueError('Invalid gravity') from exc
    if gravity.shape not in ((3,),(frames,3)) or not np.isfinite(gravity).all():raise ValueError('Invalid gravity')
    if not isinstance(phases,list) or not phases:raise ValueError('Explicit phases required')
    labels=np.full(frames,-1,dtype=int);ids=set()
    for i,phase in enumerate(phases):
        if not isinstance(phase,dict) or set(phase)!={'id','start_frame','end_frame_exclusive','support_assumption'}:
            raise ValueError('Invalid phase fields')
        a,b=phase['start_frame'],phase['end_frame_exclusive']
        if type(a)!=int or type(b)!=int or not 0<=a<b<=frames:raise ValueError('Invalid phase interval')
        if not isinstance(phase['id'],str) or not phase['id'] or phase['id'] in ids:raise ValueError('Invalid phase id')
        if phase['support_assumption'] not in ('unknown','supported','free_flight'):raise ValueError('Invalid support assumption')
        if np.any(labels[a:b]!=-1):raise ValueError('Overlapping phases')
        labels[a:b]=i;ids.add(phase['id'])
    if np.any(labels<0):raise ValueError('Phases must cover every sample')
    r=Rotation.from_quat(q).as_matrix();dt=1/fps
    delta=Rotation.from_matrix(r[1:]@r[:-1].transpose(0,2,1)).as_rotvec()
    if np.any(np.linalg.norm(delta,axis=1)>=np.pi-1e-6):raise ValueError('Ambiguous near-pi angular step')
    # Interval angular velocities are expressed in the common inertial frame.
    interval_w=delta/dt
    w=(interval_w[1:]+interval_w[:-1])/2
    alpha=(interval_w[1:]-interval_w[:-1])/dt
    acceleration=(p[2:]-2*p[1:-1]+p[:-2])/dt**2
    force=mass_kg*(acceleration-(gravity if gravity.shape==(3,) else gravity[1:-1]))
    iw=r[1:-1]@inertia@r[1:-1].transpose(0,2,1)
    torque=np.einsum('fij,fj->fi',iw,alpha)+np.cross(w,np.einsum('fij,fj->fi',iw,w))
    valid=(labels[:-2]==labels[1:-1])&(labels[1:-1]==labels[2:])
    sample_frames=np.arange(1,frames-1)
    force_norm=np.linalg.norm(force,axis=1);torque_norm=np.linalg.norm(torque,axis=1)
    def stats(values,mask):
        indices=np.flatnonzero(mask)
        if len(indices)==0:return None
        peak=indices[np.argmax(values[indices])]
        return dict(max=float(values[peak]),p95=float(np.percentile(values[indices],95)),
                    mean=float(values[indices].mean()),peak_frame=int(sample_frames[peak]))
    summaries=[]
    for i,phase in enumerate(phases):
        mask=valid&(labels[1:-1]==i)
        summaries.append(dict(**phase,interior_samples=int(mask.sum()),
            required_non_gravity_force_N=stats(force_norm,mask),
            required_torque_about_com_Nm=stats(torque_norm,mask),
            free_flight_residual_applicable=phase['support_assumption']=='free_flight',
            interpretation='Required net wrench; does not prove feasible hand, ground or friction forces.'))
    return dict(fps=fps,frame_count=frames,mass_kg=mass_kg,
        inertia_body_kg_m2=inertia.tolist(),gravity_m_s2=gravity.tolist(),phases=summaries,
        sample_frames=sample_frames.tolist(),same_phase_stencil=valid.tolist(),
        excluded_boundary_frames=sample_frames[~valid].tolist(),
        acceleration_world_m_s2=acceleration.tolist(),angular_velocity_world_rad_s=w.tolist(),
        angular_acceleration_world_rad_s2=alpha.tolist(),required_non_gravity_force_world_N=force.tolist(),
        required_torque_about_com_world_Nm=torque.tolist(),physical_approval=None,
        method='Three-point central translation differences; adjacent SO(3) interval logs for world angular velocity/acceleration. No smoothing. Endpoints have no estimate. Phase-boundary samples retained but excluded from phase aggregates.',
        limitations='Required net wrench under supplied COM/mass/inertia/gravity assumptions; no force allocation, friction, grip strength, human balance, collisions or physical certification. Rotation faster than the sample clock can alias; impacts need impulse/contact treatment.')
