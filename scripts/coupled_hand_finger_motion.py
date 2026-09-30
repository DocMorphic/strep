"""Compose existing native arm and finger controls before hierarchy evaluation.

This preserves the original arm reference and independent finger edit limits.
It adds a parameterization, not collision, motion-rate or contact approval.
"""
import copy
import numpy as np
from independent_hand_motion import actor_controls
from smooth_hand_proposal import SmoothIndependentHandProposal
from timed_rotation_edit import sampled_rotations
from paired_guarded_temporal import world_from_local
from gltf_tools import append_accessor, write_glb, local_matrix


class CoupledHandFingerMotion:
    def __init__(self, arm, finger):
        self.arm=arm;self.finger=finger
        oriented=arm.model;self.base=oriented.model;other=finger.model
        if set(self.base.nodes)&set(finger.nodes):raise ValueError('Disjoint arm and finger channels required')
        if not np.array_equal(self.base.times,other.times):raise ValueError('Identical evaluation clocks required')
        if self.base.parents!=other.parents or oriented.rig.joints!=finger.rig.joints:
            raise ValueError('Identical joint hierarchy required')
        np.testing.assert_array_equal([local_matrix(n) for n in oriented.rig.document['nodes']],
                                      [local_matrix(n) for n in finger.rig.document['nodes']])
        if [n.get('name') for n in oriented.rig.document['nodes']]!=[n.get('name') for n in finger.rig.document['nodes']]:
            raise ValueError('Matching node identities required')
        for node in finger.nodes:
            parent=finger.rig.parents[node]
            while parent>=0 and parent!=oriented.chain[-1]:parent=finger.rig.parents[parent]
            if parent!=oriented.chain[-1]:raise ValueError('Fingers must descend from the controlled hand')
        if self.base.channels.keys()!=other.channels.keys():raise ValueError('Matching rotation channel populations required')
        for node,(_,clock,q) in self.base.channels.items():
            np.testing.assert_array_equal(clock,other.channels[node][1])
            if node not in self.base.nodes:np.testing.assert_array_equal(q,other.channels[node][2])
        # A donor may contain different arm rotations, never a rebased finger,
        # translation, scale or unrelated-body baseline.
        np.testing.assert_array_equal(self.base.local[:,:,:3,3],other.local[:,:,:3,3])
        for node in self.base.scales:np.testing.assert_array_equal(self.base.scales[node],other.scales[node])
        untouched=[n for n in range(len(self.base.parents)) if n not in self.base.nodes]
        np.testing.assert_array_equal(self.base.local[:,untouched],other.local[:,untouched])
        self.smooth=SmoothIndependentHandProposal(oriented.rig,oriented.chain,oriented.native,oriented.times,
            self.base.protected,oriented.placement,arm.actor)
        self.entries=self.base.entries+other.entries
        self.channels=[e['node'] for e in self.entries]

    def quaternions(self, arm_controls, finger_controls, *, quantize=True):
        mapped=actor_controls(arm_controls,self.arm.count,self.arm.actor)
        engine=self.arm.model if quantize else self.smooth.model
        values,maximum=engine.quaternions_vector(mapped)
        values.update(self.finger.model.quaternions(finger_controls,quantize=quantize))
        return values,maximum

    def evaluate(self, arm_controls, finger_controls, *, quantize=True):
        values,maximum=self.quaternions(arm_controls,finger_controls,quantize=quantize)
        if all(np.array_equal(values[node],self.base.channels[node][2]) for node in self.channels):
            return self.base.source_world.copy(),maximum
        local=self.base.local.copy()
        for entry in self.entries:
            node=entry['node']
            # Leave unchanged local channels exact, including common samplers.
            if np.array_equal(values[node],self.base.channels[node][2]):continue
            local[:,node,:3,:3]=sampled_rotations(entry['clock'],values[node],self.base.times)*self.base.scales[node][:,None,:]
        return world_from_local(local,self.base.parents),maximum

    def export(self, arm_controls, finger_controls, path):
        vectors=np.asarray(finger_controls,float)
        if vectors.shape!=(self.finger.size,) or not np.isfinite(vectors).all():raise ValueError('Finite matching finger controls required')
        if np.any(np.linalg.norm(vectors.reshape(-1,3),axis=1)>self.finger.limits):raise ValueError('Original per-finger edit limits exceeded')
        values,maximum=self.quaternions(arm_controls,vectors)
        if maximum>45.+1e-4:raise ValueError('Original native arm edit budget exceeded')
        document=copy.deepcopy(self.base.document);binary=bytearray(self.base.binary);animation=document['animations'][0]
        for channel in animation['channels']:
            node=channel['target']['node']
            if channel['target']['path']=='rotation' and node in values:
                sampler=copy.deepcopy(animation['samplers'][channel['sampler']])
                sampler['output']=append_accessor(document,binary,values[node],'VEC4')
                channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
        write_glb(path,document,binary)
