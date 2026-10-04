"""Empirical proposal reserves conditioned on an explicit control trust box.

Every protected row is retained. Larger trials remain in the receipt but do not
set a smaller-box envelope. This is observed-error calibration, not a bound on
unobserved directions; decoded source limits still decide motion acceptance.
"""
import numpy as np
from measured_proposal_reserve import _observations, tighten
from budgeted_native_conic import direction
from native_scene_norms import NormRows


def tighten_in_box(system, predicted, actual, observed_deltas, trust, hard_rows, *, factor=1.):
    """Calibrate complete rows from trials inside the declared infinity-norm box.

    All arrays must belong to the same derivative origin, model and closed-trial
    ordering. Callers must establish those identities from immutable evidence.
    No error extrapolation or radius scaling is performed.
    """
    if type(trust) not in (int, float) or not np.isfinite(trust) or trust <= 0:
        raise ValueError('A finite positive control trust radius is required')
    predicted = _observations(predicted, 'Predictions')
    actual = _observations(actual, 'Closed observations')
    deltas = _observations(observed_deltas, 'Observed control deltas')
    if (predicted.shape != actual.shape or len(deltas) != len(predicted)
            or not len(deltas) or not deltas.shape[1]):
        raise ValueError('Matching complete trials and nonempty control deltas required')
    # Validate complete row populations even for out-of-box trials. An excluded
    # trial must not conceal incomplete, nonfinite or misordered input data.
    if type(hard_rows) is not int or predicted.shape[1] != hard_rows:
        raise ValueError('Every observation needs the complete protected prefix')
    radii = np.abs(deltas).max(axis=1)
    inside = radii <= trust
    if not inside.any():
        raise ValueError('No closed observation within this trust box; calibration unavailable')
    model, reserves, receipt = tighten(system, predicted[inside], actual[inside], hard_rows, factor=factor)
    receipt = dict(receipt, schema='strep-trust-box-reserve-v1',
        trust_control_fraction=float(trust), control_components=deltas.shape[1],
        supplied_observed_trials=len(deltas), observed_maximum_control_steps=radii.tolist(),
        selected_trial_indices=np.flatnonzero(inside).tolist(),
        outside_box_trial_indices=np.flatnonzero(~inside).tolist(),
        selection='All observations with maximum absolute source-origin delta <= declared trust',
        error_extrapolation=False, smaller_radius_error_scaling=False,
        same_origin_and_closed_trial_association_required=True)
    return model, reserves, receipt


def propose(system, jacobian, value, lower, upper, trust, actual, observed_deltas,
            *, hard_rows, factor=1., phase_seconds=120., maximum_iterations=200):
    """Use exactly the calibration trust box for a bounded conic proposal.

    Historical samples must fit the authored boxes at this same model origin.
    Predictions are recomputed from that original model and Jacobian.
    A solver result is a proposal; it cannot approve an exported animation.
    """
    if not isinstance(system, NormRows) or type(hard_rows) is not int or not 1 <= hard_rows <= len(system.caps):
        raise ValueError('An original norm model and complete protected prefix required')
    value, lower, upper = [np.asarray(a) for a in (value, lower, upper)]
    if (value.ndim != 1 or not len(value) or lower.shape != value.shape or upper.shape != value.shape
            or any(a.dtype.kind not in 'fiu' or not np.isfinite(a).all() for a in (value, lower, upper))
            or np.any(lower >= upper) or np.any(value < lower) or np.any(value > upper)):
        raise ValueError('Finite matching control origin and authored boxes required')
    deltas = _observations(observed_deltas, 'Observed control deltas')
    if deltas.shape[1] != len(value):
        raise ValueError('Observed deltas must match every source-origin control component')
    if not len(deltas):
        raise ValueError('At least one complete closed trial required')
    with np.errstate(over='ignore', invalid='ignore'):
        samples = value.astype(float) + deltas
    if not np.isfinite(samples).all() or np.any(samples < lower) or np.any(samples > upper):
        raise ValueError('Historical closed controls lie outside these source-origin authored boxes')
    predicted = np.stack([system.residual(jacobian, delta)[:hard_rows] for delta in deltas])
    model, reserves, receipt = tighten_in_box(system, predicted, actual, deltas, trust, hard_rows, factor=factor)
    delta, solver = direction(model, jacobian, value, lower, upper, trust,
        hard_rows=hard_rows, phase_seconds=phase_seconds, maximum_iterations=maximum_iterations)
    if delta is not None and np.any(np.abs(delta) > trust):
        # The historical solver permits numerical box tolerance. Calibration
        # membership is exact, so do not extrapolate even by one floating ULP.
        solver = dict(solver, calibration_box_rejected=True, rejected_delta=np.asarray(delta).tolist(),
                      rejection='Returned step exceeds the exact calibration trust box')
        delta = None
    # Retain failures. Neither infeasible proposals nor calibration failures
    # authorize relaxing caps, widening the trust box or switching source origin.
    return delta, dict(calibration=receipt, solver=solver, predictions_recomputed_from_original_model=True,
        calibration_and_solver_trust_identical=True, original_source_limits_changed=False,
        independently_decoded_candidate_required=True, quality_approved=False, release_approved=False)
