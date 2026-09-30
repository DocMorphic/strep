"""Rebuild bounded hand proposals without rebasing the original motion limits."""
import numpy as np
from hand_norm_proposal import validate, measurement, linearize, direction, backtrack


def solve(exact, smooth, point, solver, *, iterations=6, trusts=(.01, .001, .0001),
          step=1e-4, observe=None, checkpoint=None):
    point = np.asarray(point, float).copy(); trusts = np.asarray(trusts, float)
    if (type(iterations) is not int or not 1 <= iterations <= 12 or point.ndim != 1
            or not len(point) or not np.isfinite(point).all() or np.any(np.abs(point) > 1)
            or trusts.ndim != 1 or not len(trusts) or not np.isfinite(trusts).all()
            or np.any(trusts <= 0) or np.any(trusts > 1)
            or not np.isfinite(step) or not 0 < step < 1):
        raise ValueError('Bounded finite point, positive trust radii/step and 1-12 iterations required')
    original = {key: value.copy() for key, value in validate(exact(point)).items()}
    def bound(function):
        def evaluate(x):
            value = validate(function(x))
            if any(value[key].shape != original[key].shape for key in original):
                raise ValueError('Original motion/witness population changed')
            if any(not np.array_equal(value[key], original[key]) for key in ['caps', 'scales']):
                raise ValueError('Original motion caps/scales changed; rebasing is forbidden')
            return value
        return evaluate
    exact, smooth = bound(exact), bound(smooth)
    initial = measurement(original)
    if initial['minimum_margin'] < 0: raise ValueError('Motion-feasible initial controls required')
    history = []; reason = 'iteration_budget'; current = initial
    for iteration in range(iterations):
        if current['witness_peak_m'] == 0:
            reason = 'zero_witness_depth'; break
        if np.any(np.abs(point)+step > 1):
            reason = 'central_probe_boundary'; break
        def progress(count, total):
            if observe: observe(dict(phase='jacobian', iteration=iteration+1, coordinates=count, total=total))
        try: model = linearize(exact, smooth, point, step, progress)
        except ValueError as error:
            if 'outside two-bone reach' not in str(error): raise
            reason = 'derivative_outside_reach'; break
        current = measurement(model['base']); selected = None; selected_metric = current
        attempts = []
        for trust in trusts:
            delta, report = direction(model, float(trust), solver)
            if delta is not None:
                candidate, trials = backtrack(exact, point, delta, model['base'])
                report['trials'] = trials
                if candidate is not None:
                    metric = measurement(exact(candidate))
                    if metric['witness_peak_m'] < selected_metric['witness_peak_m']:
                        selected, selected_metric = candidate.copy(), metric
            attempts.append(report)
        record = dict(iteration=iteration+1, point_before=point.tolist(), before=current,
                      attempts=attempts, accepted=selected is not None,
                      point_after=(point if selected is None else selected).tolist(), after=selected_metric)
        history.append(record)
        if checkpoint: checkpoint(model, record)
        if observe: observe(dict(phase='iteration', iteration=iteration+1, accepted=record['accepted'], **selected_metric))
        if selected is None:
            reason = 'no_exact_feasible_improvement'; break
        point, current = selected, selected_metric
    final = measurement(exact(point))
    if final['minimum_margin'] < 0 or final['witness_peak_m'] > initial['witness_peak_m']:
        raise ValueError('Final exact replay lost feasibility or objective improvement')
    return point, dict(method='iterated_vector_norm_proposal_v1', iterations_limit=iterations,
        trusts=trusts.tolist(), derivative_step=float(step), history=history, stop_reason=reason,
        before=initial, after=final, final_point=point.tolist(), original_caps_preserved=True,
        quality_approved=False, fresh_geometry_required=True)
