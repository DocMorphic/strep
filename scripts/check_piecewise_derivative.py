"""Finite differences only within the same active smooth branch."""
import numpy as np


def check_direction(evaluate, signature, x, direction, tolerance=2e-4):
    base = evaluate(x); active = signature(x); trials = []
    for step in (1e-6, 1e-7):
        minus_x, plus_x = x-step*direction, x+step*direction
        minus, plus = evaluate(minus_x), evaluate(plus_x)
        stable = signature(minus_x) == active == signature(plus_x)
        objective_error = float(abs((plus[0]-minus[0])/(2*step)-base[1]@direction))
        constraint_error = float(np.abs((plus[2]-minus[2])/(2*step)-base[3]@direction).max())
        trials.append(dict(step=step, stable_branch=stable, objective_error=objective_error, constraint_error=constraint_error))
        if stable:
            return dict(passed=bool(np.isfinite([objective_error,constraint_error]).all() and max(objective_error,constraint_error)<=tolerance),
                selected_step=step, objective_error=objective_error, constraint_error=constraint_error, trials=trials)
    return dict(passed=False, selected_step=None, trials=trials, reason='No stable branch at either fixed diagnostic step')
