"""Box-constrained knee smoothing for an explicitly authored stance interval.

Native-key clearance bounds do not imply serialized or continuous clearance.
This is a geometric proposal, not a balance model or a naturalness judgment.
"""
import numpy as np
from scipy.optimize import minimize
from elbow_swivel import local_transforms


def corridor(worlds, parents, chain, heights, *, up=(0., 1., 0.),
             clearance=.00025, maximum_height=.00475, maximum_lift=.03):
    worlds = np.asarray(worlds, float); heights = np.asarray(heights, float)
    parents = np.asarray(parents); up = np.asarray(up, float); chain = list(chain)
    if (worlds.ndim != 4 or worlds.shape[1:] != (len(parents), 4, 4)
            or len(worlds) < 3 or heights.shape != (len(worlds),)
            or not np.isfinite(worlds).all() or not np.isfinite(heights).all()):
        raise ValueError('Finite native worlds and matching heights required')
    if (len(chain) != 3 or len(set(chain)) != 3
            or any(not isinstance(n, (int, np.integer)) or not 0 <= n < len(parents) for n in chain)
            or parents[chain[1]] != chain[0] or parents[chain[2]] != chain[1]):
        raise ValueError('Direct thigh/knee/foot chain required')
    if up.shape != (3,) or not np.isfinite(up).all() or abs(np.linalg.norm(up)-1) > 1e-8:
        raise ValueError('Unit floor normal required')
    if (not np.isfinite([clearance, maximum_height, maximum_lift]).all()
            or not 0 <= clearance < maximum_height or maximum_lift <= 0):
        raise ValueError('Finite ordered stance height bounds required')
    for world in worlds:
        local_transforms(world, parents)  # Reject scale/shear, even for zero lift.
    points = worlds[:, :, :3, 3][:, chain]
    lengths = np.linalg.norm(np.diff(points, axis=1), axis=2)
    if np.any(lengths <= 1e-8):
        raise ValueError('Positive source leg lengths required at every key')
    # Preserve exact animated translations, including float32 key variation.
    a, b = lengths.T
    delta = points[:, 2]-points[:, 0]; vertical = delta@up
    horizontal_squared = np.sum((delta-vertical[:, None]*up)**2, axis=1)
    lower_lift = np.maximum(0., clearance-heights)
    upper_lift = np.minimum(maximum_lift, maximum_height-heights)
    if np.any(lower_lift > upper_lift) or np.any(vertical+upper_lift >= -1e-8):
        raise ValueError('Infeasible stance corridor or ankle not below hip')
    far_squared = horizontal_squared+(vertical+lower_lift)**2
    near_squared = horizontal_squared+(vertical+upper_lift)**2
    if np.any(near_squared < (a-b)**2) or np.any(far_squared > (a+b)**2+1e-12):
        raise ValueError('Unreachable stance corridor')
    def bend(distance_squared):
        cosine = (distance_squared-a*a-b*b)/(2*a*b)
        return np.arccos(np.clip(cosine, -1., 1.))
    return dict(lower=bend(far_squared), upper=bend(near_squared),
                lower_lift=lower_lift, upper_lift=upper_lift, vertical=vertical,
                horizontal_squared=horizontal_squared, lengths=lengths)


def smooth(times, lower, upper, *, acceleration_time=.15, reference_weight=.5):
    """Minimize integrated velocity, acceleration and minimal-lift deviation.

    The physical clock weights include irregular native intervals. Endpoints are
    free inside the same hard box. Reference weight is in inverse seconds squared.
    """
    times, lower, upper = [np.asarray(v, float) for v in (times, lower, upper)]
    if (times.ndim != 1 or len(times) < 3 or lower.shape != times.shape or upper.shape != times.shape
            or not np.isfinite([times, lower, upper]).all() or np.any(np.diff(times) <= 0)
            or np.any(lower < 0) or np.any(upper > np.pi) or np.any(lower > upper)):
        raise ValueError('Increasing finite clock and ordered bend boxes required')
    if (not np.isfinite([acceleration_time, reference_weight]).all()
            or acceleration_time < 0 or reference_weight <= 0):
        raise ValueError('Nonnegative acceleration time and positive reference weight required')
    n = len(times); dt = np.diff(times); midpoint_dt = (dt[:-1]+dt[1:])/2
    velocity = np.zeros((n-1, n)); rows = np.arange(n-1)
    velocity[rows, rows] = -1/dt; velocity[rows, rows+1] = 1/dt
    acceleration = np.diff(velocity, axis=0)/midpoint_dt[:, None]
    weights = np.r_[dt[0]/2, midpoint_dt, dt[-1]/2]
    reference = reference_weight*weights
    hessian = (velocity.T@(dt[:, None]*velocity)
               + acceleration_time**2*acceleration.T@(midpoint_dt[:, None]*acceleration)
               + np.diag(reference))
    linear = reference*lower
    # Scale the numerical objective only; its physical minimizer is unchanged.
    scale = float(np.diag(hessian).max()); h = hessian/scale; b = linear/scale
    def value(x):
        return float(x@h@x-2*b@x), 2*(h@x-b)
    result = minimize(value, lower.copy(), jac=True, method='L-BFGS-B',
                      bounds=list(zip(lower, upper)),
                      options=dict(ftol=1e-15, gtol=1e-11, maxiter=5000, maxls=40))
    x = result.x; gradient = value(x)[1]
    residual = float(np.abs(x-np.clip(x-gradient, lower, upper)).max())
    if not result.success or residual > 1e-7 or np.any(x < lower) or np.any(x > upper):
        raise ValueError(f'Bend optimization did not converge: {result.message}; residual={residual}')
    velocity_term = float(np.sum(dt*(velocity@x)**2))
    acceleration_term = float(acceleration_time**2*np.sum(midpoint_dt*(acceleration@x)**2))
    reference_term = float(np.sum(reference*(x-lower)**2))
    return x, dict(success=True, message=str(result.message), iterations=int(getattr(result, 'nit', 0)),
                   projected_gradient_residual=residual, numerical_scale=scale,
                   acceleration_time_s=acceleration_time, reference_weight_per_s2=reference_weight,
                   velocity_term=velocity_term, acceleration_term=acceleration_term,
                   reference_term=reference_term,
                   objective=velocity_term+acceleration_term+reference_term)


def lifts(box, bends):
    bends = np.asarray(bends, float)
    if (bends.shape != box['lower'].shape or not np.isfinite(bends).all()
            or np.any(bends < box['lower']) or np.any(bends > box['upper'])):
        raise ValueError('Bends outside authored corridor')
    a, b = box['lengths'].T
    vertical_squared = a*a+b*b+2*a*b*np.cos(bends)-box['horizontal_squared']
    if np.any(vertical_squared <= 0):
        raise ValueError('Invalid smoothed ankle height')
    result = -np.sqrt(vertical_squared)-box['vertical']
    if np.any(result < box['lower_lift']-1e-10) or np.any(result > box['upper_lift']+1e-10):
        raise ValueError('Smoothed lift outside authored corridor')
    # Only remove floating-point roundoff at exact endpoints, never widen bounds.
    return np.clip(result, box['lower_lift'], box['upper_lift'])


def rate_score(values, caps, columns, tolerance=1e-5):
    """Diagnostic leg-only excess objective; never changes acceptance caps."""
    columns = np.asarray(columns)
    if (len(values) != 4 or len(caps) != 4 or columns.ndim != 1 or not len(columns)
            or columns.dtype.kind not in 'iu' or len(np.unique(columns)) != len(columns)
            or not np.isfinite(tolerance) or tolerance < 0):
        raise ValueError('Four rates, distinct joint columns and finite tolerance required')
    terms = []
    for actual, cap, floor in zip(values, caps, (.05, .5, .1, 1.)):
        actual, cap = np.asarray(actual, float), np.asarray(cap, float)
        if (actual.ndim != 2 or actual.shape != cap.shape or not all(actual.shape)
                or not np.isfinite(actual).all() or not np.isfinite(cap).all()
                or np.any(actual < 0) or np.any(cap < 0)
                or np.any(columns < 0) or np.any(columns >= actual.shape[1])):
            raise ValueError('Matching nonnegative rates/caps and in-range columns required')
        excess = np.maximum(0., actual[:, columns]-cap[:, columns]-tolerance)
        terms.append(float(np.mean((excess/np.maximum(cap[:, columns], floor))**2)))
    return dict(score=sum(terms), terms=terms,
                denominator_floors=[.05, .5, .1, 1.],
                note='Leg-only normalized excess for proposal ranking; original acceptance caps unchanged')
