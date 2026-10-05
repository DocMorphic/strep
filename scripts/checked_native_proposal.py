"""Check full protected affine rows after exact control projection/backoff.

The legacy solver remains unchanged. A returned candidate is an affine proposal,
never an approval of decoded animation, contacts or geometry.
"""
import numpy as np
from native_scene_norms import NormRows
from budgeted_native_conic import direction as legacy_direction
from cumulative_coupled_contacts import backoff_controls


def _inputs(system, jacobian, value, lower, upper, trust, hard_rows, backoffs):
    if not isinstance(system, NormRows):
        raise ValueError('Complete norm model required')
    if type(hard_rows) is not int or not 0 <= hard_rows <= len(system.caps):
        raise ValueError('Complete protected row prefix required')
    if type(backoffs) is not int or not 1 <= backoffs <= 16:
        raise ValueError('Choose 1-16 explicit affine backoffs')
    value, lower, upper = [np.asarray(a, float) for a in (value, lower, upper)]
    if (value.ndim != 1 or not len(value) or lower.shape != value.shape or upper.shape != value.shape
            or any(not np.isfinite(a).all() for a in (value, lower, upper))
            or np.any(lower >= upper) or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or trust <= 0):
        raise ValueError('Finite complete control origin, authored boxes and positive trust required')
    base = system.residual(jacobian, np.zeros_like(value))
    if base.shape != (len(system.caps),) or not np.isfinite(base).all():
        raise ValueError('Complete finite affine anchor residuals required')
    return value, lower, upper, base


def _score(residual):
    positive = np.maximum(residual, 0.)
    with np.errstate(over='ignore', invalid='ignore'):
        result = [float(positive.max()) if len(positive) else 0., float(positive@positive)]
    if not np.isfinite(result).all():
        raise ValueError('Finite complete affine score required')
    return result


def select(system, jacobian, value, lower, upper, trust, raw_delta, *, hard_rows=0, backoffs=10):
    value, lower, upper, base = _inputs(system, jacobian, value, lower, upper, trust, hard_rows, backoffs)
    raw = np.asarray(raw_delta, float)
    if raw.shape != value.shape or not np.isfinite(raw).all():
        raise ValueError('Matching complete finite raw direction required')
    before = _score(base[hard_rows:])
    record = dict(schema='strep-checked-affine-proposal-v1', complete_rows=len(base), protected_rows=hard_rows,
        soft_rows=len(base)-hard_rows, origin_protected_failed_rows=int((base[:hard_rows] > 0).sum()),
        origin_soft_score=before, raw_delta=raw.tolist(), raw_maximum_control_step=float(abs(raw).max()),
        trust_control_fraction=float(trust), requested_affine_backoffs=backoffs, trials=[],
        selected_backoff=None, selected_controls=None, selected_delta=None,
        strict_affine_feasibility_checked=True, protected_slack_added=False,
        authored_boxes_changed=False, caps_changed=False, decoded_animation_required=True,
        quality_approved=False, release_approved=False)
    if np.any(base[:hard_rows] > 0):
        return None, dict(record, selection_status='InfeasibleAffineAnchor',
            scope='Current affine anchor violates a protected row; no global physical infeasibility claim.')
    chosen = None
    for index in range(backoffs):
        fraction = .5**index
        candidate = backoff_controls(value, raw, lower, upper, trust, fraction)
        delta = candidate-value
        if np.any(abs(delta) > fraction*trust) or np.any(candidate < lower) or np.any(candidate > upper):
            raise ValueError('Projected controls escaped an exact original box')
        residual = system.residual(jacobian, delta)
        if residual.shape != base.shape or not np.isfinite(residual).all():
            raise ValueError('Complete finite projected affine residuals required')
        after = _score(residual[hard_rows:])
        protected = bool(np.all(residual[:hard_rows] <= 0))
        improves = bool(after[0] <= before[0] and after[1] < before[1]-1e-12)
        item = dict(index=index, fraction=fraction, complete_rows_recomputed=len(residual),
            protected_failed_rows=int((residual[:hard_rows] > 0).sum()),
            protected_maximum_excess=float(residual[:hard_rows].max()) if hard_rows else None,
            soft_score=after, maximum_control_step=float(abs(delta).max()),
            candidate_controls=candidate.tolist(), delta=delta.tolist(), protected_rows_pass=protected,
            soft_objective_improves=improves, chosen=bool(protected and improves))
        record['trials'].append(item)
        if protected and improves:
            chosen = delta
            record.update(selected_backoff=index, selected_controls=candidate.tolist(), selected_delta=delta.tolist())
            break
    return chosen, dict(record, selection_status='Selected' if chosen is not None else 'NoFeasibleImprovingStep',
        scope='Complete floating affine norm rows, strict protected prefix, exact projected control membership '
              'and positive soft-score improvement. No row/cap omission or added feasibility tolerance. '
              'All closed motion/contact/geometry/engine checks remain required.')


def direction(system, jacobian, value, lower, upper, trust, *, hard_rows=0,
              phase_seconds=120., maximum_iterations=200, affine_backoffs=10):
    _inputs(system, jacobian, value, lower, upper, trust, hard_rows, affine_backoffs)
    raw, solver = legacy_direction(system, jacobian, value, lower, upper, trust, hard_rows=hard_rows,
        phase_seconds=phase_seconds, maximum_iterations=maximum_iterations)
    if raw is None:
        return None, dict(solver, checked_affine_proposal=None, independently_decoded_candidate_required=True)
    delta, checked = select(system, jacobian, value, lower, upper, trust, raw,
        hard_rows=hard_rows, backoffs=affine_backoffs)
    return delta, dict(solver, checked_affine_proposal=checked,
        returned_step_maximum_control_fraction=None if delta is None else float(abs(delta).max()),
        returned_direction_available=delta is not None, independently_decoded_candidate_required=True)
