"""OS-released worker lock: one model job at a time, including after server restarts."""
from contextlib import contextmanager
import msvcrt
from strep import ROOT


@contextmanager
def worker_lock():
    path=ROOT/'.cache/action-worker.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as exc:raise RuntimeError('Another local action job is running') from exc
        try:yield
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def worker_busy():
    try:
        with worker_lock():return False
    except RuntimeError:return True
