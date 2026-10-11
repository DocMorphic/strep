"""Explicit corrected-key starts that keep the original scene/edit reference.

Payload identity is checked here. The optimizer still decides native/contact
feasibility and complete geometry; loading a state grants no motion approval.
"""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from native_scene_contacts import fields
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest
from strep import sha256

SCHEMA='strep-native-storage-continuation-v1'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def state_for(base,policy,value,corrections,files):
    """Bind each edited actor's exact corrected export, not a new source epoch."""
    adjusted=StorageAdjustedEdits(base,policy,corrections);value=base.controls(value)
    if not isinstance(files,dict) or set(files)!=set(base.actors):
        raise ValueError('One existing corrected asset for every edited actor required')
    base.scene.check_inputs();actors={}
    for name,file in files.items():
        path=Path(file).resolve();index=base.scene.actors[name]['animation_index']
        checksum=sha256(path)
        if not adjusted.audit(name,path,index,value=value)['passed']:
            raise ValueError('Corrected continuation exceeds original authoring bounds')
        if sha256(path)!=checksum:raise ValueError('Corrected continuation changed during binding')
        actors[name]=dict(path=str(path),sha256=checksum,animation_index=index)
    base.scene.check_inputs()
    return dict(schema=SCHEMA,authoring_sha256=authoring_digest(base),
        source_assets_sha256=copy.deepcopy(base.scene.inputs),storage_policy_sha256=fingerprint(policy),
        controls=value.tolist(),corrections=copy.deepcopy(corrections),actors=actors)


class StorageContinuationEdits(StorageAdjustedEdits):
    def __init__(self,base,policy,state,directory):
        fields(state,('schema','authoring_sha256','source_assets_sha256','storage_policy_sha256',
            'controls','corrections','actors'),'storage continuation')
        if (state['schema']!=SCHEMA or state['authoring_sha256']!=authoring_digest(base)
                or state['storage_policy_sha256']!=fingerprint(policy)
                or state['source_assets_sha256']!=base.scene.inputs):
            raise ValueError('Continuation must retain the exact original authoring/scene/storage policy')
        controls=state['controls']
        if not isinstance(controls,list) or any(type(v) not in (int,float) for v in controls):
            raise ValueError('Explicit finite numeric continuation controls required')
        value=base.controls(controls)
        if np.any(value<base.lower) or np.any(value>base.upper):
            raise ValueError('Continuation is outside original control boxes')
        super().__init__(base,policy,state['corrections'])
        if not isinstance(state['actors'],dict) or set(state['actors'])!=set(base.actors):
            raise ValueError('Complete edited-actor continuation population required')
        self.initial=value.copy();self.state=copy.deepcopy(state);self.state_sha256=fingerprint(state)
        self.continuation_inputs={};self.candidate_paths={}
        for name,actor in state['actors'].items():
            fields(actor,('path','sha256','animation_index'),'continuation actor')
            if (not isinstance(actor['path'],str) or not actor['path']
                    or type(actor['animation_index']) is not int
                    or actor['animation_index']!=base.scene.actors[name]['animation_index']):
                raise ValueError('Existing source-selected animation index required')
            path=(Path(directory)/actor['path']).resolve()
            if sha256(path)!=actor['sha256']:
                raise ValueError('Corrected continuation asset changed')
            if not self.audit(name,path,actor['animation_index'],value=value)['passed']:
                raise ValueError('Corrected continuation exceeds original authoring bounds')
            self.continuation_inputs[str(path)]=actor['sha256'];self.candidate_paths[name]=path
        self.check_continuation()

    def check_continuation(self):
        self.base.scene.check_inputs()
        if (fingerprint(self.state)!=self.state_sha256
                or authoring_digest(self.base)!=self.state['authoring_sha256']
                or fingerprint(self.policy)!=self.state['storage_policy_sha256']
                or self.corrections!=self.state['corrections']
                or not np.array_equal(self.initial,self.state['controls'])
                or self.base.scene.inputs!=self.state['source_assets_sha256']):
            raise ValueError('Continuation state or original reference changed')
        if any(sha256(path)!=digest for path,digest in self.continuation_inputs.items()):
            raise ValueError('Corrected continuation asset changed')
        return dict(state_sha256=self.state_sha256,original_scene_reference_retained=True,
            source_assets_sha256=copy.deepcopy(self.state['source_assets_sha256']),
            continuation_inputs_sha256=copy.deepcopy(self.continuation_inputs),
            native_conditions_assessed=False,geometry_assessed=False,original_selected=True,
            quality_approved=False,training_admitted=False,release_approved=False)
