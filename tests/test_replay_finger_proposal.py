import sys
from pathlib import Path
import pytest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from replay_finger_proposal import select_diagnostic,verify_scale


def population():
    return [dict(fraction=f, proposal_motion_pass=False, palm_pass=False,
        old_witness_pass=False, accepted_for_publication=False)
        for f in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]]


def test_largest_remaining_gate_feasible_step_is_selected_without_approval():
    rows=population()
    rows[0].update(proposal_motion_pass=True, palm_pass=False)
    for i in [2,3,5]: rows[i].update(proposal_motion_pass=True, palm_pass=True)
    index,reason=select_diagnostic(rows)
    assert index==2 and reason=='largest_motion_and_palm_feasible_backoff'
    assert not rows[index]['old_witness_pass'] and not rows[index]['accepted_for_publication']


def test_all_failed_returns_full_step_as_rejected_diagnostic_only():
    rows=population(); index,reason=select_diagnostic(rows)
    assert index==0 and reason=='full_step_rejected_diagnostic'
    assert not rows[index]['accepted_for_publication']


@pytest.mark.parametrize('kind',['missing','duplicate','reordered'])
def test_incomplete_or_reordered_trials_cannot_be_cherry_picked(kind):
    rows=population()
    if kind=='missing': rows.pop()
    elif kind=='duplicate': rows[1]=rows[0]
    else: rows.reverse()
    with pytest.raises(ValueError,match='Complete ordered'):select_diagnostic(rows)


def test_unit_roundtrip_keeps_authoritative_scale_without_accepting_real_changes():
    saved=np.deg2rad(np.array([5.,8.,12.]))/np.sqrt(3); original=saved.copy()
    reconstructed=np.deg2rad(np.rad2deg(saved*np.sqrt(3)))/np.sqrt(3)
    assert verify_scale(saved,reconstructed)<1e-15
    np.testing.assert_array_equal(saved,original)
    with pytest.raises(AssertionError):verify_scale(saved,reconstructed+1e-10)
