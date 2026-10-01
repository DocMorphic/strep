"""Frozen donor-axis constraints for newly observed triangle crossings.

These local proposal constraints are not a substitute for fresh mesh queries.
They retain every new proper pair at its observed time, without a count cap.
"""
import numpy as np
from sampled_surface_guard import compare, topology
from triangle_separation_objective import TriangleSeparationObjective, choose_axes, gaps


class MeshRegressionCuts:
    def __init__(self, skins, placements, times, faces, original, rejected, worlds):
        decision = compare(original, rejected)
        if topology(faces, [m['vertices'] for m in original['topology']]) != original['topology']:
            raise ValueError('Bound mesh topology required')
        times = np.asarray(times, float)
        if (times.ndim != 1 or not len(times) or not np.isfinite(times).all()
                or times[0] < 0 or np.any(np.diff(times) <= 0)):
            raise ValueError('Complete increasing pose clock required')
        rows = [(sample['time_s'], pair) for sample in decision['samples']
                for pair in sample['new_proper_pairs']]
        if not rows:
            raise ValueError('Observed new proper crossings required')
        frames = np.searchsorted(times, [t for t, _ in rows])
        if np.any(frames >= len(times)) or not np.array_equal(times[frames], [t for t, _ in rows]):
            raise ValueError('Every observed crossing time must have an exact pose')
        pairs = np.asarray([pair for _, pair in rows], int)
        vertices = np.stack([np.asarray(faces[i])[pairs[:, i]] for i in range(2)])
        provisional = TriangleSeparationObjective(skins, placements, frames, vertices,
                                                  np.tile([1., 0., 0.], (len(rows), 1)))
        triangles = provisional.triangles(worlds)
        axes = choose_axes(*triangles)
        self.objective = TriangleSeparationObjective(skins, placements, frames, vertices, axes)
        baseline = gaps(*triangles, axes).min(axis=1)
        # Preserve initially unresolved donor projections rather than pretending
        # they are separated. The fixed 1e-8 m reserve matches the mesh guard's
        # numerical scale; no existing acceptance tolerance changes.
        self.floor = np.minimum(0., baseline) - 1e-8
        self.floor.setflags(write=False)
        self.record = dict(method='frozen_donor_axis_mesh_cuts_v1',
            rows=[dict(time_s=t, left_triangle=int(pair[0]), right_triangle=int(pair[1]),
                       axis=axes[i].tolist(), baseline_gap_m=float(baseline[i]),
                       floor_m=float(self.floor[i])) for i, (t, pair) in enumerate(rows)],
            pairs=len(rows), scalar_rows=9*len(rows), donor_unseparated_pairs=int(np.count_nonzero(baseline <= 0)),
            fresh_mesh_validation_required=True, quality_approved=False)

    def margins(self, worlds):
        values = gaps(*self.objective.triangles(worlds), self.objective.axes)
        return ((values-self.floor[:, None])/.02).ravel()
