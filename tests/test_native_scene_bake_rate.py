"""Mocked transport tests; actual engine fidelity requires the separate study."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_scene_engine as producer
from verify_native_scene_engine import run as replay
from strep import read,save
from test_verify_native_scene_engine import bundle


@pytest.mark.parametrize('rate',[60.,120.,240.])
def test_rate_survives_request_engine_result_and_observation_replay(tmp_path,monkeypatch,rate):
    contacts,policy,output=bundle(tmp_path,monkeypatch,bake_fps=rate)
    for filename in ('request.json','engine-output.json','result.json'):
        assert read(output/filename)['import_bake_fps']==rate
    result=replay(contacts,policy,output,tmp_path/'replay')
    assert result['import_bake_fps']==rate and result['all_replayed_observations_exact']
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('rate',[True,False,'60',float('nan'),float('inf'),0,30.1,60.000001,-60])
def test_invalid_rate_rejected_before_creating_output_or_reading_assets(tmp_path,rate):
    output=tmp_path/'never-created'
    with pytest.raises(ValueError,match='Import bake rate'):
        producer.run(tmp_path/'missing-contacts',output,import_bake_fps=rate)
    assert not output.exists()


def test_native_authoring_keeps_original_import_setting(tmp_path):
    output=tmp_path/'never-created'
    with pytest.raises(ValueError,match='Native authoring retains'):
        producer.run(tmp_path/'missing-contacts',output,playback_mode='native-authoring',import_bake_fps=60.)
    assert not output.exists()


def test_wrong_executed_rate_cannot_be_recorded_as_complete(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='Executed import bake rate differs'):
        bundle(tmp_path,monkeypatch,bake_fps=60.,echo_bake_fps=30.)
    assert read(tmp_path/'producer/pipeline.json')['status']=='failed'
    assert not (tmp_path/'producer/result.json').exists()


def test_replay_rejects_changed_rate_metadata(tmp_path,monkeypatch):
    contacts,policy,output=bundle(tmp_path,monkeypatch,bake_fps=60.)
    changed=read(output/'result.json');changed['import_bake_fps']=30.;save(output/'result.json',changed)
    with pytest.raises(ValueError,match='Recorded import bake rate differs'):
        replay(contacts,policy,output,tmp_path/'replay')
