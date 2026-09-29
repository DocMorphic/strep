"""Source-bounded spline initialization from an explicitly matched grip pose.

Transfers correction parameters, not a contact-success claim. The original
scene, motion and edit limits remain the fitting reference.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scene_fit_initialization import recover_controls


def tapered_pose_parameters(reference,guide,editable,limits,body_count,basis,knots,start,end,fade):
    if type(start)!=int or type(end)!=int or not 0<=start<=end<len(basis) or type(fade)!=int or fade<1:
        raise ValueError('Valid contact interval and positive integer fade required')
    basis=np.asarray(basis);knots=np.asarray(knots)
    if knots.shape!=(basis.shape[1],) or not np.isfinite(knots).all():raise ValueError('Matching spline knots required')
    controls,proof=recover_controls(reference[None],guide[None],editable,limits,body_count,True,np.ones((1,1)))
    def smooth(x):
        u=np.clip(x,0,1);return u**3*(10-15*u+6*u*u)
    weights=smooth((knots-(start-fade))/fade)*smooth(((end+fade)-knots)/fade)
    values=np.einsum('fk,kjd->fjd',basis,weights[:,None,None]*controls)
    parameters=values.copy();parameters[:,body_count:]/=np.asarray(limits)[None,body_count:,None]
    vectors=np.asarray(limits)[None,:,None]*parameters/np.sqrt(1+(parameters**2).sum(-1,keepdims=True))
    rotations=Rotation.from_rotvec(vectors.reshape(-1,3)).as_matrix().reshape(*vectors.shape[:-1],3,3)
    return rotations,dict(guide_recovery=proof,knot_weights=weights.tolist(),
                          frame_weights=(basis@weights).tolist(),fade_frames=fade,
                          maximum_edit_degrees=float(np.rad2deg(np.linalg.norm(vectors,axis=-1).max())),
                          scope='Tapered correction parameters on original spline. Interpolation can overshoot weights; rotation-vector bounds still hold. Outside-interval poses are not asserted unchanged.')
