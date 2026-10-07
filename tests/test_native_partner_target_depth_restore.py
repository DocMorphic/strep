"""Preferred-depth guidance preserves every original hard norm and external limit."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partner_target_depth_restore as module
from native_scene_norms import NormRows


def fixture():
    native=NormRows([[0.,0,0]],[.015],[1.]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.r_[np.arange(9)*.002-.01,-.006,-.007]
    sj=sparse.csc_matrix(np.r_[np.ones(9),-1.,1.][:,None])
    blocks=[dict(kind='triangle-support-separation',time_s=0.),dict(kind='penetrating-vertex',time_s=0.),dict(kind='penetrating-vertex',time_s=1.)]
    policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256='a'*64,clock=dict(mode='explicit',times_s=[0.,1.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-5,surface_tolerance_m=1e-8),planes={})
    args=[native,nj,gaps,sj,[0,9,10,11],blocks,np.zeros(1),-np.ones(1),np.ones(1),.02]
    return args,dict(policy=policy,scene=SimpleNamespace(duration=1.,check_inputs=lambda:None),digest='a'*64)


def test_depth_precedes_complete_surface_and_native_penalty_coefficients_are_zero(monkeypatch):
    import clarabel
    calls=[]
    class Solver:
        __version__=clarabel.__version__
        NonnegativeConeT=clarabel.NonnegativeConeT
        SecondOrderConeT=clarabel.SecondOrderConeT
        DefaultSettings=clarabel.DefaultSettings
        @staticmethod
        def DefaultSolver(p,q,a,b,cones,settings):
            calls.append((p.copy(),q.copy(),a.copy(),b.copy(),cones))
            return clarabel.DefaultSolver(p,q,a,b,cones,settings)
    monkeypatch.setattr(module,'solver_module',lambda:Solver)
    args,kwargs=fixture();before={n:getattr(args[0],n).tobytes() for n in ('vectors','caps','scales')}
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and abs(delta[0]-.0005)<1e-8
    assert len(calls) in (2,3) and len(calls)==len(info['phase_checks'])
    assert info['phase_checks'][0]['accepted']
    if len(calls)==2:
        assert not info['phase_checks'][1]['accepted'] and info['minimum_norm_phase_status']=='not-run'
    assert info['predicted_native_excess']<=info['phase_native_check_tolerance']
    assert info['predicted_partner_depth_deficit']<=info['depth_phase_optimum']+info['phase_lock_tolerance']
    np.testing.assert_array_equal(calls[0][1],[0.,1.,0.]);np.testing.assert_array_equal(calls[1][1],[0.,0.,1.])
    np.testing.assert_array_equal(calls[0][2][4:8,1:].toarray(),np.zeros((4,2)))
    np.testing.assert_array_equal(calls[0][2][-2:,1:].toarray(),np.array([[-1.,0.],[-1.,0.]]))
    assert info['depth_phase_optimum']==pytest.approx(1.3,abs=1e-7)
    assert info['predicted_partner_depth_deficit']==pytest.approx(1.3,abs=1e-7)
    assert info['predicted_preferred_depth_deficit']==info['predicted_partner_depth_deficit']
    assert info['predicted_original_depth_floor_deficit']==pytest.approx(.3,abs=1e-7)
    assert info['full_affine_surface_excess']>1.8  # Better surface movement cannot buy worse depth.
    assert info['restored_partner_scalar_rows']==2 and info['native_norms_always_hard']
    assert info['all_original_affine_surface_rows_evaluated'] and info['every_guarded_affine_gap_evaluated']
    assert all(getattr(args[0],n).tobytes()==b for n,b in before.items())
    assert info['external_geometry_acceptance_unchanged'] and not info['quality_approved'] and not info['release_approved']


def test_native_norm_stays_hard_even_when_depth_cannot_reach_its_unconstrained_optimum():
    args,kwargs=fixture();args[0]=NormRows([[0.,0,0]],[.0001],[1.])
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and delta[0]<=.0001+1e-8
    assert info['predicted_partner_depth_deficit']>=1.37999
    assert info['predicted_native_excess']<1e-8


def test_fixed_original_native_failure_rejects():
    args,kwargs=fixture();args[0]=NormRows([[.03,0,0]],[.015],[1.]);args[1]=sparse.csc_matrix((3,1))
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is None and info['status']=='FixedProtectedConflict'


def test_no_partner_rows_still_optimizes_all_surfaces():
    args,kwargs=fixture();args[5][1]['kind']='world-plane';args[5][2]['kind']='world-plane'
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and info['restored_partner_scalar_rows']==0 and info['predicted_partner_depth_deficit']==0.
    assert info['depth_phase_optimum']<1e-7 and info['all_original_affine_surface_rows_evaluated']


@pytest.mark.parametrize('failed_phase',[2,3])
def test_failed_later_phase_retains_last_successful_point(monkeypatch,failed_phase):
    import clarabel
    calls=[]
    class Solver:
        __version__=clarabel.__version__
        NonnegativeConeT=clarabel.NonnegativeConeT
        SecondOrderConeT=clarabel.SecondOrderConeT
        DefaultSettings=clarabel.DefaultSettings
        @staticmethod
        def DefaultSolver(p,q,a,b,cones,settings):
            calls.append(1)
            if len(calls)==failed_phase:
                return SimpleNamespace(solve=lambda:SimpleNamespace(status='InsufficientProgress',x=None))
            if len(calls)==2 and failed_phase==3:
                # A genuinely feasible surface point lets this test inject
                # failure in phase three rather than stopping in phase two.
                return SimpleNamespace(solve=lambda:SimpleNamespace(status='Solved',x=np.array([.025,1.3,1.9]),iterations=1))
            return clarabel.DefaultSolver(p,q,a,b,cones,settings)
    monkeypatch.setattr(module,'solver_module',lambda:Solver)
    args,kwargs=fixture();delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and abs(delta[0]-.0005)<1e-7 and len(calls)==failed_phase
    assert info['minimum_norm_phase_status']==('not-run' if failed_phase==2 else 'InsufficientProgress')


@pytest.mark.parametrize('fault',['digest','time','incomplete','trust','gap','jacobian','clearance','scale'])
def test_unbound_or_malformed_models_reject(fault):
    args,kwargs=fixture()
    if fault=='digest':kwargs['digest']='b'*64
    elif fault=='time':args[5][1]['time_s']=.5
    elif fault=='incomplete':args[5]=args[5][:-1]
    elif fault=='trust':args[9]=True
    elif fault=='gap':args[2][9]=.001
    elif fault=='jacobian':args[3]=sparse.csc_matrix(np.full((11,1),np.nan))
    elif fault=='clearance':kwargs['clearance']=True
    elif fault=='scale':kwargs['scale']=0.
    with pytest.raises(ValueError):module.direction(*args,**kwargs)


def test_solver_edge_tolerance_is_projected_into_original_trust_box(monkeypatch):
    import clarabel
    class Solver:
        __version__=clarabel.__version__
        NonnegativeConeT=clarabel.NonnegativeConeT
        SecondOrderConeT=clarabel.SecondOrderConeT
        DefaultSettings=clarabel.DefaultSettings
        @staticmethod
        def DefaultSolver(p,q,a,b,cones,settings):
            point=np.array([1.+1e-10,10.,10.])
            return SimpleNamespace(solve=lambda:SimpleNamespace(status='Solved',x=point,iterations=1))
    monkeypatch.setattr(module,'solver_module',lambda:Solver)
    args,kwargs=fixture();args[0]=NormRows([[0.,0,0]],[.03],[1.]);delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and delta[0]==.02
    assert info['trust_projection_maximum_change']>0.
    assert delta[0]<=reduction.report['proof_delta_upper'][0]



def test_zero_target_improves_below_limit_depth_instead_of_only_staying_below_limit():
    import native_partner_depth_restore as old
    args,kwargs=fixture();args[2][9:]=[-.002,-.003]
    original={key:getattr(args[0],key).tobytes() for key in ('vectors','caps','scales')}
    original_policy=repr(kwargs['policy'])
    baseline,baseline_info,_=old.direction(*args,**kwargs)
    preferred,preferred_info,_=module.direction(*args,**kwargs)
    assert baseline is not None and preferred is not None
    assert baseline[0]>.0029 and abs(preferred[0]-.0005)<1e-7
    baseline_depth=float(-(args[2][9:]+args[3][9:]@baseline).min())
    preferred_depth=float(-(args[2][9:]+args[3][9:]@preferred).min())
    assert baseline_depth>.0049 and preferred_depth<.00251
    assert preferred_info['guidance_depth_target_m']==0. and preferred_info['depth_limit_m']==.005
    assert preferred_info['partner_depth_guard']['depth_limit_m']==.005
    assert preferred_info['partner_depth_guard']['guidance_depth_target_m']==0.
    assert preferred_info['external_geometry_acceptance_unchanged'] and preferred_info['native_norms_always_hard']
    assert not preferred_info['quality_approved'] and not preferred_info['release_approved']
    assert repr(kwargs['policy'])==original_policy
    assert all(getattr(args[0],key).tobytes()==value for key,value in original.items())


def test_declared_original_limit_target_reproduces_unchanged_floor_guidance():
    import native_partner_depth_restore as old
    args,kwargs=fixture()
    baseline,baseline_info,_=old.direction(*args,**kwargs)
    preferred,info,_=module.direction(*args,**kwargs,guidance_depth_target_m=.005)
    np.testing.assert_allclose(preferred,baseline,atol=1e-10,rtol=1e-8)
    assert info['guidance_depth_target_m']==info['depth_limit_m']==.005
    assert info['predicted_partner_depth_deficit']==pytest.approx(baseline_info['predicted_partner_depth_deficit'],abs=1e-8)


@pytest.mark.parametrize('target',[True,False,None,-.001,.005001,float('nan'),float('inf'),float('-inf'),'0'])
def test_invalid_preferred_target_rejects_before_solver(monkeypatch,target):
    args,kwargs=fixture()
    monkeypatch.setattr(module,'solver_module',lambda:pytest.fail('invalid target must not solve'))
    with pytest.raises(ValueError,match='preferred depth target'):
        module.direction(*args,**kwargs,guidance_depth_target_m=target)


@pytest.mark.parametrize('target',[0.,.002,.005])
def test_preferred_target_never_softens_original_native_norm(target):
    args,kwargs=fixture();args[0]=NormRows([[0.,0,0]],[.0001],[1.])
    delta,info,_=module.direction(*args,**kwargs,guidance_depth_target_m=target)
    assert delta is not None and abs(delta[0])<=.0001+1e-8
    assert info['predicted_native_excess']<=info['phase_native_check_tolerance']
    assert info['guidance_depth_target_m']==target and info['depth_limit_m']==.005
