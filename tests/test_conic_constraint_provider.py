"""A specialized provider must constrain proposals and survive solve dispatch."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_root_descent import affine_constraints, direction, solve
from test_root_release_block import make_problem


def test_custom_provider_prevents_an_otherwise_proposed_coordinate_edit():
    p = make_problem()
    x = p.initial[np.ix_(p.frames, p.free)].ravel()
    delta, _ = direction(p, x, .01)
    coordinate = int(np.abs(delta).argmax())
    assert abs(delta[coordinate]) > 1e-5
    calls = []
    def locked(problem, current):
        calls.append(1)
        c, j, cones = affine_constraints(problem, current)
        row = np.eye(len(current))[coordinate]
        # The chosen coordinate must remain at its initial value.
        offset = current[coordinate]-x[coordinate]
        return np.r_[c, offset, -offset], np.vstack([j, row, -row]), cones
    limited, proof = direction(p, x, .01, constraint_builder=locked)
    assert limited is not None and calls
    assert abs(limited[coordinate]) < 1e-9
    assert proof['predicted_linear_minimum'] >= -1e-8
    calls.clear()
    values, result = solve(p, steps=2, trusts=(.01,), constraint_builder=locked)
    assert calls
    final = values[np.ix_(p.frames, p.free)].ravel()
    assert abs(final[coordinate]-x[coordinate]) < 1e-9
    assert result['objective_after'] <= result['objective_before']
