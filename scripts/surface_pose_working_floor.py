"""Growing floor working sets with mandatory complete geometry assessment.

Only optimizer rows are reduced. Full vertex evaluation, failure ranking and
acceptance use every vertex. An exhausted solve is not an infeasibility proof.
Callers must freeze the row set during each optimizer invocation.
"""
import numpy as np
from surface_pose_constraints import PoseConstraints


class WorkingFloorConstraints(PoseConstraints):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.floor_vertices = np.empty(0, dtype=int)
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

    def full_values(self, values):
        values = np.asarray(values, float)
        points = self.pose(values, derivatives=False)[2]
        error = points[self.vertices]-self.targets
        gaps = [(points[:, 1]+self.floor_fit)/.1,
                1-np.sum(error**2, axis=1)/self.contact_fit**2,
                1-np.sum(values[3:].reshape(-1, 3)**2, axis=1)/self.angles**2,
                np.array([1-np.sum(values[[0, 2]]**2)/self.horizontal**2])]
        for neighbor in self.neighbors:
            limits = np.r_[self.root_step, np.full(len(self.angles), self.rotation_step)]
            gaps.append(1-np.sum((values-neighbor).reshape(-1, 3)**2, axis=1)/limits**2)
        return np.concatenate(gaps)

    def grow(self, values, *, batch_size=32):
        if type(batch_size) is not int or not 1 <= batch_size <= 4096:
            raise ValueError('Explicit positive floor batch size at most 4096 required')
        floor = self.full_values(values)[:self.model.skin.count]
        order = np.argsort(floor, kind='stable')
        missing = order[~np.isin(order, self.floor_vertices)]
        if len(self.floor_vertices):
            missing = missing[floor[missing] < 0]
        added = missing[:batch_size]
        self.floor_vertices = np.union1d(self.floor_vertices, added)
        return added.tolist()

    def row_indices(self):
        if not len(self.floor_vertices):
            raise ValueError('Initialize a floor working set before optimizer evaluation')
        count = self.model.skin.count
        tail = len(self.vertices)+len(self.angles)+1+len(self.neighbors)*(len(self.angles)+1)
        return np.r_[self.floor_vertices, np.arange(count, count+tail)]

    def values(self, values):
        return self.full_values(values)[self.row_indices()]

    def pair(self, values):
        gaps, jacobian = super().pair(values)
        rows = self.row_indices()
        return gaps[rows], jacobian[rows]

    def assess(self, values):
        # Parent checks complete points and explicit edit/neighbor limits. Replace
        # its working-row minimum with the complete fitting minimum for ranking.
        result = super().assess(values)
        result['minimum_fitting_gap'] = float(self.full_values(values).min())
        result['floor_working_vertices'] = len(self.floor_vertices)
        result['floor_assessed_vertices'] = self.model.skin.count
        return result
