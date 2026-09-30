import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from joint_continuity import rotation_residual,step_degrees


def test_physical_rotation_preference_matches_independent_rotation():
    source=Rotation.from_rotvec([[.1,.2,-.3],[-.2,.05,.1]]).as_matrix();previous=Rotation.from_rotvec([[.2,.1,.4],[.1,.03,.2]]).as_matrix()
    theta=np.array([[.15,-.2,.01],[.02,.1,-.04]]);t=lambda v:torch.tensor(v,dtype=torch.float64)
    expected=2.*(source@Rotation.from_rotvec(theta).as_matrix()-previous)
    np.testing.assert_allclose(rotation_residual(t(source),t(theta),t(previous),2.).numpy(),expected.ravel(),atol=1e-14)
    assert torch.autograd.gradcheck(lambda x:rotation_residual(t(source),x,t(previous),2.),(t(theta).requires_grad_(),),atol=1e-6)


def test_step_uses_local_physical_rotations_not_edit_coordinate_distance():
    previous=Rotation.from_rotvec([[0,0,np.deg2rad(179)],[0,0,0]]).as_matrix()
    current=Rotation.from_rotvec([[0,0,np.deg2rad(-179)],[np.deg2rad(3),0,0]]).as_matrix()
    np.testing.assert_allclose(step_degrees(previous,current),[2,3],atol=1e-12)
    frame=Rotation.from_rotvec([.3,.2,.1]).as_matrix()
    np.testing.assert_allclose(step_degrees(frame@previous,frame@current),[2,3],atol=1e-12)


def test_step_rejects_mismatched_or_nonfinite_rotations():
    with pytest.raises(ValueError):step_degrees(np.eye(3),np.eye(3))
    with pytest.raises(ValueError):step_degrees(np.eye(3)[None],np.full((1,3,3),np.nan))
