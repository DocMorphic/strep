"""Hard halfspace semantics, unchanged original norms and complete rows."""
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partner_scalar_guard as module
from native_scene_norms import NormRows
from native_pair_surface_conic import direction as mixed


def fixture():
    native=NormRows([[0.,0,0]],[.015],[1.]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.r_[np.arange(9)*.002-.01,-.003,-.002]
    sj=sparse.csc_matrix(np.r_[np.ones(9),-1.,1.][:,None])
    blocks=[dict(kind='triangle-support-separation'),dict(kind='penetrating-vertex'),dict(kind='penetrating-vertex')]
    return native,nj,gaps,sj,[0,9,10,11],blocks,np.zeros(1),-np.ones(1),np.ones(1),.02


def test_all_guards_are_hard_scalar_rows_with_zero_penalty_coefficient(monkeypatch):
    import clarabel
    calls=[]
    class Solver:
        __version__=clarabel.__version__
        NonnegativeConeT=clarabel.NonnegativeConeT
        SecondOrderConeT=clarabel.SecondOrderConeT
        DefaultSettings=clarabel.DefaultSettings
        @staticmethod
        def DefaultSolver(p,q,a,b,cones,settings):
            calls.append((a.copy(),b.copy(),cones))
            return clarabel.DefaultSolver(p,q,a,b,cones,settings)
    monkeypatch.setattr(module,'solver_module',lambda:Solver)
    args=fixture();before={k:getattr(args[0],k).tobytes() for k in ('vectors','caps','scales')}
    delta,info,reduction=module.direction(*args)
    assert delta is not None and abs(delta[0])<1e-7
    matrix,bound,cones=calls[0]
    np.testing.assert_array_equal(matrix[-2:,-1].toarray(),np.zeros((2,1)))
    np.testing.assert_array_equal(matrix[-2:,:1].toarray(),np.array([[4.],[-4.]]))
    np.testing.assert_array_equal(bound[-2:],np.zeros(2))
    assert info['hard_partner_scalar_rows']==2 and info['active_native_cones']==1
    assert sum(isinstance(c,clarabel.SecondOrderConeT) for c in cones)==1
    assert info['complete_surface_rows']==11 and info['all_original_affine_surface_rows_evaluated']
    assert info['every_guarded_affine_gap_evaluated'] and info['predicted_partner_gap_deficit']<1e-6
    assert info['guard_representation']=='hard-scalar-halfspaces' and not info['quality_approved']
    assert all(getattr(args[0],k).tobytes()==b for k,b in before.items())


def test_no_guard_matches_complete_mixed_solver():
    args=list(fixture());args[5]=[dict(kind='triangle-support-separation'),dict(kind='world-plane'),dict(kind='primitive-triangle')]
    delta,info,reduction=module.direction(*args)
    direct,report=mixed(args[0],args[1],args[2],args[3],args[6],args[7],args[8],args[9],clearance=0.)
    assert info['hard_partner_scalar_rows']==0
    np.testing.assert_allclose(delta,direct,atol=1e-7,rtol=0)
    np.testing.assert_allclose(info['full_affine_surface_excess'],report['predicted_surface_excess'],atol=1e-7)


def test_original_fixed_failure_returns_no_proposal():
    args=list(fixture());args[0]=NormRows([[.03,0,0]],[.015],[1.]);args[1]=sparse.csc_matrix((3,1))
    delta,info,reduction=module.direction(*args)
    assert delta is None and info['status']=='FixedProtectedConflict'
    assert info['protected_norm_rows']==1 and not info['release_approved']


def test_one_sided_guard_allows_improvement_without_native_cap_rebasing():
    args=list(fixture());args[5][1]=dict(kind='world-plane')
    delta,info,reduction=module.direction(*args)
    assert delta is not None and delta[0]>.001 and delta[0]<=.015+1e-8
    assert info['hard_partner_scalar_rows']==1 and info['predicted_partner_gap_deficit']==0.


@pytest.mark.parametrize('kwargs',[dict(clearance=True),dict(clearance=-.001),dict(clearance=.006),dict(clearance=float('nan')),
    dict(scale=True),dict(scale=0.),dict(scale=float('nan'))])
def test_invalid_units_reject(kwargs):
    with pytest.raises(ValueError):module.direction(*fixture(),**kwargs)


@pytest.mark.parametrize('fault',['incomplete','unknown','positive-anchor','nan-jacobian'])
def test_guard_population_validation_is_preserved(fault):
    args=list(fixture())
    if fault=='incomplete':args[5]=args[5][:-1]
    elif fault=='unknown':args[5][1]['kind']='skip'
    elif fault=='positive-anchor':args[2][9]=.001
    elif fault=='nan-jacobian':args[3]=sparse.csc_matrix(np.full((11,1),np.nan))
    with pytest.raises(ValueError):module.direction(*args)
