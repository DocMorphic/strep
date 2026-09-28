import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_floor_placement import place_above_floor,floor_lower_bound
from object_geometry import Geometry
from scene_constraints import sample_object
from release_geometry import floor_gaps


def test_sphere_constant_placement_preserves_velocity_and_grips():
    obj=dict(geometry=Geometry('sphere',(.25,)).record(),keyframes=[dict(frame=f,translation_m=[f*.1,y,0],rotation_xyzw=[0,0,0,1]) for f,y in [(0,.2),(10,1.),(20,.3)]])
    original=copy.deepcopy(obj);candidate,recipe=place_above_floor(obj,21)
    assert obj==original and recipe['vertical_shift_m']==pytest.approx(.052)
    p,r=sample_object(obj,21);q,s=sample_object(candidate,21)
    np.testing.assert_allclose(q-p,np.tile([0,.052,0],(21,1)),atol=1e-15)
    np.testing.assert_allclose(np.diff(q,axis=0),np.diff(p,axis=0),atol=1e-15);np.testing.assert_array_equal(s,r)
    with pytest.raises(ValueError,match='budget'):place_above_floor(obj,21,max_shift_m=.04)


def test_rotating_box_bound_covers_interior_sweep_not_just_keys():
    obj=dict(shape='box',size_m=[2,.2,.2],keyframes=[dict(frame=f,translation_m=[0,.3,0],rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()) for f,angle in [(0,0),(2,170)]])
    bound=floor_lower_bound(obj,3)
    assert bound['lower_bound_m']<-.69
    candidate,recipe=place_above_floor(obj,3,max_shift_m=1.)
    dense=copy.deepcopy(candidate);dense['keyframes'][-1]['frame']=2000
    p,r=sample_object(dense,2001);gaps=floor_gaps(Geometry('box',(2,.2,.2)),p,r)
    assert gaps.min()>=.002 and recipe['after']['lower_bound_m']==pytest.approx(.002)


def test_placement_rejects_negative_clearance():
    with pytest.raises(ValueError):place_above_floor({},3,clearance_m=-.01)
