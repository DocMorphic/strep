import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
if not (ROOT/'reports/conic-solver-bootstrap-v1.json').exists():
    pytest.skip('Requires the locally pinned research solver',allow_module_level=True)
from coupled_pair_proposal import solve


def test_solver_moves_both_actors_without_exceeding_motion_caps():
    gaps=np.array([-.01]);gj=np.array([[1.,0,0,-1,0,0]])
    vectors=np.zeros((2,3));j=np.zeros((2,3,6));j[0,:,:3]=np.eye(3);j[1,:,3:]=np.eye(3)
    step,report=solve(gaps,gj,np.array([.01]),vectors,j,np.array([.001,.001]),.003)
    assert report['proposal_hard_checks'] and step is not None
    assert step[0]>.00099 and step[3]<-.00099
    assert report['predicted_peak_m']==pytest.approx(.008,abs=1e-7)


def test_zero_norm_cap_is_an_exact_constraint():
    step,report=solve(np.array([-.01]),np.array([[1.,0,0]]),np.array([.01]),
                      np.zeros((1,3)),np.eye(3)[None],np.array([0.]),.003)
    assert report['proposal_hard_checks']
    np.testing.assert_allclose(step,0,atol=1e-10)
