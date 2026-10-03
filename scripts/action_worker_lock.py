"""OS-released worker lock: one model job at a time, including after server restarts."""
from contextlib import contextmanager
import errno
import os
if os.name == 'nt':
    import msvcrt
else:
    import fcntl
from strep import ROOT


def _lock(stream, acquire):
    stream.seek(0)
    if os.name == 'nt':
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK if acquire else msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(stream.fileno(), (fcntl.LOCK_EX | fcntl.LOCK_NB) if acquire else fcntl.LOCK_UN)


@contextmanager
def worker_lock():
    path=ROOT/'.cache/action-worker.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        try:_lock(stream, True)
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):raise
            raise RuntimeError('Another local action job is running') from exc
        try:yield
        finally:_lock(stream, False)


def worker_busy():
    try:
        with worker_lock():return False
    except RuntimeError:return True
