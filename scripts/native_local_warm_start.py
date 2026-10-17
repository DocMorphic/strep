"""Continue local corrections from cumulative controls, keeping original locks.

A cumulative coefficient grid is relative to the ORIGINAL actor/quaternion
source. Loading it is not a quaternion rebase or evidence of valid geometry.
The caller must verify candidate provenance and all raw/saved motion gates.
"""
import hashlib

import numpy as np

from native_key_basis import NativeKeyBasis
from native_local_basis import _LocalBasis, localized_native_basis


def localized_native_basis_from_controls(reference, cumulative_controls,
                                         first_key, peak_key, last_key):
    """Start a local block using the original domain's frozen keys only.

    ``reference`` must be the caller's original NativeKeyBasis, not a previous
    local block whose additional anchors restricted just that search. Every
    cumulative vector must still lie in the original normalized unit ball,
    and every original frozen coefficient must match byte for byte.
    """
    if type(reference) is not NativeKeyBasis:
        raise ValueError('The explicit original NativeKeyBasis reference is required')
    digest = lambda array: hashlib.sha256(np.asarray(array, dtype='<f8').tobytes()).hexdigest()
    if (digest(reference._clock) != reference.report['clock_sha256']
            or digest(reference._seed) != reference.report['seed_sha256']):
        raise ValueError('Original reference clock or cumulative seed binding changed')
    raw = np.asarray(cumulative_controls)
    if (raw.dtype.kind not in 'fiu' or raw.dtype.itemsize > 8
            or raw.shape != reference._seed.shape or not np.isfinite(raw).all()):
        raise ValueError('A complete finite cumulative control grid is required')
    warm = raw.astype(float, copy=True)
    frozen = list(reference._frozen)
    if warm[frozen].tobytes() != reference._seed[frozen].tobytes():
        raise ValueError('Original frozen cumulative coefficients changed')
    # The constructor validates the ENTIRE cumulative grid against unit balls.
    # Its zero-preserving subclass keeps all untouched signed-zero bytes. The
    # old quaternion source/caps are caller-owned and never replaced here.
    parent = _LocalBasis(reference._clock, list(reference._nodes), warm,
                         list(reference._knots), frozen,
                         maximum_jacobian_bytes=reference._maximum_bytes)
    local, block = localized_native_basis(parent, np.zeros(parent.size),
                                          first_key, peak_key, last_key)
    if local.coefficients(np.zeros(local.size)).tobytes() != warm.tobytes():
        raise ValueError('Local zero point differs from supplied cumulative controls')
    report = dict(
        schema='strep-native-local-warm-start-v1', local=block,
        original_reference_clock_sha256=reference.report['clock_sha256'],
        original_reference_seed_sha256=reference.report['seed_sha256'],
        cumulative_controls_sha256=digest(warm),
        original_frozen_keys=frozen,
        original_frozen_controls_byte_identical=True,
        cumulative_balls_not_reset=True, zero_grid_byte_identical=True,
        previous_search_anchors_not_inferred_as_original_locks=True,
        source_actor_caps_and_provenance_owned_by_caller=True,
        original_selected=True, quality_approved=False, release_approved=False,
        scope='Explicit complete cumulative source-relative grid and original '
              'domain locks only. New search anchors restrict this block; they '
              'do not create permanent author locks. All cumulative native '
              'balls remain strict. No source rebasing, provenance inference, '
              'geometry or motion approval.')
    return local, report
