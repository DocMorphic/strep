"""Cumulative multi-window edits retain original source, locks and saved bytes."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from native_key_basis import NativeKeyBasis
from native_local_basis import localized_native_basis
from native_local_warm_start import localized_native_basis_from_controls
from test_native_key_basis import declaration


def original():
    seed=np.zeros((7,2,3));seed[:,:,1]=-0.
    return NativeKeyBasis(**declaration(seed_controls=seed))


def test_a_previous_search_anchor_can_be_edited_without_unlocking_original_keys():
    reference=original()
    first,_=localized_native_basis_from_controls(reference,reference._seed,0,1,2)
    value=np.linspace(-.03,.04,first.size);warm=first.export_coefficients(value)
    # Key2 was a temporary search anchor, not an original author lock.
    with pytest.raises(ValueError,match='frozen'):
        localized_native_basis(first,value,1,2,3)
    second,report=localized_native_basis_from_controls(reference,warm,1,2,3)
    assert second.coefficients(np.zeros(second.size)).tobytes()==warm.tobytes()
    changed=second.export_coefficients(np.full(second.size,.02))
    assert changed[2].tobytes()!=warm[2].tobytes()
    assert changed[1].tobytes()==warm[1].tobytes()
    assert changed[[0,3,6]].tobytes()==reference._seed[[0,3,6]].tobytes()
    assert report['original_frozen_keys']==[0,3,6]
    assert report['previous_search_anchors_not_inferred_as_original_locks']
    assert report['cumulative_balls_not_reset'] and second.size==6


def test_all_grid_and_endpoint_bytes_include_unfrozen_signed_zeros():
    reference=original();warm=reference._seed.copy();warm[4,1,0]=.125
    local,report=localized_native_basis_from_controls(reference,warm,3,5,6)
    zero=np.zeros(local.size)
    assert local.coefficients(zero).tobytes()==warm.tobytes()
    assert local.endpoint_map(zero,list(range(7)),jacobian=False)[0].tobytes()==warm.tobytes()
    assert np.signbit(local.coefficients(zero)[4,0,1])
    warm[:]=.25;report['original_frozen_keys'].clear()
    assert local.coefficients(zero)[4,1,0]==.125
    assert local.report['frozen_keys']==[0,3,6]


def test_combined_cumulative_edit_cannot_treat_an_increment_as_a_new_source():
    reference=original();warm=reference._seed.copy();warm[5,0,0]=.8
    local,_=localized_native_basis_from_controls(reference,warm,3,5,6)
    value=np.zeros(local.size);value[0]=.3
    assert local.coefficients(value)[5,0,0]==1.1
    with pytest.raises(ValueError,match='not clipped'):
        local.export_coefficients(value)
    with pytest.raises(ValueError,match='ball|seed grid'):
        localized_native_basis_from_controls(reference,local.coefficients(value),3,5,6)


@pytest.mark.parametrize('case',['shape','boolean','complex','nan','infinity','overlong_dtype','out_of_ball','frozen_value','frozen_signed_zero'])
def test_invalid_or_unapproved_cumulative_grids_are_rejected(case):
    reference=original();warm=reference._seed.copy()
    if case=='shape':warm=warm[:-1]
    elif case=='boolean':warm=warm.astype(bool)
    elif case=='complex':warm=warm.astype(complex)
    elif case=='nan':warm[4,0,0]=np.nan
    elif case=='infinity':warm[4,0,0]=np.inf
    elif case=='overlong_dtype':warm=warm.astype(object)
    elif case=='out_of_ball':warm[4,0]=[.8,.8,0]
    elif case=='frozen_value':warm[3,0,0]=.001
    elif case=='frozen_signed_zero':warm[3,0,1]=0.
    with pytest.raises(ValueError):
        localized_native_basis_from_controls(reference,warm,3,5,6)


@pytest.mark.parametrize('field',['clock','seed'])
def test_changed_original_reference_bindings_are_rejected(field):
    reference=original();warm=reference._seed.copy();array=getattr(reference,'_'+field)
    array.setflags(write=True);array.flat[1]+=.001;array.setflags(write=False)
    with pytest.raises(ValueError,match='binding changed'):
        localized_native_basis_from_controls(reference,warm,3,5,6)


def test_original_reference_and_original_frozen_window_are_required():
    reference=original();local,_=localized_native_basis_from_controls(reference,reference._seed,3,5,6)
    for wrong in [object(),local]:
        with pytest.raises(ValueError,match='original NativeKeyBasis'):
            localized_native_basis_from_controls(wrong,reference._seed,3,5,6)
    with pytest.raises(ValueError,match='frozen'):
        localized_native_basis_from_controls(reference,reference._seed,0,4,6)


def test_all_columns_keep_complete_native_ball_derivatives_after_two_windows():
    reference=original();first,_=localized_native_basis_from_controls(reference,reference._seed,0,1,2)
    warm=first.export_coefficients(np.linspace(-.04,.06,first.size))
    second,_=localized_native_basis_from_controls(reference,warm,1,2,3);point=np.linspace(-.01,.02,second.size)
    values,jac=second.native_chunk(point,0,7)
    assert jac.shape==(14,6) and values.tobytes()==(1-np.sum(second.coefficients(point)**2,axis=2)).ravel().tobytes()
    for column in range(second.size):
        delta=np.eye(second.size)[column]*1e-6
        finite=(second.native_chunk(point+delta,0,7,jacobian=False)[0]-second.native_chunk(point-delta,0,7,jacobian=False)[0])/2e-6
        np.testing.assert_allclose(jac[:,column],finite,atol=2e-10,rtol=0)


@pytest.mark.parametrize('mode',['start','native','subkey','end'])
def test_original_actor_caps_and_glb_baseline_survive_repeated_warm_starts(tmp_path,mode):
    from test_native_basis_pose_rows import setup
    from native_key_pose_map import KeyPoseMap
    from native_basis_pose_rows import BasisPoseRows
    from native_key_contact_initializer import encode
    model,mapper,reference,caps,before,point=setup(tmp_path,mode)
    base=reference.export_coefficients(point);first,_=localized_native_basis_from_controls(reference,base,0,2,4)
    first_point=np.linspace(-.005,.006,first.size);warm=first.export_coefficients(first_point)
    second,report=localized_native_basis_from_controls(reference,warm,3,4,7)
    old_mapper=KeyPoseMap(model,mapper.time_s,base,list(mapper.pairs));old=BasisPoseRows(old_mapper,first,caps)
    new_mapper=KeyPoseMap(model,mapper.time_s,warm,list(mapper.pairs));new=BasisPoseRows(new_mapper,second,caps)
    assert new_mapper.model.actor is mapper.model.actor
    for name in ['original_quaternions','caps','source']:
        assert getattr(new_mapper,name).tobytes()==getattr(mapper,name).tobytes()
    for encoded in [False,True]:
        a=old.evaluate(first_point,jacobian=False,encoded=encoded);b=new.evaluate(np.zeros(second.size),jacobian=False,encoded=encoded)
        assert a['world'].tobytes()==b['world'].tobytes() and a['margins'].tobytes()==b['margins'].tobytes()
    actor=model.actor;channels=[next(c for c in actor['sampler'].channels if c[:2]==(node,'rotation')) for node in model.nodes]
    a=tmp_path/'old.glb';b=tmp_path/'new.glb'
    encode(actor['rig'],actor['animation_index'],list(model.nodes),channels,warm,np.degrees(model.caps),a)
    encode(actor['rig'],actor['animation_index'],list(model.nodes),channels,second.export_coefficients(np.zeros(second.size)),np.degrees(model.caps),b)
    assert a.read_bytes()==b.read_bytes() and report['source_actor_caps_and_provenance_owned_by_caller']
