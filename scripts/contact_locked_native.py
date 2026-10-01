"""Native rotation-key edits with an analytically retained inter-key contact."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
from timed_rotation_edit import TimedRotationEdit
from gltf_tools import append_accessor, write_glb


def locked_pair(contact, lower, upper, fraction):
    matrices = np.asarray([contact, lower, upper], float)
    if (matrices.shape != (3, 3, 3) or not np.isfinite(matrices).all()
            or not np.allclose(matrices.transpose(0, 2, 1)@matrices, np.eye(3), atol=1e-8, rtol=0)
            or not np.allclose(np.linalg.det(matrices), 1., atol=1e-8, rtol=0)
            or not np.isfinite(fraction) or not 0 < fraction < 1):
        raise ValueError('Proper rotations and an interior interpolation fraction required')
    contact, lower, upper = matrices
    a = Rotation.from_matrix(contact.T@lower).as_rotvec(); b = Rotation.from_matrix(contact.T@upper).as_rotvec()
    initial = (-fraction*a+(1-fraction)*b)/(fraction**2+(1-fraction)**2)
    def endpoints(omega): return contact@Rotation.from_rotvec(np.array([-fraction, 1-fraction])[:, None]*omega).as_matrix()
    def residual(omega): return Rotation.from_matrix(matrices[1:].transpose(0, 2, 1)@endpoints(omega)).as_rotvec().ravel()
    fit = least_squares(residual, initial, max_nfev=80, ftol=1e-12, xtol=1e-12, gtol=1e-12)
    if np.linalg.norm(fit.x) >= np.pi-1e-6: raise ValueError('Contact pair would use an ambiguous shortest arc')
    return endpoints(fit.x), dict(success=bool(fit.success), evaluations=int(fit.nfev), endpoint_cost=float(fit.cost), angular_step_radians=fit.x.tolist())


class NativeRotationEdit:
    def __init__(self, document, binary, names, times, window, protected, reference):
        self.model = TimedRotationEdit(document, binary, names, times, window, protected,
            knots=[window[0], float(np.mean(window)), window[1]], limit_degrees=45., reference=reference)

    def export(self, rotations, path):
        model = self.model
        if set(rotations) != set(model.nodes): raise ValueError('Every selected native rotation track required')
        values = {}; angles = {}
        for entry in model.entries:
            node = entry['node']; q = np.asarray(rotations[node], float)
            if q.shape != entry['source'].shape or not np.isfinite(q).all() or not np.allclose(np.linalg.norm(q, axis=1), 1., atol=1e-6, rtol=0):
                raise ValueError('Finite matching unit native quaternion keys required')
            fixed = np.ones(len(q), bool); fixed[entry['ids']] = False
            if not np.array_equal(q[fixed], entry['source'][fixed]): raise ValueError('Frozen native keys changed')
            q = q.astype(np.float32)
            maximum = float(np.rad2deg((Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(q)).magnitude()).max())
            if maximum > 45.+1e-4: raise ValueError('Original-reference native rotation budget exceeded')
            values[node] = q; angles[node] = maximum
        document = copy.deepcopy(model.document); binary = bytearray(model.binary); animation = document['animations'][0]
        for channel in animation['channels']:
            node = channel['target']['node']
            if channel['target']['path'] == 'rotation' and node in values:
                sampler = copy.deepcopy(animation['samplers'][channel['sampler']])
                sampler['output'] = append_accessor(document, binary, values[node], 'VEC4')
                channel['sampler'] = len(animation['samplers']); animation['samplers'].append(sampler)
        write_glb(path, document, binary)
        return angles
