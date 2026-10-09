"""Runner lifecycle without downloaded native assets or inference."""
import sys
from pathlib import Path
from contextlib import nullcontext
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import guarded_pose_restoration as module


@pytest.mark.parametrize('options',[dict(frame=True),dict(iterations=0),dict(trust=.31),dict(seconds=float('nan'))])
def test_invalid_options_never_acquire_or_run_worker(tmp_path,monkeypatch,options):
    def forbidden(*args,**kwargs):raise AssertionError('Invalid request reached worker')
    monkeypatch.setattr(module,'worker_lock',forbidden)
    args=dict(frame=72);args.update(options)
    with pytest.raises(ValueError):module.run(tmp_path,tmp_path/'new',**args)
    assert not (tmp_path/'new').exists()


def test_failure_receipt_preserves_existing_output(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **kwargs:nullcontext())
    def fail(study,output,*args):output.mkdir();raise ValueError('Bound input rejected')
    monkeypatch.setattr(module,'_run',fail);output=tmp_path/'study'
    with pytest.raises(ValueError):module.run(tmp_path,output,72)
    receipt=(output/'pipeline.json').read_bytes()
    assert module.read(output/'pipeline.json')['status']=='failed'
    with pytest.raises(FileExistsError):module.run(tmp_path,output,72)
    assert (output/'pipeline.json').read_bytes()==receipt


def test_worker_lock_covers_the_entire_source_and_result_lifecycle(tmp_path,monkeypatch):
    from contextlib import contextmanager
    active=[]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    monkeypatch.setattr(module,'worker_lock',lock)
    monkeypatch.setattr(module,'threadpool_limits',lambda **kwargs:nullcontext())
    def run(*args):assert active;return 'preserved-result'
    monkeypatch.setattr(module,'_run',run)
    assert module.run(tmp_path,tmp_path/'out',72)=='preserved-result'
    assert not active
