"""Explicit kinematic grasp/release, with no implicit physics or second-hand solve."""
import numpy as np


def attach_trajectory(object_positions,object_rotations,anchor_positions,anchor_rotations,grasp_frame,release_frame):
    p,r,a,q=[np.asarray(v,dtype=float) for v in [object_positions,object_rotations,anchor_positions,anchor_rotations]]
    frames=len(p)
    if p.shape!=(frames,3) or a.shape!=p.shape or r.shape!=(frames,3,3) or q.shape!=r.shape:raise ValueError('Attachment clock/shape mismatch')
    if any(not np.isfinite(v).all() for v in [p,r,a,q]):raise ValueError('Non-finite attachment pose')
    for rotation in [r,q]:
        if not np.allclose(rotation.transpose(0,2,1)@rotation,np.eye(3),atol=1e-5) or not np.allclose(np.linalg.det(rotation),1,atol=1e-5):raise ValueError('Attachment needs proper rigid rotations')
    if type(grasp_frame)!=int or type(release_frame)!=int or not 0<=grasp_frame<release_frame<=frames:raise ValueError('Invalid attachment interval')
    local_position=q[grasp_frame].T@(p[grasp_frame]-a[grasp_frame])
    local_rotation=q[grasp_frame].T@r[grasp_frame]
    attached_positions=a+np.einsum('fij,j->fi',q,local_position)
    attached_rotations=q@local_rotation
    result_p=p.copy();result_r=r.copy()
    result_p[grasp_frame:release_frame]=attached_positions[grasp_frame:release_frame]
    result_r[grasp_frame:release_frame]=attached_rotations[grasp_frame:release_frame]
    if release_frame<frames:
        # Align the authored free trajectory with the predicted release pose.
        # Preserves its relative movement, but makes no gravity/velocity claim.
        delta=attached_rotations[release_frame]@r[release_frame].T
        result_p[release_frame:]=(p[release_frame:]-p[release_frame])@delta.T+attached_positions[release_frame]
        result_r[release_frame:]=delta@r[release_frame:]
    return result_p,result_r,dict(grasp_frame=grasp_frame,release_frame=release_frame if release_frame<frames else None,
        anchor_local_translation_m=local_position.tolist(),anchor_local_rotation=local_rotation.tolist(),
        interval='Grasp inclusive, release exclusive; release pose sampled from the anchor at the release frame.',
        tail_policy='Rigidly aligned authored trajectory; no physics, velocity continuity or secondary-hand correction.')
