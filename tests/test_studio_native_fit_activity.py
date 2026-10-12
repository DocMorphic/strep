"""Interrupted corrections retain raw receipts; OS birth identity gates projection."""
import copy,json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import psutil,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_fit as studio
from strep import read,save,sha256


def prepared(tmp_path,monkeypatch,status='processing'):
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    folder=studio.folder_for('activity');folder.mkdir(parents=True)
    save(folder/'prepared.json',dict(fixture=True))
    save(folder/'pipeline.json',dict(status=status,stage='character-fit',original_selected=True,quality_approved=False))
    (folder/'raw-partial.bin').write_bytes(b'original partial evidence')
    return folder


def identity(folder,**updates):
    r=dict(schema='strep-studio-native-fit-worker-v1',prepared_sha256=sha256(folder/'prepared.json'),pid=12345,created_at=100.,exit_code=None)
    r.update(updates);save(folder/'worker.json',r);return r


def snapshot(folder):return {p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}


@pytest.mark.parametrize('fault,expected',[('alive','processing'),('missing','failed'),('reused','failed'),('stopped','failed'),('zombie','failed'),('denied','unknown')])
def test_os_identity_and_read_only_manifest(tmp_path,monkeypatch,fault,expected):
    folder=prepared(tmp_path,monkeypatch);identity(folder);before=snapshot(folder)
    def process(pid):
        assert pid==12345
        if fault=='missing':raise psutil.NoSuchProcess(pid)
        if fault=='denied':raise psutil.AccessDenied(pid)
        return SimpleNamespace(create_time=lambda:101. if fault=='reused' else 100.,is_running=lambda:fault!='stopped',status=lambda:psutil.STATUS_ZOMBIE if fault=='zombie' else psutil.STATUS_RUNNING)
    monkeypatch.setattr(psutil,'Process',process)
    review=studio.manifest(folder.name)
    assert review['status']==expected and review['downloads']==[] and review['original_selected']
    assert not review['quality_approved'] and not review['release_approved']
    assert studio.listing()['jobs'][0]['status']==expected and snapshot(folder)==before


@pytest.mark.parametrize('status',['complete','failed','cancelled'])
def test_terminal_receipts_take_precedence(tmp_path,monkeypatch,status):
    folder=prepared(tmp_path,monkeypatch,status);identity(folder,pid=False)
    monkeypatch.setattr(psutil,'Process',lambda pid:pytest.fail('Terminal state must not query a process'))
    before=snapshot(folder);assert studio.observed_state(folder)==read(folder/'pipeline.json');assert snapshot(folder)==before


@pytest.mark.parametrize('fault',['schema','prepared','pid-bool','pid-negative','pid-oversized','birth-bool','birth-nan','birth-negative','birth-oversized','exit-bool','extra','malformed','conflict'])
def test_invalid_identity_is_unknown_without_mutation(tmp_path,monkeypatch,fault):
    folder=prepared(tmp_path,monkeypatch);r=identity(folder)
    if fault=='schema':r['schema']='other'
    if fault=='prepared':r['prepared_sha256']='0'*64
    if fault=='pid-bool':r['pid']=True
    if fault=='pid-negative':r['pid']=-1
    if fault=='pid-oversized':r['pid']=2**64
    if fault=='birth-bool':r['created_at']=True
    if fault=='birth-nan':r['created_at']=float('nan')
    if fault=='birth-negative':r['created_at']=-1.
    if fault=='birth-oversized':r['created_at']=2**1024
    if fault=='exit-bool':r['exit_code']=False
    if fault=='extra':r['extra']=1
    if fault=='conflict':save(folder/'launched-worker.json',dict(r,pid=r['pid']+1))
    (folder/'worker.json').write_text('broken' if fault=='malformed' else json.dumps(r),encoding='utf-8')
    before=snapshot(folder);assert studio.observed_state(folder)['status']=='unknown';assert snapshot(folder)==before


def test_legacy_and_unverifiable_identity(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch);before=snapshot(folder)
    assert studio.observed_state(folder)['status']=='unknown' and snapshot(folder)==before
    save(folder/'pipeline.json',dict(status='starting'))
    assert studio.observed_state(folder)==dict(status='starting')
    identity(folder,created_at=None);assert studio.observed_state(folder)['status']=='unknown'
    identity(folder,created_at=None,exit_code=0);assert studio.observed_state(folder)['status']=='failed'


def test_terminal_write_during_liveness_query_wins(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch);identity(folder)
    def process(pid):
        save(folder/'pipeline.json',dict(status='complete',marker='terminal won'))
        raise psutil.NoSuchProcess(pid)
    monkeypatch.setattr(psutil,'Process',process)
    assert studio.observed_state(folder)==dict(status='complete',marker='terminal won')


def test_launch_and_executor_use_separate_bound_files(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch);handle=SimpleNamespace(pid=os.getpid(),poll=lambda:None)
    launched=studio.record_worker(folder,handle);executing=studio.record_worker(folder)
    assert launched==executing and executing['created_at']==psutil.Process(os.getpid()).create_time()
    assert read(folder/'worker.json')==executing and read(folder/'launched-worker.json')==launched
    assert studio.observed_state(folder)['status']=='processing'


def test_launch_exited_during_registration(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch,'starting')
    def missing(pid):raise psutil.NoSuchProcess(pid)
    monkeypatch.setattr(psutil,'Process',missing)
    r=studio.record_worker(folder,SimpleNamespace(pid=12345,poll=lambda:9))
    assert r['exit_code']==9 and r['created_at'] is None
    assert studio.observed_state(folder)['status']=='failed'


def test_cli_registration_is_inside_job_lock_and_terminal_evidence_stays(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch,'starting');calls=[]
    def execute(path):
        assert read(path/'worker.json')['pid']==os.getpid()
        with pytest.raises(RuntimeError,match='already running'):
            with studio.job_lock(path):pass
        calls.append(path);save(path/'pipeline.json',dict(status='complete'));return {'fixture':True}
    monkeypatch.setattr(studio,'execute',execute)
    assert studio.run(folder)=={'fixture':True}
    owner=(folder/'worker.json').read_bytes();assert studio.run(folder)=={'fixture':True}
    assert (folder/'worker.json').read_bytes()==owner and len(calls)==2


def test_real_child_exit_replays_without_touching_raw_state(tmp_path,monkeypatch):
    folder=prepared(tmp_path,monkeypatch)
    process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        studio.record_worker(folder,process);assert studio.observed_state(folder)['status']=='processing'
        before=snapshot(folder);process.terminate();process.wait(timeout=10)
        assert studio.manifest(folder.name)['status']=='failed' and studio.manifest(folder.name)['downloads']==[]
        assert snapshot(folder)==before and read(folder/'pipeline.json')['status']=='processing'
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=10)


def test_offline_server_records_launch_identity(tmp_path,monkeypatch):
    import action_studio_server as server
    from test_studio_native_scene_fit import setup
    from test_studio_native_scene import handler
    payload,source,resolver=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(server,'ROOT',tmp_path);monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    def launch(argv,**kwargs):
        calls.append(argv);return SimpleNamespace(pid=os.getpid(),poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch)
    request=handler(payload,'/api/native-scene-fits');request.do_POST();assert request.responses[-1][0]==202
    folder=Path(calls[0][2]);r=read(folder/'launched-worker.json')
    assert r['pid']==os.getpid() and r['prepared_sha256']==sha256(folder/'prepared.json')
    assert studio.manifest(folder.name)['status']=='starting' and not (folder/'worker.json').exists()
