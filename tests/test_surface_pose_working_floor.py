from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_working_floor import WorkingFloorConstraints
from surface_pose_constraints import PoseConstraints
from test_surface_pose_constraints import problem as full_problem


def actual_problem():
    full=full_problem()
    return WorkingFloorConstraints(full.model, angles_degrees=[45.,60.],
        root_horizontal_m=.2,root_vertical_m=.5,floor_depth_m=.005,contact_error_m=.02,
        floor_reserve_m=.001,contact_reserve_m=.001,
        contacts=[dict(vertex=0,target_m=[.2,.5,.1])],neighbors=[np.zeros(full.model.size)])


def test_selected_rows_match_complete_constraints_and_derivatives():
    p=actual_problem();x=np.linspace(-.03,.04,p.model.size);p.grow(x,batch_size=1)
    all_values,all_jac=PoseConstraints.pair(p,x)
    gaps,jac=p.pair(x)
    np.testing.assert_allclose(p.full_values(x),all_values,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(gaps,all_values[p.row_indices()])
    np.testing.assert_array_equal(jac,all_jac[p.row_indices()])
    for i in range(len(x)):
        delta=np.zeros_like(x);delta[i]=1e-6
        np.testing.assert_allclose(jac[:,i],(p.values(x+delta)-p.values(x-delta))/2e-6,atol=2e-6,rtol=1e-8)


class MovingFloor:
    rotations=[0]
    size=6
    skin=SimpleNamespace(count=3)
    def evaluate(self,x,*,derivatives=True):
        points=np.zeros((3,3));points[:,1]=[.03+x[0],.04-x[0],-.01+x[1]]
        jac=np.zeros((3,3,6)) if derivatives else None
        if derivatives:jac[0,1,0]=1; jac[1,1,0]=-1; jac[2,1,1]=1
        return None,None,points,jac


def synthetic():
    return WorkingFloorConstraints(MovingFloor(),angles_degrees=[45.],root_horizontal_m=.2,
        root_vertical_m=.5,floor_depth_m=.005,contact_error_m=.02,floor_reserve_m=.001,
        contact_reserve_m=.001,contacts=[])


def test_unselected_vertex_cannot_pass_complete_acceptance_and_is_added():
    p=synthetic();x=np.zeros(6)
    assert p.grow(x,batch_size=1)==[2]
    x[:2]=[.1,.02]
    assert p.values(x).min()>=0
    assessment=p.assess(x)
    assert not assessment['numerical_constraints_pass']
    assert assessment['floor_depth_m']==pytest.approx(.06)
    assert assessment['minimum_fitting_gap']<0
    assert p.grow(x,batch_size=1)==[1]
    np.testing.assert_array_equal(p.floor_vertices,[1,2])
    assert p.values(x).min()<0 and p.grow(x,batch_size=1)==[]
    x[0]=-.1
    assert p.grow(x,batch_size=1)==[0]
    np.testing.assert_array_equal(p.floor_vertices,[0,1,2])


def test_full_scan_does_not_require_derivatives():
    p=synthetic();x=np.zeros(6);p.grow(x,batch_size=1);p.full_values(x);p.values(x)
    assert p.evaluations==1 and p.derivative_evaluations==0
    p.pair(x);p.pair(x)
    assert p.evaluations==2 and p.derivative_evaluations==1


def test_optimizer_requires_explicit_initial_working_set():
    with pytest.raises(ValueError,match='Initialize'):synthetic().values(np.zeros(6))


@pytest.mark.parametrize('batch',[0,-1,True,1.5,4097])
def test_invalid_batch_rejected(batch):
    with pytest.raises(ValueError):synthetic().grow(np.zeros(6),batch_size=batch)
