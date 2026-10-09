import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_restoration_policy import tradeoff_policy,row_diagnostics
from protected_inequality_step import retain,fit


def test_default_preserves_even_failed_point_rows_and_every_edit_floor_and_rotation_row():
    labels=['point:Left','point:Right','normal:Left','object:box:Hand','floor',
        'all-reference-position:Hand','all-reference-speed:71:Hand','future-unknown-constraint']
    complete,mask=tradeoff_policy(labels,['Thumb1','Arm'],failure_policy='merit')
    assert complete==labels+['rotation-budget:Thumb1','rotation-budget:Arm']
    np.testing.assert_array_equal(mask,[False,False,True,True,False,False,False,False,False,False])
    _,old=tradeoff_policy(labels,[],failure_policy='merit',point_policy='tradeoff')
    assert old[:4].all() and not old[4:].any()
    _,strict=tradeoff_policy(labels,['Arm'],failure_policy='rowwise',point_policy='tradeoff')
    assert not strict.any()


def test_decreased_collision_merit_cannot_hide_a_failed_hand_distance_regression():
    labels=['object:box','point:Right'];before=[-.2,-.1];after=[-.1,-.11]
    _,preserved=tradeoff_policy(labels,[],failure_policy='merit')
    _,older=tradeoff_policy(labels,[],failure_policy='merit',point_policy='tradeoff')
    assert retain(before,after,failure_policy='merit',tradeoff_mask=older)
    assert not retain(before,after,failure_policy='merit',tradeoff_mask=preserved)


def test_bounded_repair_can_use_another_control_without_worsening_failed_hand_distance():
    labels=['object:box','point:Right','floor','all-reference-position:Hand']
    _,mask=tradeoff_policy(labels,[],failure_policy='merit')
    def measure(x):return np.array([x[0]-.2,-.1-.05*x[0]+x[1],.1-x[0],.3-x[1]])
    def derivative(x):return measure(x),np.array([[1.,0.],[-.05,1.],[-1.,0.],[0.,-1.]])
    value,r=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],trust=.1,
        failure_policy='merit',tradeoff_mask=mask,proposal='nonlinear')
    assert value[0]>0 and measure(value)[1]>=-.1
    assert r['source_passing_rows_preserved'] and r['nontradeoff_rows_preserved']


def test_complete_diagnostics_distinguish_tight_passes_failures_and_unapproved_tradeoffs():
    r=row_diagnostics(['point:Left','point:Right','object:box','rotation-budget:Arm'],
        [.1,-.1,-.2,0.],[1e-6,-.1,-.1,0.],[False,False,True,False])
    assert len(r['rows'])==4 and r['failed_rows']==['point:Right','object:box']
    assert r['tight_passing_rows']==['point:Left','rotation-budget:Arm']
    assert not r['source_passing_lost'] and not r['protected_source_regressed']
    assert not r['quality_approved'] and not r['release_approved']


@pytest.mark.parametrize('options',[dict(failure_policy='guess'),dict(point_policy='guess')])
def test_unknown_policy_rejected(options):
    with pytest.raises(ValueError):tradeoff_policy(['point:Left'],[],**options)


@pytest.mark.parametrize('labels,names',[([],[]),(['point:Left','point:Left'],[]),(['point:Left'],['Arm','Arm']),
    (['rotation-budget:Arm'],['Arm']),([3],[])])
def test_ambiguous_or_incomplete_row_identities_rejected(labels,names):
    with pytest.raises(ValueError):tradeoff_policy(labels,names)


@pytest.mark.parametrize('initial,final,mask',[([0],[0,1],[False]),([float('nan')],[0],[False]),([0],[0],[0])])
def test_diagnostics_require_full_finite_population_and_boolean_mask(initial,final,mask):
    with pytest.raises(ValueError):row_diagnostics(['point:Left'],initial,final,mask)
