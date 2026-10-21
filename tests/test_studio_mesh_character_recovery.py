"""Saved Studio requests continue through optimizer and package interruptions."""
import copy
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import zipfile
import pytest
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_studio_server as server
import action_worker_lock
import studio_mesh_character_job as jobs
import studio_mesh_character_recovery_job as recovery
import studio_mesh_character_preview as preview
from strep import read,save,sha256
from test_studio_mesh_character_budget import request,store
from test_studio_mesh_scene import authored
from test_studio_mesh_character import saved
from test_studio_prop_routes import handler


def queued():
    payload=request();payload.update(recoverable=True,max_runtime_seconds=3600)
    folder=jobs.prepare(payload);attempt=recovery.prepare_attempt(folder)
    return folder,attempt,payload


def test_nested_artifacts_work_beyond_windows_path_limit_and_stay_bounded(store):
    folder,attempt,_=queued()
    ordinary=store/'reports'/jobs.NAMESPACE/folder.name
    assert jobs.absolute(ordinary)==folder and jobs.absolute(folder)==folder
    assert jobs.verify_prepared(ordinary)==read(folder/'request.json')
    path=folder/('a'*90)/('b'*90)/'observations.bin'
    assert len(str(path))>260
    path.parent.mkdir(parents=True);path.write_bytes(b'exact saved observations')
    bindings=recovery.file_bindings(folder,[path.parent])
    assert bindings=={path.relative_to(folder).as_posix():sha256(path)}
    recovery.verify_files(folder,bindings)
    for relative in ['../outside.bin','nested/../../outside.bin']:
        with pytest.raises(ValueError,match='escapes'):recovery.local(folder,relative)
    with pytest.raises(ValueError,match='Exact correction job'):
        recovery.request_for(store/'elsewhere'/folder.name)


def stopped(attempt,reason='execution_time_guard'):
    save(attempt/'guard/pipeline.json',dict(status='failed',reason=reason))


@pytest.mark.parametrize('value',[None,0,1,'true',[]])
def test_recovery_choice_is_explicit_boolean(store,value):
    payload=request();payload['recoverable']=value
    with pytest.raises(ValueError,match='recovery choice'):jobs.prepare(payload)
    assert not (store/'reports').exists()


def test_continue_retains_previous_attempt_and_saved_budget(store):
    folder,first,payload=queued();save(first/'guard/pipeline.json',dict(status='deferred',reason='owned_worker_busy'))
    before={str(path):sha256(path) for path in first.rglob('*') if path.is_file()}
    report=jobs.review(folder.name);assert report['can_continue'] and report['max_runtime_seconds']==3600
    with pytest.raises(ValueError,match='progress changed'):recovery.prepare_attempt(folder,{**report['continuation'],'max_runtime_seconds':900})
    second=recovery.prepare_attempt(folder,report['continuation'])
    assert second!=first and read(second/'request.json')['previous']==first.name
    assert read(second/'request.json')['max_runtime_seconds']==3600 and read(folder/'request.json')==payload
    assert all(sha256(path)==digest for path,digest in before.items())
    with pytest.raises(ValueError,match='Wait'):recovery.prepare_attempt(folder,report['continuation'])


def test_live_recorded_owner_prevents_duplicate_continuation(store):
    folder,attempt,_=queued();stopped(attempt)
    save(attempt/'supervisor.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    assert not jobs.review(folder.name)['can_continue']
    with pytest.raises(ValueError,match='Wait'):recovery.prepare_attempt(folder,{})
    assert len(list((folder/'attempts').iterdir()))==1


def test_startup_failure_is_not_hidden_by_abandoned_admission_record(store):
    folder,attempt,_=queued()
    save(attempt/'guard/pipeline.json',dict(status='waiting_resources'))
    save(attempt/'startup.json',dict(status='failed',reason='Supervisor owner record could not be written'))
    report=jobs.review(folder.name)
    assert report['status']=='failed' and report['can_continue']
    assert 'owner record' in report['error']
    save(attempt/'supervisor.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    assert not jobs.review(folder.name)['can_continue']


def test_request_or_method_changes_disable_resume(store):
    folder,attempt,payload=queued();stopped(attempt)
    (store/'scripts/method.py').write_text('# changed\n')
    report=jobs.review(folder.name);assert not report['can_continue'] and 'Implementation changed' in report['continuation_error']
    with pytest.raises(ValueError,match='Implementation changed'):recovery.prepare_attempt(folder,{})
    payload['max_runtime_seconds']=900;save(folder/'request.json',payload)
    with pytest.raises(ValueError,match='request changed'):jobs.review(folder.name)


@pytest.mark.parametrize('seconds',[900,1800,3600])
def test_attempt_supervisor_uses_immutable_budget_and_existing_memory_policy(store,monkeypatch,seconds):
    import run_guarded_job,audit_guarded_job
    payload=request();payload.update(recoverable=True,max_runtime_seconds=seconds)
    folder=jobs.prepare(payload);attempt=recovery.prepare_attempt(folder);seen=[]
    def run(worker,output,policy,*,worker_args):
        assert output==attempt/'guard' and worker_args==[str(folder),attempt.name,'--worker']
        assert policy.max_seconds==seconds and policy.expected_rss_bytes==policy.max_tree_rss_bytes==512*1024**2
        assert policy.min_available_bytes==600*1024**2 and policy.stable_seconds==15 and policy.admission_seconds==600
        seen.append(policy);return dict(status='deferred')
    monkeypatch.setattr(run_guarded_job,'run',run);monkeypatch.setattr(audit_guarded_job,'audit',lambda _:dict(status='deferred'))
    monkeypatch.setattr(sys,'argv',['worker',str(folder),attempt.name])
    assert recovery.main()==2 and len(seen)==1


def test_continue_route_retains_origin_and_current_job_exclusion(store,monkeypatch):
    folder,attempt,_=queued();stopped(attempt);ticket=jobs.review(folder.name)['continuation'];calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(recovery,'launch',lambda target,payload:calls.append((target,payload)) or object())
    path=f'/api/mesh-character-jobs/{folder.name}/continue'
    def send(**headers):
        h=handler(path,json.dumps(ticket).encode(),**headers);h.server.job_lock=threading.Lock();h.server.worker=None
        h.do_POST();return h
    assert send(Origin='https://elsewhere.test').responses[0][0]==403 and not calls
    h=send();assert h.responses[0][0]==202 and calls==[(folder,ticket)]
    monkeypatch.setattr(server,'worker_busy',lambda:True)
    assert send().responses[0][0]==409 and len(calls)==1


def test_queue_and_status_have_no_numerical_imports_in_fresh_process():
    scripts=Path(recovery.__file__).parent
    program=f'''import sys,importlib.abc
sys.path.insert(0,{str(scripts)!r})
class NoNumerics(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('numpy','scipy','torch'):raise AssertionError(fullname)
sys.meta_path.insert(0,NoNumerics())
import studio_mesh_character_recovery_job,studio_mesh_character_routes
'''
    result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_worker_loads_backend_inside_lock_then_limits_real_pools(tmp_path):
    scripts=Path(recovery.__file__).parent
    program=f'''import sys,importlib.abc
from pathlib import Path
from contextlib import contextmanager
sys.path.insert(0,{str(scripts)!r})
import studio_mesh_character_recovery_job as job,action_worker_lock
held=False
@contextmanager
def lock():
 global held
 assert not held
 held=True
 try:yield
 finally:held=False
action_worker_lock.worker_lock=lock
class LockedNumerics(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('numpy','scipy'):assert held,fullname
sys.meta_path.insert(0,LockedNumerics())
folder=Path({str(tmp_path)!r})
job.verify_attempt=lambda *args:({{}},folder,{{}})
seen=[]
def inspect(*args):
 assert held
 from threadpoolctl import threadpool_info
 pools=[p for p in threadpool_info() if p['user_api']=='blas']
 assert pools and all(p['num_threads']==1 for p in pools),pools
 seen.extend(pools)
job.execute=inspect
sys.argv=['worker',str(folder),'a'*32,'--worker']
assert job.main()==0 and seen and not held
'''
    result=subprocess.run([sys.executable,'-c',program],env=dict(os.environ,OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2'),
        capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('cut',['geometry','packaging'])
@pytest.mark.parametrize('clock',['compact','native-stress'])
def test_real_saved_job_continues_after_interruption_and_serves_bound_previews(saved,monkeypatch,cut,clock):
    if clock=='native-stress' and os.environ.get('STREP_RECOVERY_STRESS')!='1':
        pytest.skip('Explicit 969-sample stress run; retain the full clock and use guarded attempts')
    import native_mesh_character_recovery as optimizer
    from native_mesh_prop_scene import MeshPropScene
    source,payload=saved;payload=copy.deepcopy(payload);payload['recoverable']=True
    if clock=='compact':
        # A separately authored scene for lifecycle CI; never change an existing
        # saved job's clock or treat these three times as full-motion evidence.
        import studio_mesh_scene_job as scenes
        mesh=payload['mesh_request'];mesh['draft']['geometry']['clock']=dict(mode='explicit',times_s=[0.,1.,2.])
        payload['correction']['draft']=copy.deepcopy(mesh['draft'])
        payload['correction']['options']['iterations']=1
        actor=source/'package/actors/A.glb'
        source=scenes.prepare(mesh);scenes.execute(source,lambda _:actor)
        save(source/'guard/pipeline.json',dict(status='complete'))
        payload.update(scene_job=source.name,scene_result_sha256=sha256(source/'package/result.json'))
    folder=jobs.prepare(payload);first=recovery.prepare_attempt(folder)
    monkeypatch.setattr(action_worker_lock,'ROOT',folder/'test-lock')
    original_bytes={str(path):sha256(path) for path in source.rglob('*') if path.is_file()}
    if cut=='geometry':
        real=MeshPropScene.geometry;calls=[]
        def interrupted(self,*args,**kwargs):
            calls.extend(kwargs.get('sample_indices',[]))
            if kwargs.get('sample_indices')==[1]:raise RuntimeError('Interrupted full geometry')
            return real(self,*args,**kwargs)
        monkeypatch.setattr(MeshPropScene,'geometry',interrupted)
    else:
        real=jobs.preview_package
        def interrupted(*args):
            real(*args);raise RuntimeError('Interrupted package assembly')
        monkeypatch.setattr(jobs,'preview_package',interrupted)
    with pytest.raises(RuntimeError,match='Interrupted'):recovery.execute(folder,first.name)
    assert not (folder/'publication.json').exists()
    pointer=read(folder/'optimizer-state.json');fit=folder/pointer['directory'];receipt=read(fit/'progress.json')
    state=read(fit/receipt['checkpoint'])
    bound=read(fit/'request.json')['original_signature']['geometry_clock_s']
    assert len(bound)==(3 if clock=='compact' else 969)
    if cut=='geometry':
        assert state['phase']=='geometry'
        journal=fit/state['pending']['audit']/'geometry-journal'
        assert read(journal/'progress.json')['completed_samples']==1
        monkeypatch.setattr(MeshPropScene,'geometry',real)
    else:
        assert state['phase']=='complete' and len(list((folder/'publications').iterdir()))==1
        monkeypatch.setattr(jobs,'preview_package',real)
        monkeypatch.setattr(optimizer,'advance',lambda *args:pytest.fail('Completed optimizer must not run again for packaging'))
    stopped(first);old_guard=sha256(first/'guard/pipeline.json')
    reviewed=jobs.review(folder.name);assert reviewed['can_continue']
    second=recovery.prepare_attempt(folder,reviewed['continuation'])
    result=recovery.execute(folder,second.name);save(second/'guard/pipeline.json',dict(status='complete'))
    assert result['optimizer_completed'] and result['original_selected'] and not result['quality_approved']
    assert sha256(first/'guard/pipeline.json')==old_guard
    assert all(sha256(path)==digest for path,digest in original_bytes.items())
    report=jobs.review(folder.name);assert report['status']=='complete' and not report['can_continue']
    descriptor=preview.descriptor(folder.name,report['result_sha256'])
    assert descriptor['candidate'] is not None and descriptor['original_selected']
    assert not descriptor['quality_approved']
    actor=descriptor['candidate']['actors']['A']
    assert sha256(preview.served_file(actor['url']))==actor['sha256']
    package=jobs.served_file(report['download_url'])
    with zipfile.ZipFile(package) as archive:
        assert json.loads(archive.read('result.json'))==result
        assert all(archive.read(name)==(folder/name).read_bytes() for name in result['files_sha256'])
    if cut=='packaging':assert len(list((folder/'publications').iterdir()))==2
    with pytest.raises(ValueError,match='Wait'):recovery.prepare_attempt(folder,reviewed['continuation'])
