"""Nested temporal refinement of contact-preserving native rotation controls."""
import numpy as np
from scipy.spatial.transform import Rotation
from contact_rate_path import ContactRatePath


class RefinedContactRatePath(ContactRatePath):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coarse_knots = self.knots.copy()
        self.knots = np.sort(np.r_[self.coarse_knots, (self.coarse_knots[:-1]+self.coarse_knots[1:])/2])
        self.width = len(self.knots)-2
        self.components = 3*self.width+3
        self.size = len(self.model.nodes)*self.components
        for entry, lock in zip(self.model.entries, self.locks):
            lock['weights'] = np.stack([np.interp(entry['clock'][entry['ids']], self.knots, np.eye(len(self.knots))[k])
                for k in range(1, len(self.knots)-1)], axis=1)

    def lift_coarse(self, value):
        value = np.asarray(value, float)
        if value.shape != (len(self.model.nodes)*12,) or not np.isfinite(value).all():
            raise ValueError('Matching finite coarse controls required')
        result = []
        for part in value.reshape(-1, 12):
            controls = np.vstack([np.zeros(3), part[:9].reshape(3, 3), np.zeros(3)])
            refined = np.stack([np.interp(self.knots[1:-1], self.coarse_knots, controls[:, axis]) for axis in range(3)], axis=1)
            result.extend(np.r_[refined.ravel(), part[9:]])
        return np.asarray(result)

    def quaternions(self, value, quantize=False):
        value = np.asarray(value, float)
        if value.shape != (self.size,) or not np.isfinite(value).all():
            raise ValueError('Matching finite refined contact-path controls required')
        result = {}
        for entry, lock, part in zip(self.model.entries, self.locks, value.reshape(-1, self.components)):
            q = entry['source'].astype(float).copy()
            if np.any(part):
                ids = entry['ids']; delta = lock['weights']@part[:-3].reshape(self.width, 3)
                changed = np.any(delta != 0, axis=1)
                q[ids[changed]] = (Rotation.from_quat(q[ids[changed]])*Rotation.from_rotvec(delta[changed])).as_quat()
                omega = lock['step']+part[-3:]
                if np.linalg.norm(omega) >= np.pi-1e-6: raise ValueError('Ambiguous contact interpolation arc')
                pair = lock['rotation']@Rotation.from_rotvec(np.array([-lock['fraction'], 1-lock['fraction']])[:, None]*omega).as_matrix()
                q[lock['left']:lock['left']+2] = Rotation.from_matrix(pair).as_quat()
                q *= np.where(np.sum(q*entry['source'], axis=1) < 0, -1., 1.)[:, None]
                if quantize: q[ids] = q[ids].astype(np.float32)
            result[entry['node']] = q
        return result
