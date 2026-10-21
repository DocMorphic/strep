from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_window import CoupledPoseWindow
from test_surface_pose_working_floor import synthetic


def window(count=3):
    poses=[synthetic() for _ in range(count)]
    for p in poses:p.grow(np.zeros(p.model.size),batch_size=1)
    return CoupledPoseWindow(poses,root_step_m=.025,rotation_step_degrees=5.)


def test_every_coupled_derivative_including_both_sides_of_each_pair():
    p=window();x=np.linspace(-.03,.04,p.size);gaps,jac=p.pair(x)
    np.testing.assert_array_equal(gaps,p.values(x))
    for i in range(p.size):
        h=np.zeros_like(x);h[i]=1e-6
        np.testing.assert_allclose(jac[:,i],(p.values(x+h)-p.values(x-h))/2e-6,atol=1e-8,rtol=1e-8)


def test_middle_pose_move_rechecks_both_adjacent_pairs():
    p=window();x=np.zeros((3,6));x[:,1]=.02
    assert p.assess(x.reshape(-1))['numerical_window_pass']
    x[1,1]+=.03
    assessment=p.assess(x.reshape(-1))
    assert not assessment['numerical_window_pass']
    assert assessment['maximum_root_step_m']==pytest.approx(.03)
    # Two root step rows fail; the intervening rotation rows still pass.
    assert np.sum(p.values(x.reshape(-1))[-4:]<0)==2


def test_unselected_floor_failure_is_not_hidden_by_window_acceptance():
    p=window(2);x=np.zeros((2,6));x[:,0]=.1;x[:,1]=.02
    assert p.values(x.reshape(-1)).min()>=0
    assert p.values(x.reshape(-1),full=True).min()<0
    assert not p.assess(x.reshape(-1))['numerical_window_pass']


@pytest.mark.parametrize('count,root,angle',[(1,.025,5.),(9,.025,5.),(2,0.,5.),(2,.025,float('nan'))])
def test_invalid_window_request_rejected(count,root,angle):
    with pytest.raises(ValueError):CoupledPoseWindow([synthetic() for _ in range(count)],root_step_m=root,rotation_step_degrees=angle)


def test_bad_parameter_population_rejected():
    p=window()
    for x in [np.zeros(p.size-1),np.full(p.size,np.nan)]:
        with pytest.raises(ValueError):p.values(x)


def test_different_parameter_meanings_cannot_be_coupled():
    a,b=synthetic(),synthetic();b.model.rotations=[1]
    with pytest.raises(ValueError):CoupledPoseWindow([a,b],root_step_m=.025,rotation_step_degrees=5.)
