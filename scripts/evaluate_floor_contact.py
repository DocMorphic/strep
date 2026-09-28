"""Independent whole-surface and fixed-source-mask correction diagnostics."""
import numpy as np
from scipy.spatial.transform import Rotation
from floor_contact import Surface
from audit_body_ground import measure


def stats(values):
    return None if not len(values) else dict(mean=float(np.mean(values)),p95=float(np.percentile(values,95)),max=float(np.max(values)))


def compare(source, corrected, skin):
    surface=Surface(skin); regions={}
    for name,indices in surface.regions.items():
        before=np.array([surface.vertices(r,p,indices) for r,p in zip(source['global_rot_mats'],source['posed_joints'])])
        after=np.array([surface.vertices(r,p,indices) for r,p in zip(corrected['global_rot_mats'],corrected['posed_joints'])])
        heights=before[:,:,1].min(1); slow=np.linalg.norm(np.diff(before.mean(1)[:,[0,2]],axis=0),axis=1)*30<.35
        # Same raw vertices and frame intervals on both sides of comparison.
        mask=(heights[:-1]<.03)&(heights[1:]<.03)&slow
        before_speed=[];after_speed=[];before_gap=[];after_gap=[]
        for f in np.flatnonzero(mask):
            patch=before[f,:,1]<heights[f]+.01
            for vertices,speed,gap in [(before,before_speed,before_gap),(after,after_speed,after_gap)]:
                speed.append(float(np.linalg.norm((vertices[f+1,patch]-vertices[f,patch])[:,[0,2]],axis=1).mean()*30))
                gap.append(max(0,float(vertices[f,patch,1].min())))
        regions[name]=dict(before_depth_m=max(0,float(-before[:,:,1].min())),after_depth_m=max(0,float(-after[:,:,1].min())),
            fixed_mask_intervals=int(mask.sum()),before_slide_m_s=stats(before_speed),after_slide_m_s=stats(after_speed),
            before_gap_m=stats(before_gap),after_gap_m=stats(after_gap),
            scope='Low, slow raw surface is a contact candidate, not independently annotated support. Same raw patch/intervals measured after editing.')
    delta=corrected['posed_joints']-source['posed_joints']
    angles=np.degrees(Rotation.from_matrix((source['local_rot_mats'].transpose(0,1,3,2)@corrected['local_rot_mats']).reshape(-1,3,3)).magnitude())
    before=measure(source,skin);after=measure(corrected,skin)
    diagnostics=dict(max_joint_displacement_m=float(np.linalg.norm(delta,axis=-1).max()),
        joint_displacement_rms_m=float(np.sqrt(np.mean(delta**2))),max_local_rotation_change_degrees=float(angles.max()),
        added_joint_velocity_m_s=stats(np.linalg.norm(np.diff(delta,axis=0)*30,axis=-1).ravel()),
        added_joint_acceleration_m_s2=stats(np.linalg.norm(np.diff(delta,n=2,axis=0)*900,axis=-1).ravel()),
        root_unchanged=bool(np.array_equal(source['root_positions'],corrected['root_positions'])),
        predicted_contacts_unchanged=bool(np.array_equal(source['foot_contacts'],corrected['foot_contacts'])))
    flags=[]
    if after['mesh_max_depth_m']>.01:flags.append('residual_surface_penetration_above_1cm')
    if after['mesh_max_depth_m']>before['mesh_max_depth_m']+.001:flags.append('surface_depth_regression')
    if diagnostics['max_joint_displacement_m']>.22:flags.append('pose_change_above_22cm')
    if diagnostics['added_joint_velocity_m_s']['max']>1.5:flags.append('added_joint_speed_above_1_5m_s')
    for name,r in regions.items():
        if r['fixed_mask_intervals']<3:continue
        tolerance=.08 if name.endswith('Hand') else .02
        if r['after_slide_m_s']['p95']>r['before_slide_m_s']['p95']+tolerance:flags.append(name+'_surface_slide_regression')
        if r['after_gap_m']['p95']>r['before_gap_m']['p95']+.015:flags.append(name+'_support_gap_regression')
    return dict(before=before,after=after,regions=regions,distortion=diagnostics,flags=flags,
                screen_status='flagged' if flags else 'within_provisional_screen',human_approved=False,
                scope='Numerical screening only. No semantic/physical realism, independent contact labels, human rating or cleanup-time measurement.')
