"""Audit native motion targets and conditional x0 gradients, without updates."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time


def run(protocol_path, output):
    from strep import ROOT, read, save, sha256, now, source_check, model_directory
    import numpy as np
    import torch
    from safetensors.torch import save_file
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    from kimodo.model.diffusion import Diffusion
    from kimodo.sanitize import sanitize_texts
    from action_encoder import ActionEncoder
    from action_requests import request_digest
    from motion_profile import resolved_segments
    from kimodo_adapter_probe import feedforward_adapters, unfused_transformer, fingerprint, gradient_report
    from kimodo_denoising_target import encode_native_target, denoising_inputs, clean_motion_loss, capture_full_noise_schedule

    protocol = read(protocol_path)
    if set(protocol) != {'schema', 'job', 'cases', 'timesteps', 'conditions', 'rank', 'noise_seed'} or protocol['schema'] != 'strep-denoising-target-audit-v1':
        raise ValueError('Expected the explicit target-audit protocol')
    if protocol['timesteps'] != [0, 500, 999] or protocol['conditions'] != ['unconstrained', 'first_last_pose']:
        raise ValueError('This audit requires the predeclared schedule endpoints/midpoint and two conditions')
    if type(protocol['rank']) is not int or not 1 <= protocol['rank'] <= 32 or type(protocol['noise_seed']) is not int:
        raise ValueError('Invalid audit rank/seed')
    if not isinstance(protocol['cases'], list) or not protocol['cases'] or any(
        not isinstance(row, dict) or set(row) != {'id', 'seed'} or type(row['seed']) is not int for row in protocol['cases']):
        raise ValueError('Explicit development cases and original seeds required')
    if len({(row['id'], row['seed']) for row in protocol['cases']}) != len(protocol['cases']):
        raise ValueError('Duplicate case/seed')
    if output.exists():
        raise ValueError('Use a fresh output directory; preserve all earlier results')
    output.mkdir(parents=True)
    shutil.copyfile(protocol_path, output / 'protocol.json')
    record = {'schema': 'strep-denoising-target-audit-result-v1', 'status': 'running', 'started_at': now(),
              'protocol_sha256': sha256(protocol_path), 'optimizer_steps': 0,
              'quality_approved': False, 'training_rights_verified': False,
              'scope': 'Existing unreviewed development generation, not clean supervision or learned improvement',
              'targets': [], 'rows': [], 'inputs_sha256': {str(protocol_path): sha256(protocol_path)}}
    result_path = output / 'result.json'
    record['methods_sha256'] = {}
    # Preserve imported implementation even if target preparation fails early.
    for module in tuple(sys.modules.values()):
        raw_path = getattr(module, '__file__', None)
        if raw_path:
            path = Path(raw_path).resolve()
            if path.suffix == '.py' and (path.is_relative_to(ROOT / 'scripts') or path.is_relative_to(ROOT / 'vendor/kimodo/kimodo')):
                relative = path.relative_to(ROOT)
                dest = output / 'methods' / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                record['methods_sha256'][str(relative)] = sha256(path)
    save(result_path, record)
    try:
        record['vendor_revision'] = source_check()
        entry = read(ROOT / 'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
        checkpoint = model_directory(entry)
        record['model_revision'] = entry['revision']
        for name, expected in entry['files_sha256'].items():
            path = checkpoint / name
            if sha256(path) != expected:
                raise ValueError('Checkpoint hash mismatch')
            record['inputs_sha256'][str(path)] = expected
        job = (ROOT / 'reports/action-jobs' / protocol['job']).resolve()
        if job.parent != (ROOT / 'reports/action-jobs').resolve():
            raise ValueError('Expected one completed action-job directory')
        batch = read(job / 'request.json')
        digest = request_digest(batch)
        encoder = ActionEncoder(job / 'conditioning', batch)
        requests = {r['id']: r for r in batch['requests']}
        record['inputs_sha256'][str(job / 'request.json')] = sha256(job / 'request.json')
        record['inputs_sha256'][str(job / 'conditioning/manifest.json')] = sha256(job / 'conditioning/manifest.json')
        torch.set_num_threads(2)
        torch.manual_seed(protocol['noise_seed'])
        config = OmegaConf.merge(OmegaConf.load(checkpoint / 'config.yaml'), OmegaConf.create({'checkpoint_dir': str(checkpoint)}))
        model = instantiate_from_dict(OmegaConf.to_container(config, resolve=True)['denoiser'])
        before = fingerprint(model)
        rep = model.motion_rep
        targets = []
        for case in protocol['cases']:
            if case['id'] not in requests:
                raise ValueError('Case absent from bound request batch')
            take = (job / 'takes' / f"{case['id']}-seed-{case['seed']}").resolve()
            if take.parent != job / 'takes':
                raise ValueError('Take must be inside the action job')
            original = read(take / 'generation-record.json')
            motion_path = take / 'motion.npz'
            if original['status'] != 'generated' or original['request_sha256'] != digest or original['request'] != requests[case['id']] or original['seed'] != case['seed']:
                raise ValueError('Generation request/seed mismatch')
            if original['npz_sha256'] != sha256(motion_path) or original['checkpoint_revision'] != entry['revision'] or original['kimodo_commit'] != record['vendor_revision']:
                raise ValueError('Generated source motion/model mismatch')
            for path in (motion_path, take / 'generation-record.json'):
                record['inputs_sha256'][str(path)] = sha256(path)
            with np.load(motion_path, allow_pickle=False) as archive:
                local = torch.from_numpy(archive['local_rot_mats'].copy())
                roots = torch.from_numpy(archive['root_positions'].copy())
                original_contacts = torch.from_numpy(archive['foot_contacts'].copy())
            start = 0
            for index, segment in enumerate(resolved_segments(requests[case['id']])):
                count = round(segment['duration_s'] * 30)
                clean, heading, details = encode_native_target(rep, local[start:start + count], roots[start:start + count],
                                                               rep.skeleton.somaskel77.bone_order_names, original['fps'])
                if details['roundtrip_joint_max_error_m'] > 1e-4 or details['roundtrip_root_max_error_m'] > 1e-5 or details['roundtrip_local_rotation_max_error'] > 1e-4:
                    raise RuntimeError('Native target roundtrip exceeds the declared numerical tolerance')
                prompt = sanitize_texts([segment['prompt']])[0]
                text, lengths = encoder([prompt])
                if lengths != [1]:
                    raise ValueError('Unexpected encoded text length')
                text = text.to(torch.float32)
                text_entry = encoder.metadata['entries'][prompt]
                text_path = job / 'conditioning' / text_entry['file']
                record['inputs_sha256'][str(text_path)] = text_entry['sha256']
                recomputed = rep.unnormalize(clean)[0, :, rep.slice_dict['foot_contacts']] > .5
                source_contacts = original_contacts[start:start + count]
                if source_contacts.shape[1] == 6:
                    source_contacts = source_contacts[:, [0, 1, 3, 4]]
                target_id = f"{case['id']}-segment-{index}"
                path = output / 'targets' / f'{target_id}.safetensors'
                path.parent.mkdir(exist_ok=True)
                save_file({'clean_features': clean.contiguous(), 'text_features': text.contiguous(),
                           'first_heading': heading.contiguous()}, str(path))
                details.update(id=target_id, case=case['id'], segment=index, source_seed=case['seed'],
                               source_start_frame=start, source_end_frame_exclusive=start + count,
                               prompt=prompt, target_file=str(path), target_sha256=sha256(path),
                               original_contact_difference_count=int((recomputed != (source_contacts > .5)).sum()),
                               contact_comparison_channel_count=recomputed.numel())
                record['targets'].append(details)
                targets.append((target_id, clean, heading, text))
                start += count
            if start != len(local):
                raise ValueError('Requested segment coverage differs from generated frame count')
        # Bind exactly the project/vendor modules imported for preparation.
        methods = set()
        for module in tuple(sys.modules.values()):
            raw_path = getattr(module, '__file__', None)
            if raw_path:
                path = Path(raw_path).resolve()
                if path.suffix == '.py' and (path.is_relative_to(ROOT / 'scripts') or path.is_relative_to(ROOT / 'vendor/kimodo/kimodo')):
                    methods.add(path)
        for path in sorted(methods):
            relative = path.relative_to(ROOT)
            dest = output / 'methods' / relative
            if str(relative) in record['methods_sha256'] and sha256(path) != record['methods_sha256'][str(relative)]:
                raise RuntimeError('An imported method changed during target preparation')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            record['methods_sha256'][str(relative)] = sha256(path)
        save(result_path, record)
        if not torch.cuda.is_available():
            raise RuntimeError('Real-checkpoint gradient audit requires CUDA')
        record.update(gpu=torch.cuda.get_device_name(), torch=torch.__version__, cuda_runtime=torch.version.cuda)
        model = model.cuda().train()
        diffusion = Diffusion(num_base_steps=1000).cuda()
        noise_schedule = capture_full_noise_schedule(diffusion)
        with unfused_transformer(), feedforward_adapters(model, protocol['rank'], protocol['rank']) as adapters:
            for target_index, (target_id, clean, heading, text) in enumerate(targets):
                clean, heading, text = clean.cuda(), heading.cuda(), text.cuda()
                for timestep in protocol['timesteps']:
                    torch.manual_seed(protocol['noise_seed'] + target_index * 1000 + timestep)
                    noise = torch.randn_like(clean)
                    t = torch.tensor([timestep], device='cuda')
                    for condition in protocol['conditions']:
                        known = torch.zeros_like(clean, dtype=torch.bool)
                        if condition == 'first_last_pose':
                            known[:, [0, -1]] = True
                        args = denoising_inputs(clean, noise, t, noise_schedule, text, heading, observed=known)
                        reference_noisy = diffusion.q_sample(clean, t, noise)
                        q_delta = float((args['x'] - reference_noisy).abs().max())
                        if not torch.allclose(args['x'], reference_noisy, atol=1e-6, rtol=1e-6):
                            raise RuntimeError('Base schedule differs from pinned q_sample')
                        model.zero_grad(set_to_none=True)
                        torch.cuda.empty_cache()
                        torch.cuda.reset_peak_memory_stats()
                        torch.cuda.synchronize()
                        started = time.perf_counter()
                        pred = model(**args)
                        objective = clean_motion_loss(pred, clean, args['x_pad_mask'], known)
                        objective['loss'].backward()
                        torch.cuda.synchronize()
                        gradients = gradient_report(adapters)
                        row = {'target': target_id, 'timestep': timestep, 'condition': condition,
                               'q_sample_max_delta': q_delta, 'root_loss': float(objective['root_loss'].detach()),
                               'body_loss': float(objective['body_loss'].detach()),
                               'root_channel_count': objective['root_channel_count'], 'body_channel_count': objective['body_channel_count'],
                               'elapsed_seconds': time.perf_counter() - started,
                               'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                               'peak_reserved_bytes': torch.cuda.max_memory_reserved(),
                               'base_gradients_present': any(p.grad is not None for p in model.parameters() if not p.requires_grad),
                               'gradients': gradients}
                        record['rows'].append(row)
                        save(result_path, record)
                        if row['base_gradients_present'] or not all(g['b']['finite'] and g['b']['norm'] > 0 and g['a']['finite'] and g['a']['norm'] == 0 for g in gradients):
                            raise RuntimeError('Unexpected denoising objective gradient routing')
                        del pred, objective, args, reference_noisy
                print(json.dumps({'target': target_id, 'rows_complete': len(record['rows'])}), flush=True)
        after = fingerprint(model)
        record.update(base_fingerprint_before=before, base_fingerprint_after=after, base_unchanged=before == after)
        if before != after:
            raise RuntimeError('Base checkpoint parameters changed')
        for path, expected in record['inputs_sha256'].items():
            if sha256(path) != expected:
                raise RuntimeError('An original input changed during audit')
        for name, expected in record['methods_sha256'].items():
            if sha256(ROOT / name) != expected:
                raise RuntimeError('An archived/imported method changed during audit')
        record.update(status='complete', input_files_unchanged=True, methods_unchanged=True)
    except Exception as exc:
        record.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        record['finished_at'] = now()
        save(result_path, record)


def main():
    from strep import ROOT, offline_environment
    from action_worker_lock import worker_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    os.environ.update(offline_environment())
    sys.path.insert(0, str(ROOT / 'vendor/kimodo'))
    with worker_lock():
        run(args.protocol, args.output)


if __name__ == '__main__':
    main()
