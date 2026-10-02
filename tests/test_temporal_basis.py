"""Extracted controls remain identical to the historical interpolation rule."""
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.interpolate import make_interp_spline
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from temporal_basis import correction_basis


@pytest.mark.parametrize('frames,spacing', [(3, 1), (3, 10), (7, 2), (30, 6), (80, 8), (120, 10), (180, 6)])
def test_controls_are_byte_equal_to_historical_spline(frames, spacing):
    knots=np.unique(np.r_[np.arange(0,frames,spacing),frames-1])
    expected=make_interp_spline(knots,np.eye(len(knots)),k=min(3,len(knots)-1))(np.arange(frames))
    basis, actual_knots=correction_basis(frames, spacing)
    np.testing.assert_array_equal(actual_knots, knots)
    np.testing.assert_array_equal(basis, expected)


@pytest.mark.parametrize('frames,spacing', [(True, 1), (2, 1), (3., 1), (3, False), (3, 0), (3, 1.)])
def test_invalid_clock_retains_original_rejection(frames, spacing):
    with pytest.raises(ValueError, match='correction clock'): correction_basis(frames, spacing)
