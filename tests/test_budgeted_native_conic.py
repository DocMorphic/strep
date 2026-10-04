"""Larger explicit CPU budgets cannot change guards or approve saved motion."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import budgeted_native_conic as budgeted
from native_scene_conic import direction as historical,solver_module
from native_scene_norms import NormRows
from native_contact_norms import protect_rows


def toy():
    return NormRows([[0.,0,0],[-1.,0,0]],[.2,0.],[1.,1.]),np.stack([np.eye(3)]*2)


@pytest.mark.parametrize('option,value',[
    ('phase_seconds',True),('phase_seconds',0.),('phase_seconds',.5),('phase_seconds',300.1),
    ('phase_seconds',float('nan')),('phase_seconds',float('inf')),('phase_seconds','120'),
    ('maximum_iterations',True),('maximum_iterations',0),('maximum_iterations',501),
    ('maximum_iterations',200.),('maximum_iterations','200')])
def test_invalid_or_unbounded_compute_settings_reject_before_solver_load(monkeypatch,option,value):
    monkeypatch.setattr(budgeted,'solver_module',lambda:pytest.fail('Invalid settings must reject before solver load'))
    system,jac=toy()
    with pytest.raises(ValueError,match='budget'):budgeted.direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.,**{option:value})


@pytest.mark.parametrize('sparse_jac',[False,True])
def test_actual_solver_matches_historical_formulation_and_reports_explicit_budget(sparse_jac):
    system,jac=toy();jac=sparse.csc_matrix(jac.reshape(6,3)) if sparse_jac else jac
    old,old_info=historical(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.)
    new,info=budgeted.direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.,phase_seconds=120.,maximum_iterations=200)
    np.testing.assert_allclose(new,old,atol=1e-10,rtol=0)
    assert info['norm_rows']==old_info['norm_rows']==2 and info['active_cones']==old_info['active_cones']==2
    assert info['phase_time_limit_seconds']==120. and info['phase_maximum_iterations']==200
    assert info['independently_decoded_candidate_required'] and not info['quality_approved'] and not info['release_approved']


def test_larger_compute_budget_preserves_every_individual_hard_contact_guard():
    system=NormRows([[0.,0,0],[3.,0,0],[2.,0,0]],np.ones(3),np.ones(3))
    jac=sparse.csc_matrix(np.array([0,0,0,-1,0,0,1,0,0])[:,None])
    protected,j,guard=protect_rows(system,jac,1,system.residual()[1:])
    delta,info=budgeted.direction(protected,j,np.zeros(1),-np.ones(1),np.ones(1),.02,hard_rows=guard['hard_rows'])
    assert abs(delta[0])<1e-8 and info['protected_norm_rows']==3
    np.testing.assert_array_equal(system.caps,np.ones(3))


def test_fixed_failed_protected_row_cannot_be_bypassed_with_longer_budget():
    system=NormRows([[2.,0,0],[1.,0,0]],[1.,0.],[1.,1.]);jac=sparse.csc_matrix((6,1))
    delta,info=budgeted.direction(system,jac,np.zeros(1),-np.ones(1),np.ones(1),.02,hard_rows=1,phase_seconds=300.,maximum_iterations=500)
    assert delta is None and info['status']=='FixedProtectedConflict'
    assert info['phase_time_limit_seconds']==300. and not info['physical_or_authored_limits_relaxed']


def test_iteration_exhaustion_produces_no_affine_direction():
    system,jac=toy()
    delta,info=budgeted.direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.,maximum_iterations=1)
    assert delta is None and info['status']=='MaxIterations'
    assert info['phase_maximum_iterations']==1 and 'minimum_norm_phase_status' not in info


@pytest.mark.parametrize('secondary_timeout',[False,True])
def test_both_phases_receive_the_budget_and_secondary_timeout_keeps_primary_only(monkeypatch,secondary_timeout):
    real=solver_module();settings=[]
    def factory(*args):
        s=args[-1];settings.append((s.time_limit,s.max_iter))
        if secondary_timeout and len(settings)==2:
            return SimpleNamespace(solve=lambda:SimpleNamespace(status='MaxTime',x=[]))
        return real.DefaultSolver(*args)
    proxy=SimpleNamespace(DefaultSettings=real.DefaultSettings,DefaultSolver=factory,SecondOrderConeT=real.SecondOrderConeT,
        NonnegativeConeT=real.NonnegativeConeT,__version__=real.__version__)
    monkeypatch.setattr(budgeted,'solver_module',lambda:proxy)
    system=NormRows([[0.,0,0],[-1.,0,0]],[.2,0.],[1.,1.]);jac=np.stack([np.eye(3)]*2)
    delta,info=budgeted.direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.,hard_rows=1,phase_seconds=90.,maximum_iterations=150)
    assert settings==[(90.,150),(90.,150)] and delta is not None
    assert system.residual(jac,delta)[0]<=1e-8
    if secondary_timeout:assert info['minimum_norm_phase_status']=='MaxTime'
    else:assert info['minimum_norm_phase_status'] in ('Solved','AlmostSolved')
    assert info['independently_decoded_candidate_required'] and not info['release_approved']
