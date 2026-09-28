"""Held support plus a soft cap on actual full-clip foot accelerations."""
import numpy as np
from support_reference_fit import SupportReferenceFitter
from foot_acceleration import foot_acceleration_pair, foot_acceleration_energy


class SupportAccelerationFitter(SupportReferenceFitter):
    def initialize_dynamics(self, parameters, caps, weight=1.):
        self.acceleration_weight = weight
        self.acceleration_caps = np.asarray(caps, float).copy()
        self.centroid_track = np.array([self.centroids(self.rig.vertices(self.pose(f, x)[0]))
                                       for f, x in enumerate(parameters)])
        self.initial_acceleration_energy = self.acceleration_energy()

    def centroids(self, positions):
        return np.array([positions[patch['vertices']].mean(axis=0)
                         for patch in self.spec['patches'].values()])

    def surface_jacobian(self, frame, values):
        positions, jac = super().surface_jacobian(frame, values)
        self._surface_frame = frame
        self._surface_values = values.copy()
        self._centroids = self.centroids(positions)
        self._centroid_jac = np.array([jac[patch['vertices']].mean(axis=0)
                                     for patch in self.spec['patches'].values()])
        return positions, jac

    def objective_pair(self, frame, values, neighbors):
        residual, derivative = super().objective_pair(frame, values, neighbors)
        extra, jac = foot_acceleration_pair(self.centroid_track, frame, self._centroids,
            self._centroid_jac, self.acceleration_caps, self.spec['fps'], self.acceleration_weight)
        return np.r_[residual, extra], np.vstack([derivative, jac])

    def accept_frame(self, frame, values):
        # The optimizer may finish at a rejected trial. Never use a stale skin.
        if getattr(self, '_surface_frame', None) != frame or not np.array_equal(self._surface_values, values):
            self.surface_jacobian(frame, values)
        self.centroid_track[frame] = self._centroids

    def acceleration_energy(self):
        return foot_acceleration_energy(self.centroid_track, self.acceleration_caps,
                                        self.spec['fps'], self.acceleration_weight)
