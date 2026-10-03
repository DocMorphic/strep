"""Real OS contention and process-exit release without models or private assets."""
import errno
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_worker_lock as locks


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(locks, 'ROOT', tmp_path)
    return tmp_path


def test_independent_handles_and_exception_release(root):
    assert not locks.worker_busy()
    with pytest.raises(ValueError, match='job failure'):
        with locks.worker_lock():
            assert locks.worker_busy()
            with pytest.raises(RuntimeError, match='Another local action job'):
                with locks.worker_lock():
                    pytest.fail('Concurrent acquisition succeeded')
            raise ValueError('job failure')
    assert not locks.worker_busy()
    with locks.worker_lock():
        assert locks.worker_busy()


@pytest.mark.parametrize('crash', [False, True])
def test_other_process_blocks_and_os_releases_on_exit(root, crash):
    script = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import action_worker_lock as locks
locks.ROOT = Path(sys.argv[2])
with locks.worker_lock():
    Path(sys.argv[3]).write_text('locked')
    print('locked', flush=True)
    sys.stdin.readline()
'''
    marker = root / 'child-ready.txt'
    process = subprocess.Popen([sys.executable, '-u', '-c', script,
        str(Path(locks.__file__).parent), str(root), str(marker)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # A bounded polling loop avoids an indefinitely blocking pipe read when
        # startup fails. Only this owned process may be terminated below.
        import time
        deadline = time.monotonic() + 15
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert marker.exists(), 'Child failed to acquire the lock'
        assert locks.worker_busy()
        with pytest.raises(RuntimeError, match='Another local action job'):
            with locks.worker_lock():
                pytest.fail('Different process bypassed the lock')
        if crash:
            process.kill()
            process.communicate(timeout=15)
        else:
            _, errors = process.communicate('\n', timeout=15)
            assert process.returncode == 0, errors
        assert not locks.worker_busy()
        with locks.worker_lock():
            assert locks.worker_busy()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=15)


@pytest.mark.parametrize('code', [errno.EACCES, errno.EAGAIN, errno.EDEADLK])
def test_contention_codes_become_busy(root, monkeypatch, code):
    def fail(stream, acquire):
        raise OSError(code, 'locked')
    monkeypatch.setattr(locks, '_lock', fail)
    assert locks.worker_busy()


@pytest.mark.parametrize('code', [errno.EIO, errno.EBADF, errno.ENOSPC])
def test_other_os_failures_are_not_reported_as_another_job(root, monkeypatch, code):
    def fail(stream, acquire):
        raise OSError(code, 'filesystem failure')
    monkeypatch.setattr(locks, '_lock', fail)
    with pytest.raises(OSError) as caught:
        locks.worker_busy()
    assert caught.value.errno == code


def test_filesystem_open_failure_is_not_busy(root):
    (root / '.cache').write_text('not a directory')
    with pytest.raises(OSError):
        locks.worker_busy()
