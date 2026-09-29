"""Stationary material-point constraints at the native export audit clock."""
import numpy as np
import torch

from contact_spec import validate
from support_contact import regions
from floor_contact import Surface
from linear_skin_operator import LinearSkinOperator
from export_motion_sampling import joint_trajectory


class ExportPointPositionObjective:
    def __init__(self, rotations, positions, parents, skin, spec, *, tolerance=.005,
                 scaling='tolerance', penalty=300.):
        validate(spec, len(positions), regions(skin))
        if scaling not in ['metres', 'tolerance']:
            raise ValueError('Unknown point residual scaling')
        if type(tolerance) not in [int, float] or not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError('Positive finite point tolerance required')
        if type(penalty) not in [int, float] or not np.isfinite(penalty) or penalty <= 0:
            raise ValueError('Positive finite point penalty required')
        self.parents = parents
        self.frames = len(positions)
        self.tolerance = float(tolerance)
        self.scale = self.tolerance if scaling == 'tolerance' else 1.
        self.scaling = scaling
        self.penalty = float(penalty)
        self.rows = []
        for name, entry in spec['regions'].items():
            if entry['mode'] != 'explicit':
                continue
            for pin in entry['segments']:
                if pin['space'] != 'world' or 'vertex_id' not in pin:
                    raise ValueError('Export point positions require fixed material vertices and stationary world targets')
                self.rows.append(dict(region=name, vertex_id=pin['vertex_id'],
                    first_frame=pin['start_frame'], last_frame=pin['end_frame'], target_m=list(pin['position_m'])))
        if not self.rows:
            raise ValueError('At least one explicit stationary point required')
        self.vertices = sorted({row['vertex_id'] for row in self.rows})
        self.index = {v: i for i, v in enumerate(self.vertices)}
        surface = Surface(skin)
        ids = skin['lbs_indices'][self.vertices]
        bind = np.einsum('vwij,vj->vwi', surface.inverse[ids], surface.points[self.vertices])[..., :3]
        tensor = lambda x: torch.as_tensor(x, dtype=rotations.dtype, device=rotations.device)
        self.skin = LinearSkinOperator(torch.as_tensor(ids, dtype=torch.long, device=rotations.device),
            tensor(skin['lbs_weights'][self.vertices]), tensor(bind), positions.shape[1])
        self.targets = [tensor(row['target_m']) for row in self.rows]
        self.multipliers = [tensor(np.zeros((row['last_frame']-row['first_frame'])*4+1)) for row in self.rows]
        self.last = None

    def points(self, rotations, positions):
        if len(positions) != self.frames:
            raise ValueError('Point reference and candidate clocks differ')
        r, p = joint_trajectory(rotations, positions, self.parents, return_rotations=True)
        return self.skin(r, p)

    def loss(self, rotations, positions):
        points = self.points(rotations, positions)
        residuals, maxima, totals, counts = [], [], {}, {}
        for row, target, multiplier in zip(self.rows, self.targets, self.multipliers):
            selected = points[row['first_frame']*4:row['last_frame']*4+1, self.index[row['vertex_id']]]
            errors = torch.linalg.vector_norm(selected-target, dim=-1)
            g = (errors-self.tolerance)/self.scale
            terms = (torch.relu(multiplier+self.penalty*g).square()-multiplier.square())/(2*self.penalty)
            region = row['region']
            totals[region] = totals.get(region, 0)+terms.sum()
            counts[region] = counts.get(region, 0)+len(g)
            residuals.append(g.detach()); maxima.append(float(errors.detach().max()))
        self.last, self.maxima = residuals, maxima
        # Retain the existing equal-per-region policy. Average all samples
        # within a region, including every one of its disjoint intervals.
        return sum(totals[name]/counts[name] for name in totals)/len(totals)

    def advance_stage(self, growth):
        if self.last is None:
            raise ValueError('Evaluate accepted point samples before updating multipliers')
        if type(growth) not in [int, float] or not np.isfinite(growth) or growth <= 0:
            raise ValueError('Positive finite penalty growth required')
        self.multipliers = [torch.relu(m+self.penalty*g) for m, g in zip(self.multipliers, self.last)]
        self.penalty *= growth

    def record(self):
        return dict(fps=120, tolerance_m=self.tolerance, scaling=self.scaling, penalty=self.penalty,
            rows=[dict(**row, samples=len(m), maximum_error_m=None if self.last is None else self.maxima[i])
                  for i, (row, m) in enumerate(zip(self.rows, self.multipliers))],
            scope='All fixed stationary points and inclusive intervals at quarter-frames, all skin influences. '
                  'Replaces native-key point merit; unchanged per-region averaging and point tolerance. '
                  'Augmented objectives do not guarantee feasibility; export quantization and full quality need independent audit.')
