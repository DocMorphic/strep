import subprocess
import sys
import time
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from process_monitor import tree_rss, kill_tree


def test_worker_memory_and_termination(tmp_path):
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
        kill_tree(process.pid)
        process.wait(timeout=5)
    assert all(not child.is_running() for child in children)
