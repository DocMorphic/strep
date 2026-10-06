"""Source-bound smooth proposal curve centered on a verified stored clip.

Frozen key offsets include rounding and explicit storage corrections. Only the
unrounded proposal curve changes; exports and original acceptance stay intact.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.spatial.transform import Rotation
from paired_guarded_temporal import world_from_local
from native_rotation_storage_repair import StorageAdjustedEdits
from native_scene_edit import SceneEdits
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import sha256


class StoredCurveProxy:
    def __init__(self, base, anchor, files):
        if not isinstance(base, StorageAdjustedEdits) or not isinstance(files, dict) or set(files)!=set(base.actors):
            raise ValueError('Explicit storage editor and every edited actor export required')
        anchor=base.controls(anchor).copy()
        if np.any(anchor<base.lower) or np.any(anchor>base.upper):
            raise ValueError('Anchor must remain in original authoring boxes')
        self.base=base;self.anchor=anchor;self.anchor.setflags(write=False)
        self.files={n:Path(p).resolve() for n,p in files.items()}
        self.hashes={n:sha256(p) for n,p in self.files.items()};self.offsets={};self.stored={}
        base.scene.check_inputs()
        for name,path in self.files.items():
            index=base.scene.actors[name]['animation_index']
            if not base.audit(name,path,index,value=anchor)['passed']:
                raise ValueError('Verified exact storage-adjusted anchor payload required')
            rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index)
            actual={(node,track):payload for node,track,clock,payload,mode in reader.channels}
            continuous=base.values(name,anchor,quantized=False);nearest=base.values(name,anchor)
            self.offsets[name]={};self.stored[name]={}
            for key,values in continuous.items():
                target=actual[key].astype(float).copy()
                if not np.array_equal(target,nearest[key]) or target.shape!=values.shape:
                    raise ValueError('Stored anchor differs from declared storage payload')
                offset=target-values
                if not np.isfinite(offset).all():raise ValueError('Finite complete stored offsets required')
                entry=next(e for e in base.actors[name]['tracks'] if (e['node'],e['path'])==key)
                frozen=np.ones(len(offset),bool);frozen[entry['ids']]=False
                if np.any(offset[frozen]!=0):raise ValueError('Proxy offsets cannot alter protected keys')
                offset.setflags(write=False);target.setflags(write=False)
                self.offsets[name][key]=offset;self.stored[name][key]=target
        self.editor_binding=self._binding();self._check()

    def __getattr__(self,name):return getattr(self.base,name)

    def _binding(self):
        tracks={n:[dict(node=e['node'],path=e['path'],unit=float(e['unit']),maximum=e['maximum'],
            **{k:e[k].tolist() for k in ('clock','source','ids','weights','controls')}) for e in a['tracks']]
            for n,a in self.base.actors.items()}
        state=dict(request=self.base.request,policy=self.base.policy,corrections=self.base.corrections,
            lower=self.base.lower.tolist(),upper=self.base.upper.tolist(),tracks=tracks,
            storage_mode=self.base.rotation_storage_policy)
        return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def _check(self):
        self.base.scene.check_inputs()
        if self._binding()!=self.editor_binding:raise ValueError('Stored proxy editor contract changed; rebuild proxy')
        if any(sha256(p)!=self.hashes[n] for n,p in self.files.items()):
            raise ValueError('Stored proxy anchor bytes changed')

    def values(self,name,value,*,quantized=True):
        if type(quantized) is not bool:raise ValueError('Explicit Boolean storage mode required')
        self._check();value=self.base.controls(value)
        result=self.base.values(name,value,quantized=quantized)
        if quantized:return result
        if np.array_equal(value,self.anchor):return {k:v.copy() for k,v in self.stored[name].items()}
        return {k:v+self.offsets[name][k] for k,v in result.items()}

    def worlds(self,name,value,times,*,quantized=True):
        if type(quantized) is not bool:raise ValueError('Explicit Boolean storage mode required')
        if quantized:
            self._check();return self.base.worlds(name,value,times,quantized=True)
        values=self.values(name,value,quantized=False);times=np.asarray(times,float)
        if times.ndim!=1 or not np.isfinite(times).all():raise ValueError('Finite one-dimensional sample clock required')
        actor=self.actors[name]['source'];cache=self.actors[name]['world_cache'];key=tuple(times)
        if key not in cache:self.base.worlds(name,value,times,quantized=True)
        _,original=cache[key];local=original.copy()
        for entry in self.actors[name]['tracks']:
            node,path=entry['node'],entry['path'];payload=values[node,path]
            sampled=np.array([NativeSupportSampler.value(path,entry['clock'],payload,'LINEAR',float(t)) for t in times])
            if path=='rotation':
                scales=np.linalg.norm(original[:,node,:3,:3],axis=1)
                local[:,node,:3,:3]=Rotation.from_quat(sampled).as_matrix()*scales[:,None,:]
            else:local[:,node,:3,3]=sampled
        return world_from_local(local,actor['rig'].parents)

    def export(self,name,value,path):
        self._check();return self.base.export(name,value,path)

    def audit(self,name,path,index,*,value):
        self._check();return self.base.audit(name,path,index,value=value)

    def append_candidate(self,name,value,path,label):
        self._check();return self.base.append_candidate(name,value,path,label)
