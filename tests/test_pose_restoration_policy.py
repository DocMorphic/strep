import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_restoration_policy import tradeoff_policy,row_diagnostics,proposal_headroom
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


def test_body_margin_only_tightens_position_proposals_and_leaves_other_rows_unchanged():
    labels=['point:Left','normal:Left','object:box','floor','all-reference-position:Hand',
        'all-reference-speed:97:Hand','rotation-budget:Arm','future-unknown-constraint']
    np.testing.assert_array_equal(proposal_headroom(labels),np.zeros(len(labels)))
    np.testing.assert_array_equal(proposal_headroom(labels,point=1e-5,body=1e-3),[1e-5,0,0,0,1e-3,0,0,0])
    np.testing.assert_array_equal(proposal_headroom(labels,normal=1e-3),[0,1e-3,0,0,0,0,0,0])


def test_collision_merit_cannot_hide_failed_normal_regression_under_preservation():
    labels=['object:box','normal:Left','normal:Right','floor','rotation-budget:Arm']
    before=[-.2,-.1,-.09,1.,1.];after=[-.1,-.11,-.08,1.,1.]
    _,old=tradeoff_policy(labels,[],failure_policy='merit')
    _,protected=tradeoff_policy(labels,[],failure_policy='merit',normal_policy='preserve')
    assert retain(before,after,failure_policy='merit',tradeoff_mask=old)
    assert not retain(before,after,failure_policy='merit',tradeoff_mask=protected)
    np.testing.assert_array_equal(protected,[True,False,False,False,False])


def test_normal_improvement_cannot_hide_failed_collision_regression_when_both_preserved():
    labels=['normal:Left','object:box:Hand','floor','all-reference-position:Hand']
    before=[-.8,-.2,.1,.3];after=[-.6,-.25,.1,.3]
    _,legacy=tradeoff_policy(labels,[],failure_policy='merit',normal_policy='preserve')
    _,protected=tradeoff_policy(labels,[],failure_policy='merit',normal_policy='preserve',object_policy='preserve')
    assert retain(before,after,failure_policy='merit',tradeoff_mask=legacy)
    assert not retain(before,after,failure_policy='merit',tradeoff_mask=protected)
    assert not protected.any()


def test_joint_correction_uses_clearance_control_without_regressing_collision_or_normal():
    labels=['normal:Left','object:box:Hand','floor','all-reference-position:Hand']
    _,mask=tradeoff_policy(labels,[],failure_policy='merit',normal_policy='preserve',object_policy='preserve')
    def measure(x):return np.array([x[0]-.2,-.1-.05*x[0]+x[1],.1-x[0],.3-x[1]])
    def derivative(x):return measure(x),np.array([[1.,0.],[-.05,1.],[-1.,0.],[0.,-1.]])
    value,r=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],trust=.1,iterations=1,
        failure_policy='merit',tradeoff_mask=mask,proposal='nonlinear',
        proposal_headroom=proposal_headroom(labels,object=1e-3))
    assert value[0]>0 and measure(value)[1]>=-.1 and measure(value)[0]>-.2
    assert r['nontradeoff_rows_preserved'] and not r['quality_approved']
    assert r['proposal_headroom_normalized']==[0,1e-3,0,0]


def test_collision_margin_is_separate_from_point_normal_body_floor_and_speed():
    labels=['point:Left','normal:Left','object:box:Hand','floor','all-reference-position:Hand',
        'all-reference-speed:97:Hand','rotation-budget:Arm','future-unknown-constraint']
    np.testing.assert_array_equal(proposal_headroom(labels,object=1e-3),[0,0,1e-3,0,0,0,0,0])
    np.testing.assert_array_equal(proposal_headroom(labels,point=1e-5,normal=1e-3,object=1e-4,body=1e-3),
        [1e-5,1e-3,1e-4,0,1e-3,0,0,0])


def test_nonlinear_correction_improves_contact_without_worsening_failed_normal():
    labels=['object:box','normal:Left','floor','all-reference-position:Hand']
    _,mask=tradeoff_policy(labels,[],failure_policy='merit',normal_policy='preserve')
    def measure(x):return np.array([x[0]-.2,-.1-.05*x[0]+x[1],.1-x[0],.3-x[1]])
    def derivative(x):return measure(x),np.array([[1.,0.],[-.05,1.],[-1.,0.],[0.,-1.]])
    value,r=fit(measure,derivative,[0.,0.],[-1.,-1.],[1.,1.],trust=.1,iterations=1,
        failure_policy='merit',tradeoff_mask=mask,proposal='nonlinear',proposal_headroom=proposal_headroom(labels,normal=1e-3))
    assert value[0]>0 and measure(value)[1]>=-.1 and r['nontradeoff_rows_preserved']
    assert not r['quality_approved'] and r['proposal_headroom_normalized']==[0,1e-3,0,0]


@pytest.mark.parametrize('body',[True,-1e-6,1.0001e-3,float('nan'),float('inf'),'0.001'])
def test_invalid_body_margin_rejected(body):
    with pytest.raises(ValueError):proposal_headroom(['all-reference-position:Hand'],body=body)
    with pytest.raises(ValueError):proposal_headroom(['normal:Left'],normal=body)
    with pytest.raises(ValueError):proposal_headroom(['object:box'],object=body)


@pytest.mark.parametrize('labels',[[],['x','x'],[3],[['x']]])
def test_invalid_margin_row_identity_rejected(labels):
    with pytest.raises(ValueError):proposal_headroom(labels,body=1e-3)


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


@pytest.mark.parametrize('options',[dict(failure_policy='guess'),dict(point_policy='guess'),dict(normal_policy='guess'),dict(object_policy='guess')])
def test_unknown_policy_rejected(options):
    with pytest.raises(ValueError):tradeoff_policy(['point:Left'],[],**options)


@pytest.mark.parametrize('labels,names',[([],[]),(['point:Left','point:Left'],[]),(['point:Left'],['Arm','Arm']),
    (['rotation-budget:Arm'],['Arm']),([3],[])])
def test_ambiguous_or_incomplete_row_identities_rejected(labels,names):
    with pytest.raises(ValueError):tradeoff_policy(labels,names)


@pytest.mark.parametrize('initial,final,mask',[([0],[0,1],[False]),([float('nan')],[0],[False]),([0],[0],[0])])
def test_diagnostics_require_full_finite_population_and_boolean_mask(initial,final,mask):
    with pytest.raises(ValueError):row_diagnostics(['point:Left'],initial,final,mask)
