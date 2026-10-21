from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_compact import soft_floor, CompactPoseConstraints
from test_surface_pose_model import fixture
from surface_pose_model import SurfacePoseModel


def problem():
    rig, world=fixture();rig.primitives.pop()
    model=SurfacePoseModel(rig,world,1,[1,2])
    return CompactPoseConstraints(model,angles_degrees=[45.,60.],root_horizontal_m=.2,root_vertical_m=.5,
        floor_depth_m=.005,contact_error_m=.02,floor_reserve_m=.001,contact_reserve_m=.001,
        contacts=[dict(vertex=0,target_m=[.2,.5,.1])],neighbors=[np.zeros(model.size)],floor_softmin_gap_m=.00025)


@pytest.mark.parametrize('heights', [[.2],[-.2,-.2,.3],[1.,1.,1.],[-1000.,1000.]])
def test_soft_floor_bias_is_conservative_and_complete(heights):
    lower,weights=soft_floor(heights,.00025)
    assert min(heights)-.00025-1e-12<=lower<=min(heights)+1e-12
    assert weights.sum()==pytest.approx(1.) and len(weights)==len(heights)
    if len(set(heights))==1:np.testing.assert_allclose(weights,np.full(len(heights),1/len(heights)))


def test_soft_floor_tied_height_derivatives():
    heights=np.array([.001,.001,.002]);value,weights=soft_floor(heights,.00025)
    for i in range(3):
        h=np.zeros(3);h[i]=1e-8
        derivative=(soft_floor(heights+h,.00025)[0]-soft_floor(heights-h,.00025)[0])/2e-8
        assert derivative==pytest.approx(weights[i],abs=1e-8)


def test_compact_values_and_complete_derivatives_match():
    p=problem();x=np.linspace(-.03,.04,p.model.size);gaps,jac=p.pair(x)
    np.testing.assert_allclose(p.values(x),gaps,atol=1e-12,rtol=0)
    for i in range(len(x)):
        h=np.zeros_like(x);h[i]=1e-6
        np.testing.assert_allclose(jac[:,i],(p.values(x+h)-p.values(x-h))/2e-6,atol=2e-6,rtol=1e-8)


def test_derivatives_are_only_computed_when_requested():
    p=problem();x=np.zeros(p.model.size)
    p.values(x);p.values(x.copy())
    assert p.evaluations==1 and p.derivative_evaluations==0
    p.pair(x);p.pair(x.copy());p.values(x)
    assert p.evaluations==2 and p.derivative_evaluations==1
    p.values(x+.001)
    assert p.evaluations==3 and p.derivative_evaluations==1


@pytest.mark.parametrize('heights,gap', [([], .001),([float('nan')],.001),([0.],0.),([0.],True)])
def test_bad_floor_request_rejected(heights,gap):
    with pytest.raises(ValueError):soft_floor(heights,gap)
