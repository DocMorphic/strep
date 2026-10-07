from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
from scipy import sparse
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_norm_guided_step as guide


def arguments():
    return [NormRows([[0.,0.,0.]],[.004],[1.]), sparse.csr_matrix([[1.],[0.],[0.]]),
            np.array([-.015]), sparse.eye(1), np.zeros(1), -np.ones(1), np.ones(1), .02]


def test_hard_original_norm_caps_guide_despite_unreachable_target_and_replay_every_selected_row():
    a=arguments(); before=[getattr(a[0],k).copy() for k in ('vectors','caps','scales')]
    delta,info=guide.direction(*a)
    assert delta is not None and 0<delta[0]<=.004
    assert info['status']=='VerifiedAffineGuideCandidate' and info['selected_original_native_maximum_excess']<=0
    assert info['guide_squared_error_after']<info['guide_squared_error_before']
    assert not info['quality_approved'] and not info['release_approved']
    for key,saved in zip(('vectors','caps','scales'),before):np.testing.assert_array_equal(getattr(a[0],key),saved)


def test_optional_complete_parameter_equation_couples_controls_without_replacing_norm_bounds():
    a=arguments();a[0]=NormRows([[0.,0.,0.]],[.02],[1.]);a[1]=sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.]])
    a[2]=np.array([-.01]);a[3]=sparse.csr_matrix([[1.,0.]]);a[4]=np.zeros(2);a[5]=-np.ones(2);a[6]=np.ones(2)
    delta,info=guide.direction(*a,parameter_rows=np.array([[1.,1.]]))
    assert delta is not None and delta[0]>.009 and abs(delta.sum())<1e-9
    assert info['parameter_rows']==1 and np.linalg.norm(delta)<=.02


def test_every_coupled_original_norm_is_hard_and_exact_zero_derivative_rows_only_are_omitted():
    a=arguments();a[0]=NormRows([[0.,0.,0.],[0.,0.,0.],[.001,0.,0.]],[.01,.002,.001],[1.,1.,1.])
    a[1]=sparse.csr_matrix([[1.],[0.],[0.],[2.],[3.],[0.],[0.],[0.],[0.]])
    delta,info=guide.direction(*a)
    assert delta is not None and np.sqrt(13)*delta[0]<=.002
    assert info['active_original_norm_cones']==2 and info['omitted_exactly_fixed_passing_norms']==1


def test_failed_original_anchor_never_invokes_solver(monkeypatch):
    a=arguments();a[0]=NormRows([[.005,0.,0.]],[.004],[1.])
    monkeypatch.setattr(guide,'solver_module',lambda:pytest.fail('Failed original anchor must not solve'))
    delta,info=guide.direction(*a);assert delta is None and info['status']=='OriginalAnchorNotStrictlyPassing'


def test_exactly_satisfied_guidance_cannot_claim_strict_improvement():
    a=arguments();a[2]=np.zeros(1)
    delta,info=guide.direction(*a);assert delta is None
    assert info['status'] in ('NoStrictFiniteRayCandidate','NoStrictGuideImprovement')


@pytest.mark.parametrize('fault',['guide_shape','native_shape','cap','scale','bad_box','out_of_box','nan','trust','parameter_shape','parameter_count'])
def test_bad_or_incomplete_model_is_rejected(fault):
    a=arguments();kw={}
    if fault=='guide_shape':a[3]=sparse.eye(2)
    elif fault=='native_shape':a[1]=sparse.eye(3)
    elif fault=='cap':a[0].caps[0]=-.1
    elif fault=='scale':a[0].scales[0]=0.
    elif fault=='bad_box':a[5]=a[6].copy()
    elif fault=='out_of_box':a[4][0]=2.
    elif fault=='nan':a[2][0]=np.nan
    elif fault=='trust':a[7]=True
    elif fault=='parameter_shape':kw['parameter_rows']=np.zeros((1,2))
    elif fault=='parameter_count':kw['parameter_rows']=np.zeros((97,1))
    with pytest.raises(ValueError):guide.direction(*a,**kw)


def test_unsolved_candidate_is_retained_as_failure_metadata(monkeypatch):
    class Solver:
        def solve(self):return SimpleNamespace(status='MaxTime',iterations=100,x=[np.nan])
    class Settings:
        pass
    fake=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
                         ZeroConeT=lambda n:n,DefaultSettings=Settings,DefaultSolver=lambda *a:Solver())
    monkeypatch.setattr(guide,'solver_module',lambda:fake)
    delta,info=guide.direction(*arguments());assert delta is None and info['solver_status']=='MaxTime' and info['status']=='NoFiniteSolverCandidate'


@pytest.mark.parametrize('point,expected', [
    ([2.], 'SolverCandidateOutsideProposalBox'),
    ([np.nan], 'NoFiniteSolverCandidate'),
    ([0., 0.], 'NoFiniteSolverCandidate'),
])
def test_invalid_solved_point_is_rejected_without_ray_exception(monkeypatch, point, expected):
    class Solver:
        def solve(self):return SimpleNamespace(status='Solved', iterations=1, x=point)
    class Settings:
        pass
    fake=SimpleNamespace(__version__='0.11.1', NonnegativeConeT=lambda n:n, SecondOrderConeT=lambda n:n,
                         ZeroConeT=lambda n:n, DefaultSettings=Settings, DefaultSolver=lambda *a:Solver())
    monkeypatch.setattr(guide, 'solver_module', lambda:fake)
    monkeypatch.setattr(guide, 'project', lambda *a:pytest.fail('Invalid solver point must not reach ray projection'))
    delta, info=guide.direction(*arguments())
    assert delta is None and info['solver_status']=='Solved' and info['status']==expected
    assert not info['quality_approved'] and not info['release_approved']
    if expected=='SolverCandidateOutsideProposalBox':
        assert info['raw_control_step']==[.04]
