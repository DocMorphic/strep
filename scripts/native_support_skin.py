"""Full skin for native support: preserve every skinned primitive and influence."""
import numpy as np
from paired_approach_basis import BoundSkin


class NativeSupportSkin(BoundSkin):
    """Shared single-skin vertex order, with zero-weight padding up to eight slots."""
    def __init__(self, rig):
        primitives = rig.primitives
        if not primitives or any(p['joints'] is None for p in primitives):
            raise ValueError('Native support requires all primitives to use the validated skin')
        width = max(p['joints'].shape[1] for p in primitives)
        nodes, weights, points, references = [], [], [], []
        self.primitive_offsets = [0]
        for p in primitives:
            ids = p['joints']; count = len(p['positions']); padding = width-ids.shape[1]
            # Unused slots have a valid skin index and exactly zero weight.
            indices = np.pad(ids, ((0,0),(0,padding)))
            nodes.append(np.asarray(rig.joints)[indices])
            weights.append(np.pad(p['weights'], ((0,0),(0,padding))))
            vertices = np.c_[p['positions'], np.ones(count)]
            points.append(np.einsum('vkij,vj->vki', rig.inverse[indices], vertices))
            references.extend((p['node'], p['primitive'], i) for i in range(count))
            self.primitive_offsets.append(self.primitive_offsets[-1]+count)
        self.nodes = np.concatenate(nodes)
        self.weights = np.concatenate(weights)
        self.points = np.concatenate(points)
        self.vertex_references = np.asarray(references, int)
