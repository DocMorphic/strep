import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_refined_solver_scaling import objective_scalings


def test_distance_rescaling_preserves_physical_objective_and_ordering():
    penalties=np.array([.001,.0007,.002]);peaks=np.array([.02,.0201,.0199])
    original=peaks+.005*1e-4*penalties
    variants=objective_scalings()
    assert len({v['name'] for v in variants})==len(variants)==2
    for v in variants:
        assert v['scale']*v['regularizer']==pytest.approx(.005*1e-4)
        physical=v['scale']*(peaks/v['scale']+v['regularizer']*penalties)
        np.testing.assert_allclose(physical,original,atol=1e-17,rtol=0)
        np.testing.assert_array_equal(np.argsort(physical),np.argsort(original))
