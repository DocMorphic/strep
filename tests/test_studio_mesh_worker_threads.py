"""Fresh Studio workers must limit numerical pools loaded by their backend."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('module,backend', [
    ('studio_mesh_character_job', 'native_mesh_character_fit'),
    ('studio_mesh_scene_job', 'studio_mesh_scene'),
])
def test_fresh_worker_limits_lazily_loaded_pools(module, backend, tmp_path):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    program = f'''
import sys, importlib, importlib.abc
from contextlib import contextmanager
from pathlib import Path
sys.path.insert(0, {str(scripts)!r})
import {module} as job
import action_worker_lock
assert not {{'numpy', 'scipy'}} & set(sys.modules)
held = False
@contextmanager
def lock():
    global held
    assert not held
    held = True
    try: yield
    finally: held = False
action_worker_lock.worker_lock = lock
class LockedNumerics(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('numpy', 'scipy'):
            assert held, 'Numerical imports must occur inside the worker lock'
sys.meta_path.insert(0, LockedNumerics())
folder = Path({str(tmp_path)!r}).resolve()
job.folder_for = lambda _: folder
seen = []
def inspect(*args):
    assert held
    importlib.import_module({backend!r})
    from threadpoolctl import threadpool_info
    pools = [p for p in threadpool_info() if p['user_api'] == 'blas']
    assert pools, 'Test needs actual loaded BLAS pools'
    seen.extend(pools)
    assert all(p['num_threads'] == 1 for p in pools), pools
job.execute = inspect
sys.argv = ['worker', str(folder), '--worker']
assert job.main() == 0
assert seen and not held
'''
    # An explicit >1 initial setting catches the defect even on single-core CI.
    env = dict(os.environ, OPENBLAS_NUM_THREADS='2', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    result = subprocess.run([sys.executable, '-c', program], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('module', ['studio_mesh_character_job', 'studio_mesh_scene_job'])
def test_queue_module_remains_free_of_numerical_imports(module):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    program = f'''
import sys, importlib.abc
sys.path.insert(0, {str(scripts)!r})
class NoNumerics(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('numpy', 'scipy', 'torch'):
            raise AssertionError('Queue import loaded ' + fullname)
sys.meta_path.insert(0, NoNumerics())
import {module}
'''
    result = subprocess.run([sys.executable, '-c', program], capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
