"""Small CPU PyTorch tests; require the inference environment, no checkpoint."""
import sys
from pathlib import Path

import pytest
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from kimodo_adapter_probe import LowRankLinear, feedforward_adapters, fingerprint, unfused_transformer


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.seqTransEncoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(8, 2, 16, dropout=0, batch_first=True),
            2, enable_nested_tensor=False)

    def forward(self, x):
        return self.seqTransEncoder(x)


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.root_model, self.body_model = Block(), Block()

    def forward(self, x):
        return self.body_model(self.root_model(x))


def test_zero_delta_and_nonzero_residual_use_both_factors():
    torch.manual_seed(10)
    base = nn.Linear(5, 3)
    x = torch.randn(2, 4, 5)
    reference = base(x).detach()
    adapter = LowRankLinear(base, 2, 4)
    assert torch.equal(adapter(x), reference)
    adapter(x).square().mean().backward()
    assert adapter.a.grad is not None and adapter.a.grad.count_nonzero() == 0
    assert adapter.b.grad.norm() > 0
    assert all(p.grad is None for p in base.parameters())
    with torch.no_grad():
        adapter.b.fill_(.2)
    adapter.zero_grad(set_to_none=True)
    expected = reference + x @ adapter.a.T @ adapter.b.T * 2
    assert torch.allclose(adapter(x), expected)
    adapter(x).square().mean().backward()
    assert adapter.a.grad.norm() > 0 and adapter.b.grad.norm() > 0


def test_transformer_eval_calls_residual_and_restores_exact_base():
    torch.manual_seed(20)
    model = Model().eval()
    before = fingerprint(model)
    parameters = list(model.parameters())
    parameters[0].requires_grad_(False)
    flags = [p.requires_grad for p in parameters]
    x = torch.randn(1, 5, 8)
    with unfused_transformer(), torch.no_grad():
        reference = model(x)
        with feedforward_adapters(model, 2, 2) as adapters:
            assert len(adapters) == 8
            assert torch.equal(model(x), reference)
            for _, layer in adapters:
                layer.b.normal_(std=.2)
            assert not torch.allclose(model(x), reference)
    assert fingerprint(model) == before
    assert [p.requires_grad for p in parameters] == flags
    assert list(model.parameters()) == parameters


def test_restore_on_exception_and_fastpath_guard():
    model = Model().eval()
    before = fingerprint(model)
    previous = torch.backends.mha.get_fastpath_enabled()
    torch.backends.mha.set_fastpath_enabled(True)
    try:
        with pytest.raises(RuntimeError, match='avoid bypass'):
            with feedforward_adapters(model, 2, 2):
                model(torch.randn(1, 4, 8))
        assert fingerprint(model) == before
        assert all(p.requires_grad for p in model.parameters())
        with pytest.raises(RuntimeError, match='intentional'):
            with unfused_transformer(), feedforward_adapters(model, 2, 2):
                raise RuntimeError('intentional')
        assert torch.backends.mha.get_fastpath_enabled()
        assert fingerprint(model) == before
        # Hook removed, so the restored original model works normally.
        with torch.no_grad():
            assert torch.isfinite(model(torch.randn(1, 4, 8))).all()
    finally:
        torch.backends.mha.set_fastpath_enabled(previous)


@pytest.mark.parametrize('rank,alpha', [(True, 1), (0, 1), (9, 1), (2, float('nan')), (2, True)])
def test_invalid_adapter_configuration_leaves_model_unchanged(rank, alpha):
    model = Model()
    before = fingerprint(model)
    with pytest.raises(ValueError):
        with feedforward_adapters(model, rank, alpha):
            pytest.fail('invalid configuration entered')
    assert fingerprint(model) == before
    assert all(p.requires_grad for p in model.parameters())


def test_no_targets_rejected_and_non_fp32_rejected():
    with pytest.raises(ValueError, match='layout'):
        with feedforward_adapters(nn.Linear(3, 3)):
            pytest.fail('entered')
    model = Model().double()
    before = fingerprint(model)
    with pytest.raises(ValueError, match='FP32'):
        with feedforward_adapters(model, 2):
            pytest.fail('entered')
    assert fingerprint(model) == before


def test_training_gradients_freeze_all_base_parameters():
    model = Model().train()
    before = fingerprint(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        model(torch.randn(1, 5, 8)).square().mean().backward()
        for _, layer in adapters:
            assert layer.b.grad is not None and torch.isfinite(layer.b.grad).all()
            assert layer.b.grad.norm() > 0
            assert layer.a.grad.count_nonzero() == 0
        assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
    assert fingerprint(model) == before
