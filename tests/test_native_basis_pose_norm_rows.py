from pathlib import Path
import sys
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_key_basis.py').is_file())
sys.path[:0]=[str(root/'tests'),str(root/'scripts')]
from native_basis_pose_norm_rows import BasisPoseNormRows
from native_key_basis import NativeKeyBasis
from native_key_pose_map import KeyPoseMap
from test_native_basis_pose_rows import setup


@pytest.mark.parametrize('mode',['start','native','subkey','end'])
def test_canonical_vectors_reproduce_every_legacy_pose_margin(tmp_path,mode):
    model,mapper,basis,caps,old,point=setup(tmp_path,mode)
    helper=BasisPoseNormRows(mapper,basis,caps);result=helper.evaluate_vectors(point);source=old.evaluate(point)
    assert result['canonical_margins'].tobytes()==source['margins'].tobytes()
    assert result['world'].tobytes()==source['world'].tobytes()
    assert result['radii'].tobytes()==np.r_[np.ones(len(model.nodes)),caps].tobytes()
    assert result['jacobian'].shape==(len(source['margins']),3,basis.size)
    projected=-2*np.einsum('ri,ric->rc',result['vectors'],result['jacobian'])/result['radii'][:,None]**2
    np.testing.assert_allclose(projected,source['jacobian'],atol=2e-10,rtol=2e-9)
    assert not result['report']['quality_approved'] and not result['report']['release_approved']


def test_transverse_information_survives_zero_scalar_gradient(tmp_path):
    model,mapper,basis,caps,old,point=setup(tmp_path,'native');seed=np.zeros_like(mapper.seed)
    mapper=KeyPoseMap(model,mapper.time_s,seed,list(mapper.pairs))
    info=basis.report;basis=NativeKeyBasis(mapper.clock,list(model.nodes),seed,sorted(set(info['variable_knots']+[0,len(mapper.clock)-1])),info['frozen_keys'])
    helper=BasisPoseNormRows(mapper,basis,caps);result=helper.evaluate_vectors(np.zeros(basis.size))
    norms=np.linalg.norm(result['vectors'],axis=1);derivatives=np.linalg.norm(result['jacobian'],axis=(1,2))
    assert np.any((norms<1e-12)&(derivatives>1e-6))


def test_full_vector_directions_include_last_basis_column(tmp_path):
    model,mapper,basis,caps,old,point=setup(tmp_path);helper=BasisPoseNormRows(mapper,basis,caps);result=helper.evaluate_vectors(point)
    directions=[np.eye(basis.size)[-1],np.random.default_rng(37).normal(size=basis.size)]
    for direction in directions:
        direction/=np.linalg.norm(direction);step=1e-5
        plus=helper.evaluate_vectors(point+step*direction,jacobian=False);minus=helper.evaluate_vectors(point-step*direction,jacobian=False)
        finite=(plus['vectors']-minus['vectors'])/(2*step);predicted=np.einsum('ric,c->ri',result['jacobian'],direction)
        np.testing.assert_allclose(predicted,finite,atol=3e-7,rtol=3e-5)


def test_encoded_mode_is_value_only(tmp_path):
    model,mapper,basis,caps,old,point=setup(tmp_path);helper=BasisPoseNormRows(mapper,basis,caps)
    result=helper.evaluate_vectors(point,jacobian=False,encoded=True)
    assert result['jacobian'] is None and result['world_jacobian'] is None and result['report']['encoded']
    assert result['canonical_margins'].tobytes()==old.evaluate(point,jacobian=False,encoded=True)['margins'].tobytes()
    with pytest.raises(ValueError):helper.evaluate_vectors(point,encoded=True)


def test_extra_vector_workspace_rejects_before_pose_allocation(tmp_path,monkeypatch):
    model,mapper,basis,caps,old,point=setup(tmp_path)
    helper=BasisPoseNormRows(mapper,basis,caps,maximum_working_bytes=old.report['estimated_owned_array_bytes'])
    from native_basis_pose_rows import BasisPoseRows
    monkeypatch.setattr(BasisPoseRows,'evaluate',lambda *a,**k:pytest.fail('pose before vector budget'))
    with pytest.raises(ValueError,match='workspace'):helper.evaluate_vectors(point)


def test_owned_basis_and_results_are_snapshots(tmp_path):
    model,mapper,basis,caps,old,point=setup(tmp_path);helper=BasisPoseNormRows(mapper,basis,caps);before=helper.evaluate_vectors(point)
    expected=before['vectors'].copy();caps[:]=.9;basis._weights=np.zeros_like(basis.weights);before['vectors'][:]=20;before['radii'][:]=20
    after=helper.evaluate_vectors(point);assert after['vectors'].tobytes()==expected.tobytes()


@pytest.mark.parametrize('kwargs',[{'jacobian':1},{'encoded':1},{'jacobian':False,'encoded':1}])
def test_invalid_modes_reject(tmp_path,kwargs):
    model,mapper,basis,caps,old,point=setup(tmp_path)
    with pytest.raises(ValueError):BasisPoseNormRows(mapper,basis,caps).evaluate_vectors(point,**kwargs)
