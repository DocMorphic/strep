"""Speed/displacement upper bounds for LINEAR rig skinning between pose samples.

These floating-point bounds support conservative interval diagnostics. They are
not exact arithmetic, collision detection, or an animation-quality certificate.
No linear interpolation of the resulting world vertices is assumed.
"""
import numpy as np
from gltf_tools import local_matrix
from rig_clip_import import AnimationSampler


def angular_bound(a, b, duration):
    """Bounds both shortest-arc SLERP and the sampler's small-angle NLERP."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != (4,) or b.shape != (4,) or not np.isfinite(np.r_[a, b, duration]).all() or duration <= 0:
        raise ValueError('Finite nonzero quaternion pair and positive duration required')
    if min(np.linalg.norm(a), np.linalg.norm(b)) < 1e-12:
        raise ValueError('Nonzero quaternion pair required')
    a, b = a/np.linalg.norm(a), b/np.linalg.norm(b)
    if a@b < 0: b = -b
    # Stable even when arccos(dot) rounds to zero for different quaternions.
    theta = 2*np.arctan2(np.linalg.norm(a-b), np.linalg.norm(a+b))
    return float(4*np.tan(theta/2)/duration)


class SkinMotionBounds:
    def __init__(self, rig, sampler):
        if rig.document is not sampler.document:
            raise ValueError('Sampler and rig must share the same document')
        self.rig, self.sampler = rig, sampler
        self.local = np.array([local_matrix(n) for n in rig.document['nodes']])
        self.channels = sampler.channels
        for node, path, clock, values, mode in self.channels:
            if mode == 'CUBICSPLINE':
                raise ValueError('CUBICSPLINE motion bounds are unsupported')
            if mode == 'STEP' and not np.array_equal(values, np.repeat(values[:1], len(values), axis=0)):
                raise ValueError('Discontinuous STEP motion requires a separate jump audit')
            if path == 'scale' and not np.array_equal(values, np.ones_like(values)):
                raise ValueError('Animated scale drift is unsupported by these bounds')
        self.knots = np.unique(np.concatenate([channel[2] for channel in self.channels]))
        self.bind_points = []
        for primitive in rig.primitives:
            points = np.c_[primitive['positions'], np.ones(len(primitive['positions']))]
            if primitive['joints'] is not None:
                points = np.einsum('nvij,nj->nvi', rig.inverse[primitive['joints']], points)
            self.bind_points.append(points)

    def _span(self, start, end):
        middle = (start+end)/2; count = len(self.local)
        length = np.linalg.norm(self.local[:, :3, 3], axis=1)
        translation_rate = np.zeros(count); rotation_rate = np.zeros(count)
        # Allow the static matrix/scale drift accepted by RigAsset. Multiplying
        # actual operator bounds avoids assuming every ancestor is exactly rigid.
        stretch = np.linalg.norm(self.local[:, :3, :3], ord=2, axis=(1, 2))
        for node, path, clock, values, mode in self.channels:
            if path == 'scale':
                stretch[node] = 1.; continue
            if path == 'translation':
                ends = [AnimationSampler.value(path, clock, values, mode, t) for t in [start, end]]
                length[node] = max(np.linalg.norm(p) for p in ends)
            if mode == 'STEP' or len(clock) < 2 or middle < clock[0] or middle > clock[-1]: continue
            k = int(np.searchsorted(clock, middle, side='right')-1)
            k = min(k, len(clock)-2); dt = float(clock[k+1]-clock[k])
            if path == 'translation': translation_rate[node] = np.linalg.norm(values[k+1]-values[k])/dt
            elif path == 'rotation': rotation_rate[node] = angular_bound(values[k], values[k+1], dt)
        operator = np.zeros(count); derivative = np.zeros(count); velocity = np.zeros(count)
        visited = np.zeros(count, bool)
        def visit(node):
            if visited[node]: return
            parent = self.rig.parents[node]
            if parent < 0: m, d, v = 1., 0., 0.
            else:
                visit(parent); m, d, v = operator[parent], derivative[parent], velocity[parent]
            operator[node] = m*stretch[node]
            derivative[node] = d*stretch[node] + m*rotation_rate[node]*stretch[node]
            velocity[node] = v + d*length[node] + m*translation_rate[node]
            # Explicit floating-point inflation, not an exact predicate claim.
            operator[node] = np.nextafter(operator[node]*(1+1e-12), np.inf)
            derivative[node] = np.nextafter(derivative[node]*(1+1e-12), np.inf)
            velocity[node] = np.nextafter(velocity[node]*(1+1e-12), np.inf)
            visited[node] = True
        for node in range(count): visit(node)
        parts = []
        for primitive, points in zip(self.rig.primitives, self.bind_points):
            if primitive['joints'] is None:
                node = primitive['node']
                bound = derivative[node]*np.linalg.norm(points[:, :3], axis=1) + velocity[node]*abs(points[:, 3])
            else:
                nodes = np.asarray(self.rig.joints)[primitive['joints']]
                per_joint = derivative[nodes]*np.linalg.norm(points[:, :, :3], axis=2) + velocity[nodes]*abs(points[:, :, 3])
                bound = (per_joint*primitive['weights']).sum(axis=1)
            parts.append(bound)
        return np.concatenate(parts)

    def interval(self, start, end):
        if not np.isfinite([start, end]).all() or not 0 <= start < end <= self.sampler.duration:
            raise ValueError('Finite increasing interval inside clip required')
        times = np.r_[start, self.knots[(self.knots > start) & (self.knots < end)], end]
        if len(times) > 4097: raise ValueError('Interval exceeds 4096 native spans')
        speed = np.maximum.reduce([self._span(a, b) for a, b in zip(times[:-1], times[1:])])
        if not np.isfinite(speed).all(): raise ValueError('Nonfinite motion bound')
        center = (start+end)/2
        vertices = self.rig.vertices(self.sampler.sample(center))
        radius = np.nextafter(speed*((end-start)/2)+1e-10, np.inf)
        return dict(start_s=float(start), end_s=float(end), center_s=float(center),
                    center_vertices=vertices, radius_m=radius, speed_bound_m_s=speed,
                    native_spans=len(times)-1, floating_padding_m=1e-10,
                    collision_free_certified=False)
