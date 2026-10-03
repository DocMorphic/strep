"""Source-bound point contacts for supplied rigs, moving primitives and partners.

Read-only CPU measurements; no anatomy inference, correction or quality approval.
"""
import argparse
from pathlib import Path
import re
import shutil
import sys
import numpy as np
import scipy
from scipy.spatial.transform import Rotation, Slerp
from strep import ROOT, read, save, sha256
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from engine_contact_sampling import frame_populations, contract, contract_sha256
from object_geometry import Geometry

METHODS = ('native_scene_contacts.py', 'native_support_clock.py', 'native_support_skin.py',
           'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'paired_approach_basis.py',
           'paired_temporal_neighbor.py', 'paired_guarded_temporal.py', 'engine_contact_sampling.py',
           'object_geometry.py', 'strep.py')


def fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Explicit ' + label + ' fields required')


def scalar(value, low, high, label):
    if type(value) not in (int, float) or not np.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid ' + label)
    return float(value)


def vector(value, size, label):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError('Invalid ' + label)
    return np.array([scalar(v, -1e6, 1e6, label) for v in value])


def pose(value):
    fields(value, ('translation_m', 'rotation_xyzw'), 'rigid pose')
    p = vector(value['translation_m'], 3, 'translation'); q = vector(value['rotation_xyzw'], 4, 'quaternion')
    if abs(np.linalg.norm(q) - 1) > 1e-8:
        raise ValueError('Unit pose quaternion required')
    return p, Rotation.from_quat(q).as_matrix()


def references(value, skin):
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise ValueError('Choose 1-256 explicit skin vertex references')
    table = {tuple(r): i for i, r in enumerate(skin.vertex_references.tolist())}; ids = []
    for ref in value:
        if (not isinstance(ref, list) or len(ref) != 3 or any(type(i) is not int for i in ref)
                or tuple(ref) not in table or table[tuple(ref)] in ids):
            raise ValueError('Distinct existing [mesh node, primitive, vertex] references required')
        ids.append(table[tuple(ref)])
    return np.array(ids, int)


def points(value, count):
    if not isinstance(value, list) or len(value) != count:
        raise ValueError('One explicit target point for each effector vertex required')
    return np.array([vector(v, 3, 'target point') for v in value])


class SceneContacts:
    def __init__(self, spec, base):
        fields(spec, ('schema', 'duration_s', 'actors', 'objects', 'contacts'), 'native scene contact')
        if spec['schema'] != 'strep-native-scene-contacts-v1':
            raise ValueError('Native scene contact schema required')
        self.duration = scalar(spec['duration_s'], .000001, 30, 'shared duration')
        self.actors = {}; self.objects = {}; self.inputs = {}; self.rows = []
        if not isinstance(spec['actors'], dict) or not 1 <= len(spec['actors']) <= 8:
            raise ValueError('Choose 1-8 named actors')
        for name, entry in spec['actors'].items():
            self.name(name); fields(entry, ('glb', 'sha256', 'animation_index', 'placement'), 'actor')
            if not isinstance(entry['glb'], str) or not entry['glb']:
                raise ValueError('Actor GLB path required')
            path = (Path(base) / entry['glb']).resolve(); digest = sha256(path)
            if entry['sha256'] != digest or type(entry['animation_index']) is not int:
                raise ValueError('Actor source hash and explicit animation index required')
            rig = RigAsset.load(path); sampler = NativeSupportSampler(rig.document, rig.binary, entry['animation_index'])
            if sampler.duration != self.duration:
                raise ValueError('Actors must share the exact declared clip duration; retime explicitly first')
            self.actors[name] = dict(rig=rig, sampler=sampler, animation_index=entry['animation_index'],
                skin=NativeSupportSkin(rig), placement=pose(entry['placement']))
            self.inputs[str(path)] = digest
        if not isinstance(spec['objects'], dict) or len(spec['objects']) > 32:
            raise ValueError('Named object dictionary required')
        for name, entry in spec['objects'].items():
            self.name(name); fields(entry, ('geometry', 'keyframes'), 'object')
            geometry = Geometry.parse(entry['geometry']); keys = entry['keyframes']
            if not isinstance(keys, list) or not 1 <= len(keys) <= 3601:
                raise ValueError('Explicit rigid object pose keys required')
            times = []; poses = []
            for key in keys:
                fields(key, ('time_s', 'translation_m', 'rotation_xyzw'), 'object pose key')
                times.append(scalar(key['time_s'], 0, self.duration, 'object key time'))
                poses.append(pose({k: key[k] for k in ('translation_m', 'rotation_xyzw')}))
            times = np.array(times)
            if times[0] != 0 or np.any(np.diff(times) <= 0) or len(times) > 1 and times[-1] != self.duration:
                raise ValueError('Object keys must be static at zero or cover the whole shared duration')
            self.objects[name] = dict(geometry=geometry, times=times,
                positions=np.array([p for p, _ in poses]), rotations=np.array([r for _, r in poses]))
        contacts = spec['contacts']; seen = set()
        if not isinstance(contacts, list) or not 1 <= len(contacts) <= 64:
            raise ValueError('Choose 1-64 explicit point contact conditions')
        for row in contacts:
            fields(row, ('id', 'actor', 'vertices', 'reduction', 'target', 'mode', 'interval_s', 'limits'), 'contact')
            self.name(row['id'])
            if row['id'] in seen or not isinstance(row['actor'], str) or row['actor'] not in self.actors:
                raise ValueError('Distinct contact IDs and existing effector actors required')
            seen.add(row['id']); ids = references(row['vertices'], self.actors[row['actor']]['skin'])
            self.reduction(row['reduction']); count = 1 if row['reduction'] == 'centroid' else len(ids)
            interval = vector(row['interval_s'], 2, 'contact interval'); a, b = interval
            if not 0 <= a <= b <= self.duration:
                raise ValueError('Contact interval outside the shared clip')
            mode = row['mode']
            if mode not in ('touch', 'hold') or (mode == 'touch') != (a == b):
                raise ValueError('Touch needs one exact time; hold needs a positive interval')
            expected = ('position_m',) if mode == 'touch' else ('position_m', 'relative_speed_m_s')
            fields(row['limits'], expected, 'contact limits')
            for k, v in row['limits'].items(): scalar(v, 0, 1e6, 'contact limit')
            target = row['target']
            if not isinstance(target, dict): raise ValueError('Explicit target required')
            space = target.get('space')
            if space == 'actor':
                fields(target, ('space', 'actor', 'vertices', 'reduction'), 'partner target')
                if not isinstance(target['actor'], str) or target['actor'] not in self.actors or target['actor'] == row['actor']:
                    raise ValueError('Partner target must name another loaded actor')
                target_ids = references(target['vertices'], self.actors[target['actor']]['skin'])
                self.reduction(target['reduction'])
                target_count = 1 if target['reduction'] == 'centroid' else len(target_ids)
                if target_count != count: raise ValueError('Explicit one-to-one partner point correspondence required')
            elif space in ('object', 'world'):
                fields(target, ('space', 'points_m', 'object') if space == 'object' else ('space', 'points_m'), 'point target')
                target_ids = points(target['points_m'], count)
                if space == 'object':
                    if not isinstance(target['object'], str) or target['object'] not in self.objects: raise ValueError('Unknown target object')
                    geo = self.objects[target['object']]['geometry']
                    distance = geo.distance_gradient(target_ids, np.zeros(3), np.eye(3))[0]
                    if np.max(abs(distance)) > 1e-6: raise ValueError('Object contact points must lie on the declared primitive surface')
            else: raise ValueError('World, object or partner target required')
            self.rows.append(dict(authored=row, ids=ids, target_ids=target_ids))
        self.check_inputs()

    @staticmethod
    def name(value):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
            raise ValueError('Named IDs use 1-64 letters, digits, underscores or hyphens')

    def check_inputs(self):
        if any(sha256(p) != h for p, h in self.inputs.items()):
            raise ValueError('Native scene contact source changed')

    @staticmethod
    def reduction(value):
        if value not in ('individual', 'centroid'):
            raise ValueError('Explicit individual vertices or arithmetic centroid required')

    def actor_points(self, name, ids, times):
        actor = self.actors[name]; skin = actor['skin']; result = []
        for time in times:
            world = actor['sampler'].sample(float(time))
            local = np.einsum('vkij,vkj,vk->vi', world[skin.nodes[ids], :3, :], skin.points[ids], skin.weights[ids])
            p, r = actor['placement']; result.append(local @ r.T + p)
        return np.array(result)

    def object_poses(self, name, times):
        obj = self.objects[name]; clock = obj['times']
        if len(clock) == 1:
            return np.repeat(obj['positions'], len(times), axis=0), np.repeat(obj['rotations'], len(times), axis=0)
        p = np.stack([np.interp(times, clock, obj['positions'][:, i]) for i in range(3)], axis=1)
        return p, Slerp(clock, Rotation.from_matrix(obj['rotations']))(times).as_matrix()

    def evaluate(self):
        observations = {}; results = []
        for index, entry in enumerate(self.rows):
            row = entry['authored']; start, end = row['interval_s']; target = row['target']; space = target['space']
            populations = frame_populations([start, end]) if row['mode'] == 'hold' else []
            native = [c[2] for a in self.actors.values() for c in a['sampler'].channels]
            native += [obj['times'] for obj in self.objects.values()]
            times = np.unique(np.concatenate([np.array([start, end])] + native + [p['times_s'] for p in populations]))
            times = times[(times >= start) & (times <= end)]
            effector = self.actor_points(row['actor'], entry['ids'], times)
            if row['reduction'] == 'centroid': effector = effector.mean(axis=1, keepdims=True)
            if space == 'actor':
                goal = self.actor_points(target['actor'], entry['target_ids'], times)
                if target['reduction'] == 'centroid': goal = goal.mean(axis=1, keepdims=True)
            elif space == 'world': goal = np.repeat(entry['target_ids'][None], len(times), axis=0)
            else:
                p, r = self.object_poses(target['object'], times)
                goal = np.einsum('fij,vj->fvi', r, entry['target_ids']) + p[:, None]
            error = effector - goal
            if space == 'object': error = np.einsum('fvi,fij->fvj', error, r)
            distance = np.linalg.norm(error, axis=2); frame, vertex = np.unravel_index(distance.argmax(), distance.shape)
            position_pass = bool(distance.max() <= row['limits']['position_m']); speeds = []
            for population in populations:
                clock = population['times_s']; ids = np.searchsorted(times, clock)
                if not np.array_equal(times[ids], clock): raise ValueError('Incomplete predeclared frame clock')
                available = len(clock) >= 2; maximum = None; peak = None
                if available:
                    speed = np.linalg.norm(np.diff(error[ids], axis=0), axis=2) * population['rate_hz']
                    pair, v = np.unravel_index(speed.argmax(), speed.shape); maximum = float(speed[pair, v])
                    peak = dict(times_s=clock[pair:pair+2].tolist(), vertex_correspondence_index=int(v))
                speeds.append(dict(id=population['id'], times_s=clock.tolist(), tick_indices=population['tick_indices'].tolist(),
                    rate_hz=population['rate_hz'], phase_offset_frames=population['phase_offset_frames'],
                    available=available, maximum_relative_speed_m_s=maximum, peak_pair=peak,
                    passed=bool(available and maximum <= row['limits']['relative_speed_m_s'])))
            observations.update({f'contact_{index}_times_s': times, f'contact_{index}_effector_world_m': effector,
                f'contact_{index}_target_world_m': goal, f'contact_{index}_error_m': error})
            results.append(dict(id=row['id'], mode=row['mode'], target_space=space, interval_s=row['interval_s'],
                samples=len(times), vertices=len(entry['ids']), reduction=row['reduction'], measured_points=effector.shape[1], limits=row['limits'],
                maximum_position_error_m=float(distance.max()), peak_position=dict(time_s=float(times[frame]), vertex_correspondence_index=int(vertex)),
                position_samples_pass=position_pass, relative_speed_populations=speeds,
                relative_speed_frame='object local' if space == 'object' else 'world difference between corresponding points',
                passed=bool(position_pass and all(p['passed'] for p in speeds))))
        self.check_inputs()
        return dict(schema='strep-native-scene-contact-audit-v1', inputs_sha256=self.inputs,
            frame_sampling_contract=contract(), frame_sampling_contract_sha256=contract_sha256(), contacts=results,
            passed=all(r['passed'] for r in results), loaded_skin_weights_normalized=True,
            engine_playback_verified=False, collision_verified=False, continuous_contact_certified=False,
            quality_approved=False, training_admitted=False, release_approved=False), observations


def run(spec_path, output):
    spec_path, output = Path(spec_path).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native scene contact audit directory required')
    digest = sha256(spec_path); methods = {n: sha256(ROOT / 'scripts' / n) for n in METHODS}
    scene = SceneContacts(read(spec_path), spec_path.parent)
    output.mkdir(parents=True); shutil.copyfile(spec_path, output / 'spec.json')
    snapshots = {}
    for i, (path, expected) in enumerate(scene.inputs.items()):
        dest = output / 'input' / f'actor-{i}.glb'; dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, dest)
        if sha256(dest) != expected: raise ValueError('Source snapshot differs')
        snapshots[path] = dict(path=dest.relative_to(output).as_posix(), sha256=expected)
    archive = output / 'implementation'; archive.mkdir()
    for name in methods: shutil.copyfile(ROOT / 'scripts' / name, archive / name)
    result, observations = scene.evaluate()
    if sha256(spec_path) != digest or sha256(output / 'spec.json') != digest:
        raise ValueError('Authored native scene contacts changed')
    if any(sha256(ROOT / 'scripts' / n) != h or sha256(archive / n) != h for n, h in methods.items()):
        raise ValueError('Native scene contact implementation changed')
    np.savez(output / 'observations.npz', **observations)
    scene.check_inputs()
    if any(sha256(output / s['path']) != s['sha256'] for s in snapshots.values()):
        raise ValueError('Native scene contact snapshot changed')
    result.update(spec_sha256=digest, source_snapshots=snapshots, implementation_sha256=methods,
        runtime=dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__),
        observations_sha256=sha256(output / 'observations.npz'))
    save(output / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.spec, args.output)
