"""Public restoration replay binds original inputs and complete export decisions."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_key_contact_initializer import run as initialize
from native_key_interval_restoration import run as restore
from audit_native_key_restoration import run as replay
from strep import read,save,sha256
from test_native_key_contact_initializer import setup
from test_native_key_interval_restoration import recipe


@pytest.fixture(scope='module')
def producer(tmp_path_factory):
    folder=tmp_path_factory.mktemp('restoration-replay');_,_,contacts,policy,request=setup(folder)
    gp=folder/'geometry.json';rp=folder/'initializer.json';save(gp,policy);save(rp,request)
    original=folder/'original';initialize(contacts,gp,rp,original)
    payload=recipe(original);payload['producer'].update(result_sha256=sha256(original/'result.json'),request_sha256=sha256(original/'request.json'))
    config=folder/'recipe.json';save(config,payload);output=folder/'producer';restore(config,output)
    return output


def test_complete_public_replay_does_not_inherit_human_or_release_approval(producer,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    result=replay(producer,tmp_path/'replay',sha256(producer/'result.json'),sha256(producer/'request.json'))
    assert result['retention_history_replayed'] and result['sampled_conditions_pass'] and len(result['cases'])==2
    assert not result['optimizer_executed'] and not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('kind',['result','request'])
def test_trusted_input_change_rejects_before_replay(producer,tmp_path,kind):
    result=sha256(producer/'result.json');request=sha256(producer/'request.json')
    if kind=='result':result='0'*64
    else:request='0'*64
    with pytest.raises(ValueError,match='result/request changed'):replay(producer,tmp_path/'bad',result,request)
    assert not (tmp_path/'bad').exists()


@pytest.mark.parametrize('fault',['approval','summary','omitted-final'])
def test_rehashed_claims_reject_without_a_receipt(producer,tmp_path,monkeypatch,fault):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock');path=producer/'result.json';original=path.read_bytes()
    try:
        value=read(path)
        if fault=='approval':value['quality_approved']=True
        elif fault=='summary':value['original_rate_failures']=1
        else:value['probes'].pop()
        save(path,value)
        with pytest.raises(ValueError):replay(producer,tmp_path/'rehashed',sha256(path),sha256(producer/'request.json'))
        assert not (tmp_path/'rehashed/result.json').exists()
    finally:path.write_bytes(original)
