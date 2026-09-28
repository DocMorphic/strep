from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from relax_support_window import relax


def fitter():
    desired=np.array([.2,0.,0.,.4,0.,0.])
    return SimpleNamespace(local=np.zeros((6,1,4,4)),bounds=np.array([.04]*3+[.5]*3),
        spec=dict(limits=dict(root_step_m=.015,joint_step_degrees=5),max_nfev=80),
        objective_pair=lambda frame,x,neighbors:(x-desired,np.eye(6)))


def test_real_constrained_relaxation_preserves_prefix_and_join_limits():
    initial=np.zeros((6,6));values,records,convergence=relax(fitter(),initial,2,sweeps=2)
    assert np.array_equal(values[:2],initial[:2]) and np.array_equal(initial,np.zeros((6,6)))
    assert values[-1,0]>.01 and values[-1,3]>.01
    assert np.all(np.abs(values)<=fitter().bounds+1e-10)
    assert np.linalg.norm(np.diff(values[:,:3],axis=0),axis=1).max()<=.015+1e-8
    assert np.linalg.norm(np.diff(values[:,3:],axis=0),axis=1).max()<=np.radians(5)+1e-8
    assert len(records)==8 and all(r['cost_after']<=r['cost_before'] for r in records)
    assert not convergence['stationarity_proven']


def test_rejects_initial_bound_violation_instead_of_silently_clamping():
    initial=np.zeros((6,6));initial[-1,0]=.02
    with pytest.raises(ValueError,match='adjacent'):relax(fitter(),initial,2)
    initial[:,0]=.05
    with pytest.raises(ValueError,match='absolute'):relax(fitter(),initial,2)
