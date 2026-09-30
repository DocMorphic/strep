"""Original-relative angular norm rows for bounded native rotation editing."""
import numpy as np
from joint_angular_rates import angular_vectors


class AngularMotionRows:
    def __init__(self, model, joints):
        self.times = model.times.copy(); self.joints = list(joints)
        self.knots = model.knots.copy()
        source = self._all_values(model.source_world)
        active = np.zeros((len(self.times), len(self.joints)), bool)
        for column, node in enumerate(self.joints):
            # Rotating a joint changes its orientation even if its origin never
            # moves. Include the joint itself as well as all of its ancestors.
            lineage = [node]; parent = model.parents[node]
            while parent >= 0:
                lineage.append(parent); parent = model.parents[parent]
            for entry in model.entries:
                if entry['node'] in lineage:
                    for key in entry['ids']:
                        active[:, column] |= (self.times > entry['clock'][key-1]) & (self.times < entry['clock'][key+1])
        self.specs = []
        for order, (vectors, clock) in enumerate(source, start=1):
            changed = np.zeros(vectors.shape[:2], bool)
            for offset in range(order+1): changed |= active[offset:offset+len(vectors)]
            bins = np.searchsorted(self.knots[1:-1], clock, side='right'); caps = np.zeros(vectors.shape[:2])
            for span in np.unique(bins):
                mask = bins == span; caps[mask] = np.linalg.norm(vectors[mask], axis=2).max(axis=0)
            rows, columns = np.nonzero(changed)
            self.specs.append((rows, columns, caps[rows, columns]))
        self.radii = np.concatenate([s[2] for s in self.specs])
        self.kinds = np.concatenate([np.full(len(s[0]), k) for s, k in zip(self.specs, ['angular_speed', 'angular_acceleration'])])

    def _all_values(self, world):
        return angular_vectors(np.asarray(world)[:, self.joints][:, :, :3, :3], self.times)

    def values(self, world, derivative=None, step=1e-6):
        world = np.asarray(world, float)
        all_values = self._all_values(world)
        vectors = np.concatenate([value[rows, columns] for (value, _), (rows, columns, _) in zip(all_values, self.specs)])
        if derivative is None: return vectors, None
        derivative = np.asarray(derivative, float)
        if derivative.shape[:-1] != world.shape or not np.isfinite(derivative).all() or not np.isfinite(step) or step <= 0:
            raise ValueError('Matching finite world derivatives and positive step required')
        jacobian = np.zeros(vectors.shape+(derivative.shape[-1],))
        for column in range(derivative.shape[-1]):
            if not np.any(derivative[..., column]): continue
            delta = step*derivative[..., column]
            # The perturbed first-order matrices are projected by Rotation's
            # matrix decoder. The original tracks must pass proper-rotation
            # validation; this is a derivative approximation, not an export.
            plus = self._all_values(world+delta); minus = self._all_values(world-delta)
            jacobian[..., column] = np.concatenate([
                ((a-b)/(2*step))[rows, cols] for (a, _), (b, _), (rows, cols, _) in zip(plus, minus, self.specs)])
        return vectors, jacobian
