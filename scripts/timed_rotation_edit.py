"""Bounded GLB rotation controls on actual key clocks and protected time spans."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import append_accessor, hierarchy, local_matrix, write_glb
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from paired_guarded_temporal import world_from_local


def sampled_rotations(clock, values, times):
    """Batch the existing decoder's SLERP, including its native clock arithmetic."""
    left = np.clip(np.searchsorted(clock, times, side='right')-1, 0, len(clock)-2)
    # Preserve float32 key subtraction used by AnimationSampler.value.
    duration = (clock[left+1]-clock[left]).astype(float)
    t = (times-clock[left].astype(float))/duration
    t = np.where(times <= clock[0], 0., np.where(times >= clock[-1], 1., t))[:, None]
    a = values[left]/np.linalg.norm(values[left], axis=1)[:, None]
    b = values[left+1]/np.linalg.norm(values[left+1], axis=1)[:, None]
    dot = np.sum(a*b, axis=1); b *= np.where(dot < 0, -1., 1.)[:, None]
    angle = np.arccos(np.clip(np.abs(dot), 0, 1))[:, None]
    small = angle[:, 0] < 1e-6; result = (1-t)*a+t*b
    active = ~small
    result[active] = (np.sin((1-t[active])*angle[active])*a[active]+np.sin(t[active]*angle[active])*b[active])/np.sin(angle[active])
    result /= np.linalg.norm(result, axis=1)[:, None]
    return Rotation.from_quat(result).as_matrix()


def editable_keys(clock, window, protected):
    """Only edit a key when its entire open interpolation support is allowed."""
    clock = np.asarray(clock, float)
    if clock.ndim != 1 or len(clock) < 3 or not np.isfinite(clock).all() or clock[0] < 0 or np.any(np.diff(clock) <= 0):
        raise ValueError('Distinct increasing key times required')
    bounds = np.asarray(window, float)
    if bounds.shape != (2,) or not np.isfinite(bounds).all() or not 0 <= bounds[0] < bounds[1]:
        raise ValueError('Positive-width finite edit window required')
    spans = np.asarray(protected, float).reshape(-1, 2)
    if not np.isfinite(spans).all() or np.any(spans[:, 0] < 0) or np.any(spans[:, 1] < spans[:, 0]):
        raise ValueError('Ordered finite protected intervals required')
    indices = np.arange(1, len(clock)-1)
    before, after = clock[:-2], clock[2:]
    valid = (before >= bounds[0]) & (after <= bounds[1])
    for first, last in spans:
        valid &= ~((before < last) & (after > first))
    return indices[valid]


class TimedRotationEdit:
    def __init__(self, document, binary, names, sample_times, window, protected=(), *,
                 knots=None, limit_degrees=5., reference=None):
        self.document, self.binary = document, binary
        self.times = np.asarray(sample_times, float)
        self.limit_degrees = float(limit_degrees)
        if not np.isfinite(self.limit_degrees) or not 0 < self.limit_degrees <= 45:
            raise ValueError('Choose a finite original-reference edit budget up to 45 degrees')
        sampler = AnimationSampler(document, binary, 0)
        if self.times.ndim != 1 or len(self.times) < 2 or not np.isfinite(self.times).all() or np.any(np.diff(self.times) <= 0) or self.times[0] < 0 or self.times[-1] > sampler.duration:
            raise ValueError('Increasing sample times inside the animation required')
        self.window = np.asarray(window, float)
        if self.window.shape != (2,) or not np.isfinite(self.window).all() or not 0 <= self.window[0] < self.window[1] <= sampler.duration:
            raise ValueError('Edit window must lie inside the animation')
        self.protected = np.asarray(protected, float).reshape(-1, 2)
        if not np.isfinite(self.protected).all() or np.any(self.protected < 0) or np.any(self.protected > sampler.duration) or np.any(self.protected[:, 1] < self.protected[:, 0]):
            raise ValueError('Protected times must lie inside the animation')
        self.knots = np.linspace(*self.window, 5) if knots is None else np.asarray(knots, float)
        if self.knots.ndim != 1 or not 3 <= len(self.knots) <= 12 or not np.isfinite(self.knots).all() or np.any(np.diff(self.knots) <= 0) or not np.array_equal(self.knots[[0, -1]], self.window):
            raise ValueError('Distinct knots including exact window endpoints required')
        lookup = {}
        for i, node in enumerate(document['nodes']):
            if node.get('name') in lookup:
                lookup[node['name']] = None
            elif node.get('name'):
                lookup[node['name']] = i
        if not isinstance(names, list) or not names or len(set(names)) != len(names) or any(lookup.get(n) is None for n in names):
            raise ValueError('Distinct unambiguous joint names required')
        self.nodes = [lookup[n] for n in names]
        if len(document.get('skins', [])) != 1 or any(n not in document['skins'][0]['joints'] or 'matrix' in document['nodes'][n] for n in self.nodes):
            raise ValueError('Selected TRS joints in one skin required')
        self.channels = rotation_channels(document, binary)
        ref_doc, ref_binary = (document, binary) if reference is None else reference
        references = rotation_channels(ref_doc, ref_binary)
        if hierarchy(ref_doc) != hierarchy(document) or ref_doc['skins'][0]['joints'] != document['skins'][0]['joints']:
            raise ValueError('Original reference must use the same joint hierarchy')
        np.testing.assert_array_equal([local_matrix(n) for n in ref_doc['nodes']], [local_matrix(n) for n in document['nodes']])
        self.entries = []; self.width = len(self.knots)-2
        self.size = len(self.nodes)*self.width*3
        for number, node in enumerate(self.nodes):
            if node not in self.channels or node not in references or ref_doc['nodes'][node].get('name') != document['nodes'][node].get('name'):
                raise ValueError('Matching original rotation channels required')
            _, clock, source = self.channels[node]; _, ref_clock, original = references[node]
            np.testing.assert_array_equal(clock, ref_clock)
            ids = editable_keys(clock, self.window, self.protected)
            if not len(ids):
                raise ValueError('Window and guards leave no editable native key for '+document['nodes'][node]['name'])
            weights = np.stack([np.interp(clock[ids], self.knots, np.eye(len(self.knots))[i]) for i in range(1, len(self.knots)-1)], axis=1)
            relative = (Rotation.from_quat(original).inv()*Rotation.from_quat(source)).as_rotvec()
            if np.rad2deg(np.linalg.norm(relative, axis=1)).max() > self.limit_degrees+1e-4:
                raise ValueError('Starting clip already exceeds its original-reference edit budget')
            self.entries.append(dict(node=node, ids=ids, weights=weights, original=original, source=source, clock=clock.copy(), relative=relative))
        self.parents = hierarchy(document)
        self.local = np.tile(np.array([local_matrix(n) for n in document['nodes']]), (len(self.times), 1, 1, 1))
        sampled = {(node, path): np.array([sampler.value(path, clock, values, mode, t) for t in self.times]) for node, path, clock, values, mode in sampler.channels}
        self.scales = {}
        for node, item in enumerate(document['nodes']):
            if 'matrix' in item:
                continue
            scale = sampled.get((node, 'scale'), np.tile(item.get('scale', [1, 1, 1]), (len(self.times), 1)))
            self.scales[node] = scale
            if (node, 'rotation') in sampled:
                self.local[:, node, :3, :3] = Rotation.from_quat(sampled[node, 'rotation']).as_matrix()*scale[:, None, :]
            if (node, 'translation') in sampled:
                self.local[:, node, :3, 3] = sampled[node, 'translation']
        self.source_world = np.array([sampler.sample(t) for t in self.times])
        np.testing.assert_allclose(world_from_local(self.local, self.parents), self.source_world, atol=1e-12, rtol=0)

    def controls(self, value):
        result = np.asarray(value, float)
        if result.shape != (self.size,) or not np.isfinite(result).all():
            raise ValueError('Finite matching cumulative controls required')
        return result.reshape(len(self.nodes), self.width, 3)

    def edit_rows(self, value):
        controls = self.controls(value); vectors = []; jacobians = []
        for number, (entry, part) in enumerate(zip(self.entries, controls)):
            values = entry['relative'][entry['ids']]+entry['weights']@part
            mapping = np.zeros((len(values), 3, self.size)); offset = number*self.width*3
            mapping[:, :, offset:offset+self.width*3] = np.kron(entry['weights'], np.eye(3)).reshape(-1, 3, self.width*3)
            vectors.append(values); jacobians.append(mapping)
        return np.concatenate(vectors), np.concatenate(jacobians)

    def quaternions(self, value, quantize=False):
        result = {}
        for entry, part in zip(self.entries, self.controls(value)):
            delta = entry['weights']@part; q = entry['source'].astype(float).copy(); ids = entry['ids']
            changed = np.any(delta != 0, axis=1); selected = ids[changed]
            if len(selected):
                edited = (Rotation.from_quat(entry['original'][selected])*Rotation.from_rotvec(entry['relative'][selected]+delta[changed])).as_quat()
                edited *= np.where(np.sum(edited*q[selected], axis=1) < 0, -1, 1)[:, None]
                q[selected] = edited.astype(np.float32) if quantize else edited
            result[entry['node']] = q
        return result

    def world(self, value):
        local = self.local.copy(); quaternions = self.quaternions(value)
        for entry in self.entries:
            q = quaternions[entry['node']]
            rotations = sampled_rotations(entry['clock'], q, self.times)
            local[:, entry['node'], :3, :3] = rotations*self.scales[entry['node']][:, None, :]
        return world_from_local(local, self.parents)

    def world_pair(self, value, step=1e-6):
        self.controls(value)
        if not np.isfinite(step) or step <= 0:
            raise ValueError('Positive finite derivative step required')
        value = np.asarray(value, float); result = self.world(value); jac = np.empty(result.shape+(self.size,))
        for col in range(self.size):
            delta = np.zeros(self.size); delta[col] = step
            jac[..., col] = (self.world(value+delta)-self.world(value-delta))/(2*step)
        return result, jac

    def export(self, value, path):
        quaternions = self.quaternions(value, quantize=True)
        for entry in self.entries:
            angle = np.rad2deg((Rotation.from_quat(entry['original']).inv()*Rotation.from_quat(quaternions[entry['node']])).magnitude()).max()
            if angle > self.limit_degrees+1e-4:
                raise ValueError('Cumulative export exceeds original-reference rotation budget')
        document = copy.deepcopy(self.document); binary = bytearray(self.binary); animation = document['animations'][0]
        for channel in animation['channels']:
            node = channel['target']['node']
            if channel['target']['path'] == 'rotation' and node in quaternions:
                # A sampler can be shared by unselected nodes. Clone its descriptor
                # so editing one joint cannot also change another channel.
                sampler = copy.deepcopy(animation['samplers'][channel['sampler']])
                sampler['output'] = append_accessor(document, binary, quaternions[node], 'VEC4')
                channel['sampler'] = len(animation['samplers']); animation['samplers'].append(sampler)
        write_glb(path, document, binary)
