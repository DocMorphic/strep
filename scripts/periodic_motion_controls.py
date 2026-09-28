"""Periodic upper-body trajectories; root and legs remain unchanged."""
import numpy as np
from correct_loops import assemble
from combined_controls import combine
from motion_controls import edit_diagnostics, KEYS


def periodic_upper_source(source, skeleton):
    local=source['local_rot_mats'].astype(float).copy()
    names=skeleton.bone_order_names;parents=skeleton.joint_parents.numpy()
    selected=[]
    for i,name in enumerate(names):
        parent=i
        while parent>=0:
            if names[parent] in ('Spine1',):
                selected.append(i);break
            parent=int(parents[parent])
    # Symmetric circular filtering includes the cycle boundary. Project the
    # matrix mean to SO(3), rather than averaging Euler angles or duplicating
    # endpoints. Two passes keep the original timing and phase.
    values=source['global_rot_mats'][:,selected].astype(float).copy()
    for _ in range(2):
        average=.25*np.roll(values,1,axis=0)+.5*values+.25*np.roll(values,-1,axis=0)
        u,_,vt=np.linalg.svd(average)
        correction=np.broadcast_to(np.eye(3),average.shape).copy()
        correction[...,2,2]=np.linalg.det(u@vt)
        values=u@correction@vt
    desired=source['global_rot_mats'].astype(float).copy()
    desired[:,selected]=values
    for j in selected:
        local[:,j]=desired[:,parents[j]].transpose(0,2,1)@desired[:,j]
    return assemble(local,source['root_positions'],source['foot_contacts'],skeleton)


def combine_periodic(source,skeleton,arm,lean):
    if arm < 45:
        result,report=combine(source,skeleton,arm,lean)
        report['periodic_filter_applied']=False
        return result,report
    result,parameters=combine(periodic_upper_source(source,skeleton),skeleton,arm,lean)
    report=edit_diagnostics(source,result,skeleton,'arm',arm)
    report['target_errors_degrees']={k:abs(report['after'][KEYS[k]]-v) for k,v in [('arm',arm),('lean',lean)]}
    report['parameters']=parameters['parameters']
    report['periodic_filter_applied']=True
    return result,report


def cyclic_dynamics(data):
    """Whole-cycle diagnostics ensure an improvement is not just relocated."""
    relative=data['posed_joints']-data['root_positions'][:,None]
    velocity=(np.roll(relative,-1,axis=0)-relative)*30
    acceleration=(np.roll(velocity,-1,axis=0)-velocity)*30
    return {'joint_speed_max_m_s':float(np.linalg.norm(velocity,axis=-1).max()),
        'joint_acceleration_max_m_s2':float(np.linalg.norm(acceleration,axis=-1).max())}
