import sys
from pathlib import Path
import copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from action_studio_server import validate_contact_request,allowed_file
from strep import ROOT,read


def request():
    return dict(collection='body-contact-v1',take_id='get-up-seed-11',contact_spec=read(ROOT/'benchmarks/contact-authoring-example-v1.json'))


def test_valid_contact_source_resolves_to_canonical_take():
    source,spec=validate_contact_request(request())
    assert source==ROOT/'reports/body-contact-v1/takes/get-up-seed-11'
    assert spec['frame_count']==180


@pytest.mark.parametrize('field,value',[
    ('collection','../../models'),('collection','body-contact-v1/../../models'),
    ('take_id','../get-up-seed-11'),('take_id','missing-take'),
    ('collection','action-coverage-v1'),('collection','body-contact-v1-fake'),
])
def test_unavailable_or_ineligible_source_rejected(field,value):
    payload=request();payload[field]=value
    with pytest.raises(ValueError):validate_contact_request(payload)


def test_mismatched_constraint_timing_rejected():
    payload=request();payload['contact_spec']['frame_count']=2
    with pytest.raises(ValueError):validate_contact_request(payload)


def test_contact_jobs_cannot_expose_arbitrary_project_files():
    assert allowed_file('/files/contact-jobs/example/result/takes/motion/soma.glb')
    assert allowed_file('/files/contact-jobs/../../../models/manifest.json') is None
    assert allowed_file('/files/contact-jobs-fake/example/summary.json') is None
    assert allowed_file('/files/contact-jobs/example/supervisor.log') is None


def test_contact_job_keeps_live_worker_state(tmp_path):
    import psutil
    from contact_edit_job import observed_state
    from strep import save
    p=psutil.Process();save(tmp_path/'worker.json',dict(pid=p.pid,created_at=p.create_time()))
    save(tmp_path/'pipeline.json',dict(status='processing'))
    assert observed_state(tmp_path)['status']=='processing'


def test_reused_pid_does_not_keep_a_dead_job_running(tmp_path):
    import psutil
    from contact_edit_job import observed_state
    from strep import save
    p=psutil.Process();save(tmp_path/'worker.json',dict(pid=p.pid,created_at=p.create_time()-10))
    save(tmp_path/'pipeline.json',dict(status='processing'))
    assert observed_state(tmp_path)['status']=='failed'
