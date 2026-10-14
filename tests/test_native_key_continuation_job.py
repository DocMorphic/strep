"""Public continuation preserves original references and audits the edited start."""
from pathlib import Path
import copy
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_key_continuation_job as job
from audit_native_key_continuation_job import run as replay
from strep import read,save,sha256
from test_native_key_restoration_continuation import source


def recipe(source):
    producer,proof=source
    return dict(schema=job.SCHEMA,parent=dict(path=str(producer),result_sha256=sha256(producer/'result.json'),
        request_sha256=sha256(producer/'request.json'),replay=str(proof),replay_sha256=sha256(proof)),
        iterations=1,trust=.02,difference_step=.001,backoffs=2,maximum_seconds=600.)


@pytest.fixture(scope='module')
def completed(source,tmp_path_factory):
    folder=tmp_path_factory.mktemp('continuation-job');path=folder/'recipe.json';save(path,recipe(source))
    output=folder/'job';job.run(path,output)
    return output


def test_public_command_preserves_complete_clip_caps_and_replays_lineage(completed,tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    result=read(completed/'result.json');request=read(completed/'request.json')
    parent=Path(request['recipe']['parent']['path'])
    assert result['history']==[] and result['stop_reason']=='sampled_conditions_pass'
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert sha256(completed/'probes/start/character.glb')==sha256(parent/'probes/final/character.glb')==sha256(completed/'probes/final/character.glb')
    with np.load(parent/'probes/final/observations.npz') as before,np.load(completed/'probes/final/observations.npz') as after:
        for name in before.files:np.testing.assert_array_equal(before[name],after[name])
    proof=replay(completed,tmp_path/'replay',sha256(completed/'result.json'),sha256(completed/'request.json'))
    assert proof['schema']=='strep-native-key-continuation-job-replay-v1'
    assert proof['retention_history_replayed'] and proof['original_reference_unchanged'] and not proof['optimizer_executed']
    assert [c['label'] for c in proof['cases']]==['start','final']


@pytest.mark.parametrize('fault',['receipt','result','request','approval'])
def test_changed_binding_or_approval_rejects_before_replay(completed,tmp_path,fault):
    # Restore every mutation so module-scoped evidence remains immutable to other tests.
    target=completed/('probes/start/continuation.json' if fault=='receipt' else 'request.json' if fault=='request' else 'result.json')
    old=target.read_bytes();rd=sha256(completed/'result.json');qd=sha256(completed/'request.json')
    try:
        value=read(target)
        if fault=='approval':value['quality_approved']=True
        else:value['unexpected']='changed'
        save(target,value)
        if fault=='approval':rd=sha256(completed/'result.json')
        with pytest.raises(ValueError):replay(completed,tmp_path/'rejected',rd,qd)
        assert not (tmp_path/'rejected').exists()
    finally:target.write_bytes(old)


@pytest.mark.parametrize('field,value',[
    ('iterations',True),('iterations',5),('trust',.020001),('difference_step',0),
    ('maximum_seconds',751),('backoffs',0),('schema','strep-native-key-verified-continuation-trial-v1')])
def test_invalid_effort_or_private_trial_rejects(source,field,value):
    payload=recipe(source);payload[field]=value
    with pytest.raises(ValueError):job.validate(payload)


def test_continuation_cannot_change_active_keys_or_original_reference(source):
    payload=recipe(source);payload['active_keys']=[1,2]
    with pytest.raises(ValueError):job.validate(payload)
    payload=recipe(source);payload['parent']['replay_sha256']='x'*64
    with pytest.raises(ValueError):job.validate(payload)


def test_iteration_starts_from_saved_controls_and_keeps_rejected_probe(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    parent=tmp_path/'parent';parent.mkdir();save(parent/'result.json',{});save(parent/'request.json',{});save(parent/'replay.json',{})
    payload=recipe((parent,parent/'replay.json'));path=tmp_path/'recipe.json';save(path,payload)
    class Problem:
        initial=np.array([0.]);lower=np.array([-1.]);upper=np.array([1.]);size=1;pins={}
        def linearize(self,value,worlds,radius,step):
            np.testing.assert_array_equal(value,[.25])
            return type('System',(),dict(vectors=np.array([[1.,0.,0.]]),caps=np.array([1.]),scales=np.array([1.])))(),sparse.eye(3,1),dict(hard_rows=0)
        def check(self):np.testing.assert_array_equal(self.initial,[0.])
    problem=Problem();calls=[]
    def evaluate(problem,value,folder):
        folder=Path(folder);folder.mkdir(parents=True);calls.append((folder.name,value.copy()))
        # Full step creates a new failure; half step repairs the existing failure.
        full=np.array([1. if value[0]<=.25 else .5,1. if value[0]>.325 else 0.])
        record=dict(label=folder.name,controls=value.tolist(),decoded_prefix_pass=True,score=[float(full.max()),float(full@full),int((full>0).sum())],
            sampled_conditions_pass=False,original_rate_failures=1,floor_failures=0)
        return dict(record=record,worlds=np.zeros((1,1,4,4)),full=full,geometry_identity=['existing','previously-passing'],geometry_face_state={})
    def start(recipe,path,output):
        current=evaluate(problem,np.array([.25]),output);save(Path(output)/'continuation.json',{})
        return problem,np.array([.25]),current,{}
    monkeypatch.setattr(job,'start',start);monkeypatch.setattr(job,'evaluate',evaluate)
    monkeypatch.setattr(job,'direction',lambda *a,**k:(np.array([.1]),dict(status='test-direction')))
    result=job.run(path,tmp_path/'output')
    assert [c[0] for c in calls]==['start','1-0','1-1','final']
    assert result['history'][0]['probes'][0]['accepted'] is False
    assert result['history'][0]['accepted_fraction']==.5
    np.testing.assert_array_equal(result['selected_controls'],[.3])
    np.testing.assert_array_equal(problem.initial,[0.])
    assert result['original_selected'] and not result['quality_approved']
