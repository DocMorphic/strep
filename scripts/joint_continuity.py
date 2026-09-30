"""Local joint-motion preference, separate from source-relative edit budgets."""
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from support_contact_v8 import rodrigues


def rotation_residual(source_local,edit_vectors,previous_local,weight):
    """Chordal SO(3) preference in physical local rotations, not optimizer coordinates."""
    return (weight*(source_local@rodrigues(edit_vectors)-previous_local)).reshape(-1)


def step_degrees(previous_local,current_local):
    previous,current=np.asarray(previous_local),np.asarray(current_local)
    if previous.shape!=current.shape or previous.ndim!=3 or previous.shape[1:]!=(3,3) or not np.isfinite(previous).all() or not np.isfinite(current).all():
        raise ValueError('Matching finite joint rotation matrices required')
    # Normalize serialized float drift before taking relative rotations.
    previous=Rotation.from_matrix(previous).as_matrix();current=Rotation.from_matrix(current).as_matrix()
    return np.rad2deg(np.linalg.norm(Rotation.from_matrix(previous.transpose(0,2,1)@current).as_rotvec(),axis=1))
