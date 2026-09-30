"""Native-key finger curves with separate proposal and serialized evaluation."""
import numpy as np
from timed_rotation_edit import TimedRotationEdit, sampled_rotations
from paired_guarded_temporal import world_from_local


class NativeFingerMotion:
    def __init__(self, rig, hand_root, nodes, limits_degrees, times, window, peak):
        self.nodes = list(nodes); self.rig = rig
        limits = np.asarray(limits_degrees, float)
        if (hand_root not in rig.joints or not self.nodes or len(set(self.nodes)) != len(self.nodes)
                or limits.shape != (len(self.nodes),) or not np.isfinite(limits).all() or np.any(limits <= 0)
                or np.any(limits > 45) or not np.isfinite(peak) or not window[0] < peak < window[1]):
            raise ValueError('Mapped fingers, explicit rotation limits and interior peak required')
        for node in self.nodes:
            if node not in rig.joints or node == hand_root: raise ValueError('Only descendants of the hand may change')
            parent = rig.parents[node]
            while parent >= 0 and parent != hand_root: parent = rig.parents[parent]
            if parent != hand_root: raise ValueError('Only descendants of the hand may change')
        self.limits = np.deg2rad(limits)
        self.model = TimedRotationEdit(rig.document, rig.binary, [rig.document['nodes'][n]['name'] for n in self.nodes],
            times, window, [], knots=[window[0], peak, window[1]], limit_degrees=float(limits.max()))
        # Fixed-axis correction curves commute; native weight differences bound
        # adjacent correction angles before quantization (5 degrees maximum).
        for index, entry in enumerate(self.model.entries):
            weights = np.zeros(len(entry['clock'])); weights[entry['ids']] = entry['weights'][:, 0]
            maximum = float(np.abs(np.diff(weights)).max())
            if maximum: self.limits[index] = min(self.limits[index], np.deg2rad(5.)/maximum)
        self.size = self.model.size
        self.body = []
        for node in range(len(rig.parents)):
            parent = node
            while parent >= 0 and parent not in self.nodes: parent = rig.parents[parent]
            if parent < 0: self.body.append(node)

    def world(self, radians, *, quantize=True):
        values = self.model.quaternions(radians, quantize=quantize)
        if all(np.array_equal(values[e['node']], e['source']) for e in self.model.entries):
            return self.model.source_world.copy()
        local = self.model.local.copy()
        for entry in self.model.entries:
            node = entry['node']
            local[:, node, :3, :3] = sampled_rotations(entry['clock'], values[node], self.model.times)*self.model.scales[node][:, None, :]
        return world_from_local(local, self.model.parents)

    def export(self, radians, path):
        values = np.asarray(radians, float).reshape(len(self.nodes), 3)
        if not np.isfinite(values).all() or np.any(np.linalg.norm(values, axis=1) > self.limits):
            raise ValueError('Per-finger original edit limits exceeded')
        self.model.export(values.ravel(), path)


def palm_geometry(vertices, local_faces, center_index):
    """Actual skin vertex and area-weighted surface normal, not a joint proxy."""
    p, f = np.asarray(vertices, float), np.asarray(local_faces)
    if (p.ndim != 2 or p.shape[1] != 3 or not len(p) or not np.isfinite(p).all()
            or f.ndim != 2 or f.shape[1] != 3 or not len(f) or not np.issubdtype(f.dtype, np.integer)
            or f.min() < 0 or f.max() >= len(p) or type(center_index) is not int or not 0 <= center_index < len(p)):
        raise ValueError('Finite palm vertices, valid triangles and center index required')
    triangles = p[f]
    normal = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]).sum(axis=0)
    length = np.linalg.norm(normal)
    if not np.isfinite(length) or length < 1e-12: raise ValueError('Degenerate palm neighborhood')
    return p[center_index].copy(), normal/length
