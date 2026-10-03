"""Separate worst-geometry proxy bounds for local motion proposals.

Fixed witness vectors guide proposals; the complete decoded mesh audit remains
the geometry acceptance criterion. Original authored norm caps are untouched.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows


def protect_worst(system,jacobian,hard_rows,geometry_rows):
    """Duplicate the geometry block into the protected proposal prefix.

    Geometry follows the existing hard prefix. Its separate guard caps preserve
    the baseline worst positive witness residual, rather than allowing a larger
    contact objective to absorb worsening geometry.
    """
    jacobian=sparse.csc_matrix(jacobian)
    if (type(hard_rows) is not int or type(geometry_rows) is not int
            or not 0<hard_rows<=len(system.caps) or not 1<=geometry_rows<=len(system.caps)-hard_rows
            or jacobian.shape[0]!=3*len(system.caps) or not np.isfinite(jacobian.data).all()):
        raise ValueError('Complete protected prefix and consecutive geometry block required')
    ids=np.arange(hard_rows,hard_rows+geometry_rows)
    before=system.residual()[ids]
    if not np.isfinite(before).all():raise ValueError('Finite complete geometry residual population required')
    bound=float(max(0.,before.max()))
    order=np.r_[np.arange(hard_rows),ids,np.arange(hard_rows,len(system.caps))]
    caps=system.caps[order].copy()
    caps[hard_rows:hard_rows+geometry_rows]=system.caps[ids]+bound*system.scales[ids]
    # At an active baseline row, avoid subtraction-roundoff fixed-cone conflicts.
    caps[hard_rows:hard_rows+geometry_rows]=np.maximum(caps[hard_rows:hard_rows+geometry_rows],np.linalg.norm(system.vectors[ids],axis=1))
    guarded=NormRows(system.vectors[order],caps,system.scales[order])
    derivative=jacobian[(3*order[:,None]+np.arange(3)).ravel()]
    return guarded,derivative,dict(existing_hard_rows=hard_rows,protected_geometry_rows=geometry_rows,
        hard_rows=hard_rows+geometry_rows,baseline_worst_positive_residual=bound,
        authored_norm_rows_unchanged=True,
        scope='Separate baseline worst-witness bound in the affine proposal. Actual fixed witnesses can restore proposal defects; complete decoded geometry still decides acceptance. No collision certificate or relaxed authored geometry limit.')


def regression(residual,bound):
    residual=np.asarray(residual,float)
    if (residual.ndim!=1 or not len(residual) or not np.isfinite(residual).all()
            or type(bound) not in (float,int) or not np.isfinite(bound) or bound<0):
        raise ValueError('Complete finite geometry residuals and nonnegative explicit bound required')
    return residual-bound
