"""Representable Float32 proposals for an axis-aligned vertical root track.

This changes proposal coordinates, never exported motion acceptance. Frozen
keys retain their exact original values. General root axes require a different
storage representation and are rejected explicitly by this optional method.
"""
import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp


def coordinates(values, axis, maximum_displacement, frozen):
    values = np.asarray(values, float)
    axis = np.asarray(axis, float)
    if (values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all()
            or axis.shape != (3,) or not np.isfinite(axis).all()
            or np.count_nonzero(axis) != 1 or np.max(np.abs(axis)) != 1
            or not np.isfinite(maximum_displacement) or maximum_displacement <= 0
            or not np.array_equal(values, values.astype(np.float32).astype(float))):
        raise ValueError('Exact Float32 source and one signed unit root axis required')
    if (not isinstance(frozen, list) or not frozen or len(set(frozen)) != len(frozen)
            or any(type(i) is not int or not 0 <= i < len(values) for i in frozen)):
        raise ValueError('Explicit distinct frozen root keys required')
    component = int(np.flatnonzero(axis)[0]); sign = float(axis[component])
    original = values[:, component]
    magnitude = np.maximum(np.abs(original), np.abs(original + sign * maximum_displacement))
    # Every integer multiple at this power-of-two spacing in the declared range
    # is a Float32 value, including when an edit crosses an exponent boundary.
    spacing = np.exp2(np.maximum(np.floor(np.log2(magnitude)) - 23, -149))
    anchor = np.rint(original / spacing) * spacing
    intercept = sign * (anchor - original)
    lower = np.ceil(-intercept / spacing)
    upper = np.floor((maximum_displacement - intercept) / spacing)
    for i in frozen:
        spacing[i] = 1.; intercept[i] = 0.; lower[i] = upper[i] = 0.
    return spacing, intercept, lower, upper


def solve(matrix, limits, values, axis, maximum_displacement, frozen):
    spacing, intercept, lower, upper = coordinates(values, axis, maximum_displacement, frozen)
    # A stricter model reserve protects Float64 row arithmetic. The original
    # rate, displacement and exported geometry acceptance tolerances are fixed.
    reserve = 1e-8
    transformed = matrix @ sparse.diags(spacing)
    movable = upper > lower
    objective_scale = float(spacing[movable].max()) if movable.any() else 1.
    fit = milp(spacing / objective_scale, integrality=np.ones(len(spacing)),
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(transformed, -np.inf, limits - matrix @ intercept - reserve),
        options=dict(time_limit=60., mip_rel_gap=0., threads=1,
            mip_feasibility_tolerance=1e-9, primal_feasibility_tolerance=1e-9))
    metadata = dict(method='scipy-highs-milp', maximum_solver_seconds=60.,
        model_row_reserve=reserve, grid_spacing_m=spacing.tolist(),
        grid_intercept_m=intercept.tolist(), lower_integer_controls=lower.tolist(),
        upper_integer_controls=upper.tolist(), integer_controls=None)
    if fit.success:
        integer = np.rint(fit.x)
        metadata['integer_integrality_maximum_error'] = float(np.max(abs(fit.x - integer)))
        if metadata['integer_integrality_maximum_error'] > 1e-6:
            raise ValueError('Solver did not return integral storage coordinates')
        metadata['integer_controls'] = integer.tolist()
        fit.x = intercept + spacing * integer
    return fit, metadata
