import sys
from pathlib import Path
import numpy as np
import pytest
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from regional_pose_bundle import active_rows,BundleProblem
from regional_pose_witness import RegionalPoseProblem
from regional_pose_bounded import coordinates
from constraint_restoration import minimax_step,assess_trial


def test_near_ties_and_individual_contact_rows_are_retained():
    values=np.array([5.,4.99,1.,-2.,-.1,-3.])
    ids=active_rows(values,[np.arange(3),np.array([3,4])],[5],margin=.02,cap=4)
    np.testing.assert_array_equal(ids,[0,1,4,5])
    assert 2 in active_rows(values,[np.arange(3),np.array([3,4])],[5],extra=[2],cap=5)


def test_cap_never_drops_mandatory_contact_or_cut_rows():
    with pytest.raises(ValueError,match='cap exhausted'):
        active_rows(np.array([2.,1.,0.]),[np.array([0,1])],[2],extra=[1],cap=2)


@pytest.mark.parametrize('extra,margin,cap',[([4],.1,5),([],float('nan'),5),([],.1,True)])
def test_invalid_active_policy_rejected(extra,margin,cap):
    with pytest.raises(ValueError):active_rows(np.array([2.,1.]),[np.arange(2)],[],extra,margin,cap)


def test_both_tied_rows_allow_joint_descent_without_trading_them():
    g=np.array([1.,1.]);jac=np.array([[1.,0.],[-1.,1.]])
    ids=active_rows(g,[np.arange(2)],[],margin=.1,cap=2)
    step,record=minimax_step(np.zeros(2),g[ids],jac[ids],np.full(2,-1.),np.ones(2),np.full(2,.1))
    assert record['success'] and assess_trial(g,g+jac@step)['accepted']
    assert np.all(g+jac@step<g)


def test_full_vertex_acceptance_rejects_a_trade_hidden_by_the_maximum():
    before=np.array([1.,.1,-.1]);after=np.array([.9,.2,-.1])
    assert assess_trial(np.array([before.max()]),np.array([after.max()]))['accepted']
    full=assess_trial(before,after)
    assert not full['accepted'] and full['worsened_existing_failures']==1


def test_full_regional_vector_reduces_to_original_constraints_and_serializes():
    p=RegionalPoseProblem(ROOT/'reports/scene-region-jobs/cylinder-contact-v1/fit',96)
    b=BundleProblem(p);initial,_=coordinates(p)
    with torch.no_grad():full=b.residual(p.t(initial)).numpy();original=-p.geometry_slack(p.t(p.seed)).numpy()
    assert len(full)==b.count and len(b.groups)==4 and len(b.singles)==26
    np.testing.assert_allclose(b.collapsed(full),original,atol=1e-9,rtol=1e-9)
    saved,audit,motion,physical=b.serialized(initial)
    assert saved.shape==full.shape and audit['bounds_passed'] and not audit['pose_witness_passed']
    np.testing.assert_allclose(physical,p.seed,atol=1e-12,rtol=1e-12)
