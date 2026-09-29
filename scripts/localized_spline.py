"""Preserve native keys and adjoining export segments around an edit window."""
import numpy as np


def localized_controls(basis, window):
    """Lock outside keys and shared endpoints of adjoining interpolation segments."""
    from scipy.linalg import null_space
    basis=np.asarray(basis,dtype=float)
    if basis.ndim!=2 or not np.isfinite(basis).all():raise ValueError('Finite frame/control basis required')
    if not isinstance(window,(list,tuple)) or len(window)!=2 or any(type(v) is not int for v in window):
        raise ValueError('Two integer edit-window endpoints required')
    start,end=window
    if not 0<=start<=end<len(basis):raise ValueError('Edit window outside clip')
    outside=(np.arange(len(basis))<start)|(np.arange(len(basis))>end)
    locked=outside.copy()
    boundaries=([start] if start>0 else [])+([end] if end<len(basis)-1 else [])
    locked[boundaries]=True
    transform=null_space(basis[locked],rcond=1e-12) if locked.any() else np.eye(basis.shape[1])
    if transform.shape[1]==0:raise ValueError('Edit window has no free spline controls')
    error=float(np.abs(basis[locked]@transform).max()) if locked.any() else 0.
    if error>1e-11:raise ValueError('Locked-key control residual too large')
    return transform,locked,dict(window=list(window),free_controls=transform.shape[1],outside_keys=int(outside.sum()),locked_keys=int(locked.sum()),locked_boundary_keys=sorted(set(boundaries)),basis_residual=error,
        scope='Seed rotations and root lift locked at outside native keys and adjoining window endpoints. Baked LINEAR/SLERP exports preserve outside segments; export precision and boundary dynamics still require audit.')


