import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from process_monitor import tree_rss, kill_tree
import process_monitor


@pytest.mark.parametrize('reap_parent',[True,False])
def test_worker_memory_and_termination(tmp_path,reap_parent):
    ready = tmp_path / 'ready'
    worker = "import sys,time; from pathlib import Path; block=bytearray(64*1024**2); Path(sys.argv[1]).write_text('ready'); time.sleep(30)"
    launcher = "import subprocess,sys; subprocess.run([sys.executable,'-c',sys.argv[1],sys.argv[2]])"
    process = subprocess.Popen([sys.executable, '-c', launcher, worker, str(ready)])
    children = []
    try:
        deadline = time.monotonic() + 15
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), 'Synthetic worker did not become ready'
        children = psutil.Process(process.pid).children(recursive=True)
        assert children
        assert tree_rss(process.pid) >= 64 * 1024**2
    finally:
        kill_tree(process.pid,reap_parent=reap_parent)
        process.wait(timeout=5)
    if not reap_parent:assert process.returncode!=0
    assert all(not child.is_running() for child in children)


def test_popen_owned_parent_is_killed_but_never_reaped_by_psutil(monkeypatch):
    class Process:
        def __init__(self,name):self.name=name;self.killed=False
        def children(self,recursive):assert recursive;return children
        def kill(self):self.killed=True
    parent=Process('parent');children=[Process('child'),Process('grandchild')];waited=[]
    monkeypatch.setattr(process_monitor.psutil,'Process',lambda pid:parent)
    monkeypatch.setattr(process_monitor.psutil,'wait_procs',lambda processes,timeout:waited.extend(processes))
    kill_tree(1,reap_parent=False)
    assert parent.killed and all(p.killed for p in children)
    assert waited==children and parent not in waited


def test_invalid_reaping_flag_never_touches_a_process(monkeypatch):
    monkeypatch.setattr(process_monitor.psutil,'Process',lambda pid:pytest.fail('Invalid option reached a process'))
    with pytest.raises(ValueError):kill_tree(1,reap_parent=1)
