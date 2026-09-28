"""Same bounded controls, with verified analytic integer skin derivatives."""
from bounded_path_trajectory import BoundedPathFitter
from fast_path_skin import FastTrajectoryActor


class FastBoundedPathFitter(BoundedPathFitter):
    def __init__(self, actors, **kwargs):
        super().__init__(actors, **kwargs)
        self.actors = [FastTrajectoryActor(actor, self.matrix) for actor in actors]
