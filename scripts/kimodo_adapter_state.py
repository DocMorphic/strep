"""Bound, non-pickle adapter/AdamW/Torch-RNG checkpoints for development.

The caller installs adapters under unfused_transformer(). This format never
approves training data or promotes an adapter into the production Studio.
"""
from __future__ import annotations

import copy
import hashlib
import math
import os
from pathlib import Path
import re

import torch
from safetensors.torch import load_file, save_file

from strep import read, save, sha256
from kimodo_adapter_probe import LowRankLinear

SCHEMA = 'strep-kimodo-adapter-state-v1'
BINDING_FIELDS = {'model_id', 'model_revision', 'vendor_revision', 'checkpoint_sha256',
                  'configuration_sha256', 'base_state_fingerprint', 'objective', 'data_manifest_sha256', 'purpose'}
HYPER_FIELDS = {'lr', 'betas', 'eps', 'weight_decay', 'amsgrad', 'maximize', 'foreach',
                'capturable', 'differentiable', 'fused', 'decoupled_weight_decay'}


def _binding(value):
    if not isinstance(value, dict) or set(value) != BINDING_FIELDS:
        raise ValueError('Explicit model/source/configuration/objective/data binding required')
    for key in ('model_revision', 'vendor_revision'):
        if not isinstance(value[key], str) or not re.fullmatch('[0-9a-f]{40}', value[key]):
            raise ValueError('Revisions must be exact lowercase Git hashes')
    for key in ('checkpoint_sha256', 'configuration_sha256', 'base_state_fingerprint', 'data_manifest_sha256'):
        if not isinstance(value[key], str) or not re.fullmatch('[0-9a-f]{64}', value[key]):
            raise ValueError('Bindings must include exact SHA-256 values')
    if any(not isinstance(value[k], str) or not value[k].strip() for k in ('model_id', 'objective')):
        raise ValueError('Model and objective identifiers required')
    if value['purpose'] not in ('numerical_lifecycle', 'development_training'):
        raise ValueError('Only unapproved development checkpoint purposes are supported')
    return dict(value)


def _parameters(adapters):
    named, layout = [], []
    for name, layer in adapters:
        if not isinstance(name, str) or not re.fullmatch(r'(root_model|body_model)\.seqTransEncoder\.layers\.\d+\.linear[12]', name):
            raise ValueError('Explicit two-stage feedforward target names required')
        if any(p.dtype != torch.float32 or not isinstance(p, torch.nn.Parameter) for p in (layer.a, layer.b)):
            raise ValueError('FP32 adapter Parameters required')
        if layer.a.ndim != 2 or layer.b.ndim != 2 or layer.a.shape[0] != layer.b.shape[1] or not math.isfinite(layer.scale) or layer.scale <= 0:
            raise ValueError('Invalid adapter factor dimensions/scale')
        named.extend(((name + '.a', layer.a), (name + '.b', layer.b)))
        layout.append({'name': name, 'a_shape': list(layer.a.shape), 'b_shape': list(layer.b.shape), 'scale': layer.scale})
    if not named or len({name for name, _ in named}) != len(named) or len({id(p) for _, p in named}) != len(named):
        raise ValueError('Distinct, nonempty adapter factors required')
    return named, layout


def _cursor(value):
    if value is not None and (not isinstance(value, dict) or set(value) != {'epoch', 'next_example'} or any(type(v) is not int or v < 0 for v in value.values())):
        raise ValueError('Cursor supports explicit sequential epoch/next_example only')
    return copy.deepcopy(value)


def _verify_base(model, adapters, binding):
    if not isinstance(model, torch.nn.Module):
        raise ValueError('The live wrapped base model is required')
    installed = [(name, module) for name, module in model.named_modules() if isinstance(module, LowRankLinear)]
    if len(installed) != len(adapters) or any(name != expected or layer is not expected_layer for (name,layer),(expected,expected_layer) in zip(installed,adapters)):
        raise ValueError('Checkpoint must include every adapter installed in the live model')
    factor_ids = {id(p) for _, layer in adapters for p in (layer.a,layer.b)}
    if any(parameter.requires_grad for parameter in model.parameters() if id(parameter) not in factor_ids):
        raise ValueError('The live base model must remain frozen')
    omit = {name + suffix for name, _ in adapters for suffix in ('.a','.b')}
    renames = {name + '.base.' + key:name + '.' + key for name, layer in adapters
               for key in layer.base.state_dict()}
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        if name in omit:
            continue
        name = renames.get(name,name)
        digest.update(name.encode())
        digest.update(str((value.dtype,tuple(value.shape))).encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    if digest.hexdigest() != binding['base_state_fingerprint']:
        raise ValueError('Live frozen base state differs from the checkpoint binding')


def _hyper(value):
    if not isinstance(value, dict) or set(value) != HYPER_FIELDS:
        raise ValueError('Unsupported AdamW hyperparameter layout')
    for key in ('amsgrad', 'maximize', 'foreach', 'capturable', 'differentiable', 'fused'):
        if value[key] is not False:
            raise ValueError('Explicit nonfused, noncapturable standard AdamW required')
    if value['decoupled_weight_decay'] is not True:
        raise ValueError('AdamW decoupled weight decay required')
    for key in ('lr', 'eps', 'weight_decay'):
        val = value[key]
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0 or (key == 'eps' and val == 0):
            raise ValueError('Invalid AdamW scalar')
    if not isinstance(value['betas'], (tuple, list)) or len(value['betas']) != 2 or any(
        isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v < 1 for v in value['betas']):
        raise ValueError('Invalid AdamW betas')
    return {**value, 'betas': list(value['betas'])}


def _optimizer(optimizer, named):
    if type(optimizer) is not torch.optim.AdamW or len(optimizer.param_groups) != 1:
        raise ValueError('One standard AdamW parameter group required')
    group = optimizer.param_groups[0]
    expected = [p for _, p in named]
    if len(group['params']) != len(expected) or any(a is not b for a, b in zip(group['params'], expected)):
        raise ValueError('Optimizer factors must match adapter names and order exactly')
    if any(p not in set(expected) for p in optimizer.state):
        raise ValueError('Optimizer contains stale/non-adapter state')
    return _hyper({key: value for key, value in group.items() if key != 'params'})


def _runtime():
    return {'torch': torch.__version__, 'threads': torch.get_num_threads(),
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'mha_fastpath': torch.backends.mha.get_fastpath_enabled(),
            'tf32_matmul': torch.backends.cuda.matmul.allow_tf32,
            'cublas_workspace_config': os.environ.get('CUBLAS_WORKSPACE_CONFIG')}


def _rng():
    values = {'rng.cpu': torch.get_rng_state().clone()}
    if torch.cuda.is_initialized():
        values.update({f'rng.cuda.{index}': value.clone() for index, value in enumerate(torch.cuda.get_rng_state_all())})
    return values


def _restore_rng(values):
    torch.set_rng_state(values['rng.cpu'])
    cuda = [values[f'rng.cuda.{index}'] for index in range(len(values)-1)]
    if cuda:
        torch.cuda.set_rng_state_all(cuda)


def save_state(folder, adapters, binding, *, model, completed_steps, optimizer=None, cursor=None, capture_rng=True):
    """Publish a fresh checkpoint directory with a manifest written last."""
    folder = Path(folder)
    binding = _binding(binding)
    named, layout = _parameters(adapters)
    _verify_base(model,adapters,binding)
    if type(completed_steps) is not int or completed_steps < 0 or type(capture_rng) is not bool:
        raise ValueError('Nonnegative completed step and explicit RNG policy required')
    cursor = _cursor(cursor)
    weights = {name: parameter.detach().cpu().contiguous().clone() for name, parameter in named}
    if not all(torch.isfinite(value).all() for value in weights.values()):
        raise ValueError('Nonfinite adapter weights')
    state, optimizer_record = {}, None
    if optimizer is not None:
        hyper = _optimizer(optimizer, named)
        for name, parameter in named:
            current = optimizer.state.get(parameter, {})
            if completed_steps == 0:
                if current:
                    raise ValueError('A zero-step checkpoint cannot have initialized moments')
                continue
            if set(current) != {'step', 'exp_avg', 'exp_avg_sq'}:
                raise ValueError('Each trained factor needs complete standard AdamW state')
            for key in ('step', 'exp_avg', 'exp_avg_sq'):
                value = current[key].detach().cpu().contiguous().clone()
                shape = () if key == 'step' else parameter.shape
                if value.dtype != torch.float32 or value.shape != shape or not torch.isfinite(value).all():
                    raise ValueError('Invalid AdamW tensor state')
                if key == 'step' and float(value) != completed_steps:
                    raise ValueError('Optimizer counter differs from completed steps')
                if key == 'exp_avg_sq' and (value < 0).any():
                    raise ValueError('Second moments must be nonnegative')
                state[f'optim.{name}.{key}'] = value
        optimizer_record = {'type': 'AdamW', 'hyperparameters': hyper, 'initialized': completed_steps > 0}
    rng_values = _rng() if capture_rng else {}
    state.update(rng_values)
    manifest = {'schema': SCHEMA, 'binding': binding, 'targets': layout, 'completed_steps': completed_steps,
                'cursor': cursor, 'optimizer': optimizer_record, 'rng_shapes': {key: list(value.shape) for key, value in rng_values.items()},
                'rng_scope': 'Torch CPU and initialized CUDA generators only', 'runtime': _runtime(),
                'quality_approved': False, 'release_approved': False}
    folder.mkdir(parents=True, exist_ok=False)
    save_file(weights, str(folder / 'adapter.safetensors'))
    save_file(state, str(folder / 'training.safetensors'))
    manifest['files_sha256'] = {name: sha256(folder / name) for name in ('adapter.safetensors', 'training.safetensors')}
    save(folder / 'manifest.json', manifest)
    return manifest


def load_state(folder, adapters, expected_binding, *, model, optimizer=None, restore_rng=False):
    """Validate all files first; restore weights/state/RNG transactionally."""
    folder = Path(folder)
    expected_binding = _binding(expected_binding)
    named, layout = _parameters(adapters)
    _verify_base(model,adapters,expected_binding)
    manifest = read(folder / 'manifest.json')
    fields = {'schema', 'binding', 'targets', 'completed_steps', 'cursor', 'optimizer', 'rng_shapes', 'rng_scope',
              'runtime', 'quality_approved', 'release_approved', 'files_sha256'}
    if set(manifest) != fields or manifest['schema'] != SCHEMA or manifest['binding'] != expected_binding or manifest['targets'] != layout:
        raise ValueError('Adapter model/data binding or target layout mismatch')
    if manifest['quality_approved'] is not False or manifest['release_approved'] is not False:
        raise ValueError('This development format cannot carry quality/release approval')
    _cursor(manifest['cursor'])
    if type(restore_rng) is not bool or manifest['rng_scope'] != 'Torch CPU and initialized CUDA generators only':
        raise ValueError('Explicit Torch-only RNG policy required')
    steps = manifest['completed_steps']
    if type(steps) is not int or steps < 0:
        raise ValueError('Invalid step counter')
    if set(manifest['files_sha256']) != {'adapter.safetensors', 'training.safetensors'}:
        raise ValueError('Unexpected checkpoint files')
    for name, expected in manifest['files_sha256'].items():
        if sha256(folder / name) != expected:
            raise ValueError('Checkpoint file checksum mismatch')
    weights = load_file(str(folder / 'adapter.safetensors'), device='cpu')
    state = load_file(str(folder / 'training.safetensors'), device='cpu')
    for name, expected in manifest['files_sha256'].items():
        if sha256(folder / name) != expected:
            raise ValueError('Checkpoint changed during read')
    if set(weights) != {name for name, _ in named}:
        raise ValueError('Checkpoint contains missing or non-adapter weights')
    for name, parameter in named:
        if weights[name].shape != parameter.shape or weights[name].dtype != torch.float32 or not torch.isfinite(weights[name]).all():
            raise ValueError('Adapter tensor shape/type/value mismatch')
    optimizer_record = manifest['optimizer']
    expected_keys = set(manifest['rng_shapes'])
    loaded_optimizer = None
    if optimizer_record is not None:
        if set(optimizer_record) != {'type', 'hyperparameters', 'initialized'} or optimizer_record['type'] != 'AdamW' or optimizer_record['initialized'] is not (steps > 0):
            raise ValueError('Invalid optimizer metadata')
        hyper = _hyper(optimizer_record['hyperparameters'])
        states = {}
        if steps > 0:
            for index, (name, parameter) in enumerate(named):
                values = {}
                for key in ('step', 'exp_avg', 'exp_avg_sq'):
                    tensor_key = f'optim.{name}.{key}'
                    expected_keys.add(tensor_key)
                    value = state.get(tensor_key)
                    shape = () if key == 'step' else parameter.shape
                    if value is None or value.dtype != torch.float32 or value.shape != shape or not torch.isfinite(value).all():
                        raise ValueError('Invalid optimizer tensor')
                    if key == 'step' and float(value) != steps or key == 'exp_avg_sq' and (value < 0).any():
                        raise ValueError('Optimizer counter/moment mismatch')
                    values[key] = value
                states[index] = values
        loaded_optimizer = {'state': states, 'param_groups': [{**hyper, 'betas': tuple(hyper['betas']), 'params': list(range(len(named)))}]}
    if set(state) != expected_keys:
        raise ValueError('Unexpected/missing optimizer or RNG tensors')
    rng_keys = set(manifest['rng_shapes'])
    if rng_keys and rng_keys != {'rng.cpu', *(f'rng.cuda.{index}' for index in range(len(rng_keys)-1))}:
        raise ValueError('Invalid Torch RNG names')
    for key in rng_keys:
        value = state[key]
        if value.dtype != torch.uint8 or list(value.shape) != manifest['rng_shapes'][key] or value.ndim != 1:
            raise ValueError('Invalid Torch RNG tensor')
    if optimizer is not None:
        _optimizer(optimizer, named)
        if loaded_optimizer is None:
            raise ValueError('No saved optimizer state for resuming')
    if optimizer is not None or restore_rng:
        if manifest['runtime'] != _runtime():
            raise ValueError('Exact continuation requires the same recorded Torch runtime policy')
    if restore_rng:
        current_rng = _rng()
        if rng_keys != set(current_rng) or any(state[key].shape != current_rng[key].shape for key in rng_keys) or not rng_keys:
            raise ValueError('Torch RNG device/layout mismatch')
    # Backups are small adapter/state tensors, not the frozen base checkpoint.
    old_weights = {name: parameter.detach().clone() for name, parameter in named}
    old_optimizer = copy.deepcopy(optimizer.state_dict()) if optimizer is not None else None
    old_rng = _rng() if restore_rng else None
    try:
        with torch.no_grad():
            for name, parameter in named:
                parameter.copy_(weights[name])
        if optimizer is not None:
            optimizer.load_state_dict(loaded_optimizer)
        if restore_rng:
            _restore_rng({key: state[key] for key in rng_keys})
    except Exception:
        with torch.no_grad():
            for name, parameter in named:
                parameter.copy_(old_weights[name])
        if optimizer is not None:
            optimizer.load_state_dict(old_optimizer)
        if old_rng is not None:
            _restore_rng(old_rng)
        raise
    return manifest
