"""Fixed original-axis proposal bounds for explicit self-triangle pairs.

Every pair contributes all nine vertex inequalities, including shared vertices.
Original overlaps stay unresolved; these bounds do not discover other pairs or
certify a mesh, a valid solid, or continuous-time collision freedom.
"""
import numpy as np
from native_partner_surface_rows import separation_axis

MAX_WORKSPACE_BYTES = 128 * 1024**2


def _vertices(value, count=None):
    result = np.asarray(value)
    if (result.dtype.kind not in 'fiu' or result.ndim != 2 or result.shape[1:] != (3,)
            or not 3 <= len(result) <= 250000 or count is not None and len(result) != count
            or not np.isfinite(result).all()):
        raise ValueError('Complete finite original vertex population required')
    return result.astype(float, copy=True)


class SelfSeparationCuts:
    def __init__(self, vertices, faces, pairs, *, clearance_m=.0001, maximum_rows=100000):
        vertices = _vertices(vertices)
        faces = np.asarray(faces)
        if (faces.dtype.kind not in 'iu' or faces.ndim != 2 or faces.shape[1:] != (3,)
                or not 1 <= len(faces) <= 100000 or faces.min() < 0 or faces.max() >= len(vertices)
                or type(pairs) is not list or not 1 <= len(pairs) <= 4096
                or type(clearance_m) not in (int, float) or not np.isfinite(clearance_m)
                or not 0 <= clearance_m <= .005
                or type(maximum_rows) is not int or not 1 <= maximum_rows <= 100000):
            raise ValueError('Explicit bounded mesh, self pairs, 0-5mm clearance and row budget required')
        if 9 * len(pairs) > maximum_rows:
            raise ValueError('Complete nine-row self cuts exceed budget; no subset returned')
        seen = set(); left = []; right = []; normals = []; lower = []; gaps = []; canonical = []
        for pair in pairs:
            if (type(pair) is not list or len(pair) != 2
                    or any(type(i) is not int or not 0 <= i < len(faces) for i in pair)
                    or pair[0] == pair[1]):
                raise ValueError('Two distinct existing original triangle IDs required per self pair')
            key = tuple(sorted(pair))
            if key in seen:
                raise ValueError('Duplicate unordered self-triangle pair')
            seen.add(key); canonical.append(list(key))
            a, b = faces[list(key)]
            normal, gap = separation_axis(vertices[a], vertices[b])
            target = min(float(clearance_m), gap)
            gaps.append(gap)
            for i in a:
                for j in b:
                    left.append(int(i)); right.append(int(j)); normals.append(normal); lower.append(target)
        self.vertex_count = len(vertices)
        self.left = np.asarray(left, int); self.right = np.asarray(right, int)
        self.normals = np.asarray(normals, float); self.lower_m = np.asarray(lower, float)
        self.report = dict(schema='strep-native-self-separation-cuts-v1', pairs=canonical,
            rows=len(left), rows_per_pair=9, source_axis_gaps_m=gaps,
            positive_source_axis_pairs=sum(g > 0 for g in gaps),
            unresolved_source_axis_pairs=sum(g <= 0 for g in gaps),
            clearance_m=float(clearance_m), original_vertices=len(vertices), maximum_rows=maximum_rows,
            self_collision_free_certified=False, quality_approved=False, release_approved=False,
            scope='All nine fixed original-axis bounds for every explicit self pair. Lower bound is '
                  'min(clearance, original axis gap), including negative original overlaps and shared '
                  'vertices. No discovery completeness, valid solid, nonlinear fit, motion or quality certificate.')

    def evaluate(self, vertices, vertex_jacobian=None):
        vertices = _vertices(vertices, self.vertex_count)
        value = np.einsum('ri,ri->r', vertices[self.left] - vertices[self.right], self.normals) - self.lower_m
        if vertex_jacobian is None:
            return value, None
        jac = np.asarray(vertex_jacobian)
        if (jac.dtype.kind not in 'fiu' or jac.ndim != 3 or jac.shape[:2] != vertices.shape
                or not 1 <= jac.shape[2] <= 192
                or jac.nbytes > MAX_WORKSPACE_BYTES
                or len(self.left) * 3 * jac.shape[2] * 8 * 3 > MAX_WORKSPACE_BYTES):
            raise ValueError('Complete vertex Jacobian and self-row workspace must fit explicit budget')
        if not np.isfinite(jac).all():
            raise ValueError('Finite complete vertex Jacobian required')
        derivative = np.einsum('ric,ri->rc', jac[self.left] - jac[self.right], self.normals)
        return value, derivative
