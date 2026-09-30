"""Double-precision proposal poses; actual serialized motion remains the gate.

The native-key construction matches oriented_terminal_hand, but does not round
edited quaternion components to float32. Keep this separate from the bound
editor so old control meanings, export paths and recorded studies stay intact.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from oriented_terminal_hand import OrientedTerminalMotion
from independent_hand_motion import IndependentHandMotion, SYMMETRIC_LAYOUT, INDEPENDENT_LAYOUT
from two_bone_waypoint import reach
from elbow_swivel import local_transforms


class SmoothOrientedHandProposal(OrientedTerminalMotion):
    def quaternions_vector(self, controls):
        controls = np.asarray(controls, float); count = len(self.native)-2
        if controls.shape != (11*count,) or not np.isfinite(controls).all():
            raise ValueError('Eleven finite controls per editable native key required')
        model = self.model
        values = {entry['node']: entry['source'].astype(float).copy() for entry in model.entries}
        for frame, control in enumerate(controls.reshape(count, 11)):
            hand = control[5+3*self.actor:8+3*self.actor]
            if not (np.any(control[:3]) or control[3+self.actor] != 0 or np.any(hand)): continue
            world = self.key_world[frame]; offset = control[:3]*(1 if self.actor == 0 else -1)
            arm_changed = bool(np.any(offset) or control[3+self.actor] != 0)
            if arm_changed:
                moved, local = reach(world, self.rig.parents, *self.chain,
                    world[self.chain[-1], :3, 3]+offset@self.placement, np.deg2rad(control[3+self.actor]))
            else:
                moved = world; local = local_transforms(world, self.rig.parents)
            if np.any(hand):
                delta = self.placement.T@Rotation.from_rotvec(np.deg2rad(hand)).as_matrix()@self.placement
                local[self.chain[-1], :3, :3] = moved[self.chain[-2], :3, :3].T@delta@world[self.chain[-1], :3, :3]
            quaternions = Rotation.from_matrix(local[self.chain, :3, :3]).as_quat()
            for number, entry in enumerate(model.entries):
                if not arm_changed and entry['node'] != self.chain[-1]: continue
                key = entry['ids'][frame]; quaternion = quaternions[number]
                if quaternion@entry['source'][key] < 0: quaternion = -quaternion
                values[entry['node']][key] = quaternion
        maximum = max(float(np.rad2deg((Rotation.from_quat(entry['source']).inv()
            * Rotation.from_quat(values[entry['node']])).magnitude()).max()) for entry in model.entries)
        return values, maximum

    def export_vector(self, controls, path):
        raise ValueError('Proposal precision is not an export or acceptance path; use the bound float32 editor')


class SmoothIndependentHandProposal(IndependentHandMotion):
    def __init__(self, rig, chain, native, times, protected, placement, actor):
        self.model = SmoothOrientedHandProposal(rig, chain, native, times, protected, placement, actor)
        self.actor = actor; self.count = len(native)-2


def proposal_type(name):
    if name == SYMMETRIC_LAYOUT: return SmoothOrientedHandProposal
    if name == INDEPENDENT_LAYOUT: return SmoothIndependentHandProposal
    raise ValueError('Unknown oriented hand control layout')
