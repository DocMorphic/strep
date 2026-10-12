"""Explicit one-neighbor Float32 rotation/translation changes on authored keys."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_contacts import fields
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest

SCHEMA='strep-native-component-storage-repair-v1'


class ComponentAdjustedEdits(StorageAdjustedEdits):
    def __init__(self,base,policy,corrections):
        digest=authoring_digest(base)
        fields(policy,('schema','authoring_sha256','allowed_paths','maximum_component_steps','maximum_corrections','acknowledge_storage_adjustment'),'component storage policy')
        paths=policy['allowed_paths']
        if (policy['schema']!=SCHEMA or policy['authoring_sha256']!=digest
                or not isinstance(paths,list) or not paths
                or any(type(p) is not str or p not in ('rotation','translation') for p in paths)
                or len(set(paths))!=len(paths) or type(policy['maximum_component_steps']) is not int
                or policy['maximum_component_steps']!=1 or type(policy['maximum_corrections']) is not int
                or not 1<=policy['maximum_corrections']<=64 or policy['acknowledge_storage_adjustment'] is not True):
            raise ValueError('Explicit source-bound component paths and one-neighbor policy required')
        if not isinstance(corrections,list) or len(corrections)>policy['maximum_corrections']:
            raise ValueError('Bounded complete component correction list required')
        seen=set()
        for row in corrections:
            fields(row,('actor','node','path','key_index','component','step'),'stored component correction')
            actor,node,path,key,component,step=[row[k] for k in ('actor','node','path','key_index','component','step')]
            if (type(actor) is not str or actor not in base.actors or type(node) is not int
                    or type(path) is not str or path not in paths or type(key) is not int
                    or type(component) is not int or not 0<=component<(4 if path=='rotation' else 3)
                    or type(step) is not int or step not in (-1,1)):
                raise ValueError('Authored native rotation/translation key and one signed component step required')
            matches=[e for e in base.actors[actor]['tracks'] if (e['node'],e['path'])==(node,path)]
            if len(matches)!=1 or key not in matches[0]['ids']:
                raise ValueError('Component correction lies outside existing editable keys')
            identity=actor,node,path,key,component
            if identity in seen:raise ValueError('Duplicate component would exceed one-neighbor envelope')
            seen.add(identity)
        self.base=base;self.policy=copy.deepcopy(policy);self.corrections=copy.deepcopy(corrections)
        self._component_authoring=digest
        self._component_policy=copy.deepcopy(policy);self._component_corrections=copy.deepcopy(corrections)

    def values(self,name,value,*,quantized=True):
        if (self.policy!=self._component_policy or self.corrections!=self._component_corrections
                or authoring_digest(self.base)!=self._component_authoring):
            raise ValueError('Declared component storage contract changed')
        value=self.base.controls(value)
        if np.any(value<self.base.lower) or np.any(value>self.base.upper):
            raise ValueError('Original control boxes remain required')
        values=self.base.values(name,value,quantized=quantized)
        if not quantized:return values
        for row in self.corrections:
            if row['actor']!=name:continue
            key=row['node'],row['path'];index=row['key_index'];component=row['component']
            nearest=np.float32(values[key][index,component])
            neighbor=np.nextafter(nearest,np.float32(np.inf if row['step']>0 else -np.inf))
            if not np.isfinite(neighbor):raise ValueError('Finite neighboring component required')
            values[key][index,component]=float(neighbor)
        for entry in self.base.actors[name]['tracks']:
            output=values[entry['node'],entry['path']]
            if entry['path']=='rotation':
                if np.any(abs(np.linalg.norm(output,axis=1)-1)>4*np.finfo(np.float32).eps):
                    raise ValueError('Near-unit stored quaternion population required')
                maximum=np.rad2deg((Rotation.from_quat(entry['source']).inv()*Rotation.from_quat(output)).magnitude()).max()
            else:maximum=np.linalg.norm(output-entry['source'],axis=1).max()
            if maximum>entry['maximum']:raise ValueError('Stored adjustment exceeds original strict track bound')
        return values
