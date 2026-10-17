"""Complete point-set support gaps for explicitly stronger region guidance.

This is a sufficient directional-separation proxy. Negative gaps neither prove
intersection nor infeasibility. Every original witness and complete saved mesh
must still be checked by the caller; this helper cannot approve an animation.
"""
import numpy as np

MAXIMUM_VERTICES = 65536


def region_support_gap(left, right, normal, *, temperature_m=1e-5):
    """Return projected/smooth scalar gaps and complete vertex gradients.

    Each point set is (N,3), with an independent bounded N>=1, in metres.
    A unit normal points from left to right. Smooth gap lower-bounds the
    projected gap in real arithmetic by at most t*(log(Nleft)+log(Nright)).
    Common-direction triangle gaps on subsets are at least this region gap;
    the converse is false. No point or influence is truncated or selected.
    """
    arrays = [np.asarray(value) for value in (left, right, normal)]
    if any(value.dtype.kind not in 'fiu' for value in arrays):
        raise ValueError('Real numeric complete point sets and normal required')
    a, b, n = [value.astype(np.float64, copy=False) for value in arrays]
    if (any(value.ndim != 2 or value.shape[1:] != (3,)
            or not 1 <= len(value) <= MAXIMUM_VERTICES for value in (a, b))
            or n.shape != (3,)):
        raise ValueError('Complete bounded nonempty point sets and one normal required')
    if (not all(np.isfinite(value).all() for value in (a, b, n))
            or max(float(np.abs(a).max()), float(np.abs(b).max())) > 1e6
            or np.any(np.abs(n) > 2)
            or not np.isclose(np.linalg.norm(n), 1., rtol=0., atol=1e-8)):
        raise ValueError('Finite positions within one million metres and unit normal required')
    if type(temperature_m) not in (float, int) or not 1e-9 <= temperature_m <= .1:
        raise ValueError('Finite temperature in [1e-9, .1] metres required')

    origin = a[0]
    ap = np.einsum('vi,i->v', a-origin, n)
    bp = np.einsum('vi,i->v', b-origin, n)
    upper = ap.max(); lower = bp.min()
    aw = np.exp((ap-upper)/temperature_m)
    bw = np.exp((lower-bp)/temperature_m)
    asum = aw.sum(); bsum = bw.sum()
    exact = lower-upper
    return dict(projected_gap_m=float(exact),
                smooth_gap_m=float(exact-temperature_m*(np.log(asum)+np.log(bsum))),
                left_gradient=-(aw/asum)[:, None]*n,
                right_gradient=(bw/bsum)[:, None]*n,
                maximum_entropy_error_m=float(temperature_m*(np.log(len(a))+np.log(len(b)))))
