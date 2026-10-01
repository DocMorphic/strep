"""Native arm paths with a retained fractional contact and free adjacent rates."""
import numpy as np
from scipy.spatial.transform import Rotation
from contact_locked_native import NativeRotationEdit
from rig_clip_import import AnimationSampler
from timed_rotation_edit import sampled_rotations
from paired_guarded_temporal import world_from_local


class ContactRatePath:
    def __init__(self, document, binary, names, times, window, protected, event, reference):
        if not np.isfinite(event) or not window[0] < event < window[1]:
            raise ValueError('Interior finite contact time required')
        self.exporter = NativeRotationEdit(document, binary, names, times, window, protected, reference)
        self.model = self.exporter.model
        self.knots = np.array([window[0], (window[0]+event)/2, event, (event+window[1])/2, window[1]])
        self.size = len(self.model.nodes)*12
        self.locks = []
        for entry in self.model.entries:
            clock, q = entry['clock'], entry['source']
            left = int(np.searchsorted(clock, event, side='right')-1)
            if left not in entry['ids'] or left+1 not in entry['ids']:
                raise ValueError('Contact interpolation endpoints must both be editable')
            fraction = (event-float(clock[left]))/float(clock[left+1]-clock[left])
            if not 0 < fraction < 1: raise ValueError('This parameterization requires an inter-key contact')
            rotation = Rotation.from_quat(AnimationSampler.value('rotation', clock, q, 'LINEAR', event)).as_matrix()
            step = (Rotation.from_quat(q[left]).inv()*Rotation.from_quat(q[left+1])).as_rotvec()
            weights = np.stack([np.interp(clock[entry['ids']], self.knots, np.eye(5)[k]) for k in (1, 2, 3)], axis=1)
            self.locks.append(dict(left=left, fraction=fraction, rotation=rotation, step=step, weights=weights))

    def quaternions(self, value, quantize=False):
        value = np.asarray(value, float)
        if value.shape != (self.size,) or not np.isfinite(value).all():
            raise ValueError('Matching finite contact-path controls required')
        value = value.reshape(len(self.model.nodes), 12); result = {}
        for entry, lock, part in zip(self.model.entries, self.locks, value):
            q = entry['source'].astype(float).copy()
            if np.any(part):
                ids = entry['ids']; delta = lock['weights']@part[:9].reshape(3, 3)
                changed = np.any(delta != 0, axis=1)
                q[ids[changed]] = (Rotation.from_quat(q[ids[changed]])*Rotation.from_rotvec(delta[changed])).as_quat()
                omega = lock['step']+part[9:]
                if np.linalg.norm(omega) >= np.pi-1e-6: raise ValueError('Ambiguous contact interpolation arc')
                pair = lock['rotation']@Rotation.from_rotvec(np.array([-lock['fraction'], 1-lock['fraction']])[:, None]*omega).as_matrix()
                q[lock['left']:lock['left']+2] = Rotation.from_matrix(pair).as_quat()
                q *= np.where(np.sum(q*entry['source'], axis=1) < 0, -1., 1.)[:, None]
                if quantize: q[ids] = q[ids].astype(np.float32)
            result[entry['node']] = q
        return result

    def world(self, value, quantize=False):
        local = self.model.local.copy(); q = self.quaternions(value, quantize)
        for entry in self.model.entries:
            n = entry['node']
            local[:, n, :3, :3] = sampled_rotations(entry['clock'], q[n], self.model.times)*self.model.scales[n][:, None, :]
        return world_from_local(local, self.model.parents)

    def original_angles(self, value, quantize=False):
        q = self.quaternions(value, quantize)
        return np.array([np.rad2deg((Rotation.from_quat(e['original']).inv()*Rotation.from_quat(q[e['node']])).magnitude()).max() for e in self.model.entries])

    def export(self, value, path):
        return self.exporter.export(self.quaternions(value, True), path)


class ProjectedSkin:
    """Exact linear projection of full-weight skinning onto a fixed rig axis."""
    def __init__(self, skin, vertices, axis, offset=0.):
        ids = np.asarray(vertices); axis = np.asarray(axis, float)
        if (ids.ndim != 1 or not len(ids) or ids.dtype.kind not in 'iu' or ids.min() < 0 or ids.max() >= len(skin.nodes)
                or len(np.unique(ids)) != len(ids) or axis.shape != (3,) or not np.isfinite(axis).all()
                or abs(np.linalg.norm(axis)-1) > 1e-8 or not np.isfinite(offset)):
            raise ValueError('Distinct skin vertices, a unit axis and finite offset required')
        self.axis, self.offset = axis, float(offset)
        self.nodes, mapping = np.unique(skin.nodes[ids], return_inverse=True)
        table = np.zeros((len(self.nodes), len(ids), 4))
        np.add.at(table, (mapping.ravel(), np.repeat(np.arange(len(ids)), skin.nodes.shape[1])),
            (skin.points[ids]*skin.weights[ids, :, None]).reshape(-1, 4))
        self.matrix = table.transpose(0, 2, 1).reshape(-1, len(ids))

    def evaluate(self, world):
        rows = np.einsum('tnij,i->tnj', np.asarray(world)[:, self.nodes, :3, :], self.axis)
        return rows.reshape(len(rows), -1)@self.matrix+self.offset
