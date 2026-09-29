"""Native-key edit locality within an existing bounded spline space."""
import numpy as np


def localized_controls(basis, window):
    """Null-space controls preserve the seed on every unselected native key."""
    from scipy.linalg import null_space
    basis=np.asarray(basis,dtype=float)
    if basis.ndim!=2 or not np.isfinite(basis).all():raise ValueError('Finite frame/control basis required')
    if not isinstance(window,(list,tuple)) or len(window)!=2 or any(type(v) is not int for v in window):
        raise ValueError('Two integer edit-window endpoints required')
    start,end=window
    if not 0<=start<=end<len(basis):raise ValueError('Edit window outside clip')
    outside=(np.arange(len(basis))<start)|(np.arange(len(basis))>end)
    transform=null_space(basis[outside],rcond=1e-12) if outside.any() else np.eye(basis.shape[1])
    if transform.shape[1]==0:raise ValueError('Edit window has no free spline controls')
    error=float(np.abs(basis[outside]@transform).max()) if outside.any() else 0.
    if error>1e-11:raise ValueError('Outside-window control residual too large')
    return transform,outside,dict(window=list(window),free_controls=transform.shape[1],outside_keys=int(outside.sum()),basis_residual=error,
        scope='Seed rotations preserved at unselected native keys; boundary dynamics and between-key motion still require audit.')


