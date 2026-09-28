"""Opt-in bounded fitter using separately verified fractional skin derivatives."""
from bounded_path_trajectory import BoundedPathFitter
from batched_fractional_skin import BatchedFractionalActor


class BatchedBoundedPathFitter(BoundedPathFitter):
    def __init__(self,actors,**kwargs):
        super().__init__(actors,**kwargs)
        self.actors=[BatchedFractionalActor(actor,self.matrix) for actor in actors]
