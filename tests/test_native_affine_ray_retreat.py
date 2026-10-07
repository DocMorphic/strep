"""Finite ray retreat preserves original affine caps and cannot approve exports."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_affine_ray_retreat as ray
import native_partner_ray_depth_restore as restore


def args():
    return [NormRows([[0.,0,0]],[.005],[1.]),sparse.csr_matrix([[1.],[0.],[0.]]),np.array([.005000002]),np.zeros(1),-np.ones(1),np.ones(1),.02]


def test_near_boundary_retreat_evaluates_every_original_norm_and_first_tested_point():
    a=args();snap=[getattr(a[0],k).tobytes() for k in ('vectors','caps','scales')]
    step,info=ray.project(*a)
    assert step is not None and .004999<step[0]<=.005
    assert info['status']=='VerifiedFiniteRayPoint' and 0<info['selected_fraction']<1
    assert len(info['records'])<len(ray.FRACTIONS)==81
    assert [v['fraction'] for v in info['records']]==list(ray.FRACTIONS[:len(info['records'])])
    assert all(v['original_affine_native_max_excess']>0 for v in info['records'][:-1])
    assert info['selected_native_maximum_excess']<=0 and not info['quality_approved'] and not info['release_approved']
    assert [getattr(a[0],k).tobytes() for k in ('vectors','caps','scales')]==snap


def test_all_rows_protect_coupled_norms_and_uses_small_fractions_when_needed():
    a=args();a[0]=NormRows([[0.,0,0],[0.,0,0]],[.01,.0002],[1.,.1]);a[1]=sparse.csr_matrix([[1.],[0.],[0.],[2.],[3.],[0.]])
    a[2]=np.array([.02]);step,info=ray.project(*a)
    assert step is not None and info['selected_fraction']<.5
    moved=a[0].vectors+(a[1]@step).reshape(2,3)
    excess=(np.sqrt((moved*moved).sum(axis=1))-a[0].caps)/a[0].scales
    assert np.all(excess<=0) and max(excess)==info['selected_native_maximum_excess']


def test_unmodified_valid_positive_step_is_retained():
    a=args();a[2]=np.array([.002]);step,info=ray.project(*a)
    np.testing.assert_array_equal(step,a[2]);assert info['selected_fraction']==1. and len(info['records'])==1


def test_anchor_failure_cannot_be_relabelled_as_feasible():
    a=args();a[0]=NormRows([[.006,0,0]],[.005],[1.]);step,info=ray.project(*a)
    assert step is None and info['status']=='OriginalAnchorNotStrictlyPassing' and not info['records']


def test_no_positive_feasible_step_cannot_substitute_origin():
    a=args();a[0]=NormRows([[0.,0,0]],[0.],[1.]);step,info=ray.project(*a)
    assert step is None and info['status']=='NoPositiveTestedRayPoint' and len(info['records'])==81
    assert info['records'][-1]['strict_native_pass'] and not info['records'][-1]['nonzero_step']


@pytest.mark.parametrize('fault',['nan','step_shape','jac_shape','bad_scale','cap','box','anchor_box','trust_bool','trust_large','step_box'])
def test_incomplete_or_invalid_input_cannot_trigger_retreat(fault):
    a=args()
    if fault=='nan':a[2][0]=np.nan
    elif fault=='step_shape':a[2]=np.ones(2)
    elif fault=='jac_shape':a[1]=sparse.csr_matrix((2,1))
    elif fault=='bad_scale':a[0].scales[0]=0.
    elif fault=='cap':a[0].caps[0]=-.01
    elif fault=='box':a[4]=a[5].copy()
    elif fault=='anchor_box':a[3][0]=2.
    elif fault=='trust_bool':a[6]=True
    elif fault=='trust_large':a[6]=.03
    elif fault=='step_box':a[2][0]=.0201
    with pytest.raises(ValueError):ray.project(*a)


def mock_failure():
    a=args();native,nj,raw,x,lo,hi,trust=a
    info=dict(status='UnverifiedDepthPhase',selected_phase=None,guard_scalar_ids=[0],scale_m=.005,clearance_m=0.,guidance_depth_target_m=0.,depth_limit_m=.005,
        phase_native_check_tolerance=1e-9,phase_lock_tolerance=1e-9,original_native_caps_scales_unchanged=True,external_geometry_acceptance_unchanged=True,
        phase_checks=[dict(phase='depth',status='Solved',rejections=['native_conditions'],projected_control_step=raw.tolist(),accepted=False)],invalid_solution=True,
        quality_approved=False,release_approved=False)
    reduction=SimpleNamespace(retained=np.array([0]),report={'proof_delta_lower':[-.02],'proof_delta_upper':[.02]})
    full=[native,nj,np.array([-.004]),sparse.csr_matrix([[1.]]),np.array([0,1]),[dict(kind='penetrating-vertex')],x,lo,hi,trust]
    return full,info,reduction


def test_recovery_keeps_solver_rejection_and_checks_full_surface_and_original_depth(monkeypatch):
    a,original,reduction=mock_failure();monkeypatch.setattr(restore,'solve_direction',lambda *args,**kw:(None,original,reduction))
    step,info,r=restore.direction(*a)
    assert r is reduction and step is not None and info['status']=='VerifiedRayDepthCandidate'
    assert info['selected_phase']=='depth-ray-recovery' and info['original_solver_validation_status']=='UnverifiedDepthPhase'
    assert info['phase_checks']==original['phase_checks'] and not original['phase_checks'][0]['accepted']
    assert info['predicted_native_excess']<=0 and info['predicted_preferred_depth_deficit']==0.
    assert info['original_anchor_preferred_depth_deficit']==.8
    assert info['depth_limit_m']==.005 and info['external_geometry_acceptance_unchanged']
    assert info['recovered_first_phase_candidate_not_solver_optimum'] and not info['quality_approved'] and not info['release_approved']
    assert not info['invalid_solution'] and 'depth_phase_optimum' not in info


@pytest.mark.parametrize('fault',['status','phase','solver','other_rejection','missing_step','later_phase'])
def test_other_solver_or_validation_failures_cannot_use_ray_recovery(monkeypatch,fault):
    a,info,reduction=mock_failure()
    if fault=='status':info['status']='FixedProtectedConflict'
    elif fault=='phase':info['phase_checks'][0]['phase']='surface'
    elif fault=='solver':info['phase_checks'][0]['status']='MaxTime'
    elif fault=='other_rejection':info['phase_checks'][0]['rejections'].append('depth_epigraph')
    elif fault=='missing_step':info['phase_checks'][0].pop('projected_control_step')
    elif fault=='later_phase':info['phase_checks'].append(dict(phase='surface'))
    monkeypatch.setattr(restore,'solve_direction',lambda *args,**kw:(None,info,reduction))
    monkeypatch.setattr(restore,'project',lambda *args:pytest.fail('unqualified failure must not be recovered'))
    step,report,_=restore.direction(*a);assert step is None and not report['ray_recovery_attempted']


def test_ray_cannot_buy_native_pass_with_worse_preferred_depth(monkeypatch):
    a,info,reduction=mock_failure();a[3]=sparse.csr_matrix([[-1.]])
    monkeypatch.setattr(restore,'solve_direction',lambda *args,**kw:(None,info,reduction))
    step,report,_=restore.direction(*a)
    assert step is None and report['status']=='RayDoesNotImprovePreferredDepth'


def test_original_anchor_conflict_is_kept(monkeypatch):
    a,info,reduction=mock_failure();a[0]=NormRows([[.006,0,0]],[.005],[1.])
    monkeypatch.setattr(restore,'solve_direction',lambda *args,**kw:(None,info,reduction))
    step,report,_=restore.direction(*a)
    assert step is None and report['ray_recovery']['status']=='OriginalAnchorNotStrictlyPassing'


def test_genuine_small_conic_success_needs_no_recovery():
    from test_native_partner_target_depth_restore import fixture
    a,kw=fixture();step,info,_=restore.direction(*a,**kw)
    assert step is not None and not info['ray_recovery_attempted'] and info['selected_phase'] in ('depth','surface','minimum-norm')
