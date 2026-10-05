"""Exact necessary normal-direction bounds under explicit vertex displacement boxes.

This is a geometric relaxation, not a pose solver. Callers must justify the
vertex boxes separately; joint-origin or normalized-control limits are not
vertex displacement bounds.
"""
from fractions import Fraction
import hashlib
import numpy as np


def _numeric(value, label):
    array = np.asarray(value)
    if array.dtype.kind not in 'iuf' or not np.isfinite(array).all():
        raise ValueError('Finite numeric ' + label + ' required')
    if (array.dtype.kind in 'iu' and any(abs(int(x)) > 2**53 for x in array.flat)
            or array.dtype.kind == 'f' and array.dtype.itemsize > 8):
        raise ValueError('Binary64-exact integer or at most binary64 ' + label + ' required')
    return array.astype(float)


def _exact(value):
    return Fraction.from_float(float(value))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0]]


def _nonnegative_xyz(value, label):
    array = _numeric(value, label)
    if array.shape == ():
        array = np.full(3, float(array))
    if array.shape != (3,) or (array < 0).any():
        raise ValueError('Nonnegative scalar or XYZ ' + label + ' required')
    return list(map(_exact, array))


class SurfaceNormalBox:
    """Area-weight every incident face once, with exact binary-input arithmetic.

    The cross-sum enclosure discards shared-vertex correlations, so it may be
    loose. It never drops an incident face, normalizes skin weights, infers palm
    anatomy, or assumes that a box-compatible mesh is attainable by the rig.
    """
    def __init__(self, points, faces, group):
        points = _numeric(points, 'XYZ vertices')
        faces = np.asarray(faces)
        group = np.asarray(group)
        if (points.ndim != 2 or points.shape[1:] != (3,) or not len(points)
                or faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces)
                or faces.dtype.kind not in 'iu' or faces.min() < 0
                or faces.max() >= len(points) or group.ndim != 1 or not len(group)
                or group.dtype.kind not in 'iu' or group.min() < 0
                or group.max() >= len(points) or len(np.unique(group)) != len(group)):
            raise ValueError('Complete vertices, indexed faces and distinct existing group required')
        self.vertex_count = len(points)
        self.incident = np.flatnonzero(np.isin(faces, group).any(axis=1))
        if not len(self.incident):
            raise ValueError('Contact group has no incident faces')
        self.triangles = faces[self.incident].astype(np.int64, copy=True)
        self.edges = []
        self.center = [Fraction(0)]*3
        for triangle in self.triangles:
            a, b, c = [[_exact(v) for v in points[i]] for i in triangle]
            u = [y-x for x, y in zip(a, b)]
            v = [y-x for x, y in zip(a, c)]
            self.edges.append((u, v))
            self.center = [x+y for x, y in zip(self.center, _cross(u, v))]
        self.inputs_sha256 = {
            'points_float64': hashlib.sha256(points.astype('<f8').tobytes()).hexdigest(),
            'faces_int64': hashlib.sha256(faces.astype('<i8').tobytes()).hexdigest(),
            'group_int64': hashlib.sha256(group.astype('<i8').tobytes()).hexdigest(),
        }

    def bound(self, target_normal, vertex_radius_m, *, minimum_alignment_cosine,
              cross_sum_reserve_m2=0.):
        """Exclude opposition to a FIXED target within explicit coordinate boxes.

        A radius is a scalar, one scalar per vertex, or XYZ per vertex. Every
        candidate coordinate must differ from the supplied center by at most
        its radius. Reserve encloses any additional cross-sum arithmetic/model
        uncertainty; zero reserve concerns exact real geometry only.

        For d=-target, usable cross sum m must have d.m >= q*||d||*||m||.
        Its dot upper bound and squared-norm lower bound give a necessary test.
        A strict conflict excludes that entire relaxation. No conflict is
        inconclusive, including boxes containing zero or degenerate normals.
        """
        target = _numeric(target_normal, 'fixed target direction')
        q = _numeric(minimum_alignment_cosine, 'minimum alignment cosine')
        if target.shape != (3,) or not np.any(target != 0):
            raise ValueError('Nonzero XYZ fixed target direction required')
        if q.shape != () or not 0 <= q <= 1:
            raise ValueError('Minimum alignment cosine must be in [0,1]')
        radii = _numeric(vertex_radius_m, 'vertex radii')
        if radii.shape == ():
            radii = np.full((self.vertex_count, 3), float(radii))
        elif radii.shape == (self.vertex_count,):
            radii = np.repeat(radii[:, None], 3, axis=1)
        if radii.shape != (self.vertex_count, 3) or (radii < 0).any():
            raise ValueError('Nonnegative complete scalar, per-vertex or XYZ radii required')
        error = _nonnegative_xyz(cross_sum_reserve_m2, 'cross-sum reserve')
        for triangle, (u, v) in zip(self.triangles, self.edges):
            r0, r1, r2 = [[_exact(x) for x in radii[i]] for i in triangle]
            eu = [a+b for a, b in zip(r0, r1)]
            ev = [a+b for a, b in zip(r0, r2)]
            for axis, (j, k) in enumerate(((1, 2), (2, 0), (0, 1))):
                # cross(u+du,v+dv)-cross(u,v): two linear terms and
                # one bilinear term, bounded componentwise without rounding.
                error[axis] += (abs(u[j])*ev[k]+abs(u[k])*ev[j]
                    +eu[j]*abs(v[k])+eu[k]*abs(v[j])+eu[j]*ev[k]+eu[k]*ev[j])
        intervals = [(c-e, c+e) for c, e in zip(self.center, error)]
        d = [-_exact(x) for x in target]
        dot_upper = sum((di*(hi if di >= 0 else lo)
                         for di, (lo, hi) in zip(d, intervals)), Fraction(0))
        minimum_norm_squared = sum((min(abs(lo), abs(hi))**2
            if lo > 0 or hi < 0 else Fraction(0) for lo, hi in intervals), Fraction(0))
        direction_norm_squared = sum((di*di for di in d), Fraction(0))
        rhs = _exact(q)**2*direction_norm_squared*minimum_norm_squared
        gap = rhs-max(Fraction(0), dot_upper)**2
        conflict = bool(dot_upper < 0 or gap > 0)
        return dict(schema='strep-surface-normal-box-v1',
            exact_geometric_conflict=conflict,
            reason=('opposition_dot_strictly_negative' if dot_upper < 0 else
                    'alignment_squared_bound_strictly_failed' if gap > 0 else 'inconclusive'),
            incident_faces=self.incident.tolist(), inputs_sha256=dict(self.inputs_sha256),
            cross_sum_center_exact=[str(x) for x in self.center],
            cross_sum_radius_exact=[str(x) for x in error],
            cross_sum_intervals_exact=[[str(lo), str(hi)] for lo, hi in intervals],
            opposition_dot_upper_exact=str(dot_upper),
            cross_sum_norm_squared_lower_exact=str(minimum_norm_squared),
            target_norm_squared_exact=str(direction_norm_squared),
            squared_alignment_gap_exact=str(gap),
            minimum_alignment_cosine=float(q), target_normal=target.tolist(),
            vertex_radii_float64_sha256=hashlib.sha256(radii.astype('<f8').tobytes()).hexdigest(),
            cross_sum_reserve_exact=[str(x) for x in _nonnegative_xyz(cross_sum_reserve_m2, 'reserve')],
            vertex_boxes_certified=False, pose_reachability_proven=False,
            normal_availability_proven=False, quality_approved=False, release_approved=False,
            scope='Necessary exact-real winding-derived normal-direction condition under caller-supplied '
                'complete vertex boxes and fixed target direction. Shared-vertex correlations ignored. '
                'Reserve must separately enclose implementation arithmetic for a floating-runtime claim. '
                'No conflict is inconclusive. No joint/control-to-vertex bound, anatomy, target movement, '
                'position/contact-side/force/coherence/degeneracy or rig-feasibility approval.')
