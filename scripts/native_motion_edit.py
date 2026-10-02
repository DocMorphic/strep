"""Bounded native authoring at frame keys; no physical or contact certification."""
import numpy as np
from scipy.spatial.transform import Rotation


LIMITS = {'joint_from_original_degrees': 45., 'root_from_original_m': .25,
          'correction_step_degrees': 5., 'root_correction_step_m': .05}


def _motion(local, roots):
    if (not isinstance(local, np.ndarray) or not isinstance(roots, np.ndarray)
            or local.dtype != np.float32 or roots.dtype != np.float32
            or local.ndim != 4 or local.shape[1:] != (77, 3, 3)
            or roots.shape != (len(local), 3) or not 3 <= len(local) <= 300
            or not np.isfinite(local).all() or not np.isfinite(roots).all()
            or np.max(np.abs(local @ local.transpose(0, 1, 3, 2) - np.eye(3))) > 1e-4
            or np.max(np.abs(np.linalg.det(local) - 1)) > 1e-4):
        raise ValueError('Proper native FP32 motion with 3-300 frames required')


def _vector(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (int, float) or not np.isfinite(v) for v in value)):
        raise ValueError('Explicit finite three-component edit vectors required')
    return np.asarray(value, float)


def validate_spec(spec, frames, names):
    fields = {'joint', 'rotation_vector_degrees', 'root_offset_m',
              'start_frame', 'peak_frame', 'end_frame'}
    if not isinstance(spec, dict) or set(spec) != fields:
        raise ValueError('One timed native joint/root edit required')
    if len(names) != 77 or len(set(names)) != 77 or spec['joint'] not in names:
        raise ValueError('Choose one known native joint')
    start, peak, end = (spec[k] for k in ('start_frame', 'peak_frame', 'end_frame'))
    if any(type(v) is not int for v in (start, peak, end)) or not 0 <= start < peak < end < frames:
        raise ValueError('Edit needs ordered start, interior peak and end frame keys')
    rotation, shift = _vector(spec['rotation_vector_degrees']), _vector(spec['root_offset_m'])
    if np.linalg.norm(rotation) > LIMITS['joint_from_original_degrees'] or np.linalg.norm(shift) > LIMITS['root_from_original_m']:
        raise ValueError('Requested edit exceeds native authoring limits')
    if not np.any(rotation) and not np.any(shift):
        raise ValueError('Enter a nonzero joint rotation or root offset')
    return start, peak, end, rotation, shift


def _angles(matrices):
    shape = matrices.shape[:-2]
    return np.rad2deg(Rotation.from_matrix(matrices.reshape(-1, 3, 3)).magnitude()).reshape(shape)


def _audit(original_local, original_roots, local, roots):
    correction = original_local.transpose(0, 1, 3, 2).astype(float) @ local
    shift = roots.astype(float) - original_roots
    metrics = {'joint_from_original_degrees': float(_angles(correction).max()),
               'root_from_original_m': float(np.linalg.norm(shift, axis=1).max()),
               'correction_step_degrees': float(_angles(correction[:-1].transpose(0, 1, 3, 2) @ correction[1:]).max()),
               'root_correction_step_m': float(np.linalg.norm(np.diff(shift, axis=0), axis=1).max())}
    for key, cap in LIMITS.items():
        tolerance = 1e-4 if key.endswith('degrees') else 1e-6
        if metrics[key] > cap + tolerance:
            raise ValueError('Cumulative original-relative edit exceeds ' + key)
    return metrics


def edit_native(original_local, original_roots, candidate_local, candidate_roots, names, spec):
    """Postmultiply a local rotation vector; add a world-space root translation.

    Cubic smoothstep weight is zero at both boundary keys, one at the peak.
    Bounds apply to the entire candidate relative to the immutable original,
    including channels changed by earlier operations or external authoring.
    """
    _motion(original_local, original_roots); _motion(candidate_local, candidate_roots)
    if candidate_local.shape != original_local.shape:
        raise ValueError('Candidate and original must share the selected native clock')
    start, peak, end, rotation, shift = validate_spec(spec, len(candidate_local), names)
    _audit(original_local, original_roots, candidate_local, candidate_roots)
    weights = np.zeros(len(candidate_local))
    for first, last, rising in ((start, peak, True), (peak, end, False)):
        u = np.arange(last-first+1, dtype=float)/(last-first)
        smooth = u*u*(3-2*u)
        weights[first:last+1] = smooth if rising else 1-smooth
    active = np.flatnonzero(weights > 0); joint = names.index(spec['joint'])
    local, roots = candidate_local.copy(), candidate_roots.copy()
    if np.any(rotation):
        delta = Rotation.from_rotvec(weights[active, None] * np.deg2rad(rotation)).as_matrix()
        local[active, joint] = candidate_local[active, joint].astype(float) @ delta
    if np.any(shift):
        roots[active] = candidate_roots[active].astype(float) + weights[active, None]*shift
    _motion(local, roots)
    report = {'schema': 'strep-native-timed-edit-audit-v1', 'limits': dict(LIMITS),
              'measured': _audit(original_local, original_roots, local, roots),
              'frames': len(local), 'fps': 30, 'joint': spec['joint'],
              'changed_rotation_frame_keys': int(np.any(local != candidate_local, axis=(1, 2, 3)).sum()),
              'changed_root_frame_keys': int(np.any(roots != candidate_roots, axis=1).sum()),
              'rotation_coordinates': 'joint-local postmultiplication rotation vector',
              'root_coordinates': 'world right-handed Y-up metres',
              'scope': 'Native frame-key edit bounds only; no anatomical, subframe, collision or contact approval',
              'quality_approved': False, 'training_admitted': False, 'release_approved': False}
    if not report['changed_rotation_frame_keys'] and not report['changed_root_frame_keys']:
        raise ValueError('Requested edit has no representable FP32 effect')
    return local, roots, report
