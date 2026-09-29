"""Discard only affine inequalities certified positive throughout a step box."""
import numpy as np


def screen(margins, jacobian, lower, upper):
    c = np.asarray(margins, dtype=float)
    j = np.asarray(jacobian, dtype=float)
    lower, upper = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    if c.ndim != 1 or j.ndim != 2 or j.shape[0] != len(c) or lower.shape != (j.shape[1],) or upper.shape != lower.shape:
        raise ValueError('Matching affine rows and step bounds required')
    if any(not np.isfinite(a).all() for a in [c, j, lower, upper]) or np.any(lower > upper):
        raise ValueError('Finite ordered step bounds and rows required')
    # Each affine row reaches its box minimum at the sign-selected corner.
    try:
        with np.errstate(over='raise', invalid='raise'):
            products = j*np.where(j >= 0, lower, upper)
            magnitude = np.abs(c)+np.abs(products).sum(axis=1)
            error = 4*(j.shape[1]+3)*np.finfo(float).eps*np.maximum(magnitude, 1.)+1e-12
            guaranteed = c+products.sum(axis=1)-error
    except FloatingPointError as exc:
        raise ValueError('Affine interval arithmetic overflowed') from exc
    keep = guaranteed <= 0.
    omitted = guaranteed[~keep]
    return c[keep], j[keep], dict(original_rows=len(c), retained_rows=int(keep.sum()),
        omitted_rows=int((~keep).sum()), minimum_omitted_margin=float(omitted.min()) if len(omitted) else None,
        retained_indices=np.flatnonzero(keep).tolist(), bound='c + sum(j_i * (lower_i if j_i >= 0 else upper_i)) minus floating-point reserve')
