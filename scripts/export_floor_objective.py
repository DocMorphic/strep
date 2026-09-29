"""Per-time full-skin floor inequalities on native export interpolation.

Preserve each source sample's existing depth, or zero penetration when clear.
This is an augmented objective, not a hard feasibility or continuous-time proof.
"""
import numpy as np
import torch

from linear_skin_operator import LinearSkinOperator
from export_motion_sampling import joint_trajectory


class ExportFloorObjective:
    def __init__(self, rotations, positions, parents, skin):
        self.parents = parents
        indices = np.asarray(skin['lbs_indices'])
        inverse = np.linalg.inv(skin['bind_rig_transform'])
        points = np.c_[skin['bind_vertices'], np.ones(len(indices))]
        bind = np.einsum('vwij,vj->vwi', inverse[indices], points)[..., :3]
        tensor = lambda x: torch.as_tensor(x, dtype=rotations.dtype, device=rotations.device)
        self.skin = LinearSkinOperator(torch.as_tensor(indices, dtype=torch.long, device=rotations.device),
                                       tensor(skin['lbs_weights']), tensor(bind), positions.shape[1])
        self.vertex_count = len(points)
        with torch.no_grad():
            source = self.minimum_heights(rotations, positions)
        self.reference = torch.minimum(source, torch.zeros_like(source)).detach()
        self.multiplier = torch.zeros_like(source)
        self.scale_m = .005
        self.penalty = 10.
        self.last = None

    def minimum_heights(self, rotations, positions):
        r, p = joint_trajectory(rotations, positions, self.parents, return_rotations=True)
        # Only the world Y row is needed. Chunk time to avoid constructing the
        # full frame/vertex/XYZ tensor or an eight-influence matrix gather.
        result = []
        for start in range(0, len(r), 48):
            affine = torch.cat([r[start:start+48, :, 1, :], p[start:start+48, :, 1, None]], -1)
            columns = affine.permute(1, 2, 0).reshape(self.skin.joint_count*4, -1)
            heights = torch.sparse.mm(self.skin.operator, columns)
            result.append(heights.min(dim=0).values)
        return torch.cat(result)

    def loss(self, rotations, positions):
        heights = self.minimum_heights(rotations, positions)
        if heights.shape != self.reference.shape:
            raise ValueError('Floor reference and candidate clocks differ')
        g = (self.reference-heights)/self.scale_m
        self.last = g.detach()
        self.last_heights = heights.detach()
        # Sum individual times so a brief penetration is not diluted by a
        # longer clip. Negative slack remains available to the AL update.
        return ((torch.relu(self.multiplier+self.penalty*g).square()-self.multiplier.square())/(2*self.penalty)).sum()

    def advance_stage(self, growth):
        if self.last is None:
            raise ValueError('Evaluate accepted floor samples before updating multipliers')
        if type(growth) not in [int, float] or not np.isfinite(growth) or growth <= 0:
            raise ValueError('Positive finite penalty growth required')
        self.multiplier = torch.relu(self.multiplier+self.penalty*self.last)
        self.penalty *= growth

    def record(self):
        return dict(vertex_count=self.vertex_count, samples=len(self.reference), fps=120,
                    lower_height_bounds_m=self.reference.tolist(), scale_m=self.scale_m, penalty=self.penalty,
                    maximum_violation_m=None if self.last is None else float(self.last.relu().max()*self.scale_m),
                    maximum_depth_m=None if self.last is None else float((-self.last_heights).clamp_min(0).max()),
                    scope='Full skin and all influences at every quarter-frame; source depth per time retained, '
                          'zero penetration when source is clear. No extra depth allowance. '
                          'Normalization is not a tolerance; augmented inequalities need independent export audit. '
                          'Not continuous collision, anatomical or physical support certification.')
