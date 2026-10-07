from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_norm_hinge_guided_step as guide

def arguments():
 return [NormRows([[0.,0.,0.]],[.004],[1.]), sparse.csr_matrix([[1.],[0.],[0.]]),
         np.array([-.015]),sparse.eye(1),np.zeros(1),-np.ones(1),np.ones(1),.02]

def test_unreachable_separation_guide_cannot_relax_original_norm_cap():
 a=arguments();delta,info=guide.direction(*a)
 assert delta is not None and 0<delta[0]<=.004
 assert info['guide_squared_error_after']<info['guide_squared_error_before']
 assert info['selected_original_native_maximum_excess']<=0
 assert info['guide_loss_kind']=='squared_negative_part' and info['all_guide_rows_retained']
 assert not info['quality_approved'] and not info['release_approved']
 np.testing.assert_array_equal(a[0].caps,[.004])

def test_already_satisfied_guidance_does_not_request_motion_or_a_solver(monkeypatch):
 a=arguments();a[2]=np.array([.1]);monkeypatch.setattr(guide,'solver_module',lambda:pytest.fail('No deficits to solve'))
 delta,info=guide.direction(*a);assert delta is None and info['status']=='NoNegativeGuideResidual'

def test_positive_pair_residual_is_unpenalized_but_complete_original_norms_still_limit_step():
 a=arguments();a[0]=NormRows([[0.,0.,0.]],[.008],[1.]);a[2]=np.array([-.005,.1]);a[3]=sparse.csr_matrix([[1.],[-1.]])
 delta,info=guide.direction(*a)
 assert delta is not None and .0049<delta[0]<=.008
 assert a[2][1]-delta[0]>.09 and info['guide_squared_error_after']<1e-8
 assert info['guide_scalar_rows']==2 and len(info['raw_guide_slacks'])==2

def test_complete_parameter_equation_remains_hard_during_negative_part_guidance():
 a=arguments();a[0]=NormRows([[0.,0.,0.]],[.02],[1.]);a[1]=sparse.csr_matrix([[1.,0.],[0.,1.],[0.,0.]])
 a[2]=np.array([-.01]);a[3]=sparse.csr_matrix([[1.,0.]]);a[4]=np.zeros(2);a[5]=-np.ones(2);a[6]=np.ones(2)
 delta,info=guide.direction(*a,parameter_rows=[[1.,1.]])
 assert delta is not None and delta[0]>.009 and abs(delta.sum())<=1e-9 and np.linalg.norm(delta)<=.02

def test_every_coupled_native_row_is_hard_and_only_exactly_fixed_passing_rows_are_omitted():
 a=arguments();a[0]=NormRows([[0.,0.,0.],[0.,0.,0.],[.001,0.,0.]],[.01,.002,.001],[1.,1.,1.])
 a[1]=sparse.csr_matrix([[1.],[0.],[0.],[2.],[3.],[0.],[0.],[0.],[0.]])
 delta,info=guide.direction(*a)
 assert delta is not None and np.sqrt(13)*delta[0]<=.002
 assert info['active_original_norm_cones']==2 and info['omitted_exactly_fixed_passing_norms']==1
 np.testing.assert_array_less(a[0].residual(a[1],delta),np.full(3,1e-20))

def test_nonpassing_original_anchor_never_solves(monkeypatch):
 a=arguments();a[0]=NormRows([[.005,0.,0.]],[.004],[1.]);monkeypatch.setattr(guide,'solver_module',lambda:pytest.fail('Invalid anchor'))
 delta,info=guide.direction(*a);assert delta is None and info['status']=='OriginalAnchorNotStrictlyPassing'

@pytest.mark.parametrize('fault',['rows','jacobian','norms','trust','parameters','nan'])
def test_invalid_complete_inputs_are_rejected(fault):
 a=arguments();kw={}
 if fault=='rows':a[2]=np.zeros(4097);a[3]=sparse.csr_matrix((4097,1))
 elif fault=='jacobian':a[3]=sparse.eye(2)
 elif fault=='norms':a[1]=sparse.eye(3)
 elif fault=='trust':a[7]=True
 elif fault=='parameters':kw['parameter_rows']=np.zeros((1,2))
 else:a[2][0]=np.nan
 with pytest.raises(ValueError):guide.direction(*a,**kw)

@pytest.mark.parametrize('status,point,expected',[
 ('MaxTime',[np.nan,np.nan],'NoFiniteSolverCandidate'),
 ('Solved',[2.,0.],'SolverCandidateOutsideProposalBox'),
 ('Solved',[0.],'NoFiniteSolverCandidate'),
])
def test_invalid_solver_points_are_retained_as_rejections(monkeypatch,status,point,expected):
 class Solver:
  def solve(self):return SimpleNamespace(status=status,iterations=1,x=point)
 class Settings:pass
 fake=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
                      ZeroConeT=lambda n:n,DefaultSettings=Settings,DefaultSolver=lambda *a:Solver())
 monkeypatch.setattr(guide,'solver_module',lambda:fake)
 monkeypatch.setattr(guide,'project',lambda *a:pytest.fail('Invalid point must not reach ray check'))
 delta,info=guide.direction(*arguments());assert delta is None and info['status']==expected
 assert not info['quality_approved'] and not info['release_approved']
