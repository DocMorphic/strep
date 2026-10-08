"""Stricter working point limits; independent acceptance stays unchanged."""
import numpy as np


def validate_margin(margin):
    if type(margin) not in (int,float) or not np.isfinite(margin) or not 0<=margin<=.001:
        raise ValueError('Finite point numerical margin in [0,1mm] required')
    return margin


def working_limits(limits,active,margin):
    """Reserve at most 1% of each active explicit point limit, without mutation.

    The cap keeps a positive working limit even when a requested tolerance is
    smaller than the configured absolute headroom. This is not an error bound
    for convergence, interpolation or export; measure those independently.
    """
    validate_margin(margin)
    limits=np.asarray(limits,dtype=float);active=np.asarray(active)
    if (limits.ndim!=2 or not limits.size or active.shape!=limits.shape
            or active.dtype.kind!='b' or not np.isfinite(limits).all() or (limits<=0).any()):
        raise ValueError('Complete positive point-limit matrix and boolean active mask required')
    reserved=np.where(active,np.minimum(margin,limits*.01),0.)
    result=limits-reserved
    if not (result>0).all():raise ValueError('Positive working point limits required')
    return result,reserved
