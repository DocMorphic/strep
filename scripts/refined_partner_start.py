"""Restore a completed timed-control basis without changing its physical protocol."""
import numpy as np

from finish_bounded_surface_path import validate_control_protocol
from refined_partner_basis import refine


def restore(coarse, original_controls, recipe, parameters, initial, warm_recipe=None):
    """Accept an original or nested basis, retaining the exact saved warm controls."""
    declared = recipe if warm_recipe is None else warm_recipe
    if {k: v for k, v in declared.items() if k != 'knots'} != {
        k: v for k, v in recipe.items() if k != 'knots'
    }:
        raise ValueError('Warm recipe changes the source or physical protocol')
    controls, _, _ = validate_control_protocol(declared, parameters, initial)
    fitter, _, _ = refine(coarse, original_controls, declared['knots'])
    for key, expected in [('basis', fitter.matrix), ('control_bounds', fitter.bounds),
                          ('control_radii', fitter.control_radii)]:
        if not np.array_equal(np.asarray(parameters[key]), expected):
            raise ValueError('Warm controls do not match the reconstructed basis')
    if fitter.step_pair(controls)[0].min() < -1e-8:
        raise ValueError('Warm controls violate the unchanged edit limits')
    return fitter, controls.copy()
