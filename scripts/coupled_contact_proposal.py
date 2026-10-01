"""Joint-ball proposals with hard contact constraints and serialized replay."""
import numpy as np
from scipy.optimize import minimize
from joint_ball_least_squares import margins, margin_jacobian, feasible_projection


def contact_margins(centers, normals, target):
    from shared_palm_meeting import geometry
    centers, normals = geometry(centers, normals)
    desired, desired_normals = geometry(target['centers_m'], target['normals'])
    anchor = float(target['anchor_tolerance_m']); gap = float(target['maximum_gap_m'])
    angle = float(target['normal_tolerance_degrees'])
    if not np.isfinite([anchor, gap, angle]).all() or min(anchor, gap) <= 0 or not 0 < angle < 180:
        raise ValueError('Positive contact distances and an angle inside (0,180) required')
    cosine = np.cos(np.deg2rad(angle))
    return np.r_[1.-np.sum((centers-desired)**2, axis=1)/anchor**2,
        (np.sum(normals*desired_normals, axis=1)-cosine)/(1.-cosine),
        1.-np.sum((centers[0]-centers[1])**2)/gap**2]


def solve(residual, hard, initial, *, replay_residual=None, replay_hard=None, iterations=40, observe=None):
    point = np.asarray(initial, float).copy(); margins(point)
    if type(iterations) is not int or not 1 <= iterations <= 100 or np.any(margins(point) < 0):
        raise ValueError('Feasible joint controls and 1-100 iterations required')
    replay_residual = residual if replay_residual is None else replay_residual
    replay_hard = hard if replay_hard is None else replay_hard
    shapes = {}
    def checked(function, x, key):
        values = np.asarray(function(x), float)
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
            raise ValueError('Finite nonempty residual/contact vectors required')
        shapes.setdefault(key, values.shape)
        if shapes[key] != values.shape: raise ValueError('Fixed residual/contact population required')
        return values
    def cost(function, x):
        values = checked(function, x, 'residual')
        result = float(.5*(values@values))
        if not np.isfinite(result): raise ValueError('Finite residual cost required')
        return result
    def feasible(x):
        return (np.all(margins(x) >= 0) and np.all(checked(hard, x, 'contact') >= 0)
                and np.all(checked(replay_hard, x, 'contact') >= 0))
    if not feasible(point): raise ValueError('Initially feasible smooth and replayed contact required')
    start_cost = cost(replay_residual, point); best = point.copy(); best_cost = start_cost; history = []
    scale = max(1., cost(residual, point))
    def consider(proposal):
        nonlocal best, best_cost
        anchor = best.copy(); attempts = []
        for fraction in [1., .5, .25, .125, .0625, .03125, .015625, .0078125]:
            trial = feasible_projection(anchor+fraction*(proposal-anchor), ball=True)
            passed = feasible(trial)
            value = cost(replay_residual, trial) if passed else None
            accepted = passed and value < best_cost
            attempts.append(dict(fraction=fraction, contact_pass=bool(passed), replay_cost=value, retained=bool(accepted)))
            if accepted:
                best, best_cost = trial.copy(), value
                break
        row = dict(iteration=len(history)+1, best_cost=best_cost, attempts=attempts)
        history.append(row)
        if observe: observe(row)
    result = minimize(lambda x: cost(residual, x)/scale, point, method='SLSQP', jac='3-point',
        bounds=[(-1., 1.)]*len(point), constraints=[dict(type='ineq', fun=margins, jac=margin_jacobian),
            dict(type='ineq', fun=lambda x: checked(hard, x, 'contact'))],
        callback=consider, options=dict(maxiter=iterations, ftol=1e-10))
    consider(result.x)
    if not feasible(best) or cost(replay_residual, best) > start_cost:
        raise ValueError('Final replay lost original contact/budget feasibility')
    return best, dict(optimizer_success=bool(result.success), status=int(result.status), message=str(result.message),
        iterations=int(result.nit), iterations_limit=iterations, initial_cost=start_cost, final_cost=best_cost,
        minimum_joint_margin=float(margins(best).min()), minimum_contact_margin=float(checked(replay_hard, best, 'contact').min()),
        history=history, actual_mesh_validation_required=True, quality_approved=False)
