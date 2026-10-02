"""CPU numerical lifecycle fixtures; no motion examples or model payloads."""
import copy
import hashlib
import sys
from pathlib import Path

import pytest
import torch
from torch import nn
from safetensors.torch import load_file, save_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from kimodo_adapter_probe import feedforward_adapters, unfused_transformer, fingerprint
from kimodo_adapter_state import save_state, load_state
from strep import read, save, sha256


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        for name in ('root_model', 'body_model'):
            block = nn.Module()
            block.seqTransEncoder = nn.TransformerEncoder(
                nn.TransformerEncoderLayer(8, 2, 16, dropout=.1, batch_first=True),
                2, enable_nested_tensor=False)
            setattr(self, name, block)

    def forward(self, x):
        return self.body_model.seqTransEncoder(self.root_model.seqTransEncoder(x))


@pytest.fixture(autouse=True)
def threads():
    previous = torch.get_num_threads()
    torch.set_num_threads(2)
    yield
    torch.set_num_threads(previous)


def binding(model):
    digest = hashlib.sha256(b'numerical fixture specification').hexdigest()
    return dict(model_id='numerical_fixture', model_revision='0'*40, vendor_revision='1'*40,
                checkpoint_sha256=digest, configuration_sha256=digest,
                base_state_fingerprint=fingerprint(model), objective='numerical-lifecycle-v1',
                data_manifest_sha256=digest, purpose='numerical_lifecycle')


def optimizer(adapters, lr=.003):
    return torch.optim.AdamW([p for _, layer in adapters for p in (layer.a, layer.b)],
                            lr=lr, foreach=False, fused=False)


def update(model, optim):
    x = torch.randn(1, 5, 8)
    target = torch.cos(x)
    optim.zero_grad(set_to_none=True)
    loss = (model(x) - target).square().mean()
    loss.backward()
    optim.step()
    return float(loss.detach()), x


def tensors(adapters):
    return {name+key: parameter.detach().clone() for name, layer in adapters for key, parameter in (('.a', layer.a), ('.b', layer.b))}


def test_interrupted_adamw_and_rng_resume_matches_uninterrupted_updates(tmp_path):
    torch.manual_seed(21)
    base = Model().train()
    fresh = copy.deepcopy(base)
    identity = binding(base)
    before = fingerprint(base)
    with unfused_transformer(), feedforward_adapters(base, 2, 2) as adapters:
        optim = optimizer(adapters)
        for _ in range(3):
            update(base, optim)
        manifest = save_state(tmp_path/'checkpoint', adapters, identity, model=base, completed_steps=3,
                              optimizer=optim, cursor={'epoch':0, 'next_example':3})
        assert manifest['quality_approved'] is False and manifest['release_approved'] is False
        reference = [update(base, optim) for _ in range(2)]
        expected_weights = tensors(adapters)
        expected_states = copy.deepcopy(optim.state_dict())
    assert fingerprint(base) == before
    torch.manual_seed(99999)
    with unfused_transformer(), feedforward_adapters(fresh, 2, 2) as adapters:
        resumed = optimizer(adapters, lr=.2)
        loaded = load_state(tmp_path/'checkpoint', adapters, identity, model=fresh, optimizer=resumed, restore_rng=True)
        assert loaded['completed_steps'] == 3 and loaded['cursor'] == {'epoch':0, 'next_example':3}
        assert resumed.param_groups[0]['lr'] == .003
        replay = [update(fresh, resumed) for _ in range(2)]
        for (loss, inputs), (expected_loss, expected_inputs) in zip(replay, reference):
            assert loss == expected_loss and torch.equal(inputs, expected_inputs)
        assert all(torch.equal(value, expected_weights[name]) for name, value in tensors(adapters).items())
        actual_states = resumed.state_dict()
        assert actual_states['param_groups'] == expected_states['param_groups']
        for index, state in actual_states['state'].items():
            assert all(torch.equal(value, expected_states['state'][index][key]) for key, value in state.items())
    assert fingerprint(fresh) == before


def test_binding_rank_scale_and_checksum_mismatches_leave_factors_unchanged(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=0)
        old = tensors(adapters)
        wrong = {**identity, 'data_manifest_sha256':'f'*64}
        with pytest.raises(ValueError, match='binding'):
            load_state(tmp_path/'checkpoint', adapters, wrong, model=model)
        assert all(torch.equal(value, old[name]) for name, value in tensors(adapters).items())
    with unfused_transformer(), feedforward_adapters(model, 2, 4) as adapters:
        with pytest.raises(ValueError, match='layout'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
    with unfused_transformer(), feedforward_adapters(model, 3, 3) as adapters:
        with pytest.raises(ValueError, match='layout'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
    path = tmp_path/'checkpoint/adapter.safetensors'
    path.write_bytes(path.read_bytes()+b'corruption')
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        old = tensors(adapters)
        with pytest.raises(ValueError, match='checksum'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
        assert all(torch.equal(value, old[name]) for name, value in tensors(adapters).items())


def test_nonfinite_weights_and_malformed_moments_rejected_even_with_new_hash(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        optim = optimizer(adapters)
        update(model, optim)
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=1, optimizer=optim)
        original = tensors(adapters)
        file = tmp_path/'checkpoint/training.safetensors'
        state = load_file(str(file))
        key = next(k for k in state if k.endswith('exp_avg_sq'))
        state[key].fill_(-1)
        save_file(state, str(file))
        manifest = read(tmp_path/'checkpoint/manifest.json')
        manifest['files_sha256']['training.safetensors'] = sha256(file)
        save(tmp_path/'checkpoint/manifest.json', manifest)
        with pytest.raises(ValueError, match='moment'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model, optimizer=optim)
        assert all(torch.equal(value, original[name]) for name, value in tensors(adapters).items())
        weights_file = tmp_path/'checkpoint/adapter.safetensors'
        weights = load_file(str(weights_file))
        weights[next(iter(weights))].fill_(float('nan'))
        save_file(weights, str(weights_file))
        manifest['files_sha256']['adapter.safetensors'] = sha256(weights_file)
        save(tmp_path/'checkpoint/manifest.json', manifest)
        with pytest.raises(ValueError, match='value'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)


def test_rng_restore_error_rolls_back_weights_optimizer_and_ambient_rng(tmp_path):
    model = Model().train()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        optim = optimizer(adapters)
        update(model, optim)
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=1, optimizer=optim)
        update(model, optim)
        old_weights, old_optim, old_rng = tensors(adapters), copy.deepcopy(optim.state_dict()), torch.get_rng_state().clone()
        file = tmp_path/'checkpoint/training.safetensors'
        state = load_file(str(file))
        state['rng.cpu'].fill_(255)
        save_file(state, str(file))
        manifest = read(tmp_path/'checkpoint/manifest.json')
        manifest['files_sha256']['training.safetensors'] = sha256(file)
        save(tmp_path/'checkpoint/manifest.json', manifest)
        with pytest.raises(RuntimeError):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model, optimizer=optim, restore_rng=True)
        assert all(torch.equal(value, old_weights[name]) for name, value in tensors(adapters).items())
        assert torch.equal(torch.get_rng_state(), old_rng)
        assert optim.state_dict()['param_groups'] == old_optim['param_groups']
        for index, values in optim.state_dict()['state'].items():
            assert all(torch.equal(value, old_optim['state'][index][key]) for key,value in values.items())


def test_optimizer_parameter_order_and_step_counter_are_checked_before_write(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        reversed_params = list(reversed([p for _, layer in adapters for p in (layer.a, layer.b)]))
        wrong = torch.optim.AdamW(reversed_params, foreach=False, fused=False)
        with pytest.raises(ValueError, match='order'):
            save_state(tmp_path/'bad-order', adapters, identity, model=model, completed_steps=0, optimizer=wrong)
        assert not (tmp_path/'bad-order').exists()
        optim = optimizer(adapters)
        update(model, optim)
        with pytest.raises(ValueError, match='counter'):
            save_state(tmp_path/'bad-step', adapters, identity, model=model, completed_steps=2, optimizer=optim)
        assert not (tmp_path/'bad-step').exists()


def test_weights_only_export_loads_without_inventing_optimizer_state(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        for _, layer in adapters:
            with torch.no_grad():
                layer.b.fill_(.01)
        expected = tensors(adapters)
        save_state(tmp_path/'weights', adapters, identity, model=model, completed_steps=0, capture_rng=False)
        for _, layer in adapters:
            with torch.no_grad():
                layer.b.zero_()
        load_state(tmp_path/'weights', adapters, identity, model=model)
        assert all(torch.equal(value, expected[name]) for name, value in tensors(adapters).items())
        with pytest.raises(ValueError, match='No saved optimizer'):
            load_state(tmp_path/'weights', adapters, identity, model=model, optimizer=optimizer(adapters))
        with pytest.raises(ValueError, match='RNG device'):
            load_state(tmp_path/'weights', adapters, identity, model=model, restore_rng=True)
        with pytest.raises(FileExistsError):
            save_state(tmp_path/'weights', adapters, identity, model=model, completed_steps=0)


def test_live_base_weight_change_rejected_even_with_matching_metadata(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=0)
        with torch.no_grad():
            model.root_model.seqTransEncoder.layers[0].self_attn.in_proj_weight.add_(.01)
        old = tensors(adapters)
        with pytest.raises(ValueError, match='Live frozen base'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
        assert all(torch.equal(value, old[name]) for name,value in tensors(adapters).items())


def test_runtime_mismatch_cannot_silently_resume_optimizer_or_rng(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        optim = optimizer(adapters)
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=0, optimizer=optim)
        manifest = read(tmp_path/'checkpoint/manifest.json')
        manifest['runtime']['threads'] += 1
        save(tmp_path/'checkpoint/manifest.json', manifest)
        old_weights, old_rng = tensors(adapters), torch.get_rng_state().clone()
        with pytest.raises(ValueError, match='runtime policy'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model, optimizer=optim, restore_rng=True)
        assert torch.equal(torch.get_rng_state(), old_rng)
        assert all(torch.equal(value, old_weights[name]) for name,value in tensors(adapters).items())
        # A weight-only load makes no exact-continuation promise.
        load_state(tmp_path/'checkpoint', adapters, identity, model=model)


def test_approval_or_invalid_cursor_metadata_cannot_be_loaded(tmp_path):
    model = Model()
    identity = binding(model)
    with unfused_transformer(), feedforward_adapters(model, 2, 2) as adapters:
        save_state(tmp_path/'checkpoint', adapters, identity, model=model, completed_steps=0)
        manifest = read(tmp_path/'checkpoint/manifest.json')
        manifest['quality_approved'] = True
        save(tmp_path/'checkpoint/manifest.json', manifest)
        with pytest.raises(ValueError, match='approval'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
        manifest['quality_approved'] = False
        manifest['cursor'] = {'epoch':0, 'next_example':-1}
        save(tmp_path/'checkpoint/manifest.json', manifest)
        with pytest.raises(ValueError, match='Cursor'):
            load_state(tmp_path/'checkpoint', adapters, identity, model=model)
