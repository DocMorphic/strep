from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from relax_temporal_support import relax
from support_curvature import root_curvature_energy


def fitter():
    desired=np.array([.03,0.,0.,0.,0.,0.])
    return SimpleNamespace(local=np.zeros((7,1,4,4)),bounds=np.array([.04]*3+[.5]*3),
        spec=dict(limits=dict(root_step_m=.015,joint_step_degrees=5),max_nfev=80),
        objective_pair=lambda frame,x,neighbors:(x-desired,np.eye(6)))


def test_interior_solve_preserves_both_sides_and_regularizes_added_curvature():
    initial=np.zeros((7,6))
    control,_,_=relax(fitter(),initial,2,4,0.,sweeps=3)
    smooth,records,_=relax(fitter(),initial,2,4,10.,sweeps=3)
    for values in [control,smooth]:
        assert np.array_equal(values[:2],initial[:2]) and np.array_equal(values[5:],initial[5:])
        assert np.linalg.norm(np.diff(values[:,:3],axis=0),axis=1).max()<=.015+1e-8
        assert np.all(np.abs(values)<=fitter().bounds+1e-10)
    assert root_curvature_energy(smooth,1.)<root_curvature_energy(control,1.)
    assert len(records)==9 and all(r['cost_after']<=r['cost_before'] for r in records)
