"""Opt-in reference-relative body constraints for the V17 scene experiment.

Uses existing body screens during fitting; independent review still decides
whether a candidate meets them. Does not change baseline fitting or limits.
"""
import numpy as np


def validate_mode(solver_version, preserve_body):
    if type(preserve_body) is not bool:
        raise ValueError('Explicit body-preservation boolean required')
    if preserve_body and (type(solver_version) is not int or solver_version != 17):
        raise ValueError('Body-preserving scene fitting currently requires solver version 17')


def arguments(raw, limb, previous):
    references = {}
    shape = None
    for name, motion in [('raw', raw), ('limb', limb), ('previous', previous)]:
        if not isinstance(motion, dict) or 'posed_joints' not in motion:
            raise ValueError('All three immutable native joint references required')
        positions = np.asarray(motion['posed_joints'])
        if (positions.ndim != 3 or positions.shape[0] < 2 or positions.shape[1:] != (77, 3)
                or positions.dtype.kind not in 'fi' or not np.isfinite(positions).all()):
            raise ValueError('Finite complete SOMA77 joint clocks required')
        if shape is not None and positions.shape != shape:
            raise ValueError('Body reference clocks must agree')
        shape = positions.shape
        references[name] = {'posed_joints': positions.astype(np.float64, copy=True)}
    return dict(native_body_references=references, authored_point_scaling='tolerance')


def description():
    return dict(enabled=True, references=['raw', 'limb', 'previous'],
                authored_point_scaling='tolerance', fps=30,
                scope='Existing native 22 cm joint-displacement and 1.5 m/s added-speed inequalities '
                      'inside the unchanged V17 solver. No guaranteed feasibility or quality approval. '
                      'Original point, object, clock and rotation/root acceptance limits remain unchanged.')
