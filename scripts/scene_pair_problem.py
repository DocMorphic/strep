"""Scene-derived two-actor surface and original-relative motion constraints."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, sha256
from rig_asset import RigAsset, array
from timed_rotation_edit import TimedRotationEdit
from paired_approach_basis import BoundSkin
from coupled_surface_norms import separation_rows


class MotionRows:
    """Fixed per-joint, per-knot-span source maxima on a declared uniform clock."""
    def __init__(self, model, joints, rotation, translation):
        times = model.times
        if len(times) < 3 or not np.allclose(np.diff(times), np.diff(times)[0], atol=1e-12, rtol=0):
            raise ValueError('Uniform motion clock with at least three samples required')
        self.dt = float(times[1]-times[0]); self.joints = joints
        self.rotation, self.translation = rotation, translation
        active = np.zeros((len(times), len(joints)), bool)
        for index, node in enumerate(joints):
            ancestors = []; parent = model.parents[node]
            while parent >= 0:
                ancestors.append(parent); parent = model.parents[parent]
            for entry in model.entries:
                if entry['node'] in ancestors:
                    for key in entry['ids']:
                        active[:, index] |= (times > entry['clock'][key-1]) & (times < entry['clock'][key+1])
        self.specs = []
        reference = self.positions(model.source_world)
        # Half-open knot spans partition every stencil midpoint, including halo.
        for order in [1, 2]:
            source = np.diff(reference, n=order, axis=0)/self.dt**order
            changed = np.zeros(source.shape[:2], bool)
            for offset in range(order+1):
                changed |= active[offset:offset+len(source)]
            clock = (times[:-order]+times[order:])/2
            bins = np.searchsorted(model.knots[1:-1], clock, side='right')
            caps = np.zeros(source.shape[:2])
            for bin_id in np.unique(bins):
                selected = bins == bin_id
                caps[selected] = np.linalg.norm(source[selected], axis=2).max(axis=0)
            rows, cols = np.nonzero(changed)
            self.specs.append((order, rows, cols, caps[rows, cols]))
        self.radii = np.concatenate([s[3] for s in self.specs])
        self.kinds = np.concatenate([np.full(len(s[1]), 'speed' if s[0] == 1 else 'acceleration') for s in self.specs])

    def positions(self, world):
        return world[:, self.joints][:, :, :3, 3]@self.rotation.T+self.translation

    def values(self, world, derivative=None):
        positions = self.positions(world); vectors = []; jacobians = []
        if derivative is not None:
            derivative = np.einsum('ij,tkjd->tkid', self.rotation, derivative[:, self.joints][:, :, :3, 3, :])
        for order, rows, cols, caps in self.specs:
            vectors.append((np.diff(positions, n=order, axis=0)/self.dt**order)[rows, cols])
            if derivative is not None:
                jacobians.append((np.diff(derivative, n=order, axis=0)/self.dt**order)[rows, cols])
        return np.concatenate(vectors), None if derivative is None else np.concatenate(jacobians)


def load_actors(folder):
    folder = Path(folder).resolve(); record = read(folder/'request.json')
    if read(folder/'state.json')['status'] != 'prepared':
        raise ValueError('Immutable prepared paired request required')
    for name, digest in record['implementation'].items():
        if sha256(folder/'implementation'/name) != digest or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Prepared edit implementation changed: '+name)
    snap = record['scene_snapshot']; scene_path = (folder/snap['path']).resolve()
    if not scene_path.is_relative_to(folder) or sha256(scene_path) != snap['sha256']:
        raise ValueError('Scene snapshot changed')
    scene = read(scene_path)['scene']; request = record['authored']; actors = []
    if set(record['actors']) != set(scene['actors']) or len(record['actors']) != 2:
        raise ValueError('Exactly two matching saved actors required')
    for name, entry in record['actors'].items():
        path = (folder/entry['path']).resolve()
        if not path.is_relative_to(folder) or sha256(path) != entry['sha256'] or entry['placement'] != scene['actors'][name]['transform']:
            raise ValueError('Prepared actor or placement changed')
        rig = RigAsset.load(path)
        model = TimedRotationEdit(rig.document, rig.binary, request['actors'][name]['joints'], record['sample_times_seconds'],
            request['window_s'], record['protected_seconds'], knots=request['knots_s'], limit_degrees=request['limit_degrees'])
        if model.size != entry['controls'] or {str(e['node']): e['ids'].tolist() for e in model.entries} != entry['editable_keys']:
            raise ValueError('Prepared control layout changed')
        placement = entry['placement']; rotation = Rotation.from_quat(placement['rotation_xyzw']).as_matrix()
        translation = np.asarray(placement['translation_m'], float)
        skin = BoundSkin(rig); primitive = rig.primitives[0]
        node = rig.document['nodes'][primitive['node']]
        mesh = rig.document['meshes'][node['mesh']]['primitives'][primitive['primitive']]
        faces = array(rig.document, rig.binary, mesh['indices']).reshape(-1, 3)
        actors.append(dict(name=name, source=path, rig=rig, model=model, skin=skin, rotation=rotation, translation=translation,
                           faces=faces, rates=MotionRows(model, rig.joints, rotation, translation)))
    return record, actors


class ScenePairProblem:
    def __init__(self, actors, samples):
        if len(actors) != 2:
            raise ValueError('Two actors required')
        self.actors = actors; self.samples = samples
        self.sizes = [a['model'].size for a in actors]; self.size = sum(self.sizes)
        self.times = actors[0]['model'].times
        np.testing.assert_array_equal(self.times, actors[1]['model'].times)
        if [s['sample'] for s in samples] != list(range(len(self.times))):
            raise ValueError('Complete ordered scene sample population required')
        self.groups = []
        for source, target in [(0, 1), (1, 0)]:
            records = []
            for sample in samples:
                if sample['time_s'] != self.times[sample['sample']]:
                    raise ValueError('Witness time mismatch')
                cap = max(.005, max(d['maximum_depth_m'] for d in sample['directions']))
                direction = sample['directions'][source]
                if direction['source'] != source or direction['target'] != target:
                    raise ValueError('Explicit surface direction mismatch')
                records.extend(dict(sample=sample['sample'], cap=cap, **r) for r in direction['records'])
            self.groups.append(dict(source=source, target=target,
                frames=np.array([r['sample'] for r in records], int), ids=np.array([r['vertex'] for r in records], int),
                triangles=np.array([r['target_vertices'] for r in records], int).reshape(-1, 3),
                bary=np.array([r['barycentric'] for r in records]).reshape(-1, 3),
                normals=np.array([r['normal'] for r in records]).reshape(-1, 3), caps=np.array([r['cap'] for r in records])))

    def split(self, controls):
        controls = np.asarray(controls, float)
        if controls.shape != (self.size,) or not np.isfinite(controls).all():
            raise ValueError('Finite matching scene controls required')
        return np.split(controls, [self.sizes[0]])

    def surface_rows(self, worlds, derivatives=None):
        vectors = []; jacobians = []; normals = []; caps = []
        for group in self.groups:
            source, target = group['source'], group['target']; a, b = self.actors[source], self.actors[target]
            frames, ids, triangles = group['frames'], group['ids'], group['triangles']
            if not len(ids):
                continue
            points = a['skin'].evaluate(worlds[source], frames, ids)@a['rotation'].T+a['translation']
            target_frames = np.repeat(frames, 3)
            tri = (b['skin'].evaluate(worlds[target], target_frames, triangles.ravel())@b['rotation'].T+b['translation']).reshape(-1, 3, 3)
            if derivatives is None:
                vector = points-np.einsum('ni,nij->nj', group['bary'], tri)
            else:
                jp = np.einsum('ij,njd->nid', a['rotation'], a['skin'].derivative(derivatives[source], frames, ids))
                jq = np.einsum('ij,njd->nid', b['rotation'], b['skin'].derivative(derivatives[target], target_frames, triangles.ravel())).reshape(-1, 3, 3, self.sizes[target])
                vector, jacobian = separation_rows(points, tri, group['bary'], jp, jq, source)
                jacobians.append(jacobian)
            vectors.append(vector); normals.append(group['normals']); caps.append(group['caps'])
        if not vectors:
            raise ValueError('No nearby partner surface rows; no collision proposal needed')
        vectors, normals = np.concatenate(vectors), np.concatenate(normals)
        result = dict(surface_vectors=vectors, gaps=np.einsum('ni,ni->n', vectors, normals), depth_caps=np.concatenate(caps))
        if derivatives is not None:
            result['surface_jacobians'] = np.concatenate(jacobians)
            result['gap_jacobian'] = np.einsum('ni,nid->nd', normals, result['surface_jacobians'])
        return result

    def linearize(self, controls):
        worlds = []; derivatives = []; vectors = []; jacobians = []; radii = []; kinds = []
        for number, (actor, part) in enumerate(zip(self.actors, self.split(controls))):
            model = actor['model']; world, derivative = model.world_pair(part)
            worlds.append(world); derivatives.append(derivative); offset = sum(self.sizes[:number])
            edit, ej = model.edit_rows(part); motion, mj = actor['rates'].values(world, derivative)
            values = np.concatenate([edit, motion]); local = np.concatenate([ej, mj])
            full = np.zeros((len(values), 3, self.size)); full[:, :, offset:offset+model.size] = local
            vectors.append(values); jacobians.append(full)
            radii.append(np.r_[np.full(len(edit), np.deg2rad(model.limit_degrees)), actor['rates'].radii])
            kinds.extend(['edit']*len(edit)); kinds.extend(actor['rates'].kinds)
        return dict(**self.surface_rows(worlds, derivatives), vectors=np.concatenate(vectors), jacobians=np.concatenate(jacobians),
                    radii=np.concatenate(radii), kinds=np.array(kinds))
