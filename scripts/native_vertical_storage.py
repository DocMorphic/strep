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
            or np.count_nonzero(axis) != 1
            or not np.isfinite(maximum_displacement) or maximum_displacement <= 0
            or not np.array_equal(values, values.astype(np.float32).astype(float))):
        raise ValueError('Exact Float32 source and one nonzero root axis required')
    if (not isinstance(frozen, list) or not frozen or len(set(frozen)) != len(frozen)
            or any(type(i) is not int or not 0 <= i < len(values) for i in frozen)):
        raise ValueError('Explicit distinct frozen root keys required')
    component = int(np.flatnonzero(axis)[0]); factor = float(axis[component])
    original = values[:, component]
    magnitude = np.maximum(np.abs(original), np.abs(original + factor * maximum_displacement))
    if not np.isfinite(magnitude).all() or np.any(magnitude>np.finfo(np.float32).max):
        raise ValueError('Native root edit range must remain finite Float32 coordinates')
    # Every integer multiple at this power-of-two spacing in the declared range
    # is a Float32 value, including when an edit crosses an exponent boundary.
    native_spacing = np.exp2(np.maximum(np.floor(np.log2(magnitude)) - 23, -149))
    anchor = np.rint(original / native_spacing) * native_spacing
    # Preserve the real local-axis coefficient. A coefficient such as
    # 1.0000000000000002 changes coordinates, not the declared world-Y edit.
    spacing = native_spacing / abs(factor)
    intercept = (anchor - original) / factor
    lower = np.ceil(-intercept / spacing)
    upper = np.floor((maximum_displacement - intercept) / spacing)
    for i in frozen:
        spacing[i] = 1.; intercept[i] = 0.; lower[i] = upper[i] = 0.
    if not all(np.isfinite(v).all() for v in (spacing,intercept,lower,upper)):
        raise ValueError('Finite world-offset grid coordinates required')
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
        options=dict(time_limit=60., mip_rel_gap=0.,
            mip_feasibility_tolerance=1e-9, primal_feasibility_tolerance=1e-9))
    metadata = dict(method='scipy-highs-milp', maximum_solver_seconds=60.,
        model_row_reserve=reserve, local_axis_coefficients=np.asarray(axis).tolist(),grid_spacing_m=spacing.tolist(),
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
