import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cylinder_approach import cylinder_clearance_shift
from object_geometry import Geometry


def shift(points,direction=(1,0,0)):
    return cylinder_clearance_shift(np.array(points),Geometry('cylinder',(1,2)),np.zeros(3),np.eye(3),direction,.1)


def test_radial_side_and_initially_safe_future_obstruction():
    assert shift([[.9,0,0]])==pytest.approx(.2)
    assert shift([[0,0,0],[-1.5,0,0]])==pytest.approx(2.6)


def test_rounded_cap_guidance_is_conservative_and_safe_caps_are_unchanged():
    assert shift([[.9,1.08,0]])==pytest.approx(.2)
    assert shift([[0,1.2,0]])==0
    assert shift([[.9,0,0],[0,1.2,0]])==pytest.approx(.2)


def test_cylinder_frame_rotation_and_translation_preserve_shift():
    points=np.array([[.9,0,0],[-1.5,0,0]]);rotation=Rotation.from_rotvec([.5,.3,-.2]).as_matrix();position=np.array([2.,-.3,.7])
    value=cylinder_clearance_shift(points@rotation.T+position,Geometry('cylinder',(1,2)),position,rotation,rotation@np.array([1.,0.,0.]),.1)
    assert value==pytest.approx(shift(points),abs=1e-12)


def test_nonradial_and_invalid_geometry_rejected():
    with pytest.raises(ValueError,match='radial'):shift([[0,0,0]],(0,1,0))
    with pytest.raises(ValueError):shift([[float('nan'),0,0]])
    with pytest.raises(ValueError):shift([])
    with pytest.raises(ValueError):cylinder_clearance_shift(np.zeros((1,3)),Geometry('sphere',(1,)),np.zeros(3),np.eye(3),[1,0,0],.1)
