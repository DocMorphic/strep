"""Small linearized feasibility repairs with exact nonlinear acceptance."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, vstack, eye


def linear_step(x, constraints, jacobian, bounds, trust=1e-5, margin=1e-4):
    x, c, j, bounds = map(lambda a: np.asarray(a, float), (x, constraints, jacobian, bounds))
    if x.ndim != 1 or bounds.shape != x.shape or j.shape != (len(c), len(x)) or c.ndim != 1:
        raise ValueError('Matching coordinate, box-bound and inequality arrays required')
    if not all(np.isfinite(a).all() for a in [x, c, j, bounds]) or np.any(bounds <= 0) or trust <= 0 or margin < 0:
        raise ValueError('Finite arrays, positive bounds/trust and nonnegative margin required')
    if np.any(np.abs(x) > bounds+1e-12): raise ValueError('Starting point outside absolute edit box')
    derivative = j*trust
    movable = np.max(np.abs(derivative), axis=1) > 1e-12
    if np.any(c[~movable] < -1e-8):
        return None, dict(success=False, reason='Violated locally constant constraint')
    # Search for an interior point without changing the eventual acceptance
    # tolerance. Coordinates are scaled by trust for numerical conditioning.
    inequalities = hstack([-csr_matrix(derivative[movable]), csr_matrix((movable.sum(), 1))])
    identity = eye(len(x), format='csr'); negative_t = csr_matrix(-np.ones((len(x), 1)))
    inequalities = vstack([inequalities, hstack([identity, negative_t]), hstack([-identity, negative_t])], format='csr')
    rhs = np.r_[c[movable]-margin, np.zeros(2*len(x))]
    lower = np.maximum(-1., (-bounds-x)/trust); upper = np.minimum(1., (bounds-x)/trust)
    objective = np.r_[np.zeros(len(x)), 1.]
    fit = linprog(objective, A_ub=inequalities, b_ub=rhs,
        bounds=list(zip(lower, upper))+[(0., 1.)], method='highs',
        options=dict(primal_feasibility_tolerance=1e-9, dual_feasibility_tolerance=1e-9, threads=1))
    record = dict(success=bool(fit.success), status=int(fit.status), message=str(fit.message),
        movable_constraints=int(movable.sum()), constant_constraints=int((~movable).sum()),
        trust=trust, interior_margin=margin)
    if not fit.success: return None, record
    delta = fit.x[:-1]*trust
    record.update(max_coordinate_step=float(np.abs(delta).max()), epigraph=float(fit.x[-1]),
        predicted_minimum_constraint=float((c+j@delta).min()))
    return delta, record


def restore(problem, start, attempts=5, trust=1e-5, margin=1e-4, progress=None):
    x = np.asarray(start, float).copy(); initial = x.copy(); history = []
    bounds = np.tile(problem.fitter.bounds[problem.free], len(problem.frames))
    for iteration in range(attempts):
        current = problem.evaluate(x)
        if current[2].min() >= -1e-8 and current[0] == 0. and problem.geometric_guard(current[5]):
            break
        delta, info = linear_step(x, current[2], current[3], bounds, trust, margin)
        info['iteration'] = iteration+1; info['before_minimum_constraint'] = float(current[2].min())
        info['safeguard_trials'] = []; selected = None
        if delta is not None:
            for backtrack in range(8):
                alpha = .5**backtrack; trial = problem.evaluate(x+alpha*delta)
                minimum = float(trial[2].min())
                geometry = problem.geometric_guard(trial[5])
                # Keep the release target exactly satisfied; allow only a
                # strict reduction of the worst existing infeasibility.
                acceptable = bool(np.isfinite(minimum) and trial[0] == 0. and geometry and
                    (minimum >= -1e-8 or minimum > current[2].min()+1e-10))
                info['safeguard_trials'].append(dict(alpha=alpha, minimum_constraint=minimum, target_objective=trial[0], geometry=geometry, acceptable=acceptable))
                if acceptable: selected = alpha; x += alpha*delta; break
        info['selected_fraction'] = selected; history.append(info)
        if progress: progress(info)
        if selected is None: break
    final = problem.evaluate(x)
    feasible = bool(final[2].min() >= -1e-8 and final[0] == 0. and problem.geometric_guard(final[5]))
    return problem.values(x), dict(attempt_limit=attempts, trust=trust, interior_margin=margin, history=history,
        feasible=feasible, final_minimum_constraint=float(final[2].min()), final_target_objective=final[0],
        maximum_parameter_change=float(np.abs(x-initial).max()), starting_coordinates=initial.tolist(),
        final_coordinates=x.tolist(), variable_frames=problem.frames.tolist(), free_columns=problem.free.tolist(), quality_approved=False)
