import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from point_rate_reachability import endpoint_bound


def test_finite_travel_bound_detects_impossible_pin_without_relaxing_target():
    result=endpoint_bound([0.,0.,0.],[.047,0.,0.],.005,.067,1/3)
    assert result['endpoint_distance_incompatible']
    assert result['travel_deficit_m']>.019
    assert result['tolerance_m']==.005


def test_tolerance_ball_and_numerical_boundary_budget_are_separate():
    exact=endpoint_bound([0.,0.,0.],[.015,0.,0.],.005,.01,1.,0.)
    assert exact['travel_deficit_m']==pytest.approx(0,abs=1e-15)
    assert not exact['endpoint_distance_incompatible']
    inside=endpoint_bound([0.,0.,0.],[.004,0.,0.],.005,0.,1.)
    assert inside['minimum_travel_m']==0 and not inside['endpoint_distance_incompatible']


@pytest.mark.parametrize('speed,duration',[(-1.,1.),(float('nan'),1.),(.1,0.),(.1,True)])
def test_invalid_constraints_rejected(speed,duration):
    with pytest.raises(ValueError):endpoint_bound([0,0,0],[1,0,0],.005,speed,duration)
