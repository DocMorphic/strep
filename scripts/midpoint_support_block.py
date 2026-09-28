"""Coupled support proposals with explicit interpolated-skin floor rows."""
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from coupled_support_block import CoupledBlock, embed
from rig_clearance_fit import right_jacobian
from angular_release_block import skew
from rig_transition import compose


def interpolate_rotations(left, right, fraction):
    a, b = Rotation.from_matrix(left), Rotation.from_matrix(right)
    return (a * Rotation.from_rotvec((a.inv() * b).as_rotvec() * fraction)).as_matrix()


class MidpointCoupledBlock(CoupledBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This derivative permits editing the root rotation and its descendants,
        # but not ancestors that would change the root's world-to-local offset.
        parent = self.fitter.rig.parents[self.root]
        while parent >= 0:
            if parent in self.fitter.nodes:
                raise ValueError('Midpoint root derivative requires fixed root ancestors')
            parent = self.fitter.rig.parents[parent]

    def midpoint_surface(self, edge, values, quantized):
        fitter = self.fitter
        endpoint = [fitter.pose(edge+i, values[edge+i]) for i in (0, 1)]
        left, right = [p[1] for p in endpoint]
        times = self.oracle.times[edge:edge+2]
        t = float(((edge+.5)/30-float(times[0]))/float(times[1]-times[0]))
        local = self.oracle.reference.copy()
        animated = self.oracle.animated
        local[animated, :3, 3] = (1-t)*left[animated, :3, 3]+t*right[animated, :3, 3]
        local[animated, :3, :3] = interpolate_rotations(left[animated, :3, :3], right[animated, :3, :3], t)
        world = compose(local[None], fitter.rig.parents)[0]
        axes = [[], []]
        step = 1e-6
        for j, node in enumerate(fitter.nodes):
            parent = fitter.rig.parents[node]
            parent_rotation = np.eye(3) if parent < 0 else world[parent, :3, :3]
            for side in (0, 1):
                frame = edge+side
                value = values[frame, 3+j*3:6+j*3]
                # Differentiate only the small local SLERP map. Skin derivatives
                # remain analytic and include every weighted descendant vertex.
                columns = []
                for axis in range(3):
                    delta = np.eye(3)[axis]*step
                    mids = []
                    for sign in (1, -1):
                        changed = fitter.local[frame, node, :3, :3] @ Rotation.from_rotvec(value+sign*delta).as_matrix()
                        a = changed if side == 0 else left[node, :3, :3]
                        b = changed if side == 1 else right[node, :3, :3]
                        mids.append(interpolate_rotations(a[None], b[None], t)[0])
                    dR = (mids[0]-mids[1])/(2*step)
                    omega = dR @ local[node, :3, :3].T
                    vector = np.array([omega[2, 1]-omega[1, 2], omega[0, 2]-omega[2, 0], omega[1, 0]-omega[0, 1]])*.5
                    columns.append(parent_rotation @ vector)
                axes[side].append(np.array(columns).T)
        root_parent = fitter.rig.parents[self.root]
        half_parent = np.eye(3) if root_parent < 0 else world[root_parent, :3, :3]
        root_jac = []
        for side, weight in ((0, 1-t), (1, t)):
            parent_rotation = np.eye(3) if root_parent < 0 else endpoint[side][0][root_parent, :3, :3]
            root_jac.append(weight * half_parent @ np.linalg.inv(parent_rotation))
        heights, derivatives = [], [[], []]
        for nodes, points, weights in fitter.skin.parts:
            components = np.einsum('vkij,vkj->vki', world[nodes, :3, :], points)
            heights.append(np.sum(components[:, :, 1]*weights, axis=1))
            root_mass = np.sum(weights*fitter.descendants[self.root][nodes], axis=1)
            rows = [np.zeros((len(nodes), self.columns)) for _ in (0, 1)]
            for side in (0, 1): rows[side][:, :3] = root_mass[:, None]*root_jac[side][1]
            for j, node in enumerate(fitter.nodes):
                weighted = weights*fitter.descendants[node][nodes]
                delta = np.sum((components-world[node, :3, 3])*weighted[:, :, None], axis=1)
                for side in (0, 1):
                    axis = axes[side][j]
                    rows[side][:, 3+j*3:6+j*3] = delta[:, 0, None]*axis[2]-delta[:, 2, None]*axis[0]
            for side in (0, 1): derivatives[side].append(rows[side])
        height = np.concatenate(heights)
        if quantized:
            height = fitter.rig.vertices(self.oracle.half_pose(endpoint[0][0], endpoint[1][0], int(edge)))[:, 1]
        matrix = sparse.csc_matrix((len(height), self.width))
        for side in (0, 1):
            frame = edge+side
            if frame in self.lookup:
                matrix += embed(np.concatenate(derivatives[side]), self.lookup[frame]*self.columns, self.width)
        return height, matrix

    def pair(self, x, quantized=True):
        objective, gradient, constraints, values = super().pair(x, quantized)
        for edge in self.affected_edges:
            heights, jacobian = self.midpoint_surface(edge, values, quantized)
            lower = -self.envelope['half_depths'][edge]-self.envelope['position_epsilon_m']
            constraints.lower(heights-lower, jacobian, 'midpoint_floor')
        return objective, gradient, constraints, values
