import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_pose_witness_bounded import inverse_rotation_bound,physical_parameters


def test_inverse_preserves_interior_seed_and_bound_holds_for_large_controls():
    limits=np.array([.2,.7]);theta=np.array([[.1,.03,-.02],[.2,.1,-.3]])
    inverse=inverse_rotation_bound(theta,limits)
    actual=physical_parameters(torch.tensor(np.r_[inverse.ravel(),.04]),limits).numpy()
    np.testing.assert_allclose(actual[:-1].reshape(-1,3),theta,atol=1e-14)
    assert actual[-1]==.04
    huge=physical_parameters(torch.tensor(np.r_[np.full(6,1e6),.01]),limits).numpy()
    assert np.all(np.linalg.norm(huge[:-1].reshape(-1,3),axis=1)<=limits)
    with pytest.raises(ValueError):inverse_rotation_bound(np.array([[.2,.2,0]]),np.array([.2]))
