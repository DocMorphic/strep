"""Opt-in skin evaluation of unique vertices, restoring caller order exactly."""
import numpy as np
from batched_fractional_skin import BatchedFractionalActor
from batched_bounded_path import BatchedBoundedPathFitter


class UniqueFractionalActor(BatchedFractionalActor):
    def skin_pair(self, frame, x, vertices):
        vertices = np.asarray(vertices)
        if vertices.ndim != 1 or not np.issubdtype(vertices.dtype, np.integer):
            raise ValueError('Vertex indices must be a one-dimensional integer array')
        unique, inverse = np.unique(vertices, return_inverse=True)
        points, jacobian = super().skin_pair(frame, x, unique)
        return points[inverse], jacobian[inverse]


class UniqueBoundedPathFitter(BatchedBoundedPathFitter):
    def __init__(self, actors, **kwargs):
        super().__init__(actors, **kwargs)
        self.actors = [UniqueFractionalActor(actor, self.matrix) for actor in actors]
