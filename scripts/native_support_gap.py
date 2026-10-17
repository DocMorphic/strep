"""Triangle support gaps and vertex derivatives for coupled native-pose search.

These are floating-point projection bounds, not mesh-intersection predicates.
A positive gap proves separation along the supplied direction in real arithmetic;
a negative gap need not mean the triangles intersect. Callers retain independent
mesh, encoded-output and full-motion validation.
"""
import numpy as np

MAXIMUM_PAIRS = 16384


def triangle_support_gaps(left, right, normals, *, temperature_m=1e-5):
    """Return exact-extrema and smooth gaps (metres), plus smooth vertex gradients.

    Inputs have shapes (pairs, 3, 3), (pairs, 3, 3), (pairs, 3).
    Normals must be unit vectors oriented from left to right. All three vertices
    participate; duplicates are allowed. The smooth gap lower-bounds the extrema
    gap in real arithmetic, with error at most 2*temperature*log(3). Its gradients
    have the same shapes as the triangles. No source/target acceptance is implied.
    """
    raw = [np.asarray(value) for value in (left, right, normals)]
    if any(value.dtype.kind not in 'fiu' for value in raw):
        raise ValueError('Real numeric triangle positions and normals required')
    a, b, n = (value.astype(np.float64, copy=False) for value in raw)
    if (a.ndim != 3 or a.shape[1:] != (3, 3) or not 1 <= len(a) <= MAXIMUM_PAIRS
            or b.shape != a.shape or n.shape != (len(a), 3)):
        raise ValueError('Complete bounded triangle batches and one normal per pair required')
    if (not all(np.isfinite(value).all() for value in (a, b, n))
            or max(float(np.abs(a).max()), float(np.abs(b).max())) > 1e6
            or np.any(np.abs(n) > 2)
            or not np.allclose(np.linalg.norm(n, axis=1), 1., rtol=0., atol=1e-8)):
        raise ValueError('Finite positions within one million metres and unit normals required')
    if (type(temperature_m) not in (float, int) or not 1e-9 <= temperature_m <= .1):
        raise ValueError('Finite positive temperature in [1e-9, .1] metres required')

    # A common local origin avoids exponentiating large world coordinates. Its
    # derivative cancels because each side's support weights sum to one.
    origin = a[:, :1, :]
    ap = np.einsum('pi,pvi->pv', n, a-origin)
    bp = np.einsum('pi,pvi->pv', n, b-origin)
    upper = ap.max(axis=1)
    lower = bp.min(axis=1)
    aw = np.exp((ap-upper[:, None])/temperature_m)
    bw = np.exp((lower[:, None]-bp)/temperature_m)
    asum = aw.sum(axis=1)
    bsum = bw.sum(axis=1)
    exact = lower-upper
    smooth = exact-temperature_m*(np.log(asum)+np.log(bsum))
    left_gradient = -(aw/asum[:, None])[:, :, None]*n[:, None, :]
    right_gradient = (bw/bsum[:, None])[:, :, None]*n[:, None, :]
    return dict(projected_gap_m=exact, smooth_gap_m=smooth,
                left_gradient=left_gradient, right_gradient=right_gradient)
