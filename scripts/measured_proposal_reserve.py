"""Empirical inner reserves for complete protected affine norm populations.

This changes a proposal model only. Observed errors are not a formal bound on
another direction, and exported source constraints remain authoritative.
"""
import numpy as np
from native_scene_norms import NormRows


def _observations(value, name):
    value = np.asarray(value)
    if value.dtype.kind not in 'fiu' or value.ndim != 2 or not np.isfinite(value).all():
        raise ValueError(name + ' requires a complete finite real trial-by-row matrix')
    return value.astype(float, copy=False)


def tighten(system, predicted, actual, hard_rows, *, factor=1.):
    """Keep every row and tighten hard caps by positive observed norm error.

    Predictions and actuals must have the same original model, row ordering,
    scales, derivative origin and complete protected prefix. Caller provenance
    checks establish that association; this arithmetic cannot establish it.
    Return a separate proposal model, full norm-unit reserves and a receipt.
    Soft authored targets and the supplied source model are never modified.
    """
    if not isinstance(system, NormRows):
        raise ValueError('A complete source norm model is required')
    if type(hard_rows) is not int or not 1 <= hard_rows <= len(system.caps):
        raise ValueError('An explicit nonempty complete protected prefix is required')
    if type(factor) not in (int, float) or not np.isfinite(factor) or factor < 1.:
        raise ValueError('A finite empirical reserve factor of at least one is required')
    source = NormRows(system.vectors.copy(), system.caps.copy(), system.scales.copy())
    if np.any(source.caps[:hard_rows] < 0):
        raise ValueError('Negative protected norm radii cannot be tightened')
    predicted, actual = [_observations(a, n) for a, n in
                         ((predicted, 'Predictions'), (actual, 'Closed observations'))]
    if predicted.shape != actual.shape or predicted.shape[1] != hard_rows or not len(predicted):
        raise ValueError('Every closed trial needs every protected row in matching order')
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        error = actual - predicted
        normalized = np.maximum(error.max(axis=0), 0.) * float(factor)
        reserves = normalized * source.scales[:hard_rows]
    if not np.isfinite(error).all() or not np.isfinite(reserves).all() or not np.isfinite(normalized).all():
        raise ValueError('Observed error or reserve arithmetic overflowed')
    positive = error.max(axis=0) > 0
    caps = source.caps.copy()
    # One downward step protects against rounded subtraction and preserves a
    # positive measured reserve even when multiplying it underflows to zero.
    proposed = caps[:hard_rows] - reserves
    proposed[positive] = np.nextafter(proposed[positive], -np.inf)
    if np.any(proposed < 0):
        raise ValueError('Measured reserve exceeds a protected norm radius; no relaxed fallback')
    caps[:hard_rows] = proposed
    result = NormRows(source.vectors, caps, source.scales)
    applied = source.caps[:hard_rows] - proposed
    receipt = dict(schema='strep-measured-proposal-reserve-v1', hard_rows=hard_rows,
        complete_norm_rows=len(caps), complete_observed_trials=len(predicted), factor=float(factor),
        tightened_rows=int(positive.sum()), maximum_norm_reserve=float(applied.max()),
        maximum_normalized_error=float(normalized.max()), source_model_unchanged=True,
        soft_authored_rows_unchanged=True, row_population_and_order_unchanged=True,
        proposal_only=True, formal_error_bound_proven=False, future_directions_covered=False,
        exported_constraints_and_geometry_required=True, quality_approved=False, release_approved=False)
    return result, applied, receipt
