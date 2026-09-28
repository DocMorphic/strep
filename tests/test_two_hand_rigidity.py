import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from two_hand_rigidity import fit_two_grips,shortest_rotation


def test_known_rigid_pose_and_impossible_hand_separation():
    grips=np.array([[.2,.1,0],[-.2,.1,0]])
    r=Rotation.from_euler('xyz',[13,47,9],degrees=True).as_matrix();p=np.array([1.,2.,3.])
    palms=grips@r.T+p
    fitted_p,fitted_r,bound=fit_two_grips(grips,palms,r)
    np.testing.assert_allclose(fitted_p,p,atol=1e-12);np.testing.assert_allclose(fitted_r,r,atol=1e-12);assert bound<1e-12
    # Hands 80 cm apart cannot both reach grips 40 cm apart: each misses 20 cm
    # even after an unconstrained best rigid placement.
    palms=grips*2
    fitted_p,fitted_r,bound=fit_two_grips(grips,palms,np.eye(3))
    assert abs(bound-.2)<1e-12
    np.testing.assert_allclose(np.linalg.norm(grips@fitted_r.T+fitted_p-palms,axis=1),.2,atol=1e-12)


def test_axis_rotation_antipodal_and_degenerate_cases():
    r=shortest_rotation([1,0,0],[-1,0,0]);np.testing.assert_allclose(r@[1,0,0],[-1,0,0],atol=1e-12)
    assert abs(np.linalg.det(r)-1)<1e-12
    with pytest.raises(ValueError,match='Coincident'):shortest_rotation([0,0,0],[1,0,0])
    with pytest.raises(ValueError,match='proper'):fit_two_grips([[0,0,0],[1,0,0]],[[0,0,0],[1,0,0]],-np.eye(3))
