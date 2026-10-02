"""Shared NumPy/SciPy temporal controls; no motion model runtime required."""
import numpy as np
from scipy.interpolate import make_interp_spline


def correction_basis(frames, spacing):
    """Cubic interpolation of sparse edit controls; callers enforce edit bounds."""
    if type(frames)!=int or frames<3 or type(spacing)!=int or spacing<1:raise ValueError('Invalid correction clock')
    knots=np.unique(np.r_[np.arange(0,frames,spacing),frames-1])
    return make_interp_spline(knots,np.eye(len(knots)),k=min(3,len(knots)-1))(np.arange(frames)),knots
