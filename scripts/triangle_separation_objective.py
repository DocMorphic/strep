"""Fixed separating directions for measured triangle-crossing repair.

Nine vertex-pair gaps per triangle pair avoid a differentiated min/max. Positive
gaps separate these triangles at this pose only; fresh mesh queries are required.
"""
import numpy as np
from swept_triangle_separation import pair_bounds


def gaps(left, right, axes):
    a, b, n = (np.asarray(value, float) for value in (left, right, axes))
    if (a.ndim != 3 or a.shape[1:] != (3, 3) or not len(a) or b.shape != a.shape
            or n.shape != (len(a), 3) or not all(np.isfinite(x).all() for x in (a, b, n))
            or not np.allclose(np.linalg.norm(n, axis=1), 1., rtol=0, atol=1e-10)):
        raise ValueError('Matching finite triangle batches and unit axes required')
    return np.einsum('nabk,nk->nab', b[:, None, :, :]-a[:, :, None, :], n).reshape(-1, 9)


def choose_axes(left, right):
    a, b = np.asarray(left, float), np.asarray(right, float)
    if a.ndim != 3 or a.shape[1:] != (3, 3) or b.shape != a.shape:
        raise ValueError('Matching triangle batches required')
    radius = np.zeros(a.shape[:2])
    return pair_bounds(a, radius, b, radius, tolerance_m=0.)['axes']


class TriangleSeparationObjective:
    def __init__(self, skins, placements, frames, vertex_ids, axes, clearance_m=1e-8):
        self.frames = np.array(frames, copy=True)
        self.vertices = np.array(vertex_ids, copy=True)
        self.axes = np.array(axes, dtype=float, copy=True)
        if (self.frames.ndim != 1 or not len(self.frames) or not np.issubdtype(self.frames.dtype, np.integer)
                or np.any(self.frames < 0) or self.vertices.shape != (2, len(self.frames), 3)
                or not np.issubdtype(self.vertices.dtype, np.integer) or np.any(self.vertices < 0)
                or self.axes.shape != (len(self.frames), 3) or not np.isfinite(self.axes).all()
                or not np.allclose(np.linalg.norm(self.axes, axis=1), 1., rtol=0, atol=1e-10)
                or len(skins) != 2 or len(placements) != 2
                or not np.isfinite(clearance_m) or clearance_m < 0):
            raise ValueError('Two skins, fixed triangle indices, unit axes and nonnegative clearance required')
        self.skins = skins; self.placements = []
        for placement in placements:
            r, t = np.array(placement['rotation'], float, copy=True), np.array(placement['translation'], float, copy=True)
            if (r.shape != (3, 3) or t.shape != (3,) or not np.isfinite(r).all() or not np.isfinite(t).all()
                    or not np.allclose(r@r.T, np.eye(3), rtol=0, atol=1e-10) or np.linalg.det(r) <= 0):
                raise ValueError('Rigid finite placements required')
            r.setflags(write=False); t.setflags(write=False); self.placements.append((r, t))
        self.clearance = float(clearance_m)
        for value in (self.frames, self.vertices, self.axes): value.setflags(write=False)

    def triangles(self, worlds):
        if len(worlds) != 2: raise ValueError('Two actor pose batches required')
        result = []
        for actor in range(2):
            if self.frames.max() >= len(worlds[actor]): raise ValueError('Witness frame exceeds pose batch')
            points = self.skins[actor].evaluate(worlds[actor], np.repeat(self.frames, 3), self.vertices[actor].ravel())
            rotation, translation = self.placements[actor]
            result.append((points@rotation.T+translation).reshape(-1, 3, 3))
        return result

    def depths(self, worlds):
        return (self.clearance-gaps(*self.triangles(worlds), self.axes)).ravel()
