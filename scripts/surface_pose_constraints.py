"""Explicit full-surface/contact/edit constraints for offline pose sequences.

Neighbor constraints bound correction-parameter changes, not total animation
velocity. Contacts and their phases must be supplied by the authoring caller.
"""
import numpy as np


class PoseConstraints:
    def __init__(self, model, *, angles_degrees, root_horizontal_m, root_vertical_m,
                 floor_depth_m, contact_error_m, floor_reserve_m, contact_reserve_m,
                 contacts, neighbors=(), root_step_m=.025, rotation_step_degrees=5.):
        self.model = model
        self.angles = np.deg2rad(np.asarray(angles_degrees, float))
        numbers = np.asarray([root_horizontal_m, root_vertical_m, floor_depth_m, contact_error_m,
                              floor_reserve_m, contact_reserve_m, root_step_m, rotation_step_degrees], float)
        if (self.angles.shape != (len(model.rotations),) or not np.isfinite(self.angles).all()
                or np.any(self.angles <= 0) or np.any(self.angles > np.pi)
                or not np.isfinite(numbers).all() or np.any(numbers[:4] <= 0)
                or not 0 <= floor_reserve_m < floor_depth_m
                or not 0 <= contact_reserve_m < contact_error_m
                or root_step_m <= 0 or not 0 < rotation_step_degrees <= 180):
            raise ValueError('Finite positive edit/contact limits and interior reserves required')
        self.horizontal = root_horizontal_m
        self.vertical = root_vertical_m
        self.floor = floor_depth_m
        self.contact = contact_error_m
        self.floor_fit = floor_depth_m-floor_reserve_m
        self.contact_fit = contact_error_m-contact_reserve_m
        self.root_step = root_step_m
        self.rotation_step = np.deg2rad(rotation_step_degrees)
        self.vertices = []
        self.targets = []
        for contact in contacts:
            vertex = contact['vertex']
            target = np.asarray(contact['target_m'], float)
            if (type(vertex) is not int or not 0 <= vertex < model.skin.count or vertex in self.vertices
                    or target.shape != (3,) or not np.isfinite(target).all()):
                raise ValueError('Distinct complete contact vertices and finite targets required')
            self.vertices.append(vertex)
            self.targets.append(target.copy())
        self.vertices = np.asarray(self.vertices, int)
        self.targets = np.asarray(self.targets, float).reshape(-1, 3)
        self.neighbors = [np.asarray(n, float).copy() for n in neighbors]
        if len(self.neighbors) > 2 or any(n.shape != (model.size,) or not np.isfinite(n).all() for n in self.neighbors):
            raise ValueError('At most two complete finite neighboring corrections required')
        self.bounds = [(-self.horizontal, self.horizontal), (0., self.vertical),
                       (-self.horizontal, self.horizontal)] + [(-a, a) for a in np.repeat(self.angles, 3)]
        self.cached = None
        self.cached_pose = None
        self.evaluations = 0

    def pose(self, values):
        values = np.asarray(values, float)
        if self.cached is None or not np.array_equal(values, self.cached):
            self.cached_pose = self.model.evaluate(values)
            self.cached = values.copy()
            self.evaluations += 1
        return self.cached_pose

    def pair(self, values):
        values = np.asarray(values, float)
        _, _, points, jac = self.pose(values)
        error = points[self.vertices]-self.targets
        rotation = values[3:].reshape(-1, 3)
        gaps = [(points[:, 1]+self.floor_fit)/.1,
                1-np.sum(error**2, axis=1)/self.contact_fit**2,
                1-np.sum(rotation**2, axis=1)/self.angles**2,
                np.array([1-np.sum(values[[0, 2]]**2)/self.horizontal**2])]
        rows = [jac[:, 1]/.1, -2*np.einsum('vi,vij->vj', error, jac[self.vertices])/self.contact_fit**2]
        angular = np.zeros((len(self.angles), self.model.size))
        for i in range(len(self.angles)):
            angular[i, 3+3*i:6+3*i] = -2*rotation[i]/self.angles[i]**2
        horizontal = np.zeros((1, self.model.size))
        horizontal[0, [0, 2]] = -2*values[[0, 2]]/self.horizontal**2
        rows.extend([angular, horizontal])
        for neighbor in self.neighbors:
            delta = (values-neighbor).reshape(-1, 3)
            limits = np.r_[self.root_step, np.full(len(self.angles), self.rotation_step)]
            gaps.append(1-np.sum(delta**2, axis=1)/limits**2)
            derivative = np.zeros((len(limits), self.model.size))
            for i, limit in enumerate(limits):
                derivative[i, 3*i:3*i+3] = -2*delta[i]/limit**2
            rows.append(derivative)
        return np.concatenate(gaps), np.vstack(rows)

    def assess(self, values):
        values = np.asarray(values, float)
        _, _, points, _ = self.pose(values)
        contact = np.linalg.norm(points[self.vertices]-self.targets, axis=1)
        angles = np.linalg.norm(values[3:].reshape(-1, 3), axis=1)
        floor = max(0., -float(points[:, 1].min()))
        steps = [np.linalg.norm((values-n).reshape(-1, 3), axis=1) for n in self.neighbors]
        physical = bool(floor <= self.floor and np.all(contact <= self.contact)
            and np.all(angles <= self.angles) and np.linalg.norm(values[[0, 2]]) <= self.horizontal
            and 0 <= values[1] <= self.vertical
            and all(s[0] <= self.root_step and np.all(s[1:] <= self.rotation_step) for s in steps))
        return dict(numerical_constraints_pass=physical, floor_depth_m=floor,
                    maximum_contact_error_m=float(contact.max()) if len(contact) else None,
                    minimum_fitting_gap=float(self.pair(values)[0].min()),
                    maximum_neighbor_root_step_m=max((float(s[0]) for s in steps), default=0.),
                    maximum_neighbor_rotation_parameter_step_degrees=max((float(np.rad2deg(s[1:]).max()) for s in steps), default=0.))
