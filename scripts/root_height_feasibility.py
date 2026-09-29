"""Root-height-only feasibility proposals with original source constraints.

Rotations and all other root coordinates remain fixed. Cached skin trajectories
are valid only for this translation subspace; this is not a general pose solver.
Every proposal is checked against every sampled inequality, not only witnesses
used by the local Jacobian. Export and broader quality still need separate audit.
"""
import numpy as np
import torch

from export_motion_sampling import joint_trajectory
from export_point_position_objective import ExportPointPositionObjective
from export_point_rate_objective import ExportPointRateObjective
from export_floor_objective import ExportFloorObjective
from export_rate_objective import ExportRateObjective
from linear_feasibility_restore import linear_step


def interpolation_matrix(frames, free):
    """Match native export float32 key times, including held boundary keys."""
    keys = (np.arange(frames, dtype=np.float32)/np.float32(30)).astype(float)
    times = np.arange((frames-1)*4+1)/120
    left = np.clip(np.searchsorted(keys, times, side='right')-1, 0, frames-2)
    fraction = np.clip((times-keys[left])/(keys[left+1]-keys[left]), 0, 1)
    full = np.zeros((len(times), frames))
    full[np.arange(len(times)), left] = 1-fraction
    full[np.arange(len(times)), left+1] = fraction
    return full[:, free]


def norm_rows(vectors, vertical_jacobian):
    """Norm values and derivatives when only world Y can change."""
    lengths = np.linalg.norm(vectors, axis=-1)
    slope = np.divide(vectors[..., 1], lengths, out=np.zeros_like(lengths), where=lengths>0)
    return lengths, slope[..., None]*vertical_jacobian


class RootHeightProblem:
    def __init__(self, source, seed, parents, skin, spec, window, max_lift):
        if type(max_lift) not in [int, float] or not np.isfinite(max_lift) or max_lift<=0:
            raise ValueError('Positive finite original root budget required')
        self.source, self.seed = source, seed
        frames = len(source['root_positions'])
        if len(seed['root_positions']) != frames:
            raise ValueError('Source and seed clocks differ')
        # Constructors validate the authored intervals and rate window.
        tensor = lambda x: torch.as_tensor(x, dtype=torch.float64)
        sr, sp = tensor(source['global_rot_mats']), tensor(source['posed_joints'])
        cr, cp = tensor(seed['global_rot_mats']), tensor(seed['posed_joints'])
        self.position = ExportPointPositionObjective(sr, sp, parents, skin, spec)
        self.point_rate = ExportPointRateObjective(sr, sp, parents, skin, spec, window)
        self.floor = ExportFloorObjective(sr, sp, parents, skin)
        self.global_rate = ExportRateObjective(sr, sp, parents)
        self.free = np.arange(window[0]+int(window[0]>0), window[1]+int(window[1]==frames-1))
        if not len(self.free): raise ValueError('No free root keys inside held boundaries')
        self.basis = interpolation_matrix(frames, self.free)
        self.max_lift = float(max_lift)
        lift = seed['root_positions'][:, 1].astype(float)-source['root_positions'][:, 1]
        if np.any(lift < -2e-7) or np.any(lift > max_lift+2e-7):
            raise ValueError('Seed exceeds original source root budget')
        if np.any(lift[self.free]<0) or np.any(lift[self.free]>max_lift):
            raise ValueError('Free seed root keys must lie exactly within original bounds')
        self.start = lift[self.free]-max_lift/2
        self.bounds = np.full(len(self.free), max_lift/2)
        weights = np.asarray(skin['lbs_weights'], dtype=float).sum(-1)
        self.weights = weights
        self.point_weights = weights[self.position.vertices]
        self.rate_weights = weights[self.point_rate.points]
        with torch.no_grad():
            r, p = joint_trajectory(cr, cp, parents, return_rotations=True)
            self.joints = p.numpy()
            self.points = self.position.skin(r, p).numpy()
            self.rate_points = self.point_rate.skin(r, p).numpy()
            heights = []
            for start in range(0, len(r), 48):
                affine = torch.cat([r[start:start+48, :, 1, :], p[start:start+48, :, 1, None]], -1)
                columns = affine.permute(1, 2, 0).reshape(self.floor.skin.joint_count*4, -1)
                heights.append(torch.sparse.mm(self.floor.skin.operator, columns).T.numpy())
            self.heights = np.concatenate(heights)
        self.floor_reference = self.floor.reference.numpy()
        self.masks = [[mask.numpy() for mask in masks] for masks in self.point_rate.masks]

    def evaluate(self, x, jacobian=True):
        x = np.asarray(x, dtype=float)
        if x.shape != self.start.shape or not np.isfinite(x).all():
            raise ValueError('Finite free-root coordinate vector required')
        shift = self.basis@(x-self.start)
        points = self.points.copy(); points[..., 1] += shift[:, None]*self.point_weights
        rates = self.rate_points.copy(); rates[..., 1] += shift[:, None]*self.rate_weights
        joints = self.joints.copy(); joints[..., 1] += shift[:, None]
        values, derivatives, groups = [], [], {}
        def add(name, c, j):
            start = sum(len(v) for v in values)
            values.append(c); groups[name] = [start, start+len(c)]
            if jacobian: derivatives.append(j)
        for i, (row, target) in enumerate(zip(self.position.rows, self.position.targets)):
            select = slice(row['first_frame']*4, row['last_frame']*4+1)
            index = self.position.index[row['vertex_id']]
            errors, j = norm_rows(points[select, index]-target.numpy(), self.basis[select]*self.point_weights[index])
            add('pin:'+str(i), (self.position.tolerance-errors)/self.position.scale, -j/self.position.scale)
        for order in [1, 2]:
            frequency = 120**order
            db = np.diff(self.basis, n=order, axis=0)*frequency
            rv = np.diff(rates, n=order, axis=0)*frequency
            for i, (row, masks, caps, scales) in enumerate(zip(self.point_rate.rows, self.masks, self.point_rate.ceilings, self.point_rate.scales)):
                mask = masks[order-1]; index = row['point']
                speeds, j = norm_rows(rv[mask, index], db[mask]*self.rate_weights[index])
                scale = float(scales[order-1]); cap = float(caps[order-1])
                add('point_rate:'+str(i)+':'+str(order), (cap-speeds)/scale, -j/scale)
            # One maximum joint witness per time has the same feasible set as
            # every joint row. Re-select witnesses at every proposed motion.
            gv = np.diff(joints, n=order, axis=0)*frequency
            lengths = np.linalg.norm(gv, axis=-1)
            witness = lengths.argmax(axis=1)
            selected = gv[np.arange(len(gv)), witness]
            peaks, j = norm_rows(selected, db)
            cap = float(self.global_rate.ceilings[order-1]); scale = float(self.global_rate.scales[order-1])
            add('global_rate:'+str(order), (cap-peaks)/scale, -j/scale)
        heights = self.heights+shift[:, None]*self.weights
        witness = heights.argmin(axis=1)
        minimum = heights[np.arange(len(heights)), witness]
        add('floor', (minimum-self.floor_reference)/self.floor.scale_m,
            self.basis*self.weights[witness, None]/self.floor.scale_m)
        c = np.concatenate(values)
        summary = {name: dict(minimum_slack=float(c[a:b].min()), violations=int((c[a:b]<0).sum())) for name, (a, b) in groups.items()}
        return c, np.concatenate(derivatives) if jacobian else None, summary

    def motion(self, x):
        delta = np.zeros(len(self.seed['root_positions']))
        delta[self.free] = np.asarray(x)-self.start
        result = {name: value.copy() for name, value in self.seed.items()}
        for name in ['root_positions', 'posed_joints']:
            result[name] = result[name].astype(np.float64)
            result[name][..., 1] += delta if name=='root_positions' else delta[:, None]
        return result

    def reference_residuals(self, motion):
        """Slow independent full interpolation/skin path for cache validation."""
        r = torch.as_tensor(motion['global_rot_mats'], dtype=torch.float64)
        p = torch.as_tensor(motion['posed_joints'], dtype=torch.float64)
        with torch.no_grad():
            for obj in [self.position, self.point_rate, self.global_rate, self.floor]: obj.loss(r, p)
        values = [-g.numpy() for g in self.position.last]
        for order in range(2):
            values.extend(-g[order].numpy() for g in self.point_rate.last)
            values.append(-self.global_rate.last[order].max(dim=1).values.numpy())
        values.append(-self.floor.last.numpy())
        return np.concatenate(values)


def solve(problem, attempts=6, trust=1e-5, margin=1e-4, progress=None):
    """Retain failed proposals; exact sampled slack must improve, never waived."""
    x = problem.start.copy(); history = []
    for iteration in range(attempts):
        c, j, before = problem.evaluate(x)
        if c.min()>=0: break
        delta, record = linear_step(x, c, j, problem.bounds, trust, margin)
        record.update(iteration=iteration+1, before=before, trials=[])
        accepted = False
        if delta is not None:
            record['proposed_delta_m'] = delta.tolist()
            for backtrack in range(8):
                fraction = .5**backtrack; trial = x+fraction*delta
                v, _, summary = problem.evaluate(trial, jacobian=False)
                # Passing rows may never become violations. Already failing
                # rows must improve the worst slack without moving failures.
                passed_preserved = bool((v[c>=0]>=0).all())
                good = bool(np.isfinite(v).all() and passed_preserved and
                            np.all(np.abs(trial)<=problem.bounds) and v.min()>c.min())
                record['trials'].append(dict(fraction=fraction, minimum_slack=float(v.min()),
                    passing_rows_preserved=passed_preserved, accepted=good, groups=summary))
                if good: x=trial; accepted=True; break
        record['accepted'] = accepted; history.append(record)
        if progress: progress(record)
        if not accepted: break
    c, _, summary = problem.evaluate(x, jacobian=False)
    return problem.motion(x), dict(history=history, final_coordinates=x.tolist(),
        starting_coordinates=problem.start.tolist(), free_frames=problem.free.tolist(),
        trust_m=trust, normalized_interior_margin=margin, attempt_limit=attempts,
        maximum_root_change_m=float(np.abs(x-problem.start).max()), minimum_slack=float(c.min()),
        sampled_feasible=bool(c.min()>=0), groups=summary, quality_approved=False)
