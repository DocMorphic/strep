"""Complete hard gap changes, preserved caps and no nonlinear approval."""
from pathlib import Path
import copy,sys,itertools
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_partner_depth_guard import augment,direction


def fixture():
    native=NormRows([[0.,0,0]],[.015],[1.]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.r_[np.arange(9)*.002-.01,-.003,-.002]
    sj=sparse.csc_matrix(np.r_[np.ones(9),-1.,1.][:,None])
    blocks=[dict(kind='triangle-support-separation'),dict(kind='penetrating-vertex'),dict(kind='penetrating-vertex')]
    return native,nj,gaps,sj,[0,9,10,11],blocks,np.zeros(1),-np.ones(1),np.ones(1),.02


def test_every_partner_witness_is_guarded_and_original_native_prefix_unchanged():
    args=fixture();native,nj,gaps,sj,offsets,blocks,x,lo,hi,trust=args
    combined,jac,ids,report=augment(*args)
    assert ids.tolist()==[9,10] and report['guarded_partner_rows']==2
    for name in ('vectors','caps','scales'):
        np.testing.assert_array_equal(getattr(combined,name)[:1],getattr(native,name))
    np.testing.assert_array_equal(jac[:3].toarray(),nj.toarray())
    for delta in np.array([[-.02],[-.005],[0.],[.005],[.02]]):
        np.testing.assert_allclose(combined.residual(jac,delta)[1:],-(sj[ids]@delta)/.005,atol=1e-12,rtol=0)
    assert report['external_geometry_acceptance_unchanged'] and not report['nonlinear_nonregression_verified']
    assert not report['quality_approved'] and not report['release_approved']


def test_competing_depth_guards_block_a_soft_surface_move_without_rebasing_native_caps():
    delta,info,reduction=direction(*fixture())
    assert delta is not None and abs(delta[0])<1e-7
    assert info['partner_depth_guard']['guarded_partner_rows']==2 and info['original_native_norm_rows']==1
    assert info['predicted_partner_gap_deficit']<1e-6
    assert info['all_original_affine_surface_rows_evaluated'] and info['every_guarded_affine_gap_evaluated']


def test_no_partner_witness_preserves_original_native_objects():
    args=list(fixture());args[5]=[dict(kind='triangle-support-separation'),dict(kind='world-plane'),dict(kind='primitive-triangle')]
    result,jac,ids,report=augment(*args)
    assert result is args[0] and jac.shape==args[1].shape and len(ids)==0
    assert report['guarded_partner_rows']==0


@pytest.mark.parametrize('fault',['missing-block','wrong-offset','float-offset','unknown-kind','positive-gap','wrong-jacobian','nonfinite','trust-bool','trust-large'])
def test_incomplete_or_unbound_guidance_rejects(fault):
    args=list(fixture())
    if fault=='missing-block':args[5]=args[5][:-1]
    elif fault=='wrong-offset':args[4]=[0,8,10,11]
    elif fault=='float-offset':args[4]=[0.,9.,10.,11.]
    elif fault=='unknown-kind':args[5][1]['kind']='ignore-penetration'
    elif fault=='positive-gap':args[2][9]=.01
    elif fault=='wrong-jacobian':args[3]=sparse.csc_matrix((10,1))
    elif fault=='nonfinite':args[2][2]=np.nan
    elif fault=='trust-bool':args[9]=True
    elif fault=='trust-large':args[9]=.03
    with pytest.raises(ValueError):augment(*args)
