"""CPU PyTorch objective tests, no checkpoint/vendor/rig or network required."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from kimodo_denoising_target import clean_motion_loss, denoising_inputs, noisy_target, encode_native_target, capture_full_noise_schedule


def schedule():
    return capture_full_noise_schedule(vendor_schedule())


def vendor_schedule():
    alpha = torch.tensor([.9, .5, .01])
    return SimpleNamespace(num_base_steps=3, alphas_cumprod_base=alpha, alphas_cumprod=alpha.clone(),
                           sqrt_alphas_cumprod=alpha.sqrt(), sqrt_one_minus_alphas_cumprod=(1-alpha).sqrt())


def test_original_base_schedule_and_per_example_timesteps():
    clean = torch.ones(2, 4, 6)
    noise = torch.full_like(clean, 2)
    actual = noisy_target(clean, noise, torch.tensor([0, 2]), schedule())
    expected = torch.tensor([.9, .01]).sqrt()[:, None, None] + 2 * torch.tensor([.1, .99]).sqrt()[:, None, None]
    assert torch.allclose(actual, expected.expand_as(clean))
    assert torch.equal(clean, torch.ones_like(clean))


def test_exact_vendor_coefficients_survive_later_respacing_and_mutation():
    vendor = vendor_schedule()
    # Deliberately retain a tiny difference from directly taking sqrt(base).
    vendor.sqrt_alphas_cumprod[1] += 2e-7
    snapshot = capture_full_noise_schedule(vendor)
    clean, noise, t = torch.ones(1, 4, 6), torch.ones(1, 4, 6), torch.tensor([1])
    expected = vendor.sqrt_alphas_cumprod[1] * clean + vendor.sqrt_one_minus_alphas_cumprod[1] * noise
    vendor.alphas_cumprod = torch.tensor([.7, .2])
    vendor.sqrt_alphas_cumprod.zero_()
    assert torch.equal(noisy_target(clean, noise, t, snapshot), expected)
    with pytest.raises(ValueError):
        capture_full_noise_schedule(vendor)


def test_respaced_and_nonfinite_schedule_cannot_be_captured():
    vendor = vendor_schedule()
    vendor.alphas_cumprod = torch.tensor([.9, .01, .01])
    with pytest.raises(ValueError, match='pristine'):
        capture_full_noise_schedule(vendor)
    vendor = vendor_schedule()
    vendor.sqrt_one_minus_alphas_cumprod[1] = float('nan')
    with pytest.raises(ValueError, match='finite'):
        capture_full_noise_schedule(vendor)


def test_stage_balanced_clean_target_instead_of_global_or_noise_mse():
    pred = torch.tensor([[[2., 2., 3., 3., 3., 3.]]], requires_grad=True)
    clean = torch.zeros_like(pred)
    result = clean_motion_loss(pred, clean, torch.tensor([[True]]), root_dim=2)
    assert result['root_loss'] == 4 and result['body_loss'] == 9
    assert result['loss'] == 13
    assert result['root_channel_count'] == 2 and result['body_channel_count'] == 4
    result['loss'].backward()
    assert torch.allclose(pred.grad, torch.tensor([[[2., 2., 1.5, 1.5, 1.5, 1.5]]]))


def test_padding_and_known_features_excluded_from_loss_and_gradient():
    pred = torch.tensor([[[2., 100., 3., 3., 100., 100.], [float('nan')] * 6]], requires_grad=True)
    clean = torch.tensor([[[0.] * 6, [float('nan')] * 6]])
    valid = torch.tensor([[True, False]])
    observed = torch.tensor([[[False, True, False, False, True, True], [False] * 6]])
    result = clean_motion_loss(pred, clean, valid, observed, root_dim=2)
    assert result['loss'] == 13 and result['root_channel_count'] == 1 and result['body_channel_count'] == 2
    result['loss'].backward()
    assert torch.equal(pred.grad, torch.tensor([[[4., 0., 3., 3., 0., 0.], [0.] * 6]]))


def test_known_root_stage_has_zero_loss_without_losing_body_gradient():
    pred = torch.ones(1, 4, 6, requires_grad=True)
    observed = torch.zeros_like(pred, dtype=torch.bool)
    observed[..., :2] = True
    result = clean_motion_loss(pred, torch.zeros_like(pred), torch.ones(1, 4, dtype=torch.bool), observed, root_dim=2)
    assert result['root_loss'] == 0 and result['root_channel_count'] == 0 and result['body_loss'] == 1
    result['loss'].backward()
    assert pred.grad[..., :2].count_nonzero() == 0
    assert pred.grad[..., 2:].count_nonzero() == 16


def test_input_masks_preserve_only_selected_clean_observations():
    clean = torch.arange(24, dtype=torch.float32).reshape(1, 4, 6)
    copy = clean.clone()
    known = torch.zeros_like(clean, dtype=torch.bool)
    known[0, 0, :2] = True
    valid = torch.tensor([[True, True, True, False]])
    text = torch.randn(1, 1, 4096)
    inputs = denoising_inputs(clean, torch.zeros_like(clean), torch.tensor([1]), schedule(), text,
                             torch.tensor([.7]), valid=valid, observed=known)
    assert inputs['motion_mask'].dtype == torch.float32
    assert torch.equal(inputs['observed_motion'], torch.where(known, clean, 0))
    assert inputs['x'][0, -1].count_nonzero() == 0
    assert torch.allclose(inputs['x'][0, :3], .5 ** .5 * clean[0, :3])
    assert torch.equal(clean, copy) and torch.equal(inputs['text_feat'], text)
    assert torch.equal(inputs['first_heading_angle'], torch.tensor([.7]))


@pytest.mark.parametrize('timesteps', [torch.tensor([-1]), torch.tensor([3]), torch.tensor([1.]), torch.tensor([[1]])])
def test_invalid_timesteps_reject(timesteps):
    with pytest.raises(ValueError):
        noisy_target(torch.ones(1, 4, 6), torch.zeros(1, 4, 6), timesteps, schedule())


@pytest.mark.parametrize('weights', [(0, 1), (True, 1), (1, float('inf')), (1,), None])
def test_invalid_stage_weights_reject(weights):
    with pytest.raises(ValueError):
        clean_motion_loss(torch.ones(1, 4, 6), torch.zeros(1, 4, 6), torch.ones(1, 4, dtype=torch.bool),
                          root_dim=2, stage_weights=weights)


def test_all_known_and_nonfinite_supervision_reject():
    pred = torch.ones(1, 4, 6)
    with pytest.raises(ValueError, match='No unknown'):
        clean_motion_loss(pred, pred, torch.ones(1, 4, dtype=torch.bool), torch.ones_like(pred, dtype=torch.bool))
    pred[0, 0, 0] = float('nan')
    with pytest.raises(ValueError, match='finite'):
        clean_motion_loss(pred, torch.zeros_like(pred), torch.ones(1, 4, dtype=torch.bool))


@pytest.mark.parametrize('valid', [torch.tensor([[True, False, True, False]]), torch.tensor([[True, False, False, False]]),
                                  torch.ones(1, 4), torch.ones(1, 3, dtype=torch.bool)])
def test_invalid_padding_patterns_reject(valid):
    with pytest.raises(ValueError):
        denoising_inputs(torch.ones(1, 4, 6), torch.zeros(1, 4, 6), torch.tensor([1]), schedule(),
                         torch.zeros(1, 1, 4096), torch.zeros(1), valid=valid)


def test_padded_observations_and_nonfinite_text_reject():
    clean = torch.ones(1, 4, 6)
    known = torch.zeros_like(clean, dtype=torch.bool)
    known[0, -1, 0] = True
    with pytest.raises(ValueError, match='Padded'):
        denoising_inputs(clean, torch.zeros_like(clean), torch.tensor([1]), schedule(), torch.zeros(1, 1, 4096),
                         torch.zeros(1), valid=torch.tensor([[True, True, True, False]]), observed=known)
    with pytest.raises(ValueError, match='finite'):
        denoising_inputs(clean, torch.zeros_like(clean), torch.tensor([1]), schedule(), torch.full((1, 1, 4096), float('nan')),
                         torch.zeros(1))


def test_codec_rejects_undeclared_joint_order_fps_or_reflections_before_fk():
    full = SimpleNamespace(bone_order_names=[str(i) for i in range(77)])
    rep = SimpleNamespace(skeleton=SimpleNamespace(name='somaskel30', somaskel77=full), motion_rep_dim=369, fps=30)
    rotations = torch.eye(3).repeat(3, 77, 1, 1)
    roots = torch.zeros(3, 3)
    with pytest.raises(ValueError, match='joint order'):
        encode_native_target(rep, rotations, roots, full.bone_order_names[::-1], 30)
    with pytest.raises(ValueError, match='FPS'):
        encode_native_target(rep, rotations, roots, full.bone_order_names, 60)
    rotations[..., 0, 0] = -1
    with pytest.raises(ValueError, match='Proper'):
        encode_native_target(rep, rotations, roots, full.bone_order_names, 30)


def test_codec_calls_vendor_with_an_explicit_batch_and_lengths():
    full = SimpleNamespace(bone_order_names=[str(i) for i in range(77)])
    skeleton = SimpleNamespace(name='somaskel30', somaskel77=full,
                               from_SOMASkeleton77=lambda value: value[:, :30],
                               to_SOMASkeleton77=lambda value: torch.eye(3).repeat(len(value), 77, 1, 1))
    class VendorCall:
        motion_rep_dim, fps = 369, 30
        def __init__(self):
            self.skeleton = skeleton
        def __call__(self, rotations, roots, **kwargs):
            assert rotations.shape == (1, 3, 30, 3, 3)
            assert roots.shape == (1, 3, 3)
            assert torch.equal(kwargs['lengths'], torch.tensor([3]))
            assert kwargs['to_normalize'] is False and kwargs['to_canonicalize'] is False
            raise RuntimeError('observed explicit vendor batch')
    with pytest.raises(RuntimeError, match='observed explicit vendor batch'):
        encode_native_target(VendorCall(), torch.eye(3).repeat(3, 77, 1, 1), torch.zeros(3, 3), full.bone_order_names, 30)


def test_codec_rejects_omitted_finger_motion_instead_of_discarding_it():
    full = SimpleNamespace(bone_order_names=[str(i) for i in range(77)])
    skeleton = SimpleNamespace(name='somaskel30', somaskel77=full,
                               from_SOMASkeleton77=lambda value: value[:, :30],
                               to_SOMASkeleton77=lambda value: torch.eye(3).repeat(len(value), 77, 1, 1))
    rep = SimpleNamespace(skeleton=skeleton, motion_rep_dim=369, fps=30)
    rotations = torch.eye(3).repeat(3, 77, 1, 1)
    rotations[:, 60] = torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    with pytest.raises(ValueError, match='omitted joint/finger'):
        encode_native_target(rep, rotations, torch.zeros(3, 3), full.bone_order_names, 30)
