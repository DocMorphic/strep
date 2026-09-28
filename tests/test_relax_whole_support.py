from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from relax_whole_support import relax


def fitter(frames=6):
    return SimpleNamespace(local=np.zeros((frames,1,4,4)),bounds=np.array([.04]*3+[.5]*3),
        spec=dict(limits=dict(root_step_m=.015,joint_step_degrees=5),max_nfev=80),
        objective_pair=lambda f,x,n:((x-np.array([.02,0,0,0,0,0]))*100,np.eye(6)*100))


def test_whole_clip_can_edit_both_endpoints_without_breaking_step_limits():
    initial=np.zeros((6,6));values,records,convergence=relax(fitter(),initial,curvature_weight=10.,sweeps=3)
    assert values[0,0]>.01 and values[-1,0]>.01 and not initial.any()
    assert np.all(np.abs(values)<=fitter().bounds+1e-10)
    assert np.linalg.norm(np.diff(values[:,:3],axis=0),axis=1).max()<=.015+1e-8
    assert len(records)==18 and all(r['cost_after']<=r['cost_before'] for r in records)
    assert convergence['first_editable_frame']==0 and convergence['last_editable_frame']==5


def test_too_short_clip_is_rejected_before_fitting():
    with pytest.raises(ValueError,match='three frames'):relax(fitter(2),np.zeros((2,6)))
