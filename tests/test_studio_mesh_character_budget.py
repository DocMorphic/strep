"""Saved processing budgets reach the supervisor without relaxing memory caps."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_mesh_character_job as jobs
from strep import read,save


def request():
    draft={'scene':{'actors':{'A':{}}}}
    return dict(schema='strep-studio-mesh-character-v1',scene_job='a'*32,scene_result_sha256='b'*64,
        mesh_request={'draft':copy.deepcopy(draft)},
        correction=dict(schema='strep-studio-native-scene-fit-v1',draft=draft,actors={'A':{}},options={'iterations':8},resume_from=None),
        editable_clip_boundaries={'A':[]},acknowledge_changed_boundary_compatibility=False)


@pytest.fixture
def store(tmp_path,monkeypatch):
    monkeypatch.setattr(jobs,'ROOT',tmp_path)
    (tmp_path/'scripts').mkdir();(tmp_path/'scripts/method.py').write_text('# fixed method\n')
    return tmp_path


@pytest.mark.parametrize('seconds',[None,900,1800,3600])
def test_bound_request_reaches_actual_supervisor_policy(store,monkeypatch,seconds):
    import run_guarded_job
    import audit_guarded_job
    payload=request()
    if seconds is not None:payload['max_runtime_seconds']=seconds
    folder=jobs.prepare(payload)
    assert jobs.verify_prepared(folder)==payload
    recorded=[]
    def run(worker,output,policy,*,worker_args):
        recorded.append(policy)
        assert worker_args==[str(folder),'--worker']
        assert policy.max_seconds==(seconds or 900)
        assert policy.expected_rss_bytes==policy.max_tree_rss_bytes==512*1024**2
        assert policy.min_available_bytes==600*1024**2
        assert policy.stable_seconds==15 and policy.admission_seconds==600
        return {'status':'complete'}
    monkeypatch.setattr(run_guarded_job,'run',run)
    monkeypatch.setattr(audit_guarded_job,'audit',lambda _:dict(status='complete'))
    monkeypatch.setattr(sys,'argv',['worker',str(folder)])
    assert jobs.main()==0 and len(recorded)==1
    assert read(folder/'request.json')==payload


@pytest.mark.parametrize('seconds',[True,False,0,-900,901,3601,3600.,'3600',None,float('inf')])
def test_unsupported_or_non_integer_budgets_are_rejected_before_queue(store,seconds):
    payload=request();payload['max_runtime_seconds']=seconds
    with pytest.raises(ValueError,match='processing time'):jobs.prepare(payload)
    assert not (store/'reports').exists()


def test_changed_budget_invalidates_saved_request(store):
    payload=request();payload['max_runtime_seconds']=900
    folder=jobs.prepare(payload);payload['max_runtime_seconds']=3600;save(folder/'request.json',payload)
    with pytest.raises(ValueError,match='Queued correction changed'):jobs.verify_prepared(folder)


@pytest.mark.parametrize('seconds',[None,3600])
def test_status_uses_saved_job_budget_not_current_editor(store,seconds):
    payload=request()
    if seconds is not None:payload['max_runtime_seconds']=seconds
    folder=jobs.prepare(payload);save(folder/'guard/pipeline.json',dict(status='deferred',reason='owned_worker_busy'))
    response=jobs.review(folder.name)
    assert response['max_runtime_seconds']==(seconds or 900)
    assert response['status']=='deferred' and response['original_selected'] and not response['quality_approved']
