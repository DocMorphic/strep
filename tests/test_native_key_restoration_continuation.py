"""Continuation uses verified edited keys while retaining the original cap epoch."""
from pathlib import Path
import sys
import pytest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_key_restoration_continuation import load
from native_key_contact_initializer import run as initialize
from native_key_interval_restoration import run as restore
from audit_native_key_restoration import run as replay
from strep import read,save,sha256
from test_native_key_contact_initializer import setup
from test_native_key_interval_restoration import recipe


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    folder=tmp_path_factory.mktemp('continuation');_,_,contacts,policy,request=setup(folder)
    gp=folder/'geometry.json';rp=folder/'initializer.json';save(gp,policy);save(rp,request)
    original=folder/'original';initialize(contacts,gp,rp,original)
    config=recipe(original);config['producer'].update(result_sha256=sha256(original/'result.json'),request_sha256=sha256(original/'request.json'))
    path=folder/'recipe.json';save(path,config);producer=folder/'producer';restore(path,producer)
    proof=folder/'replay';replay(producer,proof,sha256(producer/'result.json'),sha256(producer/'request.json'))
    return producer,proof/'result.json'


def call(source,output):
    producer,proof=source
    return load(producer,sha256(producer/'result.json'),sha256(producer/'request.json'),proof,sha256(proof),output)


def test_verified_state_reproduces_complete_clip_without_changing_source_caps(source,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    problem,value,current,receipt=call(source,tmp_path/'check')
    producer,proof=source
    np.testing.assert_array_equal(value,read(producer/'result.json')['selected_controls'])
    assert current['record']['glb_sha256']==sha256(producer/'probes/final/character.glb')
    assert receipt['original_rate_caps_preserved'] and receipt['original_initializer']==str(problem.producer)
    assert problem.producer!=producer and not receipt['quality_approved'] and not receipt['release_approved']
    with np.load(producer/'probes/final/observations.npz') as original:
        for i,cap in enumerate(problem.original_caps):np.testing.assert_array_equal(cap,original[f'rate_cap_{i}'])


@pytest.mark.parametrize('fault',['missing-replay','wrong-result','incomplete-replay','approval'])
def test_unverified_or_approved_claim_cannot_become_a_continuation(source,tmp_path,fault):
    producer,proof=source;value=read(proof);bad=tmp_path/'proof.json'
    if fault=='wrong-result':value['producer_result_sha256']='0'*64
    elif fault=='incomplete-replay':value['cases'].pop()
    elif fault=='approval':value['quality_approved']=True
    else:value['retention_history_replayed']=False
    save(bad,value)
    with pytest.raises(ValueError):load(producer,sha256(producer/'result.json'),sha256(producer/'request.json'),bad,sha256(bad),tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()
