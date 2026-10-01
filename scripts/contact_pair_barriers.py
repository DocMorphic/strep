"""Accumulate source-separated triangle constraints without rebasing them."""
import numpy as np
from copy import deepcopy
from triangle_separation_objective import TriangleSeparationObjective, choose_axes, gaps


class SeparatedPairBarriers:
    def __init__(self, skins, placements, faces, reference_worlds, frame=1, clearance_m=1e-8):
        if (len(skins) != 2 or len(placements) != 2 or len(faces) != 2 or len(reference_worlds) != 2
                or type(frame) is not int or frame < 0 or not np.isfinite(clearance_m) or clearance_m <= 0):
            raise ValueError('Two fixed actors, a frame and positive clearance required')
        self.skins, self.placements, self.frame, self.clearance = skins, placements, frame, float(clearance_m)
        self.faces = [np.array(v, copy=True) for v in faces]
        self.reference = [np.array(v, copy=True) for v in reference_worlds]
        for f in self.faces:
            if f.ndim != 2 or f.shape[1:] != (3,) or not len(f) or not np.issubdtype(f.dtype, np.integer) or f.min() < 0:
                raise ValueError('Valid original triangle topology required')
            f.setflags(write=False)
        for w in self.reference: w.setflags(write=False)
        self.rows = {}; self.objective = None

    def add(self, pairs):
        pairs = np.asarray(pairs)
        if pairs.size == 0: return 0
        if (pairs.ndim != 2 or pairs.shape[1] != 2 or not np.issubdtype(pairs.dtype, np.integer)
                or pairs.min() < 0 or any(pairs[:, i].max() >= len(f) for i, f in enumerate(self.faces))):
            raise ValueError('Valid original triangle pair indices required')
        new = sorted(set(map(tuple, pairs.tolist()))-set(self.rows))
        if not new: return 0
        vertices = np.stack([f[np.array(new)[:, i]] for i, f in enumerate(self.faces)])
        provisional = TriangleSeparationObjective(self.skins, self.placements, np.full(len(new), self.frame),
            vertices, np.tile([1., 0, 0], (len(new), 1)))
        triangles = provisional.triangles(self.reference); axes = choose_axes(*triangles)
        source_gaps = gaps(*triangles, axes).min(axis=1)
        if np.any(source_gaps <= self.clearance):
            raise ValueError('Every preventive pair must be strictly separated in the original source')
        # Commit the whole batch only after all source separations are verified.
        self.rows.update({pair: dict(left_triangle=pair[0], right_triangle=pair[1], axis=axis.tolist(),
            original_gap_m=float(gap), floor_m=self.clearance) for pair, axis, gap in zip(new, axes, source_gaps)})
        ordered = sorted(self.rows); vertices = np.stack([f[np.array(ordered)[:, i]] for i, f in enumerate(self.faces)])
        self.objective = TriangleSeparationObjective(self.skins, self.placements, np.full(len(ordered), self.frame),
            vertices, np.array([self.rows[p]['axis'] for p in ordered]), clearance_m=self.clearance)
        return len(new)

    def margins(self, worlds):
        if self.objective is None: return np.empty(0)
        return -self.objective.depths(worlds)/.001

    def record(self):
        return dict(pairs=len(self.rows), scalar_rows=9*len(self.rows), clearance_m=self.clearance,
            rows=[deepcopy(self.rows[p]) for p in sorted(self.rows)], original_axes_and_floors_frozen=True,
            complete_mesh_validation_required=True, quality_approved=False)
