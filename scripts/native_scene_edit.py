"""Explicit native TRS permissions for body, object and partner proposals."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_contacts import fields, scalar, vector
from timed_rotation_edit import editable_keys, sampled_rotations
from paired_guarded_temporal import world_from_local
from gltf_tools import append_accessor, write_glb
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from native_foot_plant import mesh_accessor_payload


class SceneEdits:
    def __init__(self, permissions, scene, spec_digest):
        fields(permissions, ('schema', 'contacts_sha256', 'actors'), 'scene edit permissions')
        if permissions['schema'] != 'strep-native-scene-edit-v1' or permissions['contacts_sha256'] != spec_digest:
            raise ValueError('Permissions must bind the exact native scene contact request')
        entries = permissions['actors']
        if not isinstance(entries, dict) or not entries or set(entries) - set(scene.actors):
            raise ValueError('Explicit edit permissions for existing actors required')
        self.scene = scene; self.actors = {}; self.size = 0
        for name, declaration in entries.items():
            fields(declaration, ('window_s', 'protected_s', 'knots_s', 'tracks', 'maximum_joint_displacement_m'), 'actor edit')
            actor = scene.actors[name]; rig = actor['rig']; reader = actor['sampler']
            window = vector(declaration['window_s'], 2, 'edit window')
            if not 0 <= window[0] < window[1] <= scene.duration:
                raise ValueError('Native edit window must lie inside the shared clip')
            protected = declaration['protected_s']
            if not isinstance(protected, list): raise ValueError('Explicit protected time intervals required')
            for span in protected:
                a, b = vector(span, 2, 'protected interval')
                if not 0 <= a <= b <= scene.duration: raise ValueError('Protected interval outside clip')
            knots = declaration['knots_s']
            if not isinstance(knots, list) or not 3 <= len(knots) <= 12:
                raise ValueError('Choose 3-12 explicit edit knots')
            knots = np.array([scalar(v, 0, scene.duration, 'edit knot') for v in knots])
            if np.any(np.diff(knots) <= 0) or not np.array_equal(knots[[0,-1]], window):
                raise ValueError('Distinct knots must include the exact edit endpoints')
            displacement = scalar(declaration['maximum_joint_displacement_m'], .000001, .22, 'joint displacement bound')
            tracks = declaration['tracks']; seen = set(); edits = []
            if not isinstance(tracks, list) or not 1 <= len(tracks) <= 16:
                raise ValueError('Choose 1-16 explicit native tracks per actor')
            for track in tracks:
                fields(track, ('node', 'path', 'maximum_change'), 'native track permission')
                node, path = track['node'], track['path']
                if type(node) is not int or node not in rig.joints or path not in ('rotation','translation') or (node,path) in seen:
                    raise ValueError('Distinct existing skin-joint rotation/translation tracks required')
                matches = [c for c in reader.channels if c[:2] == (node,path)]
                if len(matches) != 1 or matches[0][4] != 'LINEAR':
                    raise ValueError('Selected track needs an existing LINEAR native channel')
                _, _, clock, values, mode = matches[0]
                maximum = scalar(track['maximum_change'], .000001, 45 if path == 'rotation' else .22, 'track change bound')
                unit = np.deg2rad(maximum) if path == 'rotation' else maximum
                ids = editable_keys(clock, window, protected)
                if not len(ids): raise ValueError('Edit window/protected times leave no editable key')
                weights = np.stack([np.interp(clock[ids], knots, np.eye(len(knots))[i]) for i in range(1,len(knots)-1)], axis=1)
                width = 3*(len(knots)-2); controls = np.arange(self.size,self.size+width).reshape(-1,3); self.size += width
                edits.append(dict(node=node,path=path,clock=clock,source=values,ids=ids,weights=weights,unit=unit,
                    maximum=maximum,controls=controls)); seen.add((node,path))
            self.actors[name] = dict(source=actor, window=window, protected=protected, knots=knots,
                displacement=displacement, tracks=edits, world_cache={})
        self.initial = np.zeros(self.size); self.lower = -np.ones(self.size); self.upper = np.ones(self.size)

    def controls(self, value):
        value = np.asarray(value, float)
        if value.shape != (self.size,) or not np.isfinite(value).all():
            raise ValueError('Finite matching normalized native scene controls required')
        return value

    def values(self, name, value, *, quantized=True):
        value = self.controls(value); result = {}
        for entry in self.actors[name]['tracks']:
            original = entry['source']; values = original.astype(float).copy(); ids = entry['ids']
            delta = entry['weights'] @ value[entry['controls']] * entry['unit']; changed = np.any(delta != 0,axis=1)
            if entry['path'] == 'rotation':
                edited = (Rotation.from_quat(original[ids[changed]]) * Rotation.from_rotvec(delta[changed])).as_quat()
                edited *= np.where(np.sum(edited*original[ids[changed]],axis=1)<0,-1,1)[:,None]
            else: edited = original[ids[changed]] + delta[changed]
            values[ids[changed]] = edited.astype(np.float32) if quantized else edited
            result[entry['node'],entry['path']] = values
        return result

    def worlds(self, name, value, times):
        """Batch LINEAR proposals; actual exports remain independently decoded."""
        actor = self.actors[name]['source']; reader = actor['sampler']; values = self.values(name,value)
        times = np.asarray(times,float); key = tuple(times); cache = self.actors[name]['world_cache']
        if key not in cache:
            world = np.array([reader.sample(float(t)) for t in times]); local = world.copy()
            for node,parent in enumerate(actor['rig'].parents):
                if parent>=0: local[:,node] = np.linalg.inv(world[:,parent]) @ world[:,node]
            cache[key] = world,local
        world,original = cache[key]
        if all(np.array_equal(values[e['node'],e['path']],e['source']) for e in self.actors[name]['tracks']):
            return world.copy()
        local = original.copy()
        for entry in self.actors[name]['tracks']:
            node,path,clock = entry['node'],entry['path'],entry['clock']; v = values[node,path]
            if np.array_equal(v,entry['source']): continue
            if path=='rotation':
                rotations = sampled_rotations(clock,v,times)
                ids = np.searchsorted(clock,times); safe = np.minimum(ids,len(clock)-1); exact = (ids<len(clock)) & (clock[safe]==times)
                rotations[exact] = Rotation.from_quat(v[safe[exact]]).as_matrix()
                scales = np.linalg.norm(original[:,node,:3,:3],axis=1)
                local[:,node,:3,:3] = rotations*scales[:,None,:]
            else:
                left = np.clip(np.searchsorted(clock,times,side='right')-1,0,len(clock)-2)
                u = (times-clock[left].astype(float))/(clock[left+1]-clock[left]).astype(float)
                u = np.where(times<=clock[0],0,np.where(times>=clock[-1],1,u))
                p = (1-u[:,None])*v[left]+u[:,None]*v[left+1]
                ids = np.searchsorted(clock,times); safe = np.minimum(ids,len(clock)-1); exact = (ids<len(clock)) & (clock[safe]==times)
                p[exact] = v[safe[exact]]; local[:,node,:3,3] = p
        return world_from_local(local,actor['rig'].parents)

    def export(self, name, value, output):
        actor = self.actors[name]['source']; rig = actor['rig']; reader = actor['sampler']
        values = self.values(name,value); document = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
        # The source-bound selected index is explicit, even for duplicate clips.
        animation = document['animations'][actor['animation_index']]
        for channel in animation['channels']:
            key = channel['target']['node'],channel['target']['path']
            if key in values:
                sampler = copy.deepcopy(animation['samplers'][channel['sampler']])
                sampler['output'] = append_accessor(document,binary,values[key],'VEC4' if key[1]=='rotation' else 'VEC3')
                channel['sampler'] = len(animation['samplers']); animation['samplers'].append(sampler)
        write_glb(output,document,binary)

    def audit(self, name, candidate, animation_index):
        original = self.actors[name]['source']; rig = original['rig']; changed = RigAsset.load(candidate)
        for key in ('nodes','skins','meshes','materials','images','textures','scenes','scene'):
            if rig.document.get(key) != changed.document.get(key): raise ValueError('Static rig/scene identity changed')
        for mesh in rig.document['meshes']:
            for primitive in mesh['primitives']:
                ids = list(primitive['attributes'].values()) + ([primitive['indices']] if 'indices' in primitive else [])
                ids += [i for target in primitive.get('targets',[]) for i in target.values()]
                for i in ids:
                    old,new = mesh_accessor_payload(rig.document,rig.binary,i),mesh_accessor_payload(changed.document,changed.binary,i)
                    if old[0]!=new[0] or not np.array_equal(old[1],new[1]): raise ValueError('Static mesh payload changed')
        if not np.array_equal(rig.inverse,changed.inverse): raise ValueError('Native skin bind payload changed')
        for image in rig.document.get('images',[]):
            if 'bufferView' in image:
                old = rig.document['bufferViews'][image['bufferView']]; new = changed.document['bufferViews'][image['bufferView']]
                a,b = old.get('byteOffset',0),new.get('byteOffset',0)
                if rig.binary[a:a+old['byteLength']] != changed.binary[b:b+new['byteLength']]: raise ValueError('Native image payload changed')
        if len(rig.document['animations']) != len(changed.document['animations']): raise ValueError('Animation population changed')
        edits = {(e['node'],e['path']):e for e in self.actors[name]['tracks']}; results = []
        for index in range(len(rig.document['animations'])):
            old_meta = {k:v for k,v in rig.document['animations'][index].items() if k not in ('channels','samplers')}
            new_meta = {k:v for k,v in changed.document['animations'][index].items() if k not in ('channels','samplers')}
            if old_meta != new_meta: raise ValueError('Animation metadata changed')
            old = NativeSupportSampler(rig.document,rig.binary,index); new = NativeSupportSampler(changed.document,changed.binary,index)
            if old.duration!=new.duration or len(old.channels)!=len(new.channels): raise ValueError('Native duration/channel count changed')
            for a,b in zip(old.channels,new.channels):
                if a[:2]!=b[:2] or a[4]!=b[4] or not np.array_equal(a[2],b[2]): raise ValueError('Native channel identity/clock changed')
                entry = edits.get(a[:2]) if index==animation_index else None
                if entry is None:
                    if not np.array_equal(a[3],b[3]): raise ValueError('Unpermitted native track changed')
                else:
                    frozen = np.ones(len(a[2]),bool); frozen[entry['ids']] = False
                    if not np.array_equal(a[3][frozen],b[3][frozen]): raise ValueError('Frozen native keys changed')
                    if entry['path']=='rotation':
                        maximum = float(np.rad2deg((Rotation.from_quat(a[3]).inv()*Rotation.from_quat(b[3])).magnitude()).max())
                        tolerance = .0001
                    else: maximum = float(np.linalg.norm(b[3]-a[3],axis=1).max()); tolerance = 1e-7
                    results.append(dict(node=entry['node'],path=entry['path'],maximum_change=maximum,
                        limit=entry['maximum'],serialization_tolerance=tolerance,passed=bool(maximum<=entry['maximum']+tolerance)))
        return dict(tracks=results,passed=all(r['passed'] for r in results),native_clocks_frozen_keys_and_static_payloads_preserved=True)
