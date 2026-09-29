import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from spatial_release import arm_path


def test_path_uses_short_arc_across_rotation_wrap_and_exact_endpoints():
    first=Rotation.from_euler('z',[170],degrees=True).as_matrix()
    last=Rotation.from_euler('z',[-170],degrees=True).as_matrix()
    np.testing.assert_allclose(arm_path(first,last,0),first,atol=1e-14)
    np.testing.assert_allclose(arm_path(first,last,1),last,atol=1e-14)
    midpoint=Rotation.from_matrix(arm_path(first,last,.5))
    assert np.rad2deg((Rotation.from_matrix(first).inv()*midpoint).magnitude())[0]==pytest.approx(10)


@pytest.mark.parametrize('fraction',[-.1,1.1,np.nan,np.inf])
def test_path_rejects_invalid_fraction(fraction):
    with pytest.raises(ValueError): arm_path(np.eye(3)[None],np.eye(3)[None],fraction)
