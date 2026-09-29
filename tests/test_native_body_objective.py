from pathlib import Path
import sys
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_body_objective import NativeBodyObjective


def reference():
    return torch.zeros((4, 2, 3), dtype=torch.float64)


def test_source_and_constant_within_budget_translation_have_finite_zero_gradient():
    ref = reference()
    objective = NativeBodyObjective({'raw': ref, 'limb': ref+.01})
    candidate = (ref+.02).requires_grad_()
    loss = objective.loss(candidate)
    assert loss == 0 and torch.isfinite(torch.autograd.grad(loss, candidate)[0]).all()


def test_translation_fails_pose_even_with_zero_added_speed():
    ref = reference(); candidate = ref.clone(); candidate[..., 0] = .23
    objective = NativeBodyObjective({'raw': ref}); assert objective.loss(candidate) > 0
    assert objective.record()['peaks']['raw'] == pytest.approx([.23, 0])
    assert objective.last['raw'][0].max() > 0 and objective.last['raw'][1].max() < 0


def test_small_fast_edit_fails_speed_even_within_pose_budget():
    ref = reference(); candidate = ref.clone(); candidate[1, 1, 0] = .06
    objective = NativeBodyObjective({'raw': ref}); assert objective.loss(candidate) > 0
    assert objective.last['raw'][0].max() < 0 and objective.last['raw'][1].max() > 0
    assert objective.record()['peaks']['raw'] == pytest.approx([.06, 1.8])


def test_speed_measures_edit_delta_not_character_travel():
    ref = reference(); ref[:, :, 0] = torch.arange(4)[:, None]*10.
    objective = NativeBodyObjective({'raw': ref})
    assert objective.loss(ref) == 0


def test_each_reference_is_enforced_and_cloned():
    raw = reference(); limb = raw.clone(); limb[..., 0] = -.21
    objective = NativeBodyObjective({'raw': raw, 'limb': limb})
    limb.zero_()
    candidate = raw.clone(); candidate[..., 0] = .02
    assert objective.loss(candidate) > 0
    assert objective.last['raw'][0].max() < 0 and objective.last['limb'][0].max() > 0


def test_gradients_and_accepted_multiplier_updates():
    ref = reference(); candidate = ref.clone(); candidate[1, 0] = torch.tensor([.25, .03, .02])
    candidate.requires_grad_(); objective = NativeBodyObjective({'raw': ref})
    assert torch.autograd.gradcheck(objective.loss, (candidate,), atol=1e-4)
    objective.loss(candidate); objective.advance_stage(4)
    assert objective.penalty == 40 and all(m.max() > 0 for m in objective.multipliers['raw'])
    objective.loss(ref); objective.advance_stage(4)
    assert all(torch.isfinite(m).all() for m in objective.multipliers['raw'])


@pytest.mark.parametrize('value', [{}, {'raw': torch.zeros((1, 2, 3), dtype=torch.float64)},
                                  {'raw': reference().float()}, {'raw': reference()*float('nan')},
                                  {'raw': reference(), 'limb': reference()[:2]}])
def test_invalid_references_rejected(value):
    with pytest.raises(ValueError): NativeBodyObjective(value)


def test_bad_candidate_and_update_rejected():
    objective = NativeBodyObjective({'raw': reference()})
    with pytest.raises(ValueError): objective.advance_stage(4)
    for value in [reference()[:2], reference().float(), reference()*float('nan')]:
        with pytest.raises(ValueError): objective.loss(value)
    objective.loss(reference())
    for growth in [0, -1, True, float('inf')]:
        with pytest.raises(ValueError): objective.advance_stage(growth)
