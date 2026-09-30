"""Center velocity and acceleration remainder for a single native skin span.

Bounds follow the production sampler's normalized SLERP/NLERP and hierarchy.
Floating reserves are explicit; this is not exact interval arithmetic.
"""
import copy
import numpy as np
from gltf_tools import local_matrix
from skin_motion_bounds import SkinMotionBounds, angular_bound


def rotation_jet(a, b, duration, fraction):
    """Return normalized quaternion derivative and rotation operator bounds.

    For raw interpolation r with ||r||>=c, ||r'||<=d and ||r''||<=e,
    normalized q satisfies ||q'||<=d/c and ||q''||<=2e/c+6d²/c².
    Consequently ||R'||<=2d/c and ||R''||<=4e/c+16d²/c².
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    if (a.shape != (4,) or b.shape != (4,) or not np.isfinite(np.r_[a, b, duration, fraction]).all()
            or duration <= 0 or not 0 <= fraction <= 1 or min(np.linalg.norm(a), np.linalg.norm(b)) < 1e-12):
        raise ValueError('Finite quaternion span and fraction required')
    a, b = a/np.linalg.norm(a), b/np.linalg.norm(b)
    dot = float(a@b)
    if dot < 0: b = -b; dot = -dot
    theta = np.arccos(np.clip(dot, 0, 1)); u = fraction
    if theta < 1e-6:
        raw = (1-u)*a+u*b; derivative = (b-a)/duration
        c = np.linalg.norm(a+b)/2; d = np.linalg.norm(derivative); e = 0.
    else:
        sine = np.sin(theta)
        raw = (np.sin((1-u)*theta)*a+np.sin(u*theta)*b)/sine
        derivative = theta*(-np.cos((1-u)*theta)*a+np.cos(u*theta)*b)/(duration*sine)
        # r=a*cos(u*theta)+v*sin(u*theta). Gram eigenvalues bound its
        # norm and both derivatives, including endpoint normalization drift.
        basis = np.stack([a, (b-a*np.cos(theta))/sine])
        eigen = np.linalg.eigvalsh(basis@basis.T)
        if eigen[0] <= 0: raise ValueError('Degenerate quaternion interpolation basis')
        c = np.sqrt(eigen[0]); d = theta/duration*np.sqrt(eigen[1])
        e = (theta/duration)**2*np.sqrt(eigen[1])
    norm = np.linalg.norm(raw); q = raw/norm
    dq = (derivative-q*(q@derivative))/norm
    first = max(angular_bound(a, b, duration), 2*d/c)
    second = 4*e/c+16*d*d/(c*c)
    return q, dq, float(np.nextafter(first*(1+1e-12), np.inf)), float(np.nextafter(second*(1+1e-12), np.inf))


def rotation_derivative(q, dq):
    x, y, z, w = q; dx, dy, dz, dw = dq
    return np.array([
        [-4*(y*dy+z*dz), 2*(dx*y+x*dy-dz*w-z*dw), 2*(dx*z+x*dz+dy*w+y*dw)],
        [2*(dx*y+x*dy+dz*w+z*dw), -4*(x*dx+z*dz), 2*(dy*z+y*dz-dx*w-x*dw)],
        [2*(dx*z+x*dz-dy*w-y*dw), 2*(dy*z+y*dz+dx*w+x*dw), -4*(x*dx+y*dy)]])


class SkinTaylorBounds(SkinMotionBounds):
    def __init__(self, rig, sampler):
        super().__init__(rig, sampler)
        if not np.array_equal(self.local[:, 3], np.tile([0., 0, 0, 1], (len(self.local), 1))):
            raise ValueError('Taylor bounds require exact affine local matrix bottom rows')

    def interval(self, start, end):
        if (not np.isfinite([start, end]).all() or not 0 <= start < end <= self.sampler.duration):
            raise ValueError('Finite increasing interval inside clip required')
        if np.any((self.knots > start) & (self.knots < end)):
            raise ValueError('Split at every native knot before using Taylor bounds')
        center = (start+end)/2; half = max(end-center, center-start)
        nodes = copy.deepcopy(self.rig.document['nodes']); count = len(nodes)
        local_derivative = np.zeros((count, 4, 4))
        translation_rate = np.zeros(count); first = np.zeros(count); second = np.zeros(count)
        for node, path, clock, values, mode in self.channels:
            nodes[node][path] = self.sampler.value(path, clock, values, mode, center).tolist()
        local = np.array([local_matrix(node) for node in nodes])
        length = np.linalg.norm(local[:, :3, 3], axis=1)
        stretch = np.linalg.norm(local[:, :3, :3], ord=2, axis=(1, 2))
        for node, path, clock, values, mode in self.channels:
            if path == 'translation':
                length[node] = max(np.linalg.norm(self.sampler.value(path, clock, values, mode, t)) for t in (start, end))
            if mode == 'STEP' or len(clock) < 2 or center < clock[0] or center > clock[-1]: continue
            k = min(int(np.searchsorted(clock, center, side='right')-1), len(clock)-2)
            dt = float(clock[k+1]-clock[k])
            if path == 'translation':
                rate = (values[k+1]-values[k])/dt
                local_derivative[node, :3, 3] = rate; translation_rate[node] = np.linalg.norm(rate)
            elif path == 'rotation':
                q, dq, first[node], second[node] = rotation_jet(values[k], values[k+1], dt, (center-clock[k])/dt)
                local_derivative[node, :3, :3] = rotation_derivative(q, dq)@np.diag(nodes[node].get('scale', [1., 1., 1.]))
        world = np.zeros_like(local); derivative = np.zeros_like(local)
        operator = np.zeros(count); rate = np.zeros(count); acceleration = np.zeros(count)
        position_acceleration = np.zeros(count); visited = np.zeros(count, bool)
        def visit(node):
            if visited[node]: return
            parent = self.rig.parents[node]
            if parent < 0:
                m, d, e, p = 1., 0., 0., 0.
                world[node], derivative[node] = local[node], local_derivative[node]
            else:
                visit(parent)
                m, d, e, p = operator[parent], rate[parent], acceleration[parent], position_acceleration[parent]
                world[node] = world[parent]@local[node]
                derivative[node] = derivative[parent]@local[node]+world[parent]@local_derivative[node]
            s = stretch[node]; ld = first[node]*s; le = second[node]*s
            operator[node] = m*s
            rate[node] = d*s+m*ld
            acceleration[node] = e*s+2*d*ld+m*le
            position_acceleration[node] = p+e*length[node]+2*d*translation_rate[node]
            for array in (operator, rate, acceleration, position_acceleration):
                array[node] = np.nextafter(array[node]*(1+1e-12), np.inf)
            visited[node] = True
        for node in range(count): visit(node)
        velocities = self.rig.vertices(derivative); parts = []
        for primitive, points in zip(self.rig.primitives, self.bind_points):
            if primitive['joints'] is None:
                node = primitive['node']
                value = acceleration[node]*np.linalg.norm(points[:, :3], axis=1)+position_acceleration[node]*abs(points[:, 3])
            else:
                joint_nodes = np.asarray(self.rig.joints)[primitive['joints']]
                value = acceleration[joint_nodes]*np.linalg.norm(points[:, :, :3], axis=2)+position_acceleration[joint_nodes]*abs(points[:, :, 3])
                value = (value*primitive['weights']).sum(axis=1)
            parts.append(value)
        acc = np.concatenate(parts)
        if not np.isfinite(velocities).all() or not np.isfinite(acc).all(): raise ValueError('Nonfinite Taylor bound')
        value = super().interval(start, end)  # Preserve the original broad-phase movement balls.
        value.update(center_velocities=velocities, acceleration_bound_m_s2=acc,
            remainder_radius_m=np.nextafter(.5*acc*half*half+1e-10, np.inf), time_radius_s=half)
        return value
