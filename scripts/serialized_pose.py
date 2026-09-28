"""In-memory evaluation of rig_loop.encode's float32 TRS animation keys.

This models this project's encoder, not arbitrary glTF serialization. It does
not change an asset or replace final file/engine validation.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import local_matrix
from rig_transition import localize, compose
from rig_clip_import import AnimationSampler


class SerializedPose:
    def __init__(self, rig, animated, root, frames):
        if type(frames) is not int or frames < 2:
            raise ValueError('At least two 30fps animation frames required')
        self.parents = rig.parents
        self.animated = sorted(set(animated) | {root})
        if any(type(n) is not int or not 0 <= n < len(self.parents) for n in self.animated):
            raise ValueError('Invalid animated node')
        self.reference = np.array([local_matrix(n) for n in rig.document['nodes']])
        self.times = np.arange(frames, dtype=np.float32)/30

    def channels(self, world):
        world = np.asarray(world, float)
        if world.shape != self.reference.shape or not np.isfinite(world).all():
            raise ValueError('One finite full-node world pose required')
        local = localize(world[None], self.parents)[0]
        translation = local[self.animated, :3, 3].astype('<f4').astype(float)
        rotation = Rotation.from_matrix(local[self.animated, :3, :3]).as_quat().astype('<f4').astype(float)
        return translation, rotation

    def from_channels(self, translation, rotation):
        local = self.reference.copy()
        rotation = rotation/np.linalg.norm(rotation, axis=1)[:, None]
        local[self.animated, :3, 3] = translation
        # prepare_animated_node in the encoder resets animated scale to one.
        local[self.animated, :3, :3] = Rotation.from_quat(rotation).as_matrix()
        return compose(local[None], self.parents)[0]

    def pose(self, world):
        return self.from_channels(*self.channels(world))

    def half_pose(self, left_world, right_world, left_frame):
        if type(left_frame) is not int or not 0 <= left_frame < len(self.times)-1:
            raise ValueError('Invalid adjacent frame pair')
        lt, lq = self.channels(left_world)
        rt, rq = self.channels(right_world)
        times = self.times[left_frame:left_frame+2]
        time = (left_frame+.5)/30
        translations, rotations = [], []
        for i in range(len(self.animated)):
            translations.append(AnimationSampler.value('translation', times, np.array([lt[i], rt[i]]), 'LINEAR', time))
            rotations.append(AnimationSampler.value('rotation', times, np.array([lq[i], rq[i]]), 'LINEAR', time))
        return self.from_channels(np.asarray(translations), np.asarray(rotations))
