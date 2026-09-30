"""Exact float32 native arm keys sampled by the regular GLB decoder per edge."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from elbow_swivel import local_transforms
from two_bone_waypoint import reach
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from sampled_motion_caps import features


class DecodedEdges:
    def __init__(self,sources,native,times,states,axis,caps):
        self.sources=sources;self.native=np.asarray(native);self.times=np.asarray(times)
        self.states=np.asarray(states);self.axis=np.asarray(axis);self.caps=caps;self.pose_cache={}
        self.reference=[]
        for source in sources:
            rig=source['rig'];source['sampler']=AnimationSampler(rig.document,rig.binary,0)
            source['channels']=rotation_channels(rig.document,rig.binary)
            source['native_ids']=[]
            for node in source['chain']:
                clock=source['channels'][node][1];ids=np.searchsorted(clock,self.native)
                if np.any(ids>=len(clock)) or not np.array_equal(clock[ids],self.native):raise ValueError('Matching native edge keys required')
                source['native_ids'].append(ids)
            self.reference.append(np.array([source['sampler'].sample(t) for t in times]))
        self.source_payload=self.combine(self.reference,np.arange(len(times)))
        self.prefix=self.slice(self.source_payload,np.flatnonzero(times<native[0])[-2:])
        self.suffix=self.slice(self.source_payload,np.flatnonzero(times>=native[-1])[:2])
        if len(self.prefix['indices'])!=2 or len(self.suffix['indices'])!=2:raise ValueError('Two frozen halo samples on each side required')

    @staticmethod
    def slice(payload,indices):
        return {k:v[indices] for k,v in payload.items()}

    def combine(self,worlds,indices):
        parts=[features(w,s['rig'].joints) for w,s in zip(worlds,self.sources)]
        return dict(indices=np.asarray(indices),**{k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']})

    def pose(self,actor,node_time,state):
        key=(actor,node_time,state)
        if key in self.pose_cache:return self.pose_cache[key]
        source=self.sources[actor];chain=source['chain'];parameters=self.states[state]
        original=np.array([source['channels'][n][2][ids[node_time]] for n,ids in zip(chain,source['native_ids'])])
        if parameters[0]==0 and parameters[actor+1]==0:result=original
        else:
            world=source['sampler'].sample(float(self.native[node_time]))
            offset=self.axis*parameters[0]*(1 if actor==0 else -1)
            try:
                _,local=reach(world,source['rig'].parents,*chain,world[chain[-1],:3,3]+offset@source['rotation'],np.deg2rad(parameters[actor+1]))
            except ValueError as error:
                if 'outside two-bone reach' not in str(error):raise
                self.pose_cache[key]=None;return None
            before=local_transforms(world,source['rig'].parents)
            maximum=np.rad2deg((Rotation.from_matrix(before[:,:3,:3]).inv()*Rotation.from_matrix(local[:,:3,:3])).magnitude()).max()
            if maximum>45+1e-4:self.pose_cache[key]=None;return None
            result=Rotation.from_matrix(local[chain,:3,:3]).as_quat()
            result*=np.where(np.sum(result*original,axis=1)<0,-1,1)[:,None]
            result=result.astype(np.float32)
        self.pose_cache[key]=result;return result

    def decode(self,layer,start,end):
        """Return raw decoded worlds before any motion or geometry predicate."""
        ids=np.flatnonzero((self.times>=self.native[layer])&(self.times<self.native[layer+1]))
        if len(ids)<2:raise ValueError('At least two uniform samples per native interval required')
        worlds=[]
        for actor,source in enumerate(self.sources):
            first=self.pose(actor,layer,start);last=self.pose(actor,layer+1,end)
            if first is None or last is None:return None
            if not np.any(self.states[start]) and not np.any(self.states[end]):
                worlds.append(self.reference[actor][ids]);continue
            reader=copy.copy(source['sampler']);reader.channels=[]
            for node,path,clock,values,mode in source['sampler'].channels:
                if path=='rotation' and node in source['chain']:
                    if mode!='LINEAR':raise ValueError('Linear native arm interpolation required')
                    number=source['chain'].index(node);keys=source['native_ids'][number]
                    values=values.copy();values[keys[layer]]=first[number];values[keys[layer+1]]=last[number]
                reader.channels.append((node,path,clock,values,mode))
            worlds.append(np.array([reader.sample(t) for t in self.times[ids]]))
        return ids,worlds

    def __call__(self,layer,start,end):
        decoded=self.decode(layer,start,end)
        if decoded is None:return None
        ids,worlds=decoded;payload=self.combine(worlds,ids)
        return payload if self.caps.check(payload) else None
