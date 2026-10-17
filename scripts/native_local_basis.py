"""Explicit local temporal increments about cumulative source-relative controls.

The original actor/quaternion curves and degree/joint permissions still belong
to the caller. A warm coefficient grid is not a new quaternion source: native
balls continue to constrain the complete cumulative grid, never just a delta.
"""
import hashlib

import numpy as np

from native_key_basis import NativeKeyBasis


class _LocalBasis(NativeKeyBasis):
    def coefficients(self, value):
        value = self._value(value)
        delta = (self._weights @ value.reshape(len(self._variable), -1)).reshape(self._seed.shape)
        result = self._seed.copy()
        # Adding exact zero can erase a seed's negative-zero bits. Preserve all
        # untouched components, not only the explicitly frozen native keys.
        np.add(self._seed, delta, out=result, where=delta != 0)
        result[list(self._frozen)] = self._seed[list(self._frozen)]
        return result

    def endpoint_map(self, value, keys, *, jacobian=True):
        value = self._value(value)
        keys = self._keys(keys)
        if type(jacobian) is not bool:
            raise ValueError('Explicit derivative mode required')
        count = len(keys) * len(self._nodes) * 3
        if jacobian and count * self.size * 8 > self._maximum_bytes:
            raise ValueError('Complete endpoint Jacobian exceeds budget; no keys or columns discarded')
        weights = self._weights[keys]
        seed = self._seed[keys]
        delta = (weights @ value.reshape(len(self._variable), -1)).reshape(seed.shape)
        result = seed.copy()
        np.add(seed, delta, out=result, where=delta != 0)
        for index, key in enumerate(keys):
            if key in self._frozen:
                result[index] = self._seed[key]
        matrix = np.kron(weights, np.eye(len(self._nodes) * 3)) if jacobian else None
        return result, matrix


def localized_native_basis(parent, point, first_key, peak_key, last_key):
    """Declare one complete local knot for every previously declared node/axis.

    All parent frozen keys remain frozen. Extra anchors restrict this search
    block only; the helper does not infer a globally feasible motion or change
    the actor, original source, caps, clocks or release criteria.
    """
    if not isinstance(parent, NativeKeyBasis):
        raise ValueError('An explicit complete parent native basis is required')
    keys = [first_key, peak_key, last_key]
    if (any(type(key) is not int for key in keys)
            or not 0 <= first_key < peak_key < last_key < len(parent._clock)):
        raise ValueError('Three increasing explicit existing native keys are required')
    original_frozen = list(parent._frozen)
    if any(first_key < key < last_key for key in original_frozen):
        raise ValueError('The local support cannot cross an existing frozen native key')
    warm = parent.export_coefficients(point)
    if warm[original_frozen].tobytes() != parent._seed[original_frozen].tobytes():
        raise ValueError('Original frozen cumulative controls changed')
    knots = sorted({0, len(parent._clock) - 1, *original_frozen, *keys})
    frozen = [key for key in knots if key != peak_key]
    basis = _LocalBasis(parent._clock, list(parent._nodes), warm, knots, frozen,
                        maximum_jacobian_bytes=parent._maximum_bytes)
    zero = np.zeros(basis.size)
    if basis.coefficients(zero).tobytes() != warm.tobytes():
        raise ValueError('Local zero point does not reproduce the cumulative warm grid exactly')
    assert not np.any(basis.weights[:first_key + 1]) and not np.any(basis.weights[last_key:])
    digest = lambda array: hashlib.sha256(np.asarray(array, dtype='<f8').tobytes()).hexdigest()
    report = dict(
        schema='strep-native-local-basis-v1', first_key=first_key, peak_key=peak_key, last_key=last_key,
        exact_native_times_s=parent._clock[keys].tolist(), declared_nodes=list(parent._nodes),
        parent_variables=parent.size, local_variables=basis.size,
        original_frozen_keys=original_frozen, search_frozen_keys=frozen,
        parent_clock_sha256=parent.report['clock_sha256'], warm_controls_sha256=digest(warm),
        parent_seed_sha256=parent.report['seed_sha256'], parent_point_sha256=digest(parent._value(point)),
        zero_coefficients_byte_identical=True, original_frozen_controls_byte_identical=True,
        complete_node_axis_population=True, cumulative_ball_limit=1.,
        actor_source_and_degree_caps_supplied_by_caller=True,
        original_selected=True, quality_approved=False, release_approved=False,
        scope='One explicitly declared local temporal search block, all parent nodes/axes retained. '
              'The warm grid remains cumulative relative to the original quaternion source; '
              'export rejects failed cumulative native balls without clipping. Source actor/caps, '
              'complete raw/saved physical acceptance and baseline motion equivalence belong to the caller. '
              'No inferred motion, global infeasibility, optimization or release approval.')
    return basis, report
