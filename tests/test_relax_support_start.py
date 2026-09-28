from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from relax_support_start import relax


def test_reverse_adapter_uses_original_objective_clock_and_preserves_suffix():
    calls=[]
    def objective(frame,x,neighbors):
        calls.append(frame);target=np.array([.001*(frame+1),0,0,0,0,0])
        # Scale the test residual above the frozen solver's gtol; this checks
        # clock mapping, not convergence below that solver's declared tolerance.
        return (x-target)*100,np.eye(6)*100
    fitter=SimpleNamespace(local=np.zeros((7,1,4,4)),bounds=np.array([.04]*3+[.5]*3),
        spec=dict(limits=dict(root_step_m=.015,joint_step_degrees=5),max_nfev=80),objective_pair=objective)
    initial=np.zeros((7,6));result,records,convergence=relax(fitter,initial,last=2,sweeps=2)
    assert calls[0]==2 and set(calls)=={0,1,2}
    np.testing.assert_allclose(result[:3,0],[.001,.002,.003],atol=1e-6)
    assert np.array_equal(result[3:],initial[3:]) and not initial.any()
    assert [r['frame'] for r in records]==[2,1,0,0,1,2]
    assert np.linalg.norm(np.diff(result[:,:3],axis=0),axis=1).max()<=.015+1e-8
    assert convergence['first_editable_frame']==0 and convergence['last_editable_frame']==2
