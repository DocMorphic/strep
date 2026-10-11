"""Selected SOMA30 channels in the existing unchanged checkpoint condition format."""
import torch
from kimodo.constraints import EndEffectorConstraintSet
from generation_constraints import SELECTABLE_JOINTS, validate_selected_joints


class SelectedJointConstraintSet(EndEffectorConstraintSet):
    name = 'joint-set'

    def __init__(self, skeleton, frame_indices, global_joints_positions,
                 global_joints_rots, smooth_root_2d=None, *, joint_names, to_crop=False):
        validate_selected_joints(joint_names)
        if tuple(skeleton.bone_order_names) != SELECTABLE_JOINTS:
            raise ValueError('Selected joint guides require the declared SOMA30 skeleton/order')
        # The upstream constructor supplies the common root/heading channels and
        # cropping behavior. Its chain expansion only understands EE groups, so
        # initialize with the valid pelvis group, then replace its channel masks
        # with exact selected indices. The skeleton and upstream code stay intact.
        super().__init__(skeleton, frame_indices, global_joints_positions,
                         global_joints_rots, smooth_root_2d,
                         joint_names=['Hips'], to_crop=to_crop)
        self.joint_names = list(joint_names)
        self.pos_indices = torch.tensor([skeleton.bone_index[j] for j in joint_names])
        self.rot_indices = self.pos_indices.clone()
