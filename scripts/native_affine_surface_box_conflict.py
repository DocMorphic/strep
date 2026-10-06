"""A fixed affine surface row can be unreachable within a declared delta box.

This is a diagnostic of the supplied local guidance, not of nonlinear mesh
separation. Ignoring native constraints makes the box relaxation larger; one
conflicting row suffices to rule out zero excess for this affine target.
"""
from fractions import Fraction
import hashlib
import numpy as np
from scipy import sparse

SCHEMA = 'strep-native-affine-surface-box-conflict-v1'


def _inputs(gaps, jacobian, lower, upper, clearance, scale):
    arrays = [np.asarray(a) for a in (gaps, lower, upper)]
    if any(a.dtype.kind not in 'fiu' for a in arrays):
        raise ValueError('Real finite represented Float64 arrays required')
    gaps, lower, upper = [np.asarray(a, dtype=np.float64) for a in arrays]
    if sparse.issparse(jacobian):
        if (jacobian.format not in ('csr', 'csc') or not jacobian.has_canonical_format
                or jacobian.dtype.kind not in 'fiu'):
            raise ValueError('Canonical real CSR or CSC Jacobian required')
    elif np.asarray(jacobian).dtype.kind not in 'fiu':
        raise ValueError('Real finite Jacobian required')
    jacobian = sparse.csr_matrix(jacobian, dtype=np.float64)
    if (gaps.ndim != 1 or not 1 <= len(gaps) <= 400000
            or lower.ndim != 1 or not 1 <= len(lower) <= 96
            or len(gaps)*len(lower) > 40000000 or upper.shape != lower.shape
            or jacobian.shape != (len(gaps), len(lower))
            or any(not np.isfinite(a).all() for a in (gaps, lower, upper, jacobian.data))
            or np.any(lower > upper)
            or type(clearance) not in (int, float) or not np.isfinite(clearance) or clearance < 0
            or type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0):
        raise ValueError('Complete finite affine rows, ordered delta box and positive scale required')
    digest = hashlib.sha256()
    for a in (gaps, jacobian.data, jacobian.indices.astype(np.int64), jacobian.indptr.astype(np.int64),
              lower, upper, np.array([clearance, scale], dtype=np.float64)):
        a = np.ascontiguousarray(a)
        digest.update(np.asarray(a.shape, np.int64).tobytes())
        digest.update(a.dtype.str.encode()); digest.update(a.tobytes())
    return gaps, jacobian, lower, upper, digest.hexdigest()


def _rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def _witness(gaps, jacobian, lower, upper, index, clearance, scale):
    row = jacobian.getrow(index)
    # Each independent scalar term is maximized at its sign-selected endpoint.
    # Fraction.from_float evaluates the represented inputs exactly, including
    # cancellation, subnormals and results outside the Float64 range.
    point = lower.copy()
    point[row.indices[row.data > 0]] = upper[row.indices[row.data > 0]]
    maximum = Fraction.from_float(float(gaps[index]))
    for column, coefficient in zip(row.indices, row.data):
        maximum += Fraction.from_float(float(coefficient))*Fraction.from_float(float(point[column]))
    deficit = Fraction.from_float(float(clearance))-maximum
    if deficit <= 0:
        raise ValueError('Exact conflicting witness required')
    return dict(row_index=int(index), maximizing_delta=point.tolist(),
        maximum_gap_exact=_rational(maximum), required_clearance_exact=_rational(Fraction.from_float(float(clearance))),
        unavoidable_gap_deficit_exact=_rational(deficit),
        normalized_surface_excess_lower_bound_exact=_rational(deficit/Fraction.from_float(float(scale))))


def diagnose(gaps, jacobian, lower, upper, *, clearance=0., scale=.005):
    """Return all outward row maxima and, when found, an exact conflict witness.

    Bounds cover every original scalar row; overflow/uncertain arithmetic gives
    +inf, never a false certificate. Failure to find a conflicting individual
    row says nothing about feasibility of their intersection or native motion.
    The caller must establish that this box encloses its permitted local step.
    """
    gaps, jacobian, lower, upper, digest = _inputs(gaps, jacobian, lower, upper, clearance, scale)
    bound = gaps.copy(); columns = jacobian.tocsc()
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        for column in range(len(lower)):
            start, end = columns.indptr[column:column+2]
            rows = columns.indices[start:end]; coefficients = columns.data[start:end]
            endpoints = np.where(coefficients > 0, upper[column], lower[column])
            active = (coefficients != 0) & (endpoints != 0)
            rows = rows[active]; coefficients = coefficients[active]; endpoints = endpoints[active]
            products = np.nextafter(coefficients*endpoints, np.inf)
            sums = np.nextafter(bound[rows]+products, np.inf)
            bound[rows] = np.where(np.isnan(sums), np.inf, sums)
    conflict = bound < clearance
    index = int(np.argmin(bound)) if conflict.any() else None
    report = dict(schema=SCHEMA, affine_inputs_sha256=digest,
        status='CertifiedAffineRowConflict' if index is not None else 'NoCertifiedIndividualRowConflict',
        original_rows=len(gaps), controls=len(lower), all_original_rows_scanned=True,
        certified_individual_conflict_rows=int(conflict.sum()), unbounded_upper_rows=int(np.isinf(bound).sum()),
        clearance_m=float(clearance), scale_m=float(scale),
        witness=_witness(gaps, jacobian, lower, upper, index, clearance, scale) if index is not None else None,
        native_feasibility_checked=False, nonlinear_geometry_infeasibility_proven=False,
        quality_approved=False, release_approved=False,
        scope='Conflict of supplied fixed affine scalar surface guidance within the declared delta box. '
              'Native constraints are ignored. A witness rules out zero excess for this local affine target, '
              'not other separating axes, relinearized guidance, nonlinear motion or the full authored control range. '
              'No individual conflict found does not prove simultaneous affine or native feasibility.')
    return bound, report


def verify_witness(report, gaps, jacobian, lower, upper, *, clearance=0., scale=.005):
    """Bind the complete inputs and verify only the selected exact certificate.

    This does not independently re-scan or verify the aggregate screening count.
    """
    gaps, jacobian, lower, upper, digest = _inputs(gaps, jacobian, lower, upper, clearance, scale)
    witness = report.get('witness')
    if (report.get('schema') != SCHEMA or report.get('affine_inputs_sha256') != digest
            or report.get('status') != 'CertifiedAffineRowConflict' or not isinstance(witness, dict)
            or type(witness.get('row_index')) is not int or not 0 <= witness['row_index'] < len(gaps)
            or report.get('original_rows') != len(gaps) or report.get('controls') != len(lower)
            or report.get('clearance_m') != clearance or report.get('scale_m') != scale
            or report.get('all_original_rows_scanned') is not True
            or any(report.get(k) is not False for k in ('native_feasibility_checked',
                'nonlinear_geometry_infeasibility_proven', 'quality_approved', 'release_approved'))):
        raise ValueError('Bound local affine conflict report required')
    exact = _witness(gaps, jacobian, lower, upper, witness['row_index'], clearance, scale)
    if witness != exact:
        raise ValueError('Exact conflicting witness changed')
    return dict(selected_exact_row_conflict_verified=True, complete_inputs_digest_bound=True,
        aggregate_screening_count_independently_verified=False,
        nonlinear_geometry_infeasibility_proven=False, quality_approved=False, release_approved=False)
