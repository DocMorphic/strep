"""Bounded shared meeting-plane orientation and complete rotation derivatives.

This is an explicit authoring variable, not a relaxation of pair contact or
collision acceptance. The original frame remains the zero-control reference.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_affine_key_pose import right_jacobian,skew


class MeetingOrientation:
    def __init__(self,normal,tangent,maximum_degrees):
        normal=np.asarray(normal,float);tangent=np.asarray(tangent,float)
        if (normal.shape!=(3,) or tangent.shape!=(3,)
                or not np.isfinite(normal).all() or not np.isfinite(tangent).all()
                or abs(np.linalg.norm(normal)-1)>1e-8 or abs(np.linalg.norm(tangent)-1)>1e-8
                or abs(normal@tangent)>1e-8 or type(maximum_degrees) not in (int,float)
                or not np.isfinite(maximum_degrees) or not 0<maximum_degrees<=30):
            raise ValueError('Finite orthonormal source frame and explicit 0-30 degree cap required')
        self.normal=normal.copy();self.tangent=tangent.copy();self.cap=np.radians(maximum_degrees)

    def evaluate(self,value):
        value=np.asarray(value,float)
        if value.shape!=(3,) or not np.isfinite(value).all():
            raise ValueError('Three complete finite meeting orientation controls required')
        vector=value*self.cap;rotation=Rotation.from_rotvec(vector).as_matrix()
        jr=right_jacobian(vector)*self.cap
        normal=rotation@self.normal if np.any(value) else self.normal.copy()
        tangent=rotation@self.tangent if np.any(value) else self.tangent.copy()
        return dict(normal_world=normal,tangent_world=tangent,
            normal_jacobian=-rotation@skew(self.normal)@jr,
            tangent_jacobian=-rotation@skew(self.tangent)@jr,
            edit_margin=float(1-value@value),edit_margin_jacobian=-2*value)
