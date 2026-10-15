"""Mixed geometry and one-thread LP solves must work in a fresh owned process."""
from pathlib import Path
import os,subprocess,sys
import pytest


@pytest.mark.parametrize('initial_threads',[None,2])
def test_project_solvers_preserve_an_existing_scheduler(initial_threads):
    root=Path(__file__).resolve().parents[1]
    code="""import sys,numpy as np
sys.path.insert(0,'scripts')
from scipy.optimize import linprog
options={} if sys.argv[1]=='None' else {'threads':int(sys.argv[1])}
warm=linprog([1.],bounds=[(0.,1.)],method='highs',options=options)
assert warm.success,warm.message
from convex_colliders import direction_hull
points=direction_hull(np.r_[np.eye(3),-np.eye(3)],np.ones(6))
assert len(points)==8
from verify_triangle_scene import interior_witness
witness=interior_witness(np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]),
    np.array([[.25,.25,-1.],[.25,.25,1.],[.5,.5,0.]]))
assert witness['feasible'] and witness['minimum_barycentric_weight']>.3
import pytest
raise SystemExit(pytest.main(['-q','tests/test_native_motion_orientation.py::test_explicit_polar_recipe_exports_without_repairing_the_stored_affine_rig']))
"""
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result=subprocess.run([sys.executable,'-c',code,str(initial_threads)],cwd=root,env=env,capture_output=True,text=True,timeout=60,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.stdout+'\n'+result.stderr
