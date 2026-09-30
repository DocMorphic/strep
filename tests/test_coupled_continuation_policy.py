import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_continuation_policy import acceptance


def test_local_steps_do_not_reset_the_total_original_edit_budget():
    assert acceptance(.02,.019,0,[0,0],[4.9,5.00005],[True,True])['accepted']
    result=acceptance(.02,.019,0,[0,0],[5.1,4.9],[True,True])
    assert not result['accepted'] and 'original_total_edit' in result['reasons']


def test_improved_worst_distance_cannot_hide_a_separate_surface_or_motion_failure():
    result=acceptance(.02,.018,2e-6,[0,1],[4.,4.],[True,True])
    assert not result['accepted']
    assert set(result['reasons'])=={'retained_surface_allowance','exported_motion'}


def test_stagnation_and_nonfinite_evidence_do_not_advance_the_sequence():
    assert not acceptance(.02,.02-1e-8,0,[0,0],[4.,4.],[True,True])['accepted']
    with pytest.raises(ValueError,match='Finite'):
        acceptance(.02,float('nan'),0,[0,0],[4.,4.],[True,True])
