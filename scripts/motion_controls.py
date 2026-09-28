"""Deterministic source-space upper-body edits with explicit measured targets."""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import brentq
from correct_loops import assemble,repeat_motion
from profile_metrics import descriptors

KEYS={'arm':'arm_swing_range_mean_degrees','lean':'torso_forward_lean_median_degrees'}


def world_x_edit(source,skeleton,joints,angles):
    local=source['local_rot_mats'].astype(float).copy()
    parents=skeleton.joint_parents.numpy()
    for joint,degrees in zip(joints,angles):
        index=skeleton.bone_order_names.index(joint)
        radians=np.deg2rad(np.broadcast_to(degrees,len(local)))
        rotations=Rotation.from_rotvec(np.column_stack([-radians,np.zeros((len(local),2))])).as_matrix()
        desired=rotations@source['global_rot_mats'][:,index]
        local[:,index]=np.swapaxes(source['global_rot_mats'][:,parents[index]],-1,-2)@desired
    return assemble(local,source['root_positions'],source['foot_contacts'],skeleton)


def edit(source,skeleton,control,target):
    if control not in KEYS or not np.isfinite(target):raise ValueError('Unsupported control or non-finite target')
    if control=='arm':
        if not 0<target<=90:raise ValueError('Arm span target outside experimental range')
        angles=[];names=skeleton.bone_order_names
        for side in ('Left','Right'):
            vector=source['posed_joints'][:,names.index(side+'Hand')]-source['posed_joints'][:,names.index(side+'Arm')]
            theta=np.degrees(np.unwrap(np.arctan2(vector[:,2],-vector[:,1])))
            # Match the study's four-cycle descriptor sampling, including
            # percentile interpolation, rather than changing the estimator later.
            sample=np.tile(theta,4)
            span=np.percentile(sample,95)-np.percentile(sample,5)
            if span<1:raise ValueError('Insufficient source arm variation; cannot amplify a static arm')
            angles.append((theta-np.median(theta))*(target/span-1))
        result=world_x_edit(source,skeleton,['LeftArm','RightArm'],angles)
        parameters={'world_x_offsets_degrees':[v.tolist() for v in angles]}
    else:
        if not -10<=target<=25:raise ValueError('Torso lean outside experimental range')
        def pose(offset):return world_x_edit(source,skeleton,['Spine1'],[offset])
        def residual(offset):return descriptors(pose(offset))[KEYS['lean']]-target
        offset=brentq(residual,-35,35,xtol=1e-5)
        result=pose(offset);parameters={'constant_spine_offset_degrees':offset}
    return result,parameters


def edit_diagnostics(source,edited,skeleton,control,target):
    from evaluate_grid import rotation_angles
    names=skeleton.bone_order_names
    lower=[i for i,n in enumerate(names) if n=='Hips' or any(n.startswith(s) for s in ('LeftLeg','RightLeg','LeftShin','RightShin','LeftFoot','RightFoot','LeftToe','RightToe'))]
    before=descriptors(repeat_motion(source,np.zeros(3),4))
    after=descriptors(repeat_motion(edited,np.zeros(3),4))
    other='lean' if control=='arm' else 'arm'
    return {'before':before,'after':after,'target_degrees':target,
        'target_error_degrees':abs(after[KEYS[control]]-target),
        'unrelated_angle_change_degrees':abs(after[KEYS[other]]-before[KEYS[other]]),
        'root_max_change_m':float(np.abs(edited['root_positions']-source['root_positions']).max()),
        'lower_body_max_change_m':float(np.linalg.norm(edited['posed_joints'][:,lower]-source['posed_joints'][:,lower],axis=-1).max()),
        'max_local_edit_degrees':float(rotation_angles(source['local_rot_mats'],edited['local_rot_mats']).max()),
        'contacts_unchanged':bool(np.array_equal(source['foot_contacts'],edited['foot_contacts']))}
