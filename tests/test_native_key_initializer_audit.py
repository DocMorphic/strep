"""Replay binds original authoring as well as output; rehashed claims cannot pass."""
from pathlib import Path
import json,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from audit_native_key_initializer import run as audit,bound
from native_key_contact_initializer import run as initialize
from strep import read,save,sha256
from test_native_key_contact_initializer import setup


@pytest.fixture(scope='module')
def producer(tmp_path_factory):
    folder=tmp_path_factory.mktemp('key-replay');_,_,contacts,policy,request=setup(folder)
    gp=folder/'geometry.json';rp=folder/'permissions.json';save(gp,policy);save(rp,request)
    initialize(contacts,gp,rp,folder/'producer')
    return folder/'producer'


def test_fresh_complete_replay_preserves_false_approval_and_original_clock(producer,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    result=audit(producer,tmp_path/'replay',sha256(producer/'result.json'),sha256(producer/'request.json'))
    assert result['sampled_conditions_pass'] and result['exact_glb_and_complete_arrays']
    assert not result['optimizer_executed'] and not result['quality_approved'] and not result['release_approved']
    assert result['source_request_sha256']==sha256(producer/'request.json')


@pytest.mark.parametrize('target',['request','result'])
def test_expected_original_binding_rejects_before_replay(producer,tmp_path,target):
    request=sha256(producer/'request.json');result=sha256(producer/'result.json')
    if target=='request':request='0'*64
    else:result='0'*64
    with pytest.raises(ValueError,match='binding changed'):audit(producer,tmp_path/'output',result,request)
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('change',['approval','unknown-certification','authoring'])
def test_rehashed_scope_or_original_authoring_claim_rejects(producer,change):
    path=producer/('request.json' if change=='authoring' else 'result.json');original=path.read_bytes()
    try:
        value=read(path)
        if change=='approval':value['quality_approved']=True
        elif change=='unknown-certification':value['continuous_collision_verified']=True
        else:value['request']['maximum_joint_displacement_m']=.2
        save(path,value)
        with pytest.raises(ValueError):bound(producer,sha256(producer/'result.json'),sha256(producer/'request.json'))
    finally:path.write_bytes(original)


def test_rehashed_numeric_decision_disagrees_with_complete_fresh_replay(producer,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock');path=producer/'result.json';original=path.read_bytes()
    try:
        value=read(path);value['failed_original_rate_rows']=1;value['original_motion_caps_pass']=False;value['sampled_conditions_pass']=False;save(path,value)
        with pytest.raises(ValueError,match='Typed proposal decision'):audit(producer,tmp_path/'false-result',sha256(path),sha256(producer/'request.json'))
        assert not (tmp_path/'false-result/result.json').exists()
    finally:path.write_bytes(original)


def test_changed_complete_observation_rejects_without_receipt(producer,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock');path=producer/'contact-observations.npz';original=path.read_bytes()
    try:
        with np.load(path) as data:arrays={n:data[n].copy() for n in data.files}
        arrays[next(n for n in arrays if n.endswith('_error_m'))].flat[0]+=.001
        np.savez_compressed(path,**arrays)
        with pytest.raises(ValueError,match='numeric observation changed'):audit(producer,tmp_path/'false-array',sha256(producer/'result.json'),sha256(producer/'request.json'))
        assert not (tmp_path/'false-array/result.json').exists()
    finally:path.write_bytes(original)
