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


def reach_report(raw, skin, spec):
    """Screen compiled, explicitly selected native point targets against raw."""
    from skin_point_reach_bound import error_lower_bound
    positions = np.asarray(raw['posed_joints'])
    rotations = np.asarray(raw['global_rot_mats'])
    frames = len(positions)
    if positions.shape != (frames, 77, 3) or rotations.shape != (frames, 77, 3, 3) or spec['frame_count'] != frames:
        raise ValueError('Complete raw SOMA77 clock required for reach preflight')
    inverse = np.linalg.inv(skin['bind_rig_transform'])
    rows, skipped = [], []
    for name, entry in spec['regions'].items():
        if entry['mode'] != 'explicit':
            continue
        for segment in entry['segments']:
            if 'vertex_id' not in segment or segment['space'] not in ('world', 'track'):
                skipped.append(dict(region=name, start_frame=segment['start_frame'], reason='No fixed surface vertex and explicit target'))
                continue
            vertex = segment['vertex_id']
            if type(vertex) is not int or not 0 <= vertex < len(skin['bind_vertices']):
                raise ValueError('Valid fixed source surface vertex required')
            first, last = segment['start_frame'], segment['end_frame']
            if type(first) is not int or type(last) is not int or not 0 <= first <= last < frames:
                raise ValueError('Inclusive native target interval required')
            indices = skin['lbs_indices'][vertex]
            local = (inverse[indices]@np.r_[skin['bind_vertices'][vertex], 1])[:, :3]
            target = (np.asarray(segment['positions_m']) if segment['space'] == 'track'
                      else np.repeat(np.asarray(segment['position_m'])[None], last-first+1, axis=0))
            bound = error_lower_bound(positions[first:last+1, indices], rotations[first:last+1, indices],
                                     local, skin['lbs_weights'][vertex], target, .22)
            tolerance = segment.get('tolerance_m', .005)
            if type(tolerance) not in (int, float) or not np.isfinite(tolerance) or tolerance <= 0:
                raise ValueError('Positive finite native contact tolerance required')
            working = min(.005, tolerance)
            working -= min(.00001, .01*working)
            lower = bound['error_lower_bound_m']
            rows.append(dict(region=name, vertex_id=vertex, start_frame=first, end_frame=last,
                position_budget_m=.22, authored_tolerance_m=tolerance, working_tolerance_m=working,
                lower_bounds_m=lower.tolist(), maximum_lower_bound_m=float(lower.max()),
                incompatible_frames=[int(first+i) for i in np.flatnonzero(lower > working)],
                authored_incompatible_frames=[int(first+i) for i in np.flatnonzero(lower > tolerance)],
                arithmetic_slack_m=bound['arithmetic_slack_m']))
    return dict(status='provably_incompatible_native_keys' if any(r['incompatible_frames'] for r in rows) else 'not_proven_incompatible',
        rows=rows, skipped=skipped, quality_approved=False, release_approved=False,
        scope='Necessary condition for unchanged skin and all native joints within 22 cm of raw. '
              'Allows arbitrary proper rotations. No converse feasibility, anatomy, speed, geometry, '
              'export or between-key certificate. Original request and tolerances remain unchanged.')
