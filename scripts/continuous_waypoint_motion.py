"""Batch replay of continuously authored wrist/swivel keys, quantized as GLB."""
import numpy as np
from scipy.spatial.transform import Rotation
from timed_rotation_edit import TimedRotationEdit,sampled_rotations
from paired_guarded_temporal import world_from_local
from rig_clip_import import AnimationSampler
from two_bone_waypoint import reach


class ContinuousWaypointMotion:
    def __init__(self,rig,chain,native,times,protected,placement,axis,actor):
        self.rig=rig;self.chain=chain;self.native=np.asarray(native,float);self.times=np.asarray(times,float)
        self.placement=np.asarray(placement,float);self.axis=np.asarray(axis,float);self.actor=actor
        if actor not in [0,1] or self.axis.shape!=(3,) or not np.isfinite(self.axis).all() or abs(np.linalg.norm(self.axis)-1)>1e-12:
            raise ValueError('Two-actor unit-axis waypoint required')
        if self.placement.shape!=(3,3) or not np.isfinite(self.placement).all() or not np.allclose(self.placement@self.placement.T,np.eye(3),atol=1e-10) or np.linalg.det(self.placement)<0:
            raise ValueError('Rigid placement required')
        names=[rig.document['nodes'][n]['name'] for n in chain]
        self.model=TimedRotationEdit(rig.document,rig.binary,names,times,self.native[[0,-1]],protected,
            knots=self.native,limit_degrees=45)
        for entry in self.model.entries:
            np.testing.assert_array_equal(entry['clock'][entry['ids']],self.native[1:-1])
        reader=AnimationSampler(rig.document,rig.binary,0)
        self.key_world=[reader.sample(t) for t in self.native[1:-1]]

    def evaluate(self,parameters):
        parameters=np.asarray(parameters,float)
        if parameters.shape!=(len(self.native),3) or not np.isfinite(parameters).all() or np.any(parameters[[0,-1]]):
            raise ValueError('Finite matching waypoint controls with zero endpoints required')
        model=self.model;values={e['node']:e['source'].astype(float).copy() for e in model.entries}
        for index,(world,controls) in enumerate(zip(self.key_world,parameters[1:-1])):
            if controls[0]==0 and controls[self.actor+1]==0:continue
            offset=self.axis*controls[0]*(1 if self.actor==0 else -1)
            _,local=reach(world,self.rig.parents,*self.chain,world[self.chain[-1],:3,3]+offset@self.placement,np.deg2rad(controls[self.actor+1]))
            quaternions=Rotation.from_matrix(local[self.chain,:3,:3]).as_quat()
            for number,entry in enumerate(model.entries):
                key=entry['ids'][index];q=quaternions[number]
                if q@entry['source'][key]<0:q=-q
                values[entry['node']][key]=q.astype(np.float32)
        maximum=max(float(np.rad2deg((Rotation.from_quat(e['source']).inv()*Rotation.from_quat(values[e['node']])).magnitude()).max()) for e in model.entries)
        if all(np.array_equal(values[e['node']],e['source']) for e in model.entries):return model.source_world.copy(),maximum
        local=model.local.copy()
        for entry in model.entries:
            node=entry['node'];rotations=sampled_rotations(entry['clock'],values[node],self.times)
            local[:,node,:3,:3]=rotations*model.scales[node][:,None,:]
        return world_from_local(local,model.parents),maximum
