"""Opt-in native planting on every predeclared game-frame contact clock.

Uniform original source-rate bins remain unchanged. The proposal model is
native skin, not imported engine skin; actual imports stay independent.
"""
import numpy as np
from scipy.sparse import lil_matrix, vstack
from native_joint_plant import JointPlantProblem
from engine_contact_sampling import frame_populations
from elbow_swivel import descendants


class FramePlantProblem(JointPlantProblem):
    def __init__(self, rig, reader, rows, limits, seed_reader):
        super().__init__(rig, reader, rows, limits, seed_reader)
        self.frame_clocks = [frame_populations(r['stance_s']) for r in rows]
        if any(len(p['times_s']) < 2 for clocks in self.frame_clocks for p in clocks):
            raise ValueError('Every fixed game-frame clock needs at least two stance frames')
        old_rates = self.raw[self.rate_ids].copy()
        self.times = np.unique(np.concatenate([self.times] +
            [p['times_s'] for clocks in self.frame_clocks for p in clocks]))
        self.raw = np.array([reader.sample(float(t)) for t in self.times])
        self.rate_ids = np.searchsorted(self.times, self.uniform)
        if not np.array_equal(self.raw[self.rate_ids], old_rates):
            raise ValueError('Original uniform source rate population changed')
        self.local = self.raw.copy()
        for node, parent in enumerate(rig.parents):
            if parent >= 0:
                self.local[:, node] = np.linalg.inv(self.raw[:, parent]) @ self.raw[:, node]
        self.endpoint_masks = {n: tuple(np.fromiter(
            (compare(float(t), clock[key]) for t in self.times), bool, len(self.times))
            for compare, key in ((np.less_equal, 0), (np.greater_equal, -1)))
            for n, (_, clock, _) in self.channels.items() if n in self.nodes}
        for d, populations in zip(self.data, self.frame_clocks):
            r = d['row']
            d['contact_ids'] = np.searchsorted(self.times, d['contact_clock'])
            d['stance'] = np.flatnonzero((self.times >= r['stance_s'][0]) & (self.times <= r['stance_s'][1]))
            d['inside'] = np.flatnonzero((self.times >= r['edit_s'][0]) & (self.times <= r['edit_s'][1]))
            d['frame_populations'] = [dict(p, indices=np.searchsorted(self.times, p['times_s'])) for p in populations]

    def contact_constraints(self, world):
        parts = []
        for d in self.data:
            r = d['row']; limit = self.limits[r['id']]; up = r['up']
            # Anchors include every native key/event/frame point, without
            # ever differentiating that union (near-coincident keys remain).
            points = np.stack([p.evaluate(world) for p in d['patch_projections']], axis=2)
            error = points[d['stance']] - d['anchor']
            error -= (error @ up)[..., None] * up
            parts.append(((np.linalg.norm(error, axis=2) - limit['anchor']) / max(limit['anchor'], .0001)).ravel())
            # Legacy exact-boundary 120 Hz velocity population is retained.
            legacy = points[d['contact_ids']]
            velocity = np.diff(legacy, axis=0) / np.diff(d['contact_clock'])[:, None, None]
            velocity -= (velocity @ up)[..., None] * up
            parts.append(((np.linalg.norm(velocity, axis=2) - limit['speed']) / max(limit['speed'], .001)).ravel())
            for population in d['frame_populations']:
                velocity = np.diff(points[population['indices']], axis=0) * population['rate_hz']
                velocity -= (velocity @ up)[..., None] * up
                parts.append(((np.linalg.norm(velocity, axis=2) - limit['speed']) / max(limit['speed'], .001)).ravel())
        return np.concatenate(parts)

    def sparsity(self, *, native_roundtrip=None):
        if native_roundtrip is None:
            native_roundtrip = self.native_roundtrip
        values, _ = self.rotations(self.initial)
        size = len(self.constraints(values, self.world(values)))
        matrix = lil_matrix((size, len(self.initial)), dtype=int); offset = 0
        for order in (1, 2, 1, 2):
            count = len(self.uniform) - order
            for d in self.data:
                branch = descendants(self.rig.parents, d['row']['chain'][0])
                joints = np.flatnonzero(branch[np.asarray(self.rig.joints)[self.columns]])
                for key, col in self.dependencies(d):
                    a, b = d['clock'][key - 1], d['clock'][key + 1]
                    relevant = np.flatnonzero((self.uniform[:count] <= b) & (self.uniform[order:] >= a))
                    matrix[offset + (relevant[:, None] * len(self.columns) + joints).ravel(), col] = 1
            offset += count * len(self.columns)
        for d in self.data:
            stance = self.times[d['stance']]; inside = self.times[d['inside']]
            for key, col in self.dependencies(d):
                a, b = d['clock'][key - 1], d['clock'][key + 1]
                ids = np.flatnonzero((stance >= a) & (stance <= b))
                matrix[offset + ids, col] = 1
                matrix[offset + len(stance) + ids, col] = 1
                ids = np.flatnonzero((inside >= a) & (inside <= b))
                matrix[offset + 2 * len(stance) + ids, col] = 1
                matrix[offset + 2 * len(stance) + len(inside) + 3 * key + np.arange(3), col] = 1
            offset += 2 * len(stance) + len(inside) + 3 * len(d['clock'])
        for d in self.data:
            p = d['patch_vertices']; clock = self.times[d['stance']]
            for key, col in self.dependencies(d):
                a, b = d['clock'][key - 1], d['clock'][key + 1]
                ids = np.flatnonzero((clock >= a) & (clock <= b))
                matrix[offset + (ids[:, None] * p + np.arange(p)).ravel(), col] = 1
            offset += len(clock) * p
            clocks = [d['contact_clock']] + [pop['times_s'] for pop in d['frame_populations']]
            for clock in clocks:
                for key, col in self.dependencies(d):
                    a, b = d['clock'][key - 1], d['clock'][key + 1]
                    ids = np.flatnonzero((clock[:-1] <= b) & (clock[1:] >= a))
                    matrix[offset + (ids[:, None] * p + np.arange(p)).ravel(), col] = 1
                offset += (len(clock) - 1) * p
        assert offset == size
        result = matrix.tocsr()
        return vstack([result, result], format='csr') if native_roundtrip else result


def exterior_ramp(problem, x):
    """Hermite-shaped exterior native controls, not C1 exported animation.

Keep interior stance-key correction vectors exactly. Estimate their edge
slopes and join to zero at the original edit boundaries. Fractional stance
endpoints can change after interpolation; independent acceptance is required.
"""
    x = np.asarray(x, float).copy()
    problem.rotations(x)
    for d in problem.data:
        clock = d['clock']; r = d['row']
        vectors = np.zeros((len(clock), 3, 3)); vectors[d['free']] = x[d['ids']]
        inside = np.flatnonzero((clock >= r['stance_s'][0]) & (clock <= r['stance_s'][1]))
        if len(inside) < 2:
            raise ValueError('At least two stance keys required for exterior slopes')
        first, last = inside[0], inside[-1]
        first_slope = (vectors[inside[1]] - vectors[first]) / (clock[inside[1]] - clock[first])
        last_slope = (vectors[last] - vectors[inside[-2]]) / (clock[last] - clock[inside[-2]])
        for key in d['free']:
            if key < first:
                duration = float(clock[first] - clock[0]); u = float((clock[key] - clock[0]) / duration)
                vectors[key] = (-2 * u**3 + 3 * u**2) * vectors[first] + (u**3 - u**2) * duration * first_slope
            elif key > last:
                duration = float(clock[-1] - clock[last]); u = float((clock[key] - clock[last]) / duration)
                vectors[key] = (2 * u**3 - 3 * u**2 + 1) * vectors[last] + (u**3 - 2 * u**2 + u) * duration * last_slope
        x[d['ids']] = vectors[d['free']]
    problem.rotations(x)  # Component bounds remain hard; no silent clipping.
    return x
