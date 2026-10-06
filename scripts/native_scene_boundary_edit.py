"""Explicit clip-boundary freedom for a new native scene editing epoch.

Existing bridge/scene edits keep their original endpoint-preservation behavior.
This separate contract can opt into a true clip endpoint; it never extends an
interior window, bypasses protected interpolation support, or grants transition,
contact, collision, engine, or animation-quality approval.
"""
import copy
from pathlib import Path
import tempfile

import numpy as np
from native_scene_contacts import fields, vector, scalar
from native_scene_edit import SceneEdits
from timed_rotation_edit import editable_keys
from gltf_tools import write_glb
from rig_asset import RigAsset

SCHEMA = 'strep-native-scene-boundary-edit-v1'


def require(value, message):
    if not value: raise ValueError(message)


def endpoint_allowed(clock, index, window, protected):
    """An endpoint's open interpolation segment must lie in the edit scope."""
    time = float(clock[index]); before, after = (clock[0],clock[1]) if index == 0 else (clock[-2],clock[-1])
    return bool(window[0] <= before < after <= window[1]
        and not any(a <= time <= b or before < b and after > a for a,b in protected))


class BoundarySceneEdits(SceneEdits):
    def __init__(self, request, scene, spec_digest, *, rotation_storage_policy='unit'):
        fields(request,('schema','permissions','boundary_keys','acknowledge_changed_boundary_compatibility'),'boundary edit request')
        require(request['schema'] == SCHEMA, 'Explicit boundary-edit schema required')
        permissions = request['permissions']
        fields(permissions,('schema','contacts_sha256','actors'),'scene edit permissions')
        require(permissions['schema'] == 'strep-native-scene-edit-v1' and permissions['contacts_sha256'] == spec_digest,
            'Permissions must bind the exact native scene contact request')
        require(rotation_storage_policy in ('unit','source-scale'), 'Choose unit or source-scale rotation storage')
        actors = permissions['actors']; policies = request['boundary_keys']
        require(isinstance(actors,dict) and actors and not set(actors)-set(scene.actors)
            and isinstance(policies,dict) and set(policies) == set(actors),
            'Explicit boundary policy for every edited actor required')
        changed = False
        for name, policy in policies.items():
            fields(policy,('start','end'),'actor boundary policy')
            require(all(policy[k] in ('preserve','edit') for k in ('start','end')), 'Choose preserve or edit for each clip boundary')
            declaration = actors[name]
            fields(declaration,('window_s','protected_s','knots_s','tracks','maximum_joint_displacement_m'),'actor edit')
            require(isinstance(declaration['protected_s'],list), 'Explicit protected time intervals required')
            for span in declaration['protected_s']:
                a,b = vector(span,2,'protected interval')
                require(0 <= a <= b <= scene.duration, 'Protected interval outside clip')
            if 'edit' in policy.values():
                changed = True
        require(type(request['acknowledge_changed_boundary_compatibility']) is bool
            and request['acknowledge_changed_boundary_compatibility'] == changed,
            'Acknowledge changed start/end compatibility exactly when a boundary is editable')
        self.rotation_storage_policy = rotation_storage_policy; self.scene = scene; self.actors = {}; self.size = 0
        # Keep original track/static/budget rules, while allowing an endpoint
        # whose single segment is permitted even with no editable interior key.
        for name, declaration in actors.items():
            actor = scene.actors[name]; rig = actor['rig']; reader = actor['sampler']
            window = vector(declaration['window_s'],2,'edit window')
            require(0 <= window[0] < window[1] <= scene.duration, 'Native edit window must lie inside the shared clip')
            knots = declaration['knots_s']
            require(isinstance(knots,list) and 3 <= len(knots) <= 12, 'Choose 3-12 explicit edit knots')
            knots = np.array([scalar(t,0,scene.duration,'edit knot') for t in knots])
            require(np.all(np.diff(knots)>0) and np.array_equal(knots[[0,-1]],window), 'Distinct knots must include exact edit endpoints')
            displacement = scalar(declaration['maximum_joint_displacement_m'],.000001,.22,'joint displacement bound')
            tracks = declaration['tracks']; seen = set(); entries = []
            require(isinstance(tracks,list) and 1 <= len(tracks) <= 16, 'Choose 1-16 explicit native tracks per actor')
            for track in tracks:
                fields(track,('node','path','maximum_change'),'native track permission')
                node,path = track['node'],track['path']
                require(type(node) is int and node in rig.joints and path in ('rotation','translation') and (node,path) not in seen,
                    'Distinct existing skin-joint rotation/translation tracks required')
                matches = [c for c in reader.channels if c[:2] == (node,path)]
                require(len(matches) == 1 and matches[0][4] == 'LINEAR', 'Selected track needs an existing LINEAR native channel')
                _,_,clock,values,_ = matches[0]
                require(len(clock) >= 2 and np.isfinite(clock).all() and clock[0] >= 0 and np.all(np.diff(clock)>0), 'Increasing native track clock required')
                if path == 'rotation' and rotation_storage_policy == 'source-scale':
                    require(np.array_equal(values,values.astype(np.float32).astype(float))
                        and np.max(abs(np.linalg.norm(values,axis=1)-1.)) <= 4*np.finfo(np.float32).eps,
                        'Source-scale rotation storage requires near-unit original Float32 quaternions')
                maximum = scalar(track['maximum_change'],.000001,45 if path == 'rotation' else .22,'track change bound')
                entries.append(dict(node=node,path=path,clock=clock,source=values,unit=np.deg2rad(maximum) if path == 'rotation' else maximum,maximum=maximum))
                seen.add((node,path))
            self.actors[name] = dict(source=actor,window=window,protected=copy.deepcopy(declaration['protected_s']),
                knots=knots,displacement=displacement,tracks=entries,world_cache={})
        self.request = copy.deepcopy(request); self.boundary_keys = copy.deepcopy(policies)
        for name, actor in self.actors.items():
            declaration, policy = actors[name], policies[name]
            actor['protected'] = copy.deepcopy(declaration['protected_s'])
            knot_ids = list(range(1,len(actor['knots'])-1))
            if policy['start'] == 'edit':
                require(actor['window'][0] == 0, 'Only the true clip start can be editable')
                knot_ids.insert(0,0)
            if policy['end'] == 'edit':
                require(actor['window'][1] == scene.duration, 'Only the true clip end can be editable')
                knot_ids.append(len(actor['knots'])-1)
            for entry in actor['tracks']:
                clock = entry['clock']; indices = editable_keys(clock,actor['window'],actor['protected']).tolist() if len(clock)>2 else []
                for key, index, time in (('start',0,0.),('end',len(clock)-1,scene.duration)):
                    if policy[key] != 'edit': continue
                    require(clock[index] == time and endpoint_allowed(clock,index,actor['window'],actor['protected']),
                        'Requested clip endpoint or interpolation support is protected/missing')
                    indices.append(index)
                require(indices, 'No editable keys remain under declared boundary/protection policy')
                entry['ids'] = np.array(sorted(set(indices)),dtype=int)
                entry['weights'] = np.stack([np.interp(clock[entry['ids']],actor['knots'],np.eye(len(actor['knots']))[i])
                    for i in knot_ids],axis=1)
                width = 3*len(knot_ids)
                entry['controls'] = np.arange(self.size,self.size+width).reshape(-1,3); self.size += width
        require(self.size <= 96, 'At most 96 complete boundary-edit control components; no truncation')
        self.initial = np.zeros(self.size); self.lower = -np.ones(self.size); self.upper = np.ones(self.size)

    def audit(self,name,candidate,animation_index):
        report = super().audit(name,candidate,animation_index)
        report.update(boundary_keys=copy.deepcopy(self.boundary_keys[name]),new_edit_epoch=True,
            previous_start_end_transition_approval_inherited=False,
            scope='Explicit selected clip boundary/native-key editing only. Static payloads, unselected clips/tracks, '
                'protected keys/interpolation support and authored track bounds remain. Displacement, source rates, '
                'contacts, geometry and new start/end compatibility still require separate validation.')
        return report

    def append_candidate(self,name,value,output,label):
        """Append a separate variant, restoring the complete original library."""
        output = Path(output)
        require(not output.exists(), 'Fresh appended boundary candidate path required')
        require(isinstance(label,str) and 1 <= len(label) <= 160, 'Explicit candidate clip label required')
        actor = self.scene.actors[name]; original = actor['rig']
        with tempfile.TemporaryDirectory() as folder:
            probe = Path(folder)/'bounded.glb'; self.export(name,value,probe)
            require(self.audit(name,probe,actor['animation_index'])['passed'], 'Candidate exceeds authored native track bounds')
            changed = RigAsset.load(probe); document = copy.deepcopy(changed.document)
            variant = copy.deepcopy(document['animations'][actor['animation_index']]); variant['name'] = label
            document['animations'][actor['animation_index']] = copy.deepcopy(original.document['animations'][actor['animation_index']])
            index = len(document['animations']); document['animations'].append(variant)
            require(document['animations'][:-1] == original.document['animations']
                and changed.binary[:len(original.binary)] == original.binary, 'Original clip library/payload changed')
            output.parent.mkdir(parents=True,exist_ok=True); write_glb(output,document,changed.binary)
        return index
