"""Bounded spline IK seed for a grip transported in an object's moving frame.

This objective fits joint frames, not skin contact or physical interaction.
All edits stay relative to the original clip; root translation is unchanged.
"""
import numpy as np
import torch
from scene_fit_initialization import recover_controls
from support_contact_v5 import rodrigues
from support_contact_v8 import bounded_edit_rotations
from floor_contact import reconstruct
from localized_spline import localized_controls


def transport_frames(positions, rotations, reference, guide_positions, guide_rotations):
    positions, rotations = np.asarray(positions), np.asarray(rotations)
    if positions.ndim != 2 or positions.shape[1] != 3 or rotations.shape != (len(positions), 3, 3):
        raise ValueError('Matching object position and rotation tracks required')
    if type(reference) != int or not 0 <= reference < len(positions):
        raise ValueError('Reference frame outside object track')
    relative_p = (np.asarray(guide_positions)-positions[reference]) @ rotations[reference]
    relative_r = rotations[reference].T @ np.asarray(guide_rotations)
    return (positions[:, None] + np.einsum('fij,hj->fhi', rotations, relative_p),
            rotations[:, None] @ relative_r[None])


def fit_frames(source, seed, parents, editable, limits, body_count, basis,
               target_joints, target_positions, target_rotations, weights,
               iterations=100, progress=None, edit_window=None):
    if type(iterations) != int or not 1 <= iterations <= 300:
        raise ValueError('Iteration count must be between 1 and 300')
    frames = len(source['root_positions'])
    weights = np.asarray(weights)
    if weights.shape != (frames,) or not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
        raise ValueError('Positive finite frame weights required')
    if np.shape(target_positions) != (frames, len(target_joints), 3) or np.shape(target_rotations) != (frames, len(target_joints), 3, 3):
        raise ValueError('Target joint frame layout mismatch')
    if not np.isfinite(target_positions).all() or not np.isfinite(target_rotations).all():
        raise ValueError('Finite targets required')
    controls, _ = recover_controls(source['local_rot_mats'], seed['local_rot_mats'], editable, limits, body_count, True, basis)
    tensor = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float64)
    offsets = np.zeros_like(source['posed_joints'], dtype=float)
    for j, p in enumerate(parents):
        if p >= 0:
            offsets[:, j] = np.einsum('fji,fj->fi', source['global_rot_mats'][:, p], source['posed_joints'][:, j]-source['posed_joints'][:, p])
    offsets, initial, root = tensor(offsets), tensor(source['local_rot_mats']), tensor(source['root_positions'])
    spline, caps = tensor(basis), tensor(limits)[None, :, None]
    target_p, target_r, weight = tensor(target_positions), tensor(target_rotations), tensor(weights)
    localization=None;control_transform=None;seed_controls=None;outside=None
    if edit_window is None:
        delta = tensor(controls).clone().requires_grad_()
    else:
        if not np.array_equal(seed['root_positions'],source['root_positions']):
            raise ValueError('Localized fitting requires matching seed and source root tracks')
        transform,outside,localization=localized_controls(basis,edit_window)
        control_transform=tensor(transform);seed_controls=tensor(controls)
        delta=torch.zeros((transform.shape[1],len(editable),3),dtype=torch.float64,requires_grad=True)
    lookup = {j: i for i, j in enumerate(editable)}

    def state():
        full_controls=delta if control_transform is None else seed_controls+torch.einsum('kr,rjd->kjd',control_transform,delta)
        values = torch.einsum('fk,kjd->fjd', spline, full_controls)
        vectors = bounded_edit_rotations(values, caps, body_count, True)
        changes = rodrigues(vectors)
        rotations, positions, locals_ = [], [], []
        for j, p in enumerate(parents):
            local = initial[:, j] if j not in lookup else initial[:, j] @ changes[:, lookup[j]]
            locals_.append(local)
            rotations.append(local if p < 0 else rotations[p] @ local)
            positions.append(root if p < 0 else positions[p]+(rotations[p] @ offsets[:, j, :, None]).squeeze(-1))
        return torch.stack(positions, 1), torch.stack(rotations, 1), torch.stack(locals_, 1), vectors

    history = []
    optimizer = torch.optim.LBFGS([delta], max_iter=iterations, line_search_fn='strong_wolfe', tolerance_grad=1e-10, tolerance_change=1e-12)

    def closure():
        optimizer.zero_grad()
        p, r, _, vectors = state()
        # A 10 cm orientation lever balances radians and positional metres.
        point = ((p[:, target_joints]-target_p).square().sum(-1).mean(-1)*weight).sum()/weight.sum()
        orient = ((r[:, target_joints]-target_r).square().sum((-1, -2)).mean(-1)*weight).sum()/weight.sum()
        pose = vectors.square().mean()
        temporal = torch.diff(vectors, n=2, dim=0).square().mean()
        loss = point + .01*orient + 1e-6*pose + .001*temporal
        loss.backward()
        if not torch.isfinite(loss) or not torch.isfinite(delta.grad).all():
            raise ValueError('Nonfinite IK objective or gradient')
        if len(history) % 20 == 0 and progress:
            progress(dict(evaluation=len(history), position_loss=float(point.detach()), orientation_loss=float(orient.detach())))
        history.append(float(loss.detach()))
        return loss

    optimizer.step(closure)
    with torch.no_grad():
        p, r, local, _ = state()
        errors = torch.linalg.vector_norm(p[:, target_joints]-target_p, dim=-1).numpy()
    result = reconstruct(source, local.detach().numpy(), parents)
    _, proof = recover_controls(source['local_rot_mats'], result['local_rot_mats'], editable, limits, body_count, True, basis)
    if localization is not None:
        from scipy.spatial.transform import Rotation
        relative=seed['local_rot_mats'][outside].transpose(0,1,3,2)@result['local_rot_mats'][outside]
        error=float(Rotation.from_matrix(relative.reshape(-1,3,3)).magnitude().max()) if outside.any() else 0.
        if error>1e-6:raise ValueError('Unselected seed rotations changed')
        localization['maximum_outside_seed_rotation_error_rad']=error
    return result, dict(localization=localization,evaluations=len(history), objective_history=history,
        target_joint_ids=target_joints, maximum_active_joint_position_error_m=float(errors[weights > 0].max()),
        reconstruction=proof, root_unchanged=bool(np.array_equal(result['root_positions'], source['root_positions'])),
        quality_approved=False, scope='Object-relative joint-frame initializer; no skin-contact, collision, temporal-quality or dynamics acceptance.')
