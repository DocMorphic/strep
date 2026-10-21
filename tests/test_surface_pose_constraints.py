from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_surface_pose_model import fixture
from surface_pose_model import SurfacePoseModel
from surface_pose_constraints import PoseConstraints


def problem(**overrides):
    rig, world = fixture(); model = SurfacePoseModel(rig, world, 1, [1, 2])
    options = dict(angles_degrees=[45., 60.], root_horizontal_m=.2, root_vertical_m=.5,
        floor_depth_m=.005, contact_error_m=.02, floor_reserve_m=.001, contact_reserve_m=.001,
        contacts=[dict(vertex=0, target_m=[.2, .5, .1])], neighbors=[np.zeros(model.size), np.full(model.size,.01)],
        root_step_m=.025, rotation_step_degrees=5.)
    options.update(overrides)
    return PoseConstraints(model, **options)


@pytest.mark.parametrize('contacts', [[], [dict(vertex=0, target_m=[.2,.5,.1])]])
def test_all_constraint_rows_have_correct_derivatives(contacts):
    p=problem(contacts=contacts); x=np.linspace(-.03,.04,p.model.size)
    gaps,jac=p.pair(x)
    for i in range(len(x)):
        h=np.zeros_like(x);h[i]=1e-6
        difference=(p.pair(x+h)[0]-p.pair(x-h)[0])/2e-6
        np.testing.assert_allclose(jac[:,i],difference,atol=2e-6,rtol=1e-8)
    assert len(gaps)==p.model.skin.count+len(contacts)+len(p.angles)+1+2*(len(p.angles)+1)


def test_neighbor_root_and_rotation_steps_are_enforced_independently():
    p=problem(contacts=[],neighbors=[np.zeros(9)])
    x=np.zeros(9);x[1]=.03
    result=p.assess(x)
    assert result['maximum_neighbor_root_step_m']==.03 and not result['numerical_constraints_pass']
    x[1]=0;x[3]=np.deg2rad(6)
    result=p.assess(x)
    assert result['maximum_neighbor_rotation_parameter_step_degrees']==pytest.approx(6)
    assert not result['numerical_constraints_pass']


@pytest.mark.parametrize('override', [dict(floor_reserve_m=.005),dict(contact_reserve_m=.02),
    dict(angles_degrees=[45.]),dict(root_step_m=0.),dict(rotation_step_degrees=float('nan')),
    dict(contacts=[dict(vertex=0,target_m=[0,0,0]),dict(vertex=0,target_m=[1,0,0])]),
    dict(neighbors=[np.zeros(2)])])
def test_invalid_constraints_rejected(override):
    with pytest.raises(ValueError):problem(**override)
