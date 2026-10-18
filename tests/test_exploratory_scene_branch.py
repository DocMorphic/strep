from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from exploratory_scene_branch import ExploratorySceneBranch
from sequential_scene_step import SceneStepGuard


def gate(required=True):
    options={'required_rows':np.array([True,False,False])} if required else {}
    return SceneStepGuard(['floor','contact','normal'],[-.2,.1,-.5],np.zeros(3),[.01,.01,.01],**options)


def test_rejected_internal_observation_never_advances_accepted_guard():
    original=gate();branch=ExploratorySceneBranch(original)
    report=branch.observe(original.names,[-.1,.2,-.4],[.3,0,0])
    assert not report['final_retention_gate_pass'] and not report['accepted_guard_advanced'] and not report['candidate_selected']
    assert np.array_equal(branch.controls,[.3,0,0]) and np.array_equal(original.controls,np.zeros(3))
    assert np.array_equal(original.margins,[-.2,.1,-.5]) and original.steps==0


def test_original_required_and_protected_masks_never_follow_exploration():
    original=gate();branch=ExploratorySceneBranch(original)
    branch.observe(original.names,[-.1,-.1,.1],[.2,0,0])
    assert np.array_equal(branch.required_rows,[True,False,False]) and np.array_equal(branch.protected_rows,[False,True,False])
    report=branch.observe(original.names,[.1,.1,-.3],[.4,0,0])
    assert report['final_retention_gate_pass'] and report['all_fixed_required_rows_pass'] and report['all_fixed_protected_rows_pass']
    assert not report['all_supplied_rows_nonnegative'] and not report['candidate_selected'] and original.steps==0


def test_chained_small_moves_cannot_rebase_original_control_balls():
    original=gate();branch=ExploratorySceneBranch(original)
    branch.observe(original.names,[-.1,.1,-.4],[.9,0,0])
    with pytest.raises(ValueError):branch.observe(original.names,[.1,.1,-.3],[1.1,0,0])
    assert np.array_equal(branch.controls,[.9,0,0]) and branch.observations==1


def test_original_progress_target_is_not_reset_after_worse_exploration():
    original=gate();branch=ExploratorySceneBranch(original)
    branch.observe(original.names,[-.5,.1,-1.],[.2,0,0])
    report=branch.observe(original.names,[-.3,.1,-.6],[.3,0,0])
    assert not report['final_retention_gate_pass']
    assert report['final_guard_report']['baseline_maximum_working_violation']==.51


def test_caller_advancing_guard_cannot_change_branch_final_origin():
    original=gate();branch=ExploratorySceneBranch(original)
    original.advance(original.names,[.1,.1,-.2],[.1,0,0])
    report=branch.observe(original.names,[.1,.1,-.3],[.2,0,0])
    assert report['final_retention_gate_pass'] and original.steps==1
    assert report['final_guard_report']['baseline_maximum_working_violation']==.51


@pytest.mark.parametrize('required',[False,True])
def test_owned_inputs_properties_and_nested_reports(required):
    original=gate(required);branch=ExploratorySceneBranch(original);m=np.array([.1,.1,-.3]);x=np.array([.2,0,0])
    report=branch.observe(original.names,m,x);m[:]=99;x[:]=99
    branch.controls[:]=99;branch.margins[:]=99;branch.required_rows[:]=False;branch.protected_rows[:]=False
    report['final_guard_report']['original_row_names'][0]='changed'
    assert np.array_equal(branch.controls,[.2,0,0]) and np.array_equal(branch.margins,[.1,.1,-.3])
    assert branch.assess()['final_guard_report']['original_row_names']==list(original.names)
    assert branch.required_rows[0]==required and branch.protected_rows[1]


def test_assessing_all_positive_observations_still_does_not_select_or_advance():
    original=gate();branch=ExploratorySceneBranch(original);branch.observe(original.names,[.1,.2,.3],[.1,0,0]);before=branch.observations
    for _ in range(2):
        report=branch.assess();assert report['all_supplied_rows_nonnegative'] and report['final_retention_gate_pass']
        assert not report['accepted_guard_advanced'] and not report['candidate_selected'] and not report['quality_approved']
    assert branch.observations==before and original.steps==0


@pytest.mark.parametrize('fault',['names','partial','nan','complex','control_shape','control_bool','control_outside'])
def test_invalid_complete_observations_cannot_update_branch(fault):
    original=gate();branch=ExploratorySceneBranch(original);names=list(original.names);m=np.array([.1,.2,.3]);x=np.zeros(3)
    if fault=='names':names.reverse()
    elif fault=='partial':m=m[:2]
    elif fault=='nan':m[0]=np.nan
    elif fault=='complex':m=m.astype(complex)
    elif fault=='control_shape':x=np.zeros(6)
    elif fault=='control_bool':x=np.zeros(3,dtype=bool)
    else:x[:]=1
    with pytest.raises(ValueError):branch.observe(names,m,x)
    assert branch.observations==0 and np.array_equal(branch.controls,np.zeros(3))


def test_explicit_final_guard_required():
    with pytest.raises(ValueError):ExploratorySceneBranch(None)
