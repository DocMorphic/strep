import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import solver_stage_count,solver_iteration_count,CONFIG


def test_stage_override_keeps_default_configuration_immutable():
    before=CONFIG.copy()
    assert solver_stage_count(None)==3
    assert solver_stage_count(6)==6
    assert CONFIG==before


@pytest.mark.parametrize('value',[0,13,True,1.5,'6'])
def test_invalid_stage_override_rejected(value):
    with pytest.raises(ValueError,match='Outer stage count'):solver_stage_count(value)


def test_inner_budget_override_does_not_change_default_configuration():
    before=CONFIG.copy()
    assert solver_iteration_count(None)==100
    for count in [1,100,300,1000]:assert solver_iteration_count(count)==count
    assert CONFIG==before


@pytest.mark.parametrize('value',[0,-1,1001,True,300.,'300',float('inf')])
def test_invalid_inner_budget_rejected(value):
    with pytest.raises(ValueError,match='Iterations must'):solver_iteration_count(value)
