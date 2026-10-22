"""Bounded feasibility proposals for existing surface-pose windows.

The objective is constant zero; original constraints and caller-selected fitting
reserves remain in the window. This helper neither changes targets nor exports
motion. Callers must separately check the dense clock, serialized clip and engine.
Floor working rows must be initialized before calling and stay frozen during it.
"""
import numpy as np
from scipy.optimize import minimize
from surface_pose_window import CoupledPoseWindow
from surface_pose_interpolation import SampledPoseWindow


def propose(window, initial, *, max_iterations):
    if (not isinstance(window, (CoupledPoseWindow, SampledPoseWindow))
            or type(max_iterations) is not int or not 1 <= max_iterations <= 1000):
        raise ValueError('A surface-pose window and 1–1000 iterations are required')
    initial = np.asarray(initial, float).copy()
    bounds = np.asarray(window.bounds, float).copy()
    if (initial.shape != (window.size,) or not np.isfinite(initial).all()
            or bounds.shape != (window.size, 2) or not np.isfinite(bounds).all()
            or np.any(bounds[:, 0] > bounds[:, 1])
            or np.any(initial < bounds[:, 0]) or np.any(initial > bounds[:, 1])):
        raise ValueError('Finite initial parameters inside explicit finite bounds required')
    fixed = bounds[:, 0] == bounds[:, 1]
    keys = window.keys if isinstance(window, SampledPoseWindow) else window
    problems = [*keys.problems, *[p for _, _, p in getattr(window, 'samples', [])]]
    frozen = [p.floor_vertices.copy() for p in problems]
    if any(not len(rows) for rows in frozen):
        raise ValueError('Initialize every floor working set before proposing')
    working_count = full_count = None

    def unchanged():
        if (not np.array_equal(np.asarray(window.bounds), bounds)
                or any(not np.array_equal(p.floor_vertices, rows)
                       for p, rows in zip(problems, frozen))):
            raise ValueError('Bounds or floor working rows changed during the solve')

    def parameters(x, *, retained=False):
        x = np.asarray(x, float)
        if x.shape != initial.shape or not np.isfinite(x).all():
            raise ValueError('Solver returned invalid parameters')
        if retained and (np.any(x < bounds[:, 0]) or np.any(x > bounds[:, 1])
                         or not np.array_equal(x[fixed], initial[fixed])):
            raise ValueError('Solver changed fixed parameters or exceeded box bounds')
        return x

    def gaps(x, *, full=False):
        nonlocal working_count, full_count
        unchanged()
        value = np.asarray(window.values(parameters(x), full=full), float)
        count = full_count if full else working_count
        if (value.ndim != 1 or not len(value) or not np.isfinite(value).all()
                or count is not None and len(value) != count):
            raise ValueError('Invalid or changing constraint population')
        if full:
            full_count = len(value)
        else:
            working_count = len(value)
        unchanged()
        return value

    def jacobian(x):
        value = gaps(x)
        paired, jac = window.pair(parameters(x))
        paired, jac = np.asarray(paired, float), np.asarray(jac, float)
        unchanged()
        # Independently evaluated interpolation paths may differ at roundoff.
        # This checks derivative consistency only; acceptance below stays strict.
        if (paired.shape != value.shape or not np.allclose(paired, value, rtol=1e-12, atol=1e-12)
                or jac.shape != (len(value), window.size) or not np.isfinite(jac).all()):
            raise ValueError('Constraint values and derivatives do not match')
        return jac

    best = initial.copy()
    best_gap = float(gaps(best, full=True).min())
    initial_gap = best_gap
    callbacks = 0
    retained_callback = 0
    retained_source = 'initial'

    def retain(x, *, terminal=False):
        nonlocal best, best_gap, callbacks, retained_callback, retained_source
        x = parameters(x, retained=True)
        gap = float(gaps(x, full=True).min())
        callbacks += int(not terminal)
        # Score every floor vertex, including ones omitted from optimizer rows.
        # Keep the initial/better iterate if the optimizer's final point regresses.
        if max(0., -gap) < max(0., -best_gap):
            best, best_gap, retained_callback = x.copy(), gap, callbacks
            retained_source = 'final' if terminal else 'callback'

    if best_gap >= 0 or np.all(fixed):
        success = None
        message = 'Initial fitting constraints pass' if best_gap >= 0 else 'All parameters are fixed'
        iterations = 0
    else:
        result = minimize(lambda x: 0., best.copy(), jac=lambda x: np.zeros_like(x),
            method='SLSQP', bounds=bounds.tolist(),
            constraints={'type': 'ineq', 'fun': gaps, 'jac': jacobian}, callback=retain,
            options={'maxiter': max_iterations, 'ftol': 1e-8})
        retain(result.x, terminal=True)
        success, message, iterations = bool(result.success), str(result.message), int(result.nit)
    unchanged()
    parameters(best, retained=True)
    final_gap = float(gaps(best, full=True).min())
    return best, dict(solver_success=success, solver_message=message, iterations=iterations,
        callbacks=callbacks, retained_callback=retained_callback, retained_source=retained_source,
        initial_minimum_fitting_gap=initial_gap, minimum_fitting_gap=final_gap,
        fitting_constraints_pass=bool(final_gap >= 0), fixed_parameters=int(fixed.sum()),
        requires_decoded_validation=True, quality_approved=False, release_approved=False)
