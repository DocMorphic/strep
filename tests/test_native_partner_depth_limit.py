"""Source-bound depth floors, hard penalty isolation and original caps."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partner_depth_limit as module
from native_scene_norms import NormRows


def fixture():
    native=NormRows([[0.,0,0]],[.015],[1.]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.r_[np.arange(9)*.002-.01,-.003,-.002]
    sj=sparse.csc_matrix(np.r_[np.ones(9),-1.,1.][:,None])
    blocks=[dict(kind='triangle-support-separation',time_s=0.),dict(kind='penetrating-vertex',time_s=0.),dict(kind='penetrating-vertex',time_s=1.)]
    scene=SimpleNamespace(duration=1.,check_inputs=lambda:None)
    policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256='a'*64,clock=dict(mode='explicit',times_s=[0.,1.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-5,surface_tolerance_m=1e-8),planes={})
    return [native,nj,gaps,sj,[0,9,10,11],blocks,np.zeros(1),-np.ones(1),np.ones(1),.02],dict(policy=policy,scene=scene,digest='a'*64)


def test_authored_floor_permits_shallow_witness_decrease_but_cannot_be_bought_by_soft_penalty(monkeypatch):
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
    args,kwargs=fixture();original=copy.deepcopy(kwargs['policy']);prefix={n:getattr(args[0],n).tobytes() for n in ('vectors','caps','scales')}
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and .0019<delta[0]<.0021
    np.testing.assert_array_equal(calls[0][0][-2:,-1].toarray(),np.zeros((2,1)))
    np.testing.assert_allclose(calls[0][1][-2:],np.array([.4,.6]),atol=1e-15)
    assert info['predicted_partner_depth_deficit']<1e-6
    assert info['hard_partner_scalar_rows']==2 and info['depth_limit_m']==.005
    assert info['all_original_affine_surface_rows_evaluated'] and info['every_guarded_affine_gap_evaluated']
    assert info['external_geometry_acceptance_unchanged'] and not info['quality_approved'] and not info['release_approved']
    assert kwargs['policy']==original and all(getattr(args[0],n).tobytes()==b for n,b in prefix.items())


def test_fixed_deep_witness_is_not_relaxed_into_soft_objective():
    args,kwargs=fixture();args[2][9]=-.006;args[3]=sparse.csc_matrix(np.r_[np.ones(9),0.,1.][:,None])
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is None and info['status']=='PrimalInfeasible' and info['hard_partner_scalar_rows']==2


def test_actual_limit_changes_guidance_and_zero_limit_requires_separation():
    args,kwargs=fixture();args[5][1]['kind']='world-plane';kwargs['policy']['limits']['penetration_m']=0.
    delta,info,reduction=module.direction(*args,**kwargs)
    assert delta is not None and delta[0]>=.002-1e-8 and info['depth_limit_m']==0.


@pytest.mark.parametrize('fault',['digest','extra-policy-field','negative-depth','large-depth','bool-depth','nan-depth','missing-depth',
    'unsorted-clock','missing-clock-end','unbound-time','bool-time','nan-time','missing-time'])
def test_changed_or_unbound_policy_and_witness_clock_reject(fault):
    args,kwargs=fixture();p=kwargs['policy']
    if fault=='digest':kwargs['digest']='b'*64
    elif fault=='extra-policy-field':p['approve']=True
    elif fault=='negative-depth':p['limits']['penetration_m']=-.001
    elif fault=='large-depth':p['limits']['penetration_m']=.2
    elif fault=='bool-depth':p['limits']['penetration_m']=True
    elif fault=='nan-depth':p['limits']['penetration_m']=float('nan')
    elif fault=='missing-depth':p['limits'].pop('penetration_m')
    elif fault=='unsorted-clock':p['clock']['times_s']=[0.,.8,.5,1.]
    elif fault=='missing-clock-end':p['clock']['times_s']=[0.,.5]
    elif fault=='unbound-time':args[5][1]['time_s']=.5
    elif fault=='bool-time':args[5][1]['time_s']=False
    elif fault=='nan-time':args[5][1]['time_s']=float('nan')
    elif fault=='missing-time':args[5][1].pop('time_s')
    with pytest.raises(ValueError):module.direction(*args,**kwargs)


def test_source_bytes_are_checked_before_solving():
    args,kwargs=fixture()
    def changed():raise ValueError('Changed source bytes')
    kwargs['scene'].check_inputs=changed
    with pytest.raises(ValueError,match='Changed source bytes'):module.direction(*args,**kwargs)
