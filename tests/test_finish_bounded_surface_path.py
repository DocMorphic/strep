import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from finish_bounded_surface_path import compose_path


def test_composition_preserves_translations_and_nonedited_joints():
    # Distinct frame/node counts and non-topological storage catch axis and
    # hierarchy assumptions. Child 0 follows root 2; helper 1 remains fixed.
    local=np.tile(np.eye(4),(5,3,1,1));parents=np.array([2,-1,-1])
    local[:,0,0,3]=1.;local[:,2,1,3]=np.arange(5)*.2
    local[:,2,:3,:3]=Rotation.from_euler('x',20,degrees=True).as_matrix()
    x=np.zeros((5,3));x[2,2]=np.pi/2
    changed,world=compose_path(local,parents,[2],x)
    np.testing.assert_array_equal(changed[:,:,:3,3],local[:,:,:3,3])
    np.testing.assert_array_equal(changed[:,:2],local[:,:2])
    expected=local[2,2].copy()
    expected[:3,:3]=expected[:3,:3]@Rotation.from_euler('z',90,degrees=True).as_matrix()
    np.testing.assert_allclose(world[2,0],expected@local[2,0],atol=1e-14)
    np.testing.assert_array_equal(changed[[0,1,3,4]],local[[0,1,3,4]])
    assert world.shape==(5,3,4,4)


def test_composition_rejects_missing_frame_or_nonfinite_controls():
    local=np.tile(np.eye(4),(5,3,1,1));parents=np.array([2,-1,-1])
    with pytest.raises(ValueError):compose_path(local,parents,[2],np.zeros((4,3)))
    with pytest.raises(ValueError):compose_path(local,parents,[2,2],np.zeros((5,6)))
    with pytest.raises(ValueError):compose_path(local,parents,[2],np.full((5,3),np.nan))
