"""Native SOMA target conversion and an explicit experimental clean-motion loss.

Numerical compatibility does not approve an example's quality or training rights.
No optimizer, training loop, data acquisition or automatic review is provided.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class FullNoiseSchedule:
    num_base_steps: int
    sqrt_alpha: torch.Tensor
    sqrt_one_minus_alpha: torch.Tensor


def capture_full_noise_schedule(diffusion):
    """Copy pristine full-schedule vendor coefficients before sampler respacing.

    Recomputing sqrt(base alpha) is mathematically equivalent but does not
    reproduce the pinned sampler's FP32 reconstruction/reciprocal operations.
    """
    steps = diffusion.num_base_steps
    if type(steps) is not int or steps < 2:
        raise ValueError('A full base schedule with at least two steps is required')
    fields = [getattr(diffusion, key, None) for key in (
        'alphas_cumprod_base', 'alphas_cumprod', 'sqrt_alphas_cumprod', 'sqrt_one_minus_alphas_cumprod')]
    for value in fields:
        _finite_float(value, (steps,), 'Diffusion coefficient table')
    base, current, clean, noise = fields
    if any(value.device != base.device for value in fields) or not torch.allclose(base, current, rtol=1e-5, atol=1e-9):
        raise ValueError('Capture a pristine full schedule, before any sampler respacing')
    if (base <= 0).any() or (base >= 1).any() or (clean <= 0).any() or (noise <= 0).any():
        raise ValueError('Invalid noise schedule coefficients')
    return FullNoiseSchedule(steps, clean.detach().clone(), noise.detach().clone())


def _finite_float(value, shape, name):
    if not isinstance(value, torch.Tensor) or value.dtype != torch.float32 or tuple(value.shape) != tuple(shape):
        raise ValueError(f'{name} must have FP32 shape {tuple(shape)}')
    if not torch.isfinite(value).all():
        raise ValueError(f'{name} must be finite')


def encode_native_target(motion_rep, local_rotations, root_positions, joint_names, fps):
    """Encode one native SOMA77 clip; retain heading, remove planar translation.

    Omitted joints must match Kimodo's relaxed default: arbitrary finger motion
    cannot be silently discarded. Geometric contacts are re-derived, not labels.
    """
    skeleton = motion_rep.skeleton
    if skeleton.name != 'somaskel30' or motion_rep.motion_rep_dim != 369 or motion_rep.fps != 30:
        raise ValueError('This target codec is restricted to pinned SOMA30 at 30 fps')
    if isinstance(fps, bool) or fps != 30:
        raise ValueError('Explicit source FPS must be 30; resample separately')
    full = skeleton.somaskel77
    if joint_names != full.bone_order_names:
        raise ValueError('Native SOMA77 joint order required; target rigs must be retargeted separately')
    if not isinstance(local_rotations, torch.Tensor) or local_rotations.ndim != 4:
        raise ValueError('Local rotations must be [frames,77,3,3]')
    count = len(local_rotations)
    if count < 2:
        raise ValueError('At least two frames required for finite differences')
    _finite_float(local_rotations, (count, 77, 3, 3), 'Local rotations')
    _finite_float(root_positions, (count, 3), 'Root positions')
    if local_rotations.device != root_positions.device:
        raise ValueError('Motion tensors must share a device')
    eye = torch.eye(3, device=local_rotations.device)
    if (local_rotations @ local_rotations.mT - eye).abs().max() > 1e-4 or (torch.linalg.det(local_rotations) - 1).abs().max() > 1e-4:
        raise ValueError('Proper orthonormal rotations required')
    subset = skeleton.from_SOMASkeleton77(local_rotations)
    expanded = skeleton.to_SOMASkeleton77(subset)
    omitted_error = float((expanded - local_rotations).abs().max())
    if omitted_error > 1e-4:
        raise ValueError('SOMA30 cannot represent the omitted joint/finger rotations in this clip')
    # The vendor decorator unbatches outputs when given unbatched inputs.
    raw = motion_rep(subset[None], root_positions[None], to_normalize=False, to_canonicalize=False,
                     lengths=torch.tensor([count], device=local_rotations.device))
    translation = raw[0, 0, :3].clone()
    translation[1] = 0
    centered = motion_rep.translate_2d_to_zero(raw)
    normalized = motion_rep.normalize(centered)
    heading = motion_rep.get_root_heading_angle(centered)[:, 0]
    if not torch.isfinite(normalized).all() or not torch.isfinite(heading).all():
        raise ValueError('Target encoding is nonfinite')
    decoded = motion_rep.inverse(normalized, is_normalized=True)
    decoded_full = skeleton.to_SOMASkeleton77(decoded['local_rot_mats'][0])
    restored_root = decoded['root_positions'][0] + translation
    _, restored_positions, _ = full.fk(decoded_full, restored_root)
    _, original_positions, _ = full.fk(local_rotations, root_positions)
    report = {
        'frames': count, 'fps': 30, 'feature_count': 369, 'source_skeleton': 'somaskel77',
        'feature_skeleton': 'somaskel30', 'root_channels': 5, 'body_channels': 364,
        'planar_translation_removed_m': translation.tolist(),
        'first_heading_radians': float(heading[0]), 'heading_rotated': False,
        'omitted_rotation_max_error': omitted_error,
        'roundtrip_local_rotation_max_error': float((decoded_full - local_rotations).abs().max()),
        'roundtrip_root_max_error_m': float((restored_root - root_positions).abs().max()),
        'roundtrip_joint_max_error_m': float((restored_positions - original_positions).norm(dim=-1).max()),
        'contact_provenance': 'recomputed native pose/velocity heuristic; not independently reviewed',
        'quality_approved': False, 'training_rights_verified': False,
    }
    return normalized.detach(), heading.detach(), report


def noisy_target(clean, noise, timesteps, diffusion):
    """Use captured original coefficients, independent of sampler respacing."""
    if not isinstance(diffusion, FullNoiseSchedule):
        raise ValueError('Capture the pristine full noise schedule first')
    if not isinstance(clean, torch.Tensor) or clean.ndim != 3:
        raise ValueError('Clean target must be [batch,frames,features]')
    _finite_float(clean, clean.shape, 'Clean target')
    _finite_float(noise, clean.shape, 'Noise')
    if noise.device != clean.device:
        raise ValueError('Noise and clean target must share a device')
    if not isinstance(timesteps, torch.Tensor) or timesteps.dtype != torch.int64 or timesteps.shape != (len(clean),):
        raise ValueError('Timesteps must be int64 [batch]')
    if timesteps.device != clean.device or diffusion.sqrt_alpha.device != clean.device or diffusion.sqrt_one_minus_alpha.device != clean.device:
        raise ValueError('Schedule, timesteps and target must share a device')
    if (timesteps < 0).any() or (timesteps >= diffusion.num_base_steps).any():
        raise ValueError('Timesteps must index the original base schedule')
    return (diffusion.sqrt_alpha[timesteps, None, None] * clean
            + diffusion.sqrt_one_minus_alpha[timesteps, None, None] * noise)


def clean_motion_loss(prediction, clean, valid, observed=None, *, root_dim=5, stage_weights=(1., 1.)):
    """Stage-balanced x0 MSE on unknown valid channels, not epsilon prediction.

    An experimental Strep objective; upstream training weights are not known.
    Padding and known constraints never contribute to numerator or denominator.
    """
    if not isinstance(prediction, torch.Tensor) or prediction.ndim != 3 or prediction.dtype != torch.float32:
        raise ValueError('Prediction must be FP32 [batch,frames,features]')
    if not isinstance(clean, torch.Tensor) or clean.shape != prediction.shape or clean.dtype != prediction.dtype or clean.device != prediction.device:
        raise ValueError('Clean target must match prediction shape/type/device')
    batch, count, dim = prediction.shape
    if type(root_dim) is not int or not 0 < root_dim < dim:
        raise ValueError('Root/body boundary must be inside the feature dimension')
    if not isinstance(valid, torch.Tensor) or valid.dtype != torch.bool or valid.shape != (batch, count) or valid.device != prediction.device:
        raise ValueError('Validity mask must be bool [batch,frames] on the prediction device')
    if observed is None:
        observed = torch.zeros_like(prediction, dtype=torch.bool)
    if not isinstance(observed, torch.Tensor) or observed.dtype != torch.bool or observed.shape != prediction.shape or observed.device != prediction.device:
        raise ValueError('Observed mask must be bool with the prediction shape/device')
    if not isinstance(stage_weights, (tuple, list)) or len(stage_weights) != 2 or any(
        isinstance(w, bool) or not isinstance(w, (float, int)) or not math.isfinite(w) or w <= 0 for w in stage_weights):
        raise ValueError('Two finite positive stage weights required')
    active = valid[..., None].expand_as(prediction) & ~observed
    if not active.any():
        raise ValueError('No unknown valid channels to supervise')
    losses, counts = [], []
    for region in (slice(0, root_dim), slice(root_dim, dim)):
        mask = active[..., region]
        pred_values = prediction[..., region][mask]
        target_values = clean[..., region][mask]
        if not torch.isfinite(pred_values).all() or not torch.isfinite(target_values).all():
            raise ValueError('Supervised predictions and targets must be finite')
        difference = pred_values - target_values
        n = difference.numel()
        losses.append(difference.square().sum() / max(1, n))
        counts.append(n)
    return {'loss': stage_weights[0] * losses[0] + stage_weights[1] * losses[1],
            'root_loss': losses[0], 'body_loss': losses[1],
            'root_channel_count': counts[0], 'body_channel_count': counts[1]}


def denoising_inputs(clean, noise, timesteps, diffusion, text, heading, *, valid=None, observed=None):
    """Construct direct conditional-denoiser inputs for a backward audit."""
    noisy = noisy_target(clean, noise, timesteps, diffusion)
    batch, count, _ = clean.shape
    _finite_float(text, (batch, 1, 4096), 'Encoded text')
    _finite_float(heading, (batch,), 'First heading')
    if text.device != clean.device or heading.device != clean.device:
        raise ValueError('Conditioning must share target device')
    if valid is None:
        valid = torch.ones(batch, count, dtype=torch.bool, device=clean.device)
    if not isinstance(valid, torch.Tensor) or valid.dtype != torch.bool or valid.shape != (batch, count) or valid.device != clean.device:
        raise ValueError('Validity mask must be bool [batch,frames] on target device')
    if (valid.sum(-1) < 2).any() or not torch.equal(valid, torch.arange(count, device=clean.device)[None] < valid.sum(-1)[:, None]):
        raise ValueError('Each example requires at least two contiguous valid frames')
    if observed is None:
        observed = torch.zeros_like(clean, dtype=torch.bool)
    if not isinstance(observed, torch.Tensor) or observed.dtype != torch.bool or observed.shape != clean.shape or observed.device != clean.device:
        raise ValueError('Observed mask must be bool with target shape/device')
    if (observed & ~valid[..., None]).any():
        raise ValueError('Padded frames cannot contain observations')
    return {'x': torch.where(valid[..., None], noisy, 0), 'x_pad_mask': valid,
            'text_feat': text, 'text_feat_pad_mask': torch.ones(batch, 1, dtype=torch.bool, device=clean.device),
            'timesteps': timesteps, 'first_heading_angle': heading,
            'motion_mask': observed.to(torch.float32),
            'observed_motion': torch.where(observed, clean.detach(), 0)}
