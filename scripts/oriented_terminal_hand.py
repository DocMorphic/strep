"""One-key arm controls with independent intermediate hand orientations."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from continuous_terminal_hand import VectorTerminalMotion
from two_bone_waypoint import reach
from elbow_swivel import local_transforms
from timed_rotation_edit import sampled_rotations
from paired_guarded_temporal import world_from_local
from gltf_tools import append_accessor,write_glb


class OrientedTerminalMotion(VectorTerminalMotion):
    def quaternions_vector(self,controls):
        controls=np.asarray(controls,float)
        if controls.shape!=(11,) or not np.isfinite(controls).all():raise ValueError('Eleven finite wrist/elbow/hand controls required')
        model=self.model;values={e['node']:e['source'].astype(float).copy() for e in model.entries}
        hand=controls[5+3*self.actor:8+3*self.actor]
        if np.any(controls[:3]) or controls[3+self.actor]!=0 or np.any(hand):
            world=self.key_world[0];offset=controls[:3]*(1 if self.actor==0 else -1)
            arm_changed=bool(np.any(offset) or controls[3+self.actor]!=0)
            if arm_changed:
                moved,local=reach(world,self.rig.parents,*self.chain,world[self.chain[-1],:3,3]+offset@self.placement,
                                  np.deg2rad(controls[3+self.actor]))
            else:moved=world;local=local_transforms(world,self.rig.parents)
            if np.any(hand):
                # Hand deltas are world-scene rotation vectors in degrees.
                delta=self.placement.T@Rotation.from_rotvec(np.deg2rad(hand)).as_matrix()@self.placement
                local[self.chain[-1],:3,:3]=moved[self.chain[-2],:3,:3].T@delta@world[self.chain[-1],:3,:3]
            quaternions=Rotation.from_matrix(local[self.chain,:3,:3]).as_quat()
            for number,entry in enumerate(model.entries):
                if not arm_changed and entry['node']!=self.chain[-1]:continue
                key=entry['ids'][0];q=quaternions[number]
                if q@entry['source'][key]<0:q=-q
                values[entry['node']][key]=q.astype(np.float32)
        maximum=max(float(np.rad2deg((Rotation.from_quat(e['source']).inv()*Rotation.from_quat(values[e['node']])).magnitude()).max()) for e in model.entries)
        return values,maximum

    def evaluate_vector(self,controls):
        values,maximum=self.quaternions_vector(controls);model=self.model
        if all(np.array_equal(values[e['node']],e['source']) for e in model.entries):return model.source_world.copy(),maximum
        local=model.local.copy()
        for entry in model.entries:
            node=entry['node'];local[:,node,:3,:3]=sampled_rotations(entry['clock'],values[node],self.times)*model.scales[node][:,None,:]
        return world_from_local(local,model.parents),maximum

    def export_vector(self,controls,path):
        values,maximum=self.quaternions_vector(controls)
        if maximum>45.+1e-4:raise ValueError('Native orientation edit budget exceeded')
        doc=copy.deepcopy(self.rig.document);binary=bytearray(self.rig.binary);animation=doc['animations'][0]
        for channel in animation['channels']:
            node=channel['target']['node']
            if channel['target']['path']=='rotation' and node in values:
                sampler=copy.deepcopy(animation['samplers'][channel['sampler']])
                sampler['output']=append_accessor(doc,binary,values[node],'VEC4')
                channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
        write_glb(path,doc,binary)


def support_clock(times,native):
    times,native=np.asarray(times,float),np.asarray(native,float)
    if times.ndim!=1 or native.shape!=(3,) or not np.isfinite(times).all() or not np.isfinite(native).all() or np.any(np.diff(times)<=0) or np.any(np.diff(native)<=0):
        raise ValueError('Increasing finite sample clock and three native keys required')
    before=np.flatnonzero(times<native[0])[-2:];inside=np.flatnonzero((times>=native[0])&(times<native[-1]));after=np.flatnonzero(times>=native[-1])[:2]
    if len(before)!=2 or len(after)!=2 or len(inside)<4:raise ValueError('Complete support and two frozen halo samples on each side required')
    ids=np.r_[before,inside,after]
    if np.any(np.diff(ids)!=1):raise ValueError('Contiguous support required')
    return inside,ids
