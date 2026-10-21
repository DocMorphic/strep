"""Conservative all-vertex floor constraint with lazy pose derivatives.

Log-sum-exp provides a smooth lower approximation of the minimum vertex height.
The declared gap bounds its bias in exact arithmetic; decoded all-vertex checks
remain authoritative. No vertex is omitted from fitting or final validation.
"""
import numpy as np
from surface_pose_constraints import PoseConstraints


def soft_floor(heights, gap_m):
    heights = np.asarray(heights, float)
    if (heights.ndim != 1 or not len(heights) or not np.isfinite(heights).all()
            or type(gap_m) not in (int, float) or not np.isfinite(gap_m) or gap_m <= 0):
        raise ValueError('Complete finite heights and positive approximation gap required')
    if len(heights) == 1:
        return float(heights[0]), np.ones(1)
    beta = np.log(len(heights))/gap_m
    minimum = float(heights.min())
    weights = np.exp(-(heights-minimum)*beta)
    total = float(weights.sum())
    return minimum-np.log(total)/beta, weights/total


class CompactPoseConstraints(PoseConstraints):
    def __init__(self, *args, floor_softmin_gap_m, **kwargs):
        super().__init__(*args, **kwargs)
        if (type(floor_softmin_gap_m) not in (int, float) or not np.isfinite(floor_softmin_gap_m)
                or not 0 < floor_softmin_gap_m <= self.floor-self.floor_fit):
            raise ValueError('Positive floor approximation gap within fitting reserve required')
        self.floor_softmin_gap_m = floor_softmin_gap_m
        self.derivative_evaluations = 0

    def pose(self, values, *, derivatives=True):
        values = np.asarray(values, float)
        changed = self.cached is None or not np.array_equal(values, self.cached)
        if changed or derivatives and self.cached_pose[3] is None:
            self.cached_pose = self.model.evaluate(values, derivatives=derivatives)
            self.cached = values.copy()
            self.evaluations += 1
            self.derivative_evaluations += int(derivatives)
        return self.cached_pose

    def values(self, values):
        values = np.asarray(values, float)
        points = self.pose(values, derivatives=False)[2]
        minimum, _ = soft_floor(points[:, 1], self.floor_softmin_gap_m)
        error = points[self.vertices]-self.targets
        gaps = [np.array([(minimum+self.floor_fit)/.1]),
                1-np.sum(error**2, axis=1)/self.contact_fit**2,
                1-np.sum(values[3:].reshape(-1, 3)**2, axis=1)/self.angles**2,
                np.array([1-np.sum(values[[0, 2]]**2)/self.horizontal**2])]
        for neighbor in self.neighbors:
            limits = np.r_[self.root_step, np.full(len(self.angles), self.rotation_step)]
            gaps.append(1-np.sum((values-neighbor).reshape(-1, 3)**2, axis=1)/limits**2)
        return np.concatenate(gaps)

    def pair(self, values):
        original, jac = super().pair(values)
        points = self.cached_pose[2]
        minimum, weights = soft_floor(points[:, 1], self.floor_softmin_gap_m)
        count = len(points)
        return (np.r_[(minimum+self.floor_fit)/.1, original[count:]],
                np.vstack([weights@jac[:count], jac[count:]]))
