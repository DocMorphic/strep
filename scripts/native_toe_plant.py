"""Fixed-frame planting with explicitly bounded extra foot-descendant rotations."""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.sparse import lil_matrix, vstack
from native_frame_plant import FramePlantProblem
from elbow_swivel import descendants


class ToePlantProblem(FramePlantProblem):
    def __init__(self, rig, reader, rows, limits, seed_reader, additions):
        self.extras = []
        super().__init__(rig, reader, rows, limits, seed_reader)
        self.leg_size = len(self.initial)
        initial, lower, upper = self.initial.tolist(), self.lower.tolist(), self.upper.tolist()
        seed = {node: q for node, kind, clock, q, mode in seed_reader.channels if kind == 'rotation'}
        for d in self.data:
            row = d['row']; a, b = row['edit_keys']
            for permission in additions.get(row['id'], []):
                node = permission['node']; original = self.channels[node][2][a:b + 1]
                warm = seed[node][a:b + 1]
                vectors = (Rotation.from_quat(original).inv() * Rotation.from_quat(warm)).as_rotvec()
                vectors[np.all(original == warm, axis=1)] = 0
                start = len(initial); initial.extend(vectors[d['free']].ravel())
                bound = np.deg2rad(permission['angle'])
                lower.extend(np.full(3 * len(d['free']), -bound)); upper.extend(np.full(3 * len(d['free']), bound))
                self.extras.append(dict(row=row, clock=d['clock'], original=original, free=d['free'],
                    node=node, angle=permission['angle'], ids=np.arange(start, len(initial)).reshape(-1, 3)))
        self.nodes = sorted(set(self.nodes) | {e['node'] for e in self.extras})
        self.initial, self.lower, self.upper = map(lambda a: np.asarray(a, float), (initial, lower, upper))
        self.endpoint_masks = {n: tuple(np.fromiter(
            (compare(float(t), clock[key]) for t in self.times), bool, len(self.times))
            for compare, key in ((np.less_equal, 0), (np.greater_equal, -1)))
            for n, (_, clock, _) in self.channels.items() if n in self.nodes}
        self.rotations(self.initial)

    def rotations(self, x):
        x = np.asarray(x, float)
        if x.shape != self.initial.shape or not np.isfinite(x).all() or np.any(x < self.lower) or np.any(x > self.upper):
            raise ValueError('Finite joint rotation controls inside component boxes required')
        values = {n: self.channels[n][2].astype(float).copy() for n in self.nodes}; angles = []
        for d in self.data:
            row = d['row']; a, b = row['edit_keys']
            vectors = np.zeros((len(d['clock']), 3, 3)); vectors[d['free']] = x[d['ids']]
            q = d['original'].astype(float).copy(); active = np.any(vectors != 0, axis=2)
            if active.any():
                q[active] = (Rotation.from_quat(q[active]) * Rotation.from_rotvec(vectors[active])).as_quat()
                q[active] *= np.where(np.sum(q[active] * d['original'][active], axis=1) < 0, -1., 1.)[:, None]
            for j, node in enumerate(row['chain']): values[node][a:b + 1] = q[:, j]
            angles.append(np.rad2deg(np.linalg.norm(vectors, axis=2)))
        for e in self.extras:
            a, b = e['row']['edit_keys']; vectors = np.zeros((len(e['clock']), 3)); vectors[e['free']] = x[e['ids']]
            q = e['original'].astype(float).copy(); active = np.any(vectors != 0, axis=1)
            if active.any():
                q[active] = (Rotation.from_quat(q[active]) * Rotation.from_rotvec(vectors[active])).as_quat()
                q[active] *= np.where(np.sum(q[active] * e['original'][active], axis=1) < 0, -1., 1.)[:, None]
            values[e['node']][a:b + 1] = q
            angles.append(np.rad2deg(np.linalg.norm(vectors, axis=1)))
        return values, angles

    def core_constraints(self, values, world):
        parts = [super().core_constraints(values, world)]
        for e in self.extras:
            a, b = e['row']['edit_keys']
            angle = np.rad2deg((Rotation.from_quat(e['original']).inv()
                * Rotation.from_quat(values[e['node']][a:b + 1])).magnitude())
            parts.append((angle - e['angle']) / max(e['angle'], .01))
        return np.concatenate(parts)

    def dependencies(self, d):
        for key, col in super().dependencies(d): yield key, col
        for e in self.extras:
            if e['row']['id'] == d['row']['id']:
                for key, cols in zip(e['free'], e['ids']):
                    for col in cols: yield int(key), int(col)

    def sparsity(self, *, native_roundtrip=None):
        if native_roundtrip is None: native_roundtrip = self.native_roundtrip
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
                matrix[offset + ids, col] = 1; matrix[offset + len(stance) + ids, col] = 1
                ids = np.flatnonzero((inside >= a) & (inside <= b))
                matrix[offset + 2 * len(stance) + ids, col] = 1
                matrix[offset + 2 * len(stance) + len(inside) + 3 * key + np.arange(3), col] = 1
            offset += 2 * len(stance) + len(inside) + 3 * len(d['clock'])
        for e in self.extras:
            for key, cols in zip(e['free'], e['ids']): matrix[offset + key, cols] = 1
            offset += len(e['clock'])
        for d in self.data:
            p = d['patch_vertices']; clock = self.times[d['stance']]
            for key, col in self.dependencies(d):
                a, b = d['clock'][key - 1], d['clock'][key + 1]
                ids = np.flatnonzero((clock >= a) & (clock <= b))
                matrix[offset + (ids[:, None] * p + np.arange(p)).ravel(), col] = 1
            offset += len(clock) * p
            for clock in [d['contact_clock']] + [pop['times_s'] for pop in d['frame_populations']]:
                for key, col in self.dependencies(d):
                    a, b = d['clock'][key - 1], d['clock'][key + 1]
                    ids = np.flatnonzero((clock[:-1] <= b) & (clock[1:] >= a))
                    matrix[offset + (ids[:, None] * p + np.arange(p)).ravel(), col] = 1
                offset += (len(clock) - 1) * p
        assert offset == size
        result = matrix.tocsr()
        return vstack([result, result], format='csr') if native_roundtrip else result
