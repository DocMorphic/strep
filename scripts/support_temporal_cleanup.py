"""Whole-clip root cleanup with drafted support and transition-edge guards.

This adapter operates on completed support corrections. All pose channels stay
fixed. Predicted support is a constraint hypothesis, never confirmed contact.
"""
import numpy as np
from authored_root_correction import Problem, serialized_cap
from strep import read


def support_mask(annotations, side, frames):
    active = np.zeros(frames, bool)
    for interval in annotations['intervals']:
        if interval['joint'] not in (side+'Foot', side+'ToeBase'):
            continue
        a, b = interval['start_frame'], interval['end_frame_exclusive']
        if not isinstance(a, int) or not isinstance(b, int) or not 0 <= a < b <= frames:
            raise ValueError('Support interval outside the complete clip clock')
        active[a:b] = True
    return active


def guarded_edges(active):
    """Protect stance, entry/release, and their immediately adjacent edges."""
    active = np.asarray(active, bool)
    if active.ndim != 1 or len(active) < 3:
        raise ValueError('At least three ordered support samples required')
    edges = active[:-1] | active[1:]
    boundary = active[:-1] != active[1:]
    edges[:-1] |= boundary[1:]
    edges[1:] |= boundary[:-1]
    return edges


class SupportProblem(Problem):
    def __init__(self, folder, case, policy):
        super().__init__(folder, case, policy)
        self.annotations = read(folder/'input/contacts.json')
        self.guides = read(folder/'support-request.json')['support']['guides']

    def additional_constraints(self, linear, norm, equal):
        edge_count = anchor_count = height_count = 0
        edits = self.root_positions-self.original_root
        for f in range(1, self.frames):
            delta = edits[f]-edits[f-1]
            cap = serialized_cap(self.spec['limits']['root_step_m'], float(np.linalg.norm(delta)),
                                 self.policy['position_tolerance_m'])
            norm(delta, self.maps[2*f]-self.maps[2*f-2], cap)
        for side, patch in self.spec['patches'].items():
            ids = patch['vertices']
            points = self.points[::2, ids]
            centers = points.mean(axis=1)
            weight = float(self.weights[ids].mean())
            active = support_mask(self.annotations, side, self.frames)
            guide = self.guides[side]
            anchors, used = np.asarray(guide['anchors_xz_m']), np.asarray(guide['weights']) > 0
            if anchors.shape != (self.frames, 2) or used.shape != (self.frames,) or not np.isfinite(anchors).all():
                raise ValueError('Drafted anchors must use the entire finite clip clock')
            for f in np.flatnonzero(used):
                vector = centers[f, [0, 2]]-anchors[f]
                norm(vector, self.maps[2*f][[0, 2]]*weight, float(np.linalg.norm(vector)))
                anchor_count += 1
            for f in np.flatnonzero(active):
                # Retain the current lowest vertex as a height witness. Its
                # nonincrease guarantees the patch minimum cannot increase.
                vertex = ids[int(np.argmin(points[f, :, 1]))]
                linear(self.maps[2*f][1]*self.weights[vertex], 0.)
                height_count += 1
            for edge in np.flatnonzero(guarded_edges(active)):
                vector = (centers[edge+1, [0, 2]]-centers[edge, [0, 2]])*30
                matrix = (self.maps[2*edge+2]-self.maps[2*edge])[[0, 2]]*(30*weight)
                norm(vector, matrix, float(np.linalg.norm(vector)))
                edge_count += 1
        return dict(guarded_support_and_boundary_edges=edge_count,
                    drafted_anchor_cones=anchor_count, supported_height_rows=height_count)
