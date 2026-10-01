"""Independent post-contact correction, preserving the existing finger reference."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from native_finger_motion import NativeFingerMotion
from coupled_hand_finger_motion import CoupledHandFingerMotion


class ReleaseFingerMotion(NativeFingerMotion):
    def __init__(self, original, contact, release_peak):
        if (not isinstance(original, NativeFingerMotion) or original.model.width != 1
                or not np.isfinite([contact, release_peak]).all()
                or contact != original.model.knots[1]
                or not contact < release_peak < original.model.window[1]):
            raise ValueError('Single-peak original and an interior post-contact peak required')
        self.__dict__ = original.__dict__.copy()
        self.original = original
        self.joint_limits = original.limits.copy()
        self.limits = np.repeat(self.joint_limits, 2)
        self.model = copy.copy(original.model)
        self.model.width = 2
        self.model.size = self.size = original.size * 2
        self.release_knots = np.array([contact, release_peak, original.model.window[1]])
        self.model.entries = []
        for entry in original.model.entries:
            extra = np.interp(entry['clock'][entry['ids']], self.release_knots, [0., 1., 0.], left=0., right=0.)
            extra[entry['clock'][entry['ids']-1] < contact] = 0.
            if not np.any(extra): raise ValueError('Release envelope has no editable native key')
            self.model.entries.append(dict(entry, weights=np.column_stack([entry['weights'], extra])))

    def embed(self, original_controls):
        controls = self.original.model.controls(original_controls)
        result = np.zeros((len(self.nodes), 2, 3))
        result[:, :1] = controls
        return result.ravel()

    def margins(self, controls):
        """Keep original per-key angle budgets and 5-degree adjacent corrections.

        The Euclidean difference of correction rotation vectors bounds their
        SO(3) distance. This is an additional conservative check, not a new cap.
        """
        parts = self.model.controls(controls); rows = []
        for entry, part, limit in zip(self.model.entries, parts, self.joint_limits):
            delta = np.zeros((len(entry['clock']), 3))
            delta[entry['ids']] = entry['weights'] @ part
            rows.extend([(limit-np.linalg.norm(delta[entry['ids']], axis=1))/limit,
                         (np.deg2rad(5.)-np.linalg.norm(np.diff(delta, axis=0), axis=1))/np.deg2rad(5.)])
        return np.concatenate(rows)

    def validate_export(self, controls):
        if np.any(self.margins(controls) < 0):
            raise ValueError('Original finger angle or adjacent correction limit exceeded')
        values = self.model.quaternions(controls, quantize=True)
        for entry, limit in zip(self.model.entries, self.joint_limits):
            angles = (Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(values[entry['node']])).magnitude()
            if np.any(angles > limit + np.deg2rad(1e-4)):
                raise ValueError('Serialized original finger angle limit exceeded')

    def export(self, controls, path):
        self.validate_export(controls)
        self.model.export(controls, path)


class ReleaseCoupledHandFingerMotion(CoupledHandFingerMotion):
    def export(self, arm_controls, finger_controls, path):
        self.finger.validate_export(finger_controls)
        super().export(arm_controls, finger_controls, path)


def expand_controls(original, arm_size, finger_sizes):
    """Embed normalized controls/scales with zero extra controls per joint."""
    value = np.asarray(original, float)
    if (type(arm_size) is not int or arm_size < 1 or len(finger_sizes) != 2
            or any(type(n) is not int or n < 3 or n % 3 for n in finger_sizes)
            or value.shape != (arm_size + sum(finger_sizes),) or not np.isfinite(value).all()):
        raise ValueError('Finite matching arm and two finger control blocks required')
    parts = [value[:arm_size]]; offset = arm_size
    for size in finger_sizes:
        expanded = np.zeros((size//3, 2, 3))
        expanded[:, 0] = value[offset:offset+size].reshape(-1, 3)
        parts.append(expanded.ravel()); offset += size
    return np.concatenate(parts)
