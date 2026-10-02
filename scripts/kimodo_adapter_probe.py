"""Offline gradient/memory audit, not a trainer or production adapter loader.

Uses synthetic tensors, no text encoder, optimizer, examples or model updates.
The existing Kimodo training branch intentionally detaches the root-to-body path.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time

import torch
from torch import nn


class LowRankLinear(nn.Module):
    """Unmerged FP32 low-rank residual with a zero initial output."""

    def __init__(self, base, rank, alpha):
        super().__init__()
        if not isinstance(base, nn.Linear):
            raise ValueError('The probe wraps only explicit Linear modules')
        if type(rank) is not int or not 0 < rank <= min(base.in_features, base.out_features):
            raise ValueError('Rank must fit both feature dimensions')
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or alpha <= 0:
            raise ValueError('Alpha must be finite and positive')
        if base.weight.dtype != torch.float32:
            raise ValueError('This audit supports FP32 only')
        self.base = base
        self.scale = float(alpha) / rank
        self.a = nn.Parameter(base.weight.new_empty(rank, base.in_features))
        self.b = nn.Parameter(base.weight.new_zeros(base.out_features, rank))
        nn.init.kaiming_uniform_(self.a, a=math.sqrt(5))
        base.requires_grad_(False)

    @property
    def weight(self):
        return self.base.weight

    @property
    def bias(self):
        return self.base.bias

    def forward(self, x):
        return self.base(x) + torch.nn.functional.linear(
            torch.nn.functional.linear(x, self.a), self.b) * self.scale


@contextlib.contextmanager
def unfused_transformer():
    """Fused evaluation can read Linear.weight and bypass the residual call."""
    previous = torch.backends.mha.get_fastpath_enabled()
    torch.backends.mha.set_fastpath_enabled(False)
    try:
        yield
    finally:
        torch.backends.mha.set_fastpath_enabled(previous)


@contextlib.contextmanager
def feedforward_adapters(model, rank=8, alpha=8):
    """Temporarily wrap both stages' feedforward layers; always restore base."""
    pattern = re.compile(r'^(root_model|body_model)\.seqTransEncoder\.layers\.\d+\.linear[12]$')
    targets = [(name, module) for name, module in model.named_modules() if pattern.fullmatch(name)]
    if not targets or any(not isinstance(m, nn.Linear) for _, m in targets):
        raise ValueError('No valid two-stage feedforward target layout')
    # Validate every wrapper before changing the original model or its flags.
    if type(rank) is not int or rank <= 0 or any(rank > min(m.in_features, m.out_features) for _, m in targets):
        raise ValueError('Rank must fit every target')
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or alpha <= 0:
        raise ValueError('Alpha must be finite and positive')
    if any(m.weight.dtype != torch.float32 for _, m in targets):
        raise ValueError('This audit supports FP32 only')
    parameters = [(p, p.requires_grad) for p in model.parameters()]
    restored = []
    guard = None
    def require_unfused(_module, _inputs):
        if torch.backends.mha.get_fastpath_enabled():
            raise RuntimeError('Probe adapters require unfused_transformer() to avoid bypass')
    try:
        model.requires_grad_(False)
        for name, base in targets:
            parent_name, attr = name.rsplit('.', 1)
            parent = model.get_submodule(parent_name)
            wrapper = LowRankLinear(base, rank, alpha)
            setattr(parent, attr, wrapper)
            restored.append((parent, attr, base, name, wrapper))
        guard = model.register_forward_pre_hook(require_unfused)
        yield [(name, wrapper) for _, _, _, name, wrapper in restored]
    finally:
        if guard is not None:
            guard.remove()
        for parent, attr, base, _, _ in reversed(restored):
            setattr(parent, attr, base)
        for parameter, flag in parameters:
            parameter.requires_grad_(flag)


def fingerprint(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode())
        digest.update(str((value.dtype, tuple(value.shape))).encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def gradient_report(adapters):
    rows = []
    for name, layer in adapters:
        row = {'name': name}
        for key in ('a', 'b'):
            gradient = getattr(layer, key).grad
            row[key] = {'present': gradient is not None,
                        'finite': bool(torch.isfinite(gradient).all()) if gradient is not None else None,
                        'norm': float(gradient.norm()) if gradient is not None else None}
        rows.append(row)
    return rows


def run(output, frames, rank, seed):
    from strep import ROOT, read, save, sha256, now, source_check, model_directory
    if not frames or any(type(n) is not int or n < 2 or n > 600 for n in frames) or len(set(frames)) != len(frames):
        raise ValueError('Distinct frame counts must be between 2 and 600')
    if output.exists():
        raise ValueError('Output must be fresh; retain earlier successes and failures')
    output.mkdir(parents=True)
    record = {'schema': 'strep-kimodo-adapter-probe-v1', 'started_at': now(),
              'status': 'running', 'frames': frames, 'rank': rank, 'alpha': rank, 'seed': seed,
              'dtype': 'float32', 'batch_size': 1, 'synthetic_input': True,
              'text_conditioning': 'zero tensor, not an encoded prompt',
              'optimizer_steps': 0, 'quality_approved': False, 'rows': []}
    result_path = output / 'result.json'
    save(result_path, record)
    checkpoint = None
    checkpoint_hashes = None
    try:
        vendor_revision = source_check()
        entry = read(ROOT / 'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
        checkpoint = model_directory(entry)
        checkpoint_hashes = {name: sha256(checkpoint / name) for name in entry['files_sha256']}
        if checkpoint_hashes != entry['files_sha256']:
            raise ValueError('Acquired checkpoint no longer matches its manifest')
        record.update(vendor_revision=vendor_revision, model_revision=entry['revision'],
                      checkpoint_files_sha256=checkpoint_hashes, torch=torch.__version__,
                      cuda_runtime=torch.version.cuda)
        methods = ['scripts/kimodo_adapter_probe.py', 'scripts/strep.py', 'scripts/action_worker_lock.py',
                   'benchmarks/sources.lock.json', 'vendor/kimodo/kimodo/model/backbone.py',
                   'vendor/kimodo/kimodo/model/twostage_denoiser.py', 'vendor/kimodo/kimodo/model/loading.py']
        record['methods_sha256'] = {}
        for name in methods:
            destination = output / 'methods' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
            record['methods_sha256'][name] = sha256(destination)
        save(result_path, record)
        if not torch.cuda.is_available():
            raise RuntimeError('The real-checkpoint memory audit requires CUDA')
        record['gpu'] = torch.cuda.get_device_name()
        record['initial_free_bytes'], record['device_total_bytes'] = torch.cuda.mem_get_info()
        torch.set_num_threads(2)
        torch.manual_seed(seed)
        sys.path.insert(0, str(ROOT / 'vendor/kimodo'))
        from omegaconf import OmegaConf
        from kimodo.model.loading import instantiate_from_dict
        config = OmegaConf.merge(OmegaConf.load(checkpoint / 'config.yaml'),
                                 OmegaConf.create({'checkpoint_dir': str(checkpoint)}))
        model = instantiate_from_dict(OmegaConf.to_container(config, resolve=True)['denoiser'])
        record['base_parameter_count'] = sum(p.numel() for p in model.parameters())
        before = fingerprint(model)
        model = model.cuda()
        dim = model.motion_rep.motion_rep_dim
        root_dim = model.motion_rep.global_root_dim
        record.update(motion_dimension=dim, root_dimension=root_dim, base_fingerprint_before=before)
        # Inputs are an allocation/gradient stress test, not valid captured motion.
        def inputs(count):
            return dict(x=torch.randn(1, count, dim, device='cuda'),
                        x_pad_mask=torch.ones(1, count, dtype=torch.bool, device='cuda'),
                        text_feat=torch.zeros(1, 1, 4096, device='cuda'),
                        text_feat_pad_mask=torch.ones(1, 1, dtype=torch.bool, device='cuda'),
                        timesteps=torch.tensor([500], device='cuda'),
                        first_heading_angle=torch.zeros(1, device='cuda'))
        sample = inputs(frames[0])
        model.eval()
        with unfused_transformer(), torch.no_grad():
            reference = model(**sample)
        with unfused_transformer(), feedforward_adapters(model, rank, rank) as adapters:
            record['target_modules'] = [name for name, _ in adapters]
            record['adapter_parameter_count'] = sum(p.numel() for _, a in adapters for p in (a.a, a.b))
            with torch.no_grad():
                adapted = model(**sample)
            record['initial_output_max_delta'] = float((reference - adapted).abs().max())
            if record['initial_output_max_delta'] != 0:
                raise RuntimeError('Zero-output adapters changed the initial prediction')
            del reference, adapted, sample
            model.train()
            for count in frames:
                model.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                start = time.perf_counter()
                args = inputs(count)
                prediction = model(**args)
                loss = prediction.square().mean()
                loss.backward()
                torch.cuda.synchronize()
                gradients = gradient_report(adapters)
                row = {'frames': count, 'elapsed_seconds': time.perf_counter() - start,
                       'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                       'peak_reserved_bytes': torch.cuda.max_memory_reserved(),
                       'loss': float(loss.detach()), 'output_finite': bool(torch.isfinite(prediction).all()),
                       'base_gradients_present': any(p.grad is not None for p in model.parameters() if not p.requires_grad),
                       'gradients': gradients}
                record['rows'].append(row)
                save(result_path, record)
                if not row['output_finite'] or row['base_gradients_present'] or not all(
                        g['b']['present'] and g['b']['finite'] and g['b']['norm'] > 0
                        and g['a']['present'] and g['a']['finite'] and g['a']['norm'] == 0 for g in gradients):
                    raise RuntimeError('Unexpected first-backward gradient routing')
                del args, prediction, loss
                print(json.dumps({k: v for k, v in row.items() if k != 'gradients'}), flush=True)
            # Verify the published training branch's root detachment directly.
            model.zero_grad(set_to_none=True)
            prediction = model(**inputs(frames[0]))
            prediction[..., root_dim:].square().mean().backward()
            gradients = gradient_report(adapters)
            record['body_only_gradients'] = gradients
            for g in gradients:
                if g['name'].startswith('root_model'):
                    if g['b']['present'] and g['b']['norm'] != 0:
                        raise RuntimeError('Body loss unexpectedly reaches the root stage')
                elif not g['b']['present'] or not g['b']['finite'] or g['b']['norm'] <= 0:
                    raise RuntimeError('Body adapter did not receive a finite gradient')
            del prediction
        after = fingerprint(model)
        record.update(base_fingerprint_after=after, base_unchanged=(before == after))
        if before != after:
            raise RuntimeError('The base parameters changed')
        model.zero_grad(set_to_none=True)
        del model
        torch.cuda.empty_cache()
        record['status'] = 'complete'
    except Exception as exc:
        record.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        if checkpoint_hashes is not None:
            record['checkpoint_files_after_sha256'] = {name: sha256(checkpoint / name) for name in checkpoint_hashes}
            record['checkpoint_files_unchanged'] = checkpoint_hashes == record['checkpoint_files_after_sha256']
            if not record['checkpoint_files_unchanged']:
                record['status'] = 'failed'
        record['finished_at'] = now()
        save(result_path, record)
    if record['status'] != 'complete':
        raise RuntimeError('Checkpoint integrity failed')
    return record


def main():
    from strep import offline_environment
    from action_worker_lock import worker_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', nargs='+', type=int, default=[30, 120, 300])
    parser.add_argument('--rank', type=int, default=8)
    parser.add_argument('--seed', type=int, default=1234)
    args = parser.parse_args()
    os.environ.update(offline_environment())
    with worker_lock():
        run(args.output, args.frames, args.rank, args.seed)


if __name__ == '__main__':
    main()
