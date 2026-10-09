import json
from pathlib import Path
from types import SimpleNamespace
import sys
import psutil
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_guarded_job as module
import audit_guarded_job as auditor
from resource_admission import ResourcePolicy


def setup(tmp_path,monkeypatch,code):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(auditor,'ROOT',tmp_path)
    monkeypatch.setattr(module,'worker_busy',lambda:False)
    worker=tmp_path/'worker.py';worker.write_text(code,encoding='utf-8')
    policy=ResourcePolicy(1024**2,stable_seconds=.01,admission_seconds=1,poll_seconds=.01,max_seconds=10)
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(available=16*1024**3))
    return worker,tmp_path/'guard',policy


def test_actual_offline_worker_literal_arguments_and_bound_terminal_output(tmp_path,monkeypatch):
    marker=tmp_path/'actual.json'
    worker,out,p=setup(tmp_path,monkeypatch,"import json,os,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(dict(args=sys.argv[2:],offline=os.environ['HF_HUB_OFFLINE'])))")
    literal='quote " and $() stay literal'
    result=module.run(worker,out,p,worker_args=[str(marker),literal])
    assert result['status']=='complete' and result['exit_code']==0 and result['worker_started']
    assert json.loads(marker.read_text())==dict(args=[literal],offline='1')
    protocol=json.loads((out/'protocol.json').read_text())
    assert literal not in (out/'protocol.json').read_text() and protocol['worker_sha256']==module.sha256(worker)
    assert all(module.sha256(out/'implementation'/n)==h for n,h in protocol['methods_sha256'].items())
    assert not result['quality_approved'] and not result['release_approved']
    replay=auditor.audit(out)
    assert replay['status']=='complete' and replay['observations_replayed']==result['resource_samples']
    before=(out/'pipeline.json').read_bytes()
    with pytest.raises(FileExistsError):module.run(worker,out,p)
    assert (out/'pipeline.json').read_bytes()==before


def test_low_headroom_defers_without_importing_or_starting_child(tmp_path,monkeypatch):
    marker=tmp_path/'should-not-exist'
    worker,out,p=setup(tmp_path,monkeypatch,f"from pathlib import Path; Path({str(marker)!r}).touch()")
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(available=p.required_available_bytes-1))
    result=module.run(worker,out,p)
    assert result['status']=='deferred' and result['reason']=='admission_timeout' and not result['worker_started']
    assert not marker.exists() and not (out/'worker.log').exists()
    assert auditor.audit(out)['status']=='deferred'


def test_busy_worker_defers_without_a_second_child(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise RuntimeError("Must not launch")')
    monkeypatch.setattr(module,'worker_busy',lambda:True)
    result=module.run(worker,out,p)
    assert result['status']=='deferred' and result['reason']=='owned_worker_busy' and not result['worker_started']


def test_revoked_headroom_before_popen_does_not_launch(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise RuntimeError("Must not launch")')
    def memory():
        state=json.loads((out/'pipeline.json').read_text()) if (out/'pipeline.json').exists() else {}
        return SimpleNamespace(available=0 if state.get('status')=='ready' else 16*1024**3)
    monkeypatch.setattr(module.psutil,'virtual_memory',memory)
    result=module.run(worker,out,p)
    assert result['reason']=='headroom_changed_before_launch' and not result['worker_started']


def test_memory_guard_kills_only_the_actual_owned_worker_tree(tmp_path,monkeypatch):
    ready=tmp_path/'ready.json'
    code="import subprocess,sys,os,time,json; from pathlib import Path; child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); Path(sys.argv[1]).write_text(json.dumps([os.getpid(),child.pid])); time.sleep(60)"
    worker,out,p=setup(tmp_path,monkeypatch,code)
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(available=0 if ready.exists() else 16*1024**3))
    result=module.run(worker,out,p,worker_args=[str(ready)])
    assert result['status']=='failed' and result['reason']=='available_ram_guard' and result['exit_code']!=0
    assert ready.exists() and all(not psutil.pid_exists(pid) for pid in json.loads(ready.read_text()))
    assert psutil.pid_exists(__import__('os').getpid())
    assert auditor.audit(out)['reason']=='available_ram_guard'


def test_time_guard_accounts_actual_exit(tmp_path,monkeypatch):
    worker,out,_=setup(tmp_path,monkeypatch,'import time;time.sleep(60)')
    p=ResourcePolicy(1024**2,stable_seconds=.01,admission_seconds=.2,poll_seconds=.01,max_seconds=.2)
    result=module.run(worker,out,p)
    assert result['status']=='failed' and result['reason']=='execution_time_guard' and result['exit_code']!=0
    assert not psutil.pid_exists(result['worker_pid'])
    assert auditor.audit(out)['reason']=='execution_time_guard'


def test_actual_worker_resident_memory_cap_is_enforced(tmp_path,monkeypatch):
    worker,out,_=setup(tmp_path,monkeypatch,'import time; block=bytearray(96*1024**2);time.sleep(60)')
    p=ResourcePolicy(1024**2,max_tree_rss_bytes=64*1024**2,stable_seconds=.01,admission_seconds=1,poll_seconds=.01,max_seconds=10)
    result=module.run(worker,out,p)
    assert result['status']=='failed' and result['reason']=='process_tree_rss_guard'
    assert result['peak_process_tree_rss_bytes']>p.max_tree_rss_bytes and result['exit_code']!=0
    assert auditor.audit(out)['reason']=='process_tree_rss_guard'


def test_self_modified_worker_is_failed_even_after_exit_zero(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,"from pathlib import Path; Path(__file__).write_text('raise SystemExit(7)')")
    with pytest.raises(ValueError):module.run(worker,out,p)
    result=json.loads((out/'pipeline.json').read_text())
    assert result['status']=='failed' and result['exit_code']==0 and result['error_type']=='ValueError'


def test_actual_nonzero_exit_is_not_a_success(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise SystemExit(7)')
    result=module.run(worker,out,p)
    assert result['status']=='failed' and result['exit_code']==7 and result['reason'] is None


def test_supervisor_exception_keeps_the_owned_workers_actual_exit(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'import time;time.sleep(60)')
    def unavailable(pid):raise RuntimeError('Process measurement unavailable')
    monkeypatch.setattr(module,'tree_rss',unavailable)
    with pytest.raises(RuntimeError,match='measurement unavailable'):module.run(worker,out,p)
    result=json.loads((out/'pipeline.json').read_text())
    assert result['status']=='failed' and result['reason']=='supervisor_exception'
    assert result['exit_code']!=0 and not psutil.pid_exists(result['worker_pid'])


def test_changed_worker_is_not_executed(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise SystemExit(0)')
    def busy():
        worker.write_text('raise SystemExit(7)');return False
    monkeypatch.setattr(module,'worker_busy',busy)
    with pytest.raises(ValueError):module.run(worker,out,p)
    result=json.loads((out/'pipeline.json').read_text())
    assert result['status']=='failed' and not result['worker_started']


def test_resealed_trace_cannot_hide_execution_before_admission(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise SystemExit(0)')
    module.run(worker,out,p)
    trace=out/'resource-samples.jsonl';rows=[json.loads(line) for line in trace.read_text().splitlines()]
    rows[0]['phase']='execution';rows[0]['tree_rss_bytes']=0
    trace.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    state=json.loads((out/'pipeline.json').read_text());state['resource_trace_sha256']=module.sha256(trace)
    module.save(out/'pipeline.json',state)
    with pytest.raises(ValueError):auditor.audit(out)


def test_modified_archived_worker_rejected(tmp_path,monkeypatch):
    worker,out,p=setup(tmp_path,monkeypatch,'raise SystemExit(0)');module.run(worker,out,p)
    (out/'implementation/worker-source.py').write_text('raise SystemExit(7)')
    with pytest.raises(ValueError):auditor.audit(out)
