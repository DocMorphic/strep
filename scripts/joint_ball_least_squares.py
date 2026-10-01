"""Least-squares proposals in joint rotation balls with feasible result replay."""
import numpy as np
from scipy.optimize import minimize

BOX_RADIUS = np.nextafter(1./np.sqrt(3), 0.)


def margins(point):
    point = np.asarray(point, float)
    if point.ndim != 1 or not len(point) or len(point) % 3 or not np.isfinite(point).all():
        raise ValueError('Finite triples of normalized joint controls required')
    return 1.-np.sum(point.reshape(-1, 3)**2, axis=1)


def margin_jacobian(point):
    margins(point)
    point = np.asarray(point, float)
    jac = np.zeros((len(point)//3, len(point)))
    for i in range(len(jac)): jac[i, 3*i:3*i+3] = -2.*point[3*i:3*i+3]
    return jac


def feasible_projection(point, *, ball):
    margins(point)
    if type(ball) is not bool: raise ValueError('Explicit boolean constraint shape required')
    values = np.asarray(point, float).reshape(-1, 3).copy()
    if ball:
        norms = np.linalg.norm(values, axis=1)
        outside = (norms > 1.) | (margins(values.ravel()) < 0)
        # Replay after inward projection; never reinterpret solver tolerance
        # as extra joint angle allowance. The reserve avoids outward roundoff.
        values[outside] *= ((1.-1e-12)/norms[outside])[:, None]
    else:
        values = np.clip(values, -BOX_RADIUS, BOX_RADIUS)
    return values.ravel()


def solve(residual, initial, *, ball=True, iterations=80, observe=None):
    point = np.asarray(initial, float).copy()
    margins(point)
    if (type(ball) is not bool or type(iterations) is not int or not 1 <= iterations <= 200
            or np.any(margins(point) < 0)
            or (not ball and np.any(np.abs(point) > BOX_RADIUS))):
        raise ValueError('Feasible start, explicit constraint shape and 1-200 iterations required')
    population = [None]; calls = [0]
    def cost(x):
        values = np.asarray(residual(np.asarray(x, float)), float)
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
            raise ValueError('Finite nonempty residual vector required')
        if population[0] is None: population[0] = values.shape
        if values.shape != population[0]: raise ValueError('Fixed residual population required')
        calls[0] += 1
        value = float(.5*(values@values))
        if not np.isfinite(value): raise ValueError('Finite residual cost required')
        return value
    initial_cost = cost(point); best = point.copy(); best_cost = initial_cost; history = []
    scale = max(1., initial_cost)
    def consider(candidate):
        nonlocal best, best_cost
        projected = feasible_projection(candidate, ball=ball)
        value = cost(projected)
        if value < best_cost:
            best, best_cost = projected.copy(), value
        record = dict(iteration=len(history)+1, replay_cost=value, best_cost=best_cost,
            minimum_joint_margin=float(margins(projected).min()),
            projection_distance=float(np.linalg.norm(projected-candidate)))
        history.append(record)
        if observe: observe(record)
    bound = 1. if ball else BOX_RADIUS
    constraint = dict(type='ineq', fun=margins, jac=margin_jacobian)
    result = minimize(lambda x: cost(x)/scale, point, method='SLSQP', jac='3-point',
        bounds=[(-bound, bound)]*len(point), constraints=[constraint] if ball else (),
        callback=consider, options=dict(maxiter=iterations, ftol=1e-10))
    consider(result.x)
    if np.any(margins(best) < 0) or (not ball and np.any(np.abs(best) > bound)):
        raise ValueError('Returned controls exceeded original joint budget')
    final_cost = cost(best)
    if final_cost > initial_cost: raise ValueError('Returned proposal lost best feasible result')
    return best, dict(method='SLSQP', constraint_shape='joint_balls' if ball else 'inscribed_component_boxes',
        optimizer_success=bool(result.success), status=int(result.status), message=str(result.message),
        iterations=int(result.nit), iterations_limit=iterations, residual_calls=calls[0],
        objective_scale=scale, initial_cost=initial_cost, final_cost=final_cost, history=history,
        minimum_joint_margin=float(margins(best).min()), quality_approved=False)
