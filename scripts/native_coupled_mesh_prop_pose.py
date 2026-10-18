"""Original-relative rigid prop map following a supplied moving hand target.

This maps a caller's authorized character variables; it never grants body edit
permissions or validates a saved clip. Original prop caps remain fixed. A target
outside those caps is reported as rejected, never clipped or used as a new base.
"""
import numpy as np
from native_affine_key_pose import right_jacobian,skew
from native_mesh_prop_pose import GripPoseEdit

MAXIMUM_BYTES=64*1024**2


def real(value,shape,label):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.dtype.itemsize>8 or raw.shape!=shape or not np.isfinite(raw).all():raise ValueError('Complete finite numeric '+label+' required')
    return raw.astype(float,copy=True)


class CoupledGripPose:
    def __init__(self,original_edit):
        if type(original_edit) is not GripPoseEdit:raise ValueError('Original permission-bound prop edit required')
        original_edit.check_inputs();self.edit=original_edit

    def evaluate(self,controls,target_world,*,target_jacobian=None):
        """Columns: every supplied body column, then original prop xyz/clearance.

        Analytic SO(3) right Jacobian; supplied body Jacobians remain complete.
        Clearance is the same authored local direction and source-bound amount.
        """
        edit=self.edit;edit.check_inputs();value=edit._value(controls);base=edit.evaluate(value);rotation=base['rotation_matrix']
        target=real(target_world,(3,),'moving target');columns=0;target_matrix=None
        if target_jacobian is not None:
            raw=np.asarray(target_jacobian)
            if raw.ndim!=2 or raw.shape[0]!=3 or not 1<=raw.shape[1]<=764:raise ValueError('Complete 1-764-column target Jacobian required')
            columns=raw.shape[1];target_matrix=real(raw,(3,columns),'target Jacobian')
        local=edit._direction*(edit._clearance*value[3])-edit._point
        position=target+rotation@local
        # Preserve the original zero-pose bytes, including signed zero, rather
        # than reconstruct an unchanged pose through rounded pivot arithmetic.
        if not np.any(value) and target.tobytes()==edit._pivot.tobytes():position=edit._position.copy()
        dr=np.zeros((3,3,columns+4));dp=np.zeros((3,columns+4))
        if columns:dp[:,:columns]=target_matrix
        axes=right_jacobian(np.radians(edit._angle)*value[:3])*np.radians(edit._angle)
        for axis in range(3):
            dr[:,:,columns+axis]=rotation@skew(axes[:,axis]);dp[:,columns+axis]=dr[:,:,columns+axis]@local
        dp[:,-1]=rotation@edit._direction*edit._clearance
        distance=float(np.linalg.norm(position-edit._position));ball=1-float(value[:3]@value[:3]);degrees=base['report']['rotation_change_degrees']
        accepted=bool(ball>=0 and degrees<=edit._angle and distance<=edit._translation)
        report=dict(schema='strep-native-coupled-mesh-prop-pose-v1',prop=edit._name,key_index=edit._key,time_s=edit._item['keyframes'][edit._key]['time_s'],
            body_columns=columns,complete_columns=columns+4,controls=value.tolist(),native_rotation_ball_margin=ball,
            rotation_change_degrees=degrees,rotation_cap_degrees=edit._angle,translation_change_m=distance,translation_cap_m=edit._translation,
            authored_clearance_m=edit._clearance*float(value[3]),target_grip_error_m=float(np.linalg.norm(position+rotation@edit._point-target)),
            native_prop_pose_permissions_pass=accepted,source_relative=True,source_rebased=False,target_permissions_verified=False,
            character_permissions_verified=False,saved_motion_verified=False,sampled_pose_bounds_verified=False,quality_approved=False,release_approved=False,
            scope='Supplied moving world grip and complete body Jacobian plus original prop rotation/clearance controls. Original source pose/caps stay fixed. Caller must bind body permissions/provenance, raw/saved motion, full clocks/contact geometry and export/engine/human checks. No candidate selection or feasibility claim.')
        edit.check_inputs()
        return dict(position_m=position,rotation_matrix=rotation,rotation_xyzw=base['rotation_xyzw'],position_jacobian=dp,rotation_jacobian=dr,report=report)

    def points(self,controls,target_world,local_points,*,target_jacobian=None,maximum_jacobian_bytes=MAXIMUM_BYTES):
        raw=np.asarray(local_points)
        if raw.ndim!=2 or raw.shape[1]!=3 or not 1<=len(raw)<=250000:raise ValueError('Complete declared local points (1-250000,3) required')
        if type(maximum_jacobian_bytes) is not int or not 1<=maximum_jacobian_bytes<=MAXIMUM_BYTES:raise ValueError('Explicit complete point Jacobian budget required')
        if target_jacobian is not None and np.asarray(target_jacobian).ndim!=2:raise ValueError('Complete two-dimensional target Jacobian required')
        body_columns=0 if target_jacobian is None else np.asarray(target_jacobian).shape[-1]
        if type(body_columns) is not int or not 0<=body_columns<=764 or len(raw)*3*(body_columns+4)*8>maximum_jacobian_bytes:raise ValueError('Complete point Jacobian exceeds budget; no points or columns dropped')
        local=real(raw,raw.shape,'local points');pose=self.evaluate(controls,target_world,target_jacobian=target_jacobian)
        values=local@pose['rotation_matrix'].T+pose['position_m']
        jac=np.einsum('ijc,vj->vic',pose['rotation_jacobian'],local)+pose['position_jacobian'][None,:,:]
        if not np.isfinite(values).all() or not np.isfinite(jac).all():raise ValueError('Nonfinite coupled point map')
        return values,jac,pose
