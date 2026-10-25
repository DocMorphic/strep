"""Complete point-set support gaps for explicitly stronger region guidance.

This is a sufficient directional-separation proxy. Negative gaps neither prove
intersection nor infeasibility. Every original witness and complete saved mesh
must still be checked by the caller; this helper cannot approve an animation.
"""
import numpy as np

MAXIMUM_VERTICES = 65536


def pair_hinge_objective(left, right, normal, *, clearance_m=.0001, scale_m=.01,
                         block_rows=64, maximum_pairs=2_000_000,
                         maximum_working_bytes=64*1024**2):
    """Sum squared separation deficits over every left/right vertex pair.

    The normal points from left to right. Return vertex gradients, allowing
    the caller to differentiate both moving regions without constructing a
    pair-by-control Jacobian. Blocking changes accumulation order only; it
    does not select points or pairs. This is a proposal objective, not a
    whole-mesh collision predicate or a feasibility certificate.
    """
    raw = [np.asarray(v) for v in (left, right, normal)]
    if any(v.dtype.kind not in 'fiu' for v in raw):
        raise ValueError('Real complete point sets and normal required')
    a, b, n = [v.astype(float, copy=False) for v in raw]
    if (any(v.ndim != 2 or v.shape[1:] != (3,) or not 1 <= len(v) <= MAXIMUM_VERTICES for v in (a, b))
            or n.shape != (3,) or not all(np.isfinite(v).all() for v in (a, b, n))
            or max(float(np.abs(a).max()), float(np.abs(b).max())) > 1e6
            or abs(np.linalg.norm(n)-1.) > 1e-8):
        raise ValueError('Complete finite bounded point sets and unit normal required')
    for value, lower, upper in ((clearance_m, 0., .1), (scale_m, 1e-6, 1.)):
        if type(value) not in (int, float) or not np.isfinite(value) or not lower <= value <= upper:
            raise ValueError('Finite bounded clearance and positive scale required')
    if (type(block_rows) is not int or not 1 <= block_rows <= 1024
            or type(maximum_pairs) is not int or not 1 <= maximum_pairs <= 2_000_000
            or len(a)*len(b) > maximum_pairs
            or type(maximum_working_bytes) is not int or not 1 <= maximum_working_bytes <= 64*1024**2):
        raise ValueError('Complete pair population and explicit bounded workspace required')
    block = min(block_rows, len(a))
    # Conservative array estimate including conversion, projections, vertex
    # gradients and block temporaries; excludes the caller's control Jacobian.
    working = 8*(16*(len(a)+len(b))+4*block*len(b))
    if working > maximum_working_bytes:
        raise ValueError('Complete blocked objective exceeds workspace; no prefix returned')
    origin = a[0]
    ap = (a-origin) @ n; bp = (b-origin) @ n
    left_coeff = np.zeros(len(a)); right_coeff = np.zeros(len(b)); loss = 0.
    for start in range(0, len(a), block):
        stop = min(start+block, len(a))
        negative = np.minimum((bp[None, :]-ap[start:stop, None]-clearance_m)/scale_m, 0.)
        loss += float(negative.ravel() @ negative.ravel())
        left_coeff[start:stop] = -2*negative.sum(axis=1)/scale_m
        right_coeff += 2*negative.sum(axis=0)/scale_m
    left_gradient = left_coeff[:, None]*n; right_gradient = right_coeff[:, None]*n
    if not np.isfinite(loss) or not np.isfinite(left_gradient).all() or not np.isfinite(right_gradient).all():
        raise ValueError('Nonfinite complete pair objective')
    return dict(loss=loss, left_gradient=left_gradient, right_gradient=right_gradient,
                projected_gap_m=float(bp.min()-ap.max()),
                report=dict(left_vertices=len(a), right_vertices=len(b), pair_rows=len(a)*len(b),
                            block_rows=block, estimated_working_bytes=working,
                            maximum_working_bytes=maximum_working_bytes,
                            all_pairs_retained=True, both_region_gradients=True,
                            quality_approved=False, release_approved=False))


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
