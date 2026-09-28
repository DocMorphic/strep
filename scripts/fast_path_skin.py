"""Exact integer-frame skin Jacobians; retain fractional interpolation path."""
import numpy as np
from paired_hand_trajectory import TrajectoryActor
from paired_hand_clearance import SkinPoints


class FastTrajectoryActor(TrajectoryActor):
    def __init__(self,actor,matrix):
        super().__init__(actor,matrix)
        self.integer_skin=SkinPoints(actor)
        self.control_maps=[np.kron(row[None,:],np.eye(actor.dim)) for row in matrix]

    def skin_pair(self,frame,x,vertices):
        if not np.isfinite(frame) or not 0<=frame<=len(self.local)-1:
            raise ValueError('Sample outside clip')
        if float(frame).is_integer():
            frame=int(frame)
            value=self.values(x)[frame]
            points,jac=self.integer_skin.evaluate(frame,value,vertices)
            return points,jac@self.control_maps[frame]
        # Actual exported local-rotation interpolation remains authoritative.
        return super().skin_pair(frame,x,vertices)
