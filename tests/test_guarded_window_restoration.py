"""Experimental window runner lifecycle without native payloads."""
import sys
from pathlib import Path
from contextlib import nullcontext,contextmanager
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import guarded_window_restoration as module


@pytest.mark.parametrize('options',[
    dict(frames=[]),dict(frames=[1]),dict(frames=[1,3]),dict(frames=[True,2]),dict(frames=[-1,0]),dict(frames=list(range(6))),
    dict(iterations=0),dict(iterations=True),dict(solve_iterations=0),dict(solve_iterations=301),dict(row_chunk=0),dict(row_chunk=True),
    dict(trust=float('nan')),dict(trust=.31),dict(seconds=0),dict(seconds=True),dict(seconds=float('inf')),
    dict(resume=[]),dict(resume={4:'saved'}),dict(resume={True:'saved'}),dict(resume={1:False}),dict(resume={1:''}),
    dict(window_resume=False),dict(window_resume=''),dict(window_resume='saved',resume={1:'pose'})])
def test_invalid_inputs_never_acquire_worker_or_create_output(tmp_path,monkeypatch,options):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Invalid window reached worker'))
    args=dict(frames=[1,2]);args.update(options)
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('output,resume',[('source/new',{}),('source',{}),('saved/new',{1:'saved'}),('saved',{1:'saved/new'})])
def test_source_and_resume_directories_remain_immutable(tmp_path,monkeypatch,output,resume):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Overlapping output reached worker'))
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/output,[1,2],resume={f:tmp_path/p for f,p in resume.items()})


def test_lock_covers_complete_lifecycle_and_forwards_each_resume(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);active=[]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    def run(study,output,frames,*args):
        assert active and frames==[1,2]
        assert args[-2]=={1:tmp_path/'first',2:tmp_path/'second'} and args[-1] is None
        return 'preserved'
    monkeypatch.setattr(module,'worker_lock',lock);monkeypatch.setattr(module,'_run',run)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    assert module.run(tmp_path/'source',tmp_path/'out',[1,2],resume={1:tmp_path/'first',2:tmp_path/'second'})=='preserved'
    assert not active


def test_window_predecessor_is_forwarded_and_cannot_overlap_output(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    def run(*args):
        assert args[-2]=={} and args[-1]==tmp_path/'saved'
        return 'verified-window'
    monkeypatch.setattr(module,'_run',run)
    assert module.run(tmp_path/'source',tmp_path/'out',[1,2],window_resume=tmp_path/'saved')=='verified-window'
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/'saved/new',[1,2],window_resume=tmp_path/'saved')


def test_fresh_failure_saved_but_existing_output_never_overwritten(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    def fail(study,output,*args):output.mkdir();raise ValueError('Native preflight failed')
    monkeypatch.setattr(module,'_run',fail);out=tmp_path/'out'
    with pytest.raises(ValueError):module.run(tmp_path/'source',out,[1,2])
    before=(out/'pipeline.json').read_bytes();assert module.read(out/'pipeline.json')['status']=='failed'
    with pytest.raises(FileExistsError):module.run(tmp_path/'source',out,[1,2])
    assert (out/'pipeline.json').read_bytes()==before
