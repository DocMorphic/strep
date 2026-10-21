"""Couple bounded pose corrections without changing fixed neighboring states.

All adjacent correction differences are active in the same solve. These are
parameter-step bounds, not total angular velocity or continuous contact proof.
Callers freeze each pose's floor working set during an optimizer invocation.
"""
import numpy as np


class CoupledPoseWindow:
    def __init__(self, problems, *, root_step_m, rotation_step_degrees):
        if (not isinstance(problems, list) or not 2 <= len(problems) <= 8
                or len({p.model.size for p in problems}) != 1
                or len({tuple(p.model.rotations) for p in problems}) != 1
                or len({getattr(p.model, 'root', None) for p in problems}) != 1
                or any(p.neighbors for p in problems)
                or not np.isfinite([root_step_m, rotation_step_degrees]).all()
                or root_step_m <= 0 or not 0 < rotation_step_degrees <= 180):
            raise ValueError('Two to eight equal-size poses without fixed neighbors and finite positive step bounds required')
        self.problems = problems.copy()
        self.width = problems[0].model.size
        self.size = self.width*len(problems)
        self.limits = np.r_[root_step_m, np.full((self.width-3)//3, np.deg2rad(rotation_step_degrees))]
        self.bounds = [bound for p in problems for bound in p.bounds]

    def unpack(self, values):
        values = np.asarray(values, float)
        if values.shape != (self.size,) or not np.isfinite(values).all():
            raise ValueError('Complete finite window parameters required')
        return values.reshape(len(self.problems), self.width)

    def values(self, values, *, full=False):
        poses = self.unpack(values)
        pose_rows = [(p.full_values(x) if full else p.values(x)) for p, x in zip(self.problems, poses)]
        delta = np.diff(poses, axis=0).reshape(len(poses)-1, -1, 3)
        steps = 1-np.sum(delta**2, axis=2)/self.limits**2
        return np.concatenate([*pose_rows, steps.reshape(-1)])

    def pair(self, values):
        poses = self.unpack(values)
        parts = [p.pair(x) for p, x in zip(self.problems, poses)]
        count = sum(len(gaps) for gaps, _ in parts)+(len(poses)-1)*len(self.limits)
        jac = np.zeros((count, self.size))
        row = 0
        for i, (gaps, gradient) in enumerate(parts):
            jac[row:row+len(gaps), i*self.width:(i+1)*self.width] = gradient
            row += len(gaps)
        for i, delta in enumerate(np.diff(poses, axis=0).reshape(len(poses)-1, -1, 3)):
            for j, limit in enumerate(self.limits):
                derivative = 2*delta[j]/limit**2
                jac[row, i*self.width+3*j:i*self.width+3*j+3] = derivative
                jac[row, (i+1)*self.width+3*j:(i+1)*self.width+3*j+3] = -derivative
                row += 1
        return self.values(values), jac

    def assess(self, values):
        poses = self.unpack(values)
        rows = [p.assess(x) for p, x in zip(self.problems, poses)]
        steps = np.linalg.norm(np.diff(poses, axis=0).reshape(len(poses)-1, -1, 3), axis=2)
        return dict(numerical_window_pass=bool(all(r['numerical_constraints_pass'] for r in rows)
                    and np.all(steps <= self.limits)), poses=rows,
                    maximum_root_step_m=float(steps[:, 0].max()),
                    maximum_rotation_parameter_step_degrees=float(np.rad2deg(steps[:, 1:]).max()),
                    minimum_fitting_gap=float(self.values(values, full=True).min()))
