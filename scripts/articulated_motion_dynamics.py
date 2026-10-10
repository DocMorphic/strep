"""Explicit rigid-body-tree inverse Newton–Euler diagnostic for baked clips.

No body properties inferred from a skin, contact allocation or human capacities.
External wrenches are world quantities about each body's COM, supplied in full.
"""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from object_dynamics import diagnose as rigid_demand


def finite(value,shape,name):
    try:a=np.array(value,dtype=float,copy=True)
    except (TypeError,ValueError) as exc:raise ValueError('Invalid '+name) from exc
    if a.shape!=shape or not np.isfinite(a).all():raise ValueError('Complete finite '+name+' required')
    return a


def diagnose(profile,positions_m,rotations_xyzw,external_forces_world_N,external_torques_about_com_world_Nm,
             *,fps,gravity_world_m_s2,phases,anchor_tolerance_m,force_tolerance_N,torque_tolerance_Nm):
    """Ball-joint tree demand; floating-root residual is necessary, not sufficient."""
    if not isinstance(profile,list) or not 1<=len(profile)<=128:raise ValueError('Explicit 1–128 rigid bodies required')
    profile=copy.deepcopy(profile);phases=copy.deepcopy(phases)
    n=len(profile)
    try:count=len(positions_m)
    except TypeError as exc:raise ValueError('Complete pose track required') from exc
    if not 3<=count<=900:raise ValueError('Explicit 3–900 uniform samples required')
    if type(fps) not in (int,float) or not np.isfinite(fps) or not 1<=fps<=240 or (count-1)/fps>30:
        raise ValueError('Explicit uniform 1–240 Hz clock within thirty seconds required')
    for value,name in [(anchor_tolerance_m,'anchor'),(force_tolerance_N,'force'),(torque_tolerance_Nm,'torque')]:
        if type(value) not in (int,float) or not np.isfinite(value) or not 0<value<=.01:raise ValueError('Explicit bounded '+name+' numerical tolerance required')
    p=finite(positions_m,(count,n,3),'world COM poses');q=finite(rotations_xyzw,(count,n,4),'body rotations')
    force=finite(external_forces_world_N,(count,n,3),'external force population');torque=finite(external_torques_about_com_world_Nm,(count,n,3),'external COM torque population')
    try:gravity_world_m_s2=np.array(gravity_world_m_s2,dtype=float,copy=True)
    except (TypeError,ValueError) as exc:raise ValueError('Complete declared gravity required') from exc
    if np.max(abs(p))>1000 or max(float(abs(force).max()),float(abs(torque).max()))>1e8:raise ValueError('Bounded world tracks required')
    ids=[];parents=[];own=[];anchors=[]
    fields={'id','parent','mass_kg','inertia_body_about_com_kg_m2','joint_from_own_com_local_m','joint_from_parent_com_local_m','provenance'}
    for item in profile:
        if not isinstance(item,dict) or set(item)!=fields:raise ValueError('Complete explicit body profile required')
        name=item['id']
        if not isinstance(name,str) or not 1<=len(name)<=128 or name in ids:raise ValueError('Unique explicit body IDs required')
        ids.append(name)
        if not isinstance(item['provenance'],str) or not 1<=len(item['provenance'])<=2000:raise ValueError('Explicit body/anchor provenance required')
        parent=item['parent']
        if parent is not None and (not isinstance(parent,str) or not parent):raise ValueError('Explicit parent ID or null required')
        parents.append(parent);own.append(finite(item['joint_from_own_com_local_m'],(3,),'own joint anchor'))
        anchors.append(None if parent is None else finite(item['joint_from_parent_com_local_m'],(3,),'parent joint anchor'))
        if parent is None and item['joint_from_parent_com_local_m'] is not None:raise ValueError('Floating root has no parent anchor')
        if np.max(abs(own[-1]))>1000 or anchors[-1] is not None and np.max(abs(anchors[-1]))>1000:raise ValueError('Bounded local anchors required')
    roots=[i for i,parent in enumerate(parents) if parent is None]
    if len(roots)!=1 or any(parent is not None and parent not in ids for parent in parents):raise ValueError('One connected rooted body tree required')
    parent_ids=[None if parent is None else ids.index(parent) for parent in parents];order=[];visiting=set();done=set()
    def visit(i):
        if i in visiting:raise ValueError('Body tree cycle')
        if i in done:return
        visiting.add(i)
        if parent_ids[i] is not None:visit(parent_ids[i])
        visiting.remove(i);done.add(i);order.append(i)
    for i in range(n):visit(i)
    demands=[rigid_demand(p[:,i],q[:,i],fps=fps,mass_kg=item['mass_kg'],inertia_body_kg_m2=item['inertia_body_about_com_kg_m2'],
        gravity_m_s2=gravity_world_m_s2,phases=phases) for i,item in enumerate(profile)]
    r=Rotation.from_quat(q.reshape(-1,4)).as_matrix().reshape(count,n,3,3)
    joints=p+np.einsum('fbij,bj->fbi',r,np.array(own));errors=np.zeros((count,n))
    for i,parent in enumerate(parent_ids):
        if parent is not None:
            expected=p[:,parent]+np.einsum('fij,j->fi',r[:,parent],anchors[i]);errors[:,i]=np.linalg.norm(joints[:,i]-expected,axis=1)
    if float(errors.max())>anchor_tolerance_m:raise ValueError('Original rigid-body joint anchors disconnect; no pose correction is inferred')
    needed_force=np.stack([d['required_non_gravity_force_world_N'] for d in demands],axis=1)-force[1:-1]
    needed_torque=np.stack([d['required_torque_about_com_world_Nm'] for d in demands],axis=1)-torque[1:-1]
    if not np.isfinite(needed_force).all() or not np.isfinite(needed_torque).all() or max(float(abs(needed_force).max()),float(abs(needed_torque).max()))>1e8:
        raise ValueError('Nonfinite or unbounded body demand')
    internal_force=needed_force.copy();internal_torque=needed_torque+np.cross(p[1:-1]-joints[1:-1],needed_force)
    for i in reversed(order):
        parent=parent_ids[i]
        if parent is not None:
            internal_force[:,parent]+=internal_force[:,i]
            internal_torque[:,parent]+=internal_torque[:,i]+np.cross(joints[1:-1,i]-joints[1:-1,parent],internal_force[:,i])
    if (not np.isfinite(internal_force).all() or not np.isfinite(internal_torque).all()
            or max(float(abs(internal_force).max()),float(abs(internal_torque).max()))>1e8):
        raise ValueError('Nonfinite or unbounded complete joint demand')
    root=roots[0];global_force=needed_force.sum(axis=1)
    global_torque=(needed_torque+np.cross(p[1:-1]-joints[1:-1,root,None],needed_force)).sum(axis=1)
    # Independent aggregation identity inside the producer; audit still separate.
    if not np.allclose(internal_force[:,root],global_force,rtol=1e-12,atol=1e-9) or not np.allclose(internal_torque[:,root],global_torque,rtol=1e-12,atol=1e-9):
        raise ValueError('Recursive and direct world wrench balance differ')
    labels=np.empty(count,object)
    for phase in phases:labels[phase['start_frame']:phase['end_frame_exclusive']]=phase['support_assumption']
    valid=np.array(demands[0]['same_phase_stencil']);assessed=valid&(labels[1:-1]!='unknown')
    residual_pass=(np.max(abs(global_force),axis=1)<=force_tolerance_N)&(np.max(abs(global_torque),axis=1)<=torque_tolerance_Nm)
    samples=[]
    for i,f in enumerate(range(1,count-1)):
        samples.append(dict(frame=f,assessed=bool(assessed[i]),reason=None if assessed[i] else ('cross_phase_stencil' if not valid[i] else 'unknown_support'),
            floating_root_wrench_consistent=bool(residual_pass[i]) if assessed[i] else None))
    for i,item in enumerate(profile):
        item['inertia_body_about_com_kg_m2']=np.asarray(item['inertia_body_about_com_kg_m2'],float).tolist()
        item['joint_from_own_com_local_m']=own[i].tolist()
        item['joint_from_parent_com_local_m']=None if anchors[i] is None else anchors[i].tolist()
    return dict(schema='strep-articulated-motion-dynamics-v1',fps=fps,frame_count=count,body_ids=ids,profile=profile,root=ids[root],
        uniform_times_s=(np.arange(count)/fps).tolist(),world_com_positions_m=p.tolist(),body_rotations_xyzw=q.tolist(),
        external_forces_world_N=force.tolist(),external_torques_about_com_world_Nm=torque.tolist(),
        numerical_tolerances=dict(anchor_m=anchor_tolerance_m,force_N=force_tolerance_N,torque_Nm=torque_tolerance_Nm),
        world_joint_centers_m=joints.tolist(),joint_anchor_errors_m=errors.tolist(),sample_frames=list(range(1,count-1)),samples=samples,unestimated_endpoint_frames=[0,count-1],
        required_parent_on_body_force_world_N=internal_force.tolist(),required_parent_on_body_torque_about_joint_world_Nm=internal_torque.tolist(),
        residual_floating_root_force_world_N=global_force.tolist(),residual_floating_root_torque_world_Nm=global_torque.tolist(),
        body_demand=demands,assessed_samples=int(assessed.sum()),floating_root_wrench_consistent_samples=int(np.sum(assessed&residual_pass)),
        all_assessed_floating_root_wrenches_consistent=bool(assessed.any() and np.all(residual_pass[assessed])),
        capacities_evaluated=False,contact_forces_allocated=False,physical_approval=None,quality_approved=False,release_approved=False,training_admitted=False,
        scope='Original uniform COM/body rotation tracks, explicit positive-mass rigid bodies, connected ball-joint anchors and complete declared external COM wrenches. Recursive Newton–Euler internal joint demands and necessary floating-root balance. No glTF-to-body/anatomy inference, force allocation, capacity calibration, joint-axis restrictions, self-collision, impacts, continuous dynamics, engine or human-quality approval.')
