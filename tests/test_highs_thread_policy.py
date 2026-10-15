"""Mixed geometry and one-thread LP solves must work in a fresh owned process."""
from pathlib import Path
import os,subprocess,sys


def test_project_hull_solve_does_not_poison_later_single_thread_solver():
    root=Path(__file__).resolve().parents[1]
    code="""import sys,numpy as np
sys.path.insert(0,'scripts')
from convex_colliders import direction_hull
from scipy.optimize import linprog
points=direction_hull(np.r_[np.eye(3),-np.eye(3)],np.ones(6))
assert len(points)==8
fit=linprog([1.],bounds=[(0.,1.)],method='highs',options={'threads':1})
assert fit.success, (fit.status,fit.message)
assert fit.x[0]==0.
from verify_triangle_scene import interior_witness
witness=interior_witness(np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]),
    np.array([[.25,.25,-1.],[.25,.25,1.],[.5,.5,0.]]))
assert witness['feasible'] and witness['minimum_barycentric_weight']>.3
"""
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result=subprocess.run([sys.executable,'-c',code],cwd=root,env=env,capture_output=True,text=True,timeout=30,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.stdout+'\n'+result.stderr
