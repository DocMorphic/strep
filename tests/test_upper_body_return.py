import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from upper_body_return import tapered_weight,rotation_neighbor_mean


def test_taper_preserves_endpoints_and_has_no_boundary_slope():
    assert tapered_weight(126,126,140,.25)==0 and tapered_weight(140,126,140,.25)==0
    assert tapered_weight(133,126,140,.25)==pytest.approx(.25)
    h=1e-5;assert tapered_weight(126+h,126,140,.25)/h<1e-5


def test_constant_rotation_rate_is_unchanged_across_wrap():
    a,b,c=Rotation.from_euler('z',[170,180,190],degrees=True).as_matrix()
    np.testing.assert_allclose(rotation_neighbor_mean(a,b,c,.25),b,atol=1e-14)


def test_neighbor_average_reduces_an_isolated_rotation_spike():
    eye=np.eye(3);spike=Rotation.from_euler('x',20,degrees=True).as_matrix()
    result=rotation_neighbor_mean(eye,spike,eye,.25)
    assert np.rad2deg(Rotation.from_matrix(result).magnitude())==pytest.approx(15)
    with pytest.raises(ValueError):tapered_weight(1,2,2,.25)
    with pytest.raises(ValueError):rotation_neighbor_mean(eye,eye,eye,np.nan)
