"""Explicit one-neighbor Float32 adjustments inside existing rotation permissions.

Discrete storage corrections are separate from the intended continuous curve.
They confer no native/contact, geometry, transition, engine or quality approval.
Old editors and exporters remain unchanged.
"""
import copy,hashlib,json,tempfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_contacts import fields
from native_scene_boundary_edit import BoundarySceneEdits
from native_scene_edit import SceneEdits
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from gltf_tools import write_glb

SCHEMA='strep-native-rotation-storage-repair-v1'


def authoring_digest(base):
    if not isinstance(base,BoundarySceneEdits):
        raise ValueError('Existing explicit boundary authoring contract required')
    return hashlib.sha256(json.dumps(base.request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class StorageAdjustedEdits:
    def __init__(self,base,policy,corrections):
        digest=authoring_digest(base)
        fields(policy,('schema','authoring_sha256','maximum_component_steps','maximum_corrections','acknowledge_storage_adjustment'),'storage repair policy')
        if (policy['schema']!=SCHEMA or policy['authoring_sha256']!=digest
                or type(policy['maximum_component_steps']) is not int or policy['maximum_component_steps']!=1
                or type(policy['maximum_corrections']) is not int or not 1<=policy['maximum_corrections']<=64
                or policy['acknowledge_storage_adjustment'] is not True):
            raise ValueError('Explicit source-bound one-neighbor storage policy required')
        if not isinstance(corrections,list) or len(corrections)>policy['maximum_corrections']:
            raise ValueError('Bounded complete correction list required')
        seen=set()
        for row in corrections:
            fields(row,('actor','node','key_index','component','step'),'stored quaternion correction')
            actor,node,key,component,step=[row[k] for k in ('actor','node','key_index','component','step')]
            if (not isinstance(actor,str) or actor not in base.actors or type(node) is not int
                    or type(key) is not int or type(component) is not int or not 0<=component<4
                    or type(step) is not int or step not in (-1,1)):
                raise ValueError('Existing actor/native rotation key and one signed component step required')
            matches=[e for e in base.actors[actor]['tracks'] if (e['node'],e['path'])==(node,'rotation')]
            if len(matches)!=1 or key not in matches[0]['ids']:
                raise ValueError('Correction lies outside existing editable rotation keys')
            identity=(actor,node,key,component)
            if identity in seen:raise ValueError('Duplicate correction would exceed one-neighbor envelope')
            seen.add(identity)
        self.base=base;self.policy=copy.deepcopy(policy);self.corrections=copy.deepcopy(corrections)

    def __getattr__(self,name):return getattr(self.base,name)

    def values(self,name,value,*,quantized=True):
        value=self.base.controls(value)
        if np.any(value<self.base.lower) or np.any(value>self.base.upper):
            raise ValueError('Original control boxes remain required')
        values=self.base.values(name,value,quantized=quantized)
        if not quantized:return values  # Intended continuous curve; not a derivative of discrete corrections.
        for row in self.corrections:
            if row['actor']!=name:continue
            key=(row['node'],'rotation');index=row['key_index'];component=row['component']
            nearest=np.float32(values[key][index,component])
            neighbor=np.nextafter(nearest,np.float32(np.inf if row['step']>0 else -np.inf))
            if not np.isfinite(neighbor):raise ValueError('Finite neighboring quaternion component required')
            values[key][index,component]=float(neighbor)
        for entry in self.base.actors[name]['tracks']:
            output=values[entry['node'],entry['path']]
            if entry['path']=='rotation':
                if np.any(abs(np.linalg.norm(output,axis=1)-1)>4*np.finfo(np.float32).eps):
                    raise ValueError('Near-unit stored quaternion population required')
                maximum=np.rad2deg((Rotation.from_quat(entry['source']).inv()*Rotation.from_quat(output)).magnitude()).max()
            else:maximum=np.linalg.norm(output-entry['source'],axis=1).max()
            if maximum>entry['maximum']:
                raise ValueError('Stored adjustment exceeds original strict track bound')
        return values

    def worlds(self,name,value,times,*,quantized=True):
        return SceneEdits.worlds(self,name,value,times,quantized=quantized)

    def export(self,name,value,path):
        if Path(path).exists():raise ValueError('Fresh storage-adjusted asset path required')
        SceneEdits.export(self,name,value,path)

    def audit(self,name,path,animation_index,*,value):
        report=self.base.audit(name,path,animation_index)
        rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,animation_index)
        actual={(node,track):data for node,track,clock,data,mode in sampler.channels}
        for key,expected in self.values(name,value).items():
            if key not in actual or not np.array_equal(actual[key],expected):
                raise ValueError('Stored payload differs from explicit one-neighbor corrections')
        report.update(storage_adjustment=copy.deepcopy(self.policy),corrections=copy.deepcopy(self.corrections),
            one_neighbor_payload_verified=True,
            native_conditions_assessed=False,geometry_assessed=False,quality_approved=False,release_approved=False)
        return report

    def append_candidate(self,name,value,output,label):
        output=Path(output)
        if output.exists() or not isinstance(label,str) or not 1<=len(label)<=160:
            raise ValueError('Fresh appended asset and explicit clip label required')
        actor=self.base.scene.actors[name];original=actor['rig']
        with tempfile.TemporaryDirectory() as folder:
            probe=Path(folder)/'adjusted.glb';self.export(name,value,probe)
            if not self.audit(name,probe,actor['animation_index'],value=value)['passed']:
                raise ValueError('Stored candidate exceeds original authoring bounds')
            changed=RigAsset.load(probe);doc=copy.deepcopy(changed.document)
            variant=copy.deepcopy(doc['animations'][actor['animation_index']]);variant['name']=label
            doc['animations'][actor['animation_index']]=copy.deepcopy(original.document['animations'][actor['animation_index']])
            index=len(doc['animations']);doc['animations'].append(variant)
            if doc['animations'][:-1]!=original.document['animations'] or changed.binary[:len(original.binary)]!=original.binary:
                raise ValueError('Original animation library or binary prefix changed')
            output.parent.mkdir(parents=True,exist_ok=True);write_glb(output,doc,changed.binary)
        return index
