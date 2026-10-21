"""Full-mesh pose values and derivatives for explicit offline correction trials.

Translations and right-multiplied local rotation edits propagate through the
actual hierarchy. Raw skin weights and homogeneous inverse binds are retained.
This is a pose model, not a solver, anatomical limit model or motion approval.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from target_rig_contact import SkinEvaluator


def skew(vector):
    x, y, z = vector
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def right_jacobian(vector):
    angle = np.linalg.norm(vector)
    hat = skew(vector)
    if angle < 1e-5:
        return np.eye(3) - (.5-angle**2/24)*hat + (1/6-angle**2/120)*hat@hat
    return np.eye(3) - (1-np.cos(angle))/angle**2*hat + (angle-np.sin(angle))/angle**3*hat@hat


class SurfacePoseModel:
    def __init__(self, rig, world, root, rotations):
        self.rig = rig
        self.parents = list(rig.parents)
        count = len(self.parents)
        if (type(root) is not int or root not in rig.joints or not isinstance(rotations, list)
                or not 1 <= len(rotations) <= 20 or len(set(rotations)) != len(rotations)
                or any(type(n) is not int or n not in rig.joints for n in rotations)):
            raise ValueError('Explicit skin root and 1-20 distinct editable skin rotations required')
        for node in rotations:
            seen = set()
            while node != root:
                if node < 0 or node in seen:
                    raise ValueError('All rotation edits must be at or below the translation root')
                seen.add(node)
                node = self.parents[node]
        world = np.asarray(world, float)
        if (world.shape != (count, 4, 4) or not np.isfinite(world).all()
                or not np.allclose(world[:, 3], [0, 0, 0, 1], atol=1e-9, rtol=0)):
            raise ValueError('Complete finite affine world pose required')
        self.root = root
        self.rotations = rotations.copy()
        self.size = 3 + 3*len(rotations)
        self.local = world.copy()
        self.order = []
        pending = set(range(count))
        while pending:
            ready = [n for n in sorted(pending) if self.parents[n] == -1 or self.parents[n] in self.order]
            if not ready:
                raise ValueError('Acyclic complete hierarchy required')
            self.order.extend(ready)
            pending.difference_update(ready)
        for node in self.order:
            parent = self.parents[node]
            if parent >= 0:
                self.local[node] = np.linalg.solve(world[parent], world[node])
        parent = self.parents[root]
        self.root_translation_map = np.eye(3) if parent < 0 else np.linalg.inv(world[parent, :3, :3])
        self.skin = SkinEvaluator(rig)

    def evaluate(self, values, *, derivatives=True):
        values = np.asarray(values, float)
        if values.shape != (self.size,) or not np.isfinite(values).all():
            raise ValueError('Complete finite pose parameters required')
        local = self.local.copy()
        local[self.root, :3, 3] += self.root_translation_map @ values[:3]
        differential = np.zeros((len(local), self.size, 4, 4)) if derivatives else None
        if derivatives:
            differential[self.root, :3, :3, 3] = self.root_translation_map.T
        for index, node in enumerate(self.rotations):
            vector = values[3+3*index:6+3*index]
            rotation = Rotation.from_rotvec(vector).as_matrix()
            local[node, :3, :3] = self.local[node, :3, :3] @ rotation
            if derivatives:
                right = right_jacobian(vector)
                for axis in range(3):
                    differential[node, 3+3*index+axis, :3, :3] = local[node, :3, :3] @ skew(right[:, axis])
        world = np.empty_like(local)
        for node in self.order:
            parent = self.parents[node]
            world[node] = local[node] if parent < 0 else world[parent] @ local[node]
            if derivatives and parent >= 0:
                differential[node] = differential[parent] @ local[node] + world[parent] @ differential[node]
        vertices = self.skin.vertices(world)
        jacobian = None
        if derivatives:
            jacobian = np.empty((len(vertices), 3, self.size))
            offset = 0
            for nodes, points, weights in self.skin.parts:
                # Bound intermediate allocation without reducing the evaluated population.
                for start in range(0, len(nodes), 128):
                    end = min(start+128, len(nodes))
                    jacobian[offset+start:offset+end] = np.einsum('vkqij,vkj,vk->viq',
                        differential[nodes[start:end], :, :3, :], points[start:end], weights[start:end])
                offset += len(nodes)
        return world, local, vertices, jacobian
