from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from projected_angular_conic import project_step


def test_projection_satisfies_both_trust_and_original_absolute_box():
    x=np.array([.99,-.99,0.]);delta=np.array([.02,-.03,.010000000006]);bounds=np.ones(3)
    projected=project_step(x,delta,bounds,.01)
    assert np.max(np.abs(projected))<=.01 and np.max(np.abs(x+projected))<=1.
    np.testing.assert_allclose(projected,[.01,-.01,.01],atol=1e-16)


def test_feasible_proposals_are_unchanged_and_invalid_inputs_rejected():
    delta=np.array([.001,-.002]);np.testing.assert_array_equal(project_step(np.zeros(2),delta,np.ones(2),.01),delta)
    for x,d,b,t in [(np.zeros(2),[np.nan,0.],np.ones(2),.01),([2.],[0.],[1.],.01),([0.],[0.],[1.],0.)]:
        with pytest.raises(ValueError):project_step(x,d,b,t)
