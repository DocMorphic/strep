"""Necessary sampled stationary-pin/rate checks, independent of the pose solver.

Each XYZ component is relaxed to a linear program. Only an independently
verified bounded-domain certificate can establish a conflict. No joint, skin,
collision, force or animation-quality feasibility follows from a missing one.
"""
from fractions import Fraction
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, hstack


def number(value):
    return Fraction.from_float(float(value))


def upper_float(value):
    result = float(value)
    return result if number(result) >= value else float(np.nextafter(result, np.inf))


def certificate(matrix, rhs, radius, multipliers):
    """Exact arithmetic on supplied binary64 data, including stationarity error.

    If Az<=b, |z|<=B and y>=0 then -B||A^T y||_1 <= y^T Az <= y^T b.
    Thus y^T b+B||A^T y||_1 < 0 is a contradiction, without assuming A^T y=0.
    """
    matrix = csr_matrix(matrix);rhs = np.asarray(rhs, float);y = np.asarray(multipliers, float)
    if rhs.shape != (matrix.shape[0],) or y.shape != rhs.shape or not matrix.shape[1]:
        raise ValueError('Matching nonempty certificate arrays required')
    if not np.isfinite(matrix.data).all() or not np.isfinite(rhs).all() or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Finite data and nonnegative certificate multipliers required')
    if isinstance(radius, bool) or not np.isfinite(radius) or radius <= 0:
        raise ValueError('Positive finite coordinate radius required')
    coefficients = [Fraction(0) for _ in range(matrix.shape[1])]
    weighted = Fraction(0)
    for row in np.flatnonzero(y):
        weight = number(y[row]);weighted += weight*number(rhs[row])
        for pos in range(matrix.indptr[row], matrix.indptr[row+1]):
            coefficients[matrix.indices[pos]] += weight*number(matrix.data[pos])
    residual = sum(map(abs, coefficients), Fraction(0))
    bound = weighted+number(radius)*residual
    return dict(conflict_verified=bool(bound < 0), contradiction_upper_bound_m=float(bound),
                contradiction_upper_bound_exact=str(bound), weighted_rhs_exact=str(weighted),
                stationarity_residual_l1_exact=str(residual), coordinate_radius_m=float(radius),
                nonzero_multipliers=[dict(row=int(i), weight=float(y[i])) for i in np.flatnonzero(y)])


def assemble(track, pins, rates, window, *, tolerance=.005, preservation_budget=1e-6):
    """Build independent component relaxations on the exact audit sample clock.

    Source samples strictly outside the window retain the audit's position
    budget. Endpoint samples are NOT fixed: native held keys alone need not make
    a decoded quarter-frame endpoint identical after timestamp quantization.
    """
    track = np.asarray(track, float)
    if track.ndim != 2 or track.shape[1] != 3 or len(track) < 13 or (len(track)-1) % 4 or not np.isfinite(track).all():
        raise ValueError('Complete finite XYZ quarter-frame source track required')
    frames = (len(track)-1)//4+1
    if not 4 <= frames <= 901 or not isinstance(window, (list, tuple)) or len(window) != 2 or any(type(v) is not int for v in window):
        raise ValueError('Supported native clock and two integer held boundaries required')
    if not 1 <= window[0] < window[1] <= frames-2:
        raise ValueError('Interior ordered edit window required')
    for value in [tolerance, preservation_budget]:
        if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
            raise ValueError('Finite nonnegative position budgets required')
    if not pins or not rates:
        raise ValueError('Stationary pins and complete phase rate limits required')
    n = len(track);entries=[];rhs=[];labels=[]
    # This tiny outward reserve belongs only to the necessary-condition test.
    reserve = number(1e-12)

    def pair(indices, coefficients, center, radius, label):
        center = [number(v) for v in center]
        radius = radius if isinstance(radius, Fraction) else number(radius)
        for sign in [1, -1]:
            row = len(rhs)
            entries.extend((row, int(i), sign*float(c)) for i, c in zip(indices, coefficients))
            rhs.append([upper_float(sign*v+radius+reserve) for v in center])
            labels.append(dict(label, sign=sign))

    times = np.arange(n)/4
    for i in np.flatnonzero((times < window[0]) | (times > window[1])):
        pair([i], [1], track[i], preservation_budget, dict(kind='held', frame=float(times[i])))
    for pin in pins:
        a, b = pin['start_frame'], pin['end_frame']
        target = np.asarray(pin['position_m'], float)
        if type(a) is not int or type(b) is not int or not window[0] < a < b < window[1] or pin.get('space') != 'world' or target.shape != (3,) or not np.isfinite(target).all():
            raise ValueError('Stationary nonempty pins strictly inside the window required')
        for i in range(a*4, b*4+1):
            pair([i], [1], target, tolerance, dict(kind='pin', frame=i/4))
    coverage = [np.zeros(n-order, bool) for order in [1, 2]]
    maxima = [0., 0.]
    for row in rates:
        a, b = row['first_frame'], row['last_frame']
        caps = row['reference_ceilings']
        if type(a) is not int or type(b) is not int or not window[0] <= a < b <= window[1] or len(caps) != 2:
            raise ValueError('Phase range and paired rate ceilings required')
        for order, cap in enumerate(caps, 1):
            if type(cap) not in (int, float) or not np.isfinite(cap) or cap < 0:
                raise ValueError('Finite nonnegative rate ceiling required')
            maxima[order-1] = max(maxima[order-1], cap)
            centers = (np.arange(n-order)+order/2)/4
            mask = (centers >= a) & (centers <= b)
            coverage[order-1] |= mask
            for i in np.flatnonzero(mask):
                pair(range(i, i+order+1), [-1, 1] if order == 1 else [1, -2, 1],
                     [0, 0, 0], number(cap)/120**order,
                     dict(kind='speed' if order == 1 else 'acceleration', phase=row.get('phase'), frame=float(centers[i])))
    for order in [1, 2]:
        centers = (np.arange(n-order)+order/2)/4
        needed = (centers >= window[0]) & (centers <= window[1])
        if not coverage[order-1][needed].all():
            raise ValueError('Rate coverage has gaps; a bounded-domain certificate would be invalid')
    rr, cc, data = zip(*entries)
    matrix = coo_matrix((data, (rr, cc)), shape=(len(rhs), n)).tocsr()
    # The first interior speed and boundary acceleration anchor the free track
    # to its preceding preserved sample. Remaining speed steps telescope. The
    # extra metre covers the accumulated 1e-12 row reserves on <=3601 samples.
    radius = upper_float(number(float(np.abs(track).max()))+number(preservation_budget)+
                         number(maxima[0])*(Fraction(frames, 30)+Fraction(2, 120))+
                         number(maxima[1])/120**2+1)
    return matrix, np.asarray(rhs), radius, labels


def analyze(track, pins, rates, window):
    matrix, rhs, radius, labels = assemble(track, pins, rates, window)
    n = matrix.shape[1];augmented = hstack([matrix, -np.ones((matrix.shape[0], 1))], format='csr')
    reports=[];solutions=[];weights=[]
    for axis in range(3):
        fit = linprog(np.r_[np.zeros(n), 1.], A_ub=augmented, b_ub=rhs[:, axis],
                      bounds=[(-radius, radius)]*n+[(0, None)], method='highs',
                      options=dict(primal_feasibility_tolerance=1e-9, dual_feasibility_tolerance=1e-9, time_limit=30.))
        row = dict(axis='XYZ'[axis], solver_status=int(fit.status), solver_message=str(fit.message), conflict_verified=False)
        y = np.zeros(matrix.shape[0])
        solution = np.full(n, np.nan)
        if fit.success:
            solution = fit.x[:n]
            y = np.maximum(0., -fit.ineqlin.marginals)
            proof = certificate(matrix, rhs[:, axis], radius, y)
            row.update(proof, minimum_common_relaxation_m=float(fit.x[-1]),
                       maximum_row_violation_m=float(np.maximum(0., matrix@solution-rhs[:, axis]).max()))
            row['certificate_rows'] = [dict(labels[v['row']], **v) for v in proof['nonzero_multipliers']]
        reports.append(row);solutions.append(solution);weights.append(y)
    return dict(axes=reports, any_verified_conflict=any(r['conflict_verified'] for r in reports),
                scope='Necessary componentwise stationary-pin/speed/acceleration relaxation with preserved outside samples. No conflict is not feasibility or quality approval.',
                quality_approved=False), dict(matrix=matrix, rhs=rhs, radius=radius,
                                             solutions=np.array(solutions), multipliers=np.array(weights))
