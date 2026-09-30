"""Reproducible local setup, acquisition and execution. Never logs credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'huggingface' / 'hub'
LOCK = ROOT / 'benchmarks' / 'sources.lock.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    # Windows readers/virus scanners can briefly deny rename while holding a
    # handle. Preserve atomic replacement and the old valid JSON throughout.
    for attempt in range(6):
        try:
            temp.replace(path)
            break
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 5:
                raise
            time.sleep(.05 * 2**attempt)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def source_check():
    vendor = ROOT / 'vendor' / 'kimodo'
    if not (vendor / '.git').exists():
        from portable_integrity import verify_vendor
        return verify_vendor(ROOT)
    prefix = ['git', '-c', f'safe.directory={vendor.as_posix()}', '-C', str(vendor)]
    commit = subprocess.check_output(prefix + ['rev-parse', 'HEAD'], text=True).strip()
    if commit != read(LOCK)['kimodo_git_commit']:
        raise RuntimeError('Source commit differs from sources.lock.json')
    if subprocess.check_output(prefix + ['status', '--porcelain'], text=True).strip():
        raise RuntimeError('Vendor checkout has modifications')
    return commit


def model_paths():
    result = {}
    for m in read(LOCK)['models']:
        if m['repo_id'].startswith('nvidia/'):
            path = ROOT / 'models' / 'checkpoints' / m['repo_id'].split('/')[1]
        else:
            path = CACHE / ('models--' + m['repo_id'].replace('/', '--')) / 'snapshots' / m['revision']
        result[m['repo_id']] = path
    return result



def model_directory(entry):
    """Resolve pinned weights in this checkout, retaining historical acquisition paths."""
    if not isinstance(entry, dict) or not isinstance(entry.get('repo_id'), str):
        raise ValueError('Model acquisition entry requires a repository identifier')
    pins = {m['repo_id']: m for m in read(LOCK)['models']}
    repo = entry['repo_id']
    if repo not in pins or entry.get('revision') != pins[repo]['revision']:
        raise ValueError('Model acquisition revision differs from the source lock')
    path = model_paths()[repo].resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Pinned model directory resolves outside the project')
    return path


def doctor(online=False, embedding_manifest=None):
    import psutil
    import torch
    from huggingface_hub import get_token, get_hf_file_metadata, hf_hub_url
    report = {'checked_at': now(), 'python': sys.version, 'executable': sys.executable,
              'kimodo_commit': source_check(), 'torch': torch.__version__,
              'cuda_runtime': torch.version.cuda, 'cuda_available': torch.cuda.is_available(),
              'ram_total_bytes': psutil.virtual_memory().total,
              'ram_available_bytes': psutil.virtual_memory().available,
              'token_configured': bool(get_token()), 'model_paths': {}, 'blockers': []}
    if report['cuda_available']:
        a = torch.arange(16, device='cuda', dtype=torch.float32).reshape(4, 4)
        product = a @ a.T
        torch.cuda.synchronize()
        report['cuda_tensor_test_passed'] = bool(torch.isfinite(product).all().item())
        report['gpu'] = torch.cuda.get_device_name(0)
        report['vram_free_bytes'], report['vram_total_bytes'] = torch.cuda.mem_get_info()
    else:
        report['blockers'].append('CUDA unavailable')
    acquisition = ROOT / 'models/manifest.json'
    acquired = read(acquisition)['models'] if acquisition.exists() else {}
    for repo, path in model_paths().items():
        staged = path.is_dir() and repo in acquired
        report['model_paths'][repo] = {'path': str(path), 'exists': path.is_dir(), 'acquisition_recorded': staged}
        if not staged and (embedding_manifest is None or repo.startswith('nvidia/')):
            report['blockers'].append(f'Missing snapshot: {repo}')
    if embedding_manifest is not None:
        from embedding_cache import CachedEncoder
        cached = CachedEncoder(embedding_manifest)
        report['encoder_mode'] = 'fixed_prompt_cache'
        report['cached_prompt_count'] = len(cached.texts)
    elif report['ram_available_bytes'] < 20 * 1024**3:
        report['blockers'].append('Unchanged CPU text encoder needs more available RAM; use a suitable host or validated exact embedding cache')
    if online:
        model = next(m for m in read(LOCK)['models'] if m['repo_id'].startswith('meta-llama/'))
        try:
            get_hf_file_metadata(hf_hub_url(model['repo_id'], 'config.json', revision=model['revision']), token=get_token())
            report['llama_access'] = 'granted'
        except Exception as exc:
            # Do not serialize request headers, tokens, or exception messages.
            report['llama_access'] = type(exc).__name__
            report['blockers'].append('Gated Llama access not verified')
    save(ROOT / 'reports' / ('doctor-online.json' if online else 'doctor.json'), report)
    print(json.dumps(report, indent=2))
    return report


def acquire(group):
    from huggingface_hub import snapshot_download
    manifest_path = ROOT / 'models' / 'manifest.json'
    manifest = read(manifest_path) if manifest_path.exists() else {'models': {}}
    for model in read(LOCK)['models']:
        motion = model['repo_id'].startswith('nvidia/')
        if (group == 'motion') != motion:
            continue
        kwargs = {'repo_id': model['repo_id'], 'revision': model['revision'],
                  'max_workers': 2, 'ignore_patterns': ['original/*', '*.pth', '*.bin']}
        if motion:
            kwargs['local_dir'] = model_paths()[model['repo_id']]
        else:
            kwargs['cache_dir'] = CACHE
        path = Path(snapshot_download(**kwargs))
        files = {str(p.relative_to(path)).replace('\\', '/'): sha256(p)
                 for p in path.rglob('*') if p.is_file() and '.cache' not in p.relative_to(path).parts}
        # Upstream resolves transitive PEFT base by name. Pin main in our dedicated
        # cache to the requested immutable revision; never touch the user's cache.
        if not motion:
            refs = path.parent.parent / 'refs'
            refs.mkdir(exist_ok=True)
            (refs / 'main').write_text(model['revision'], encoding='utf-8')
        manifest['models'][model['repo_id']] = {**model, 'weights_downloaded': True,
                                              'directory': str(path), 'files_sha256': files}
        manifest['updated_at'] = now()
        save(manifest_path, manifest)
        print(f'Pinned and hashed {model["repo_id"]}: {len(files)} files', flush=True)


def offline_environment():
    env = os.environ.copy()
    env.update({'TEXT_ENCODER_MODE': 'local', 'TEXT_ENCODER_DEVICE': 'cpu',
                'CHECKPOINT_DIR': str(ROOT / 'models' / 'checkpoints'),
                'HF_HUB_CACHE': str(CACHE), 'HUGGINGFACE_CACHE_DIR': str(CACHE),
                'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'LOCAL_CACHE': 'True',
                'PYTHONUNBUFFERED': '1'})
    # Do not inherit a remote encoder or unrelated local checkpoint override.
    env.pop('TEXT_ENCODER_URL', None)
    env.pop('TEXT_ENCODERS_DIR', None)
    return env


def run_job(job, timeout_s=1800, embedding_manifest=None):
    """Preserve blocked/failed attempts too. One subprocess; no shell interpolation."""
    source_check()
    from process_monitor import kill_tree
    base = ROOT / 'runs' / job['id']
    base_resolved = base.resolve()
    if not base_resolved.is_relative_to((ROOT / 'runs').resolve()):
        raise ValueError('Job ID escapes runs directory')
    number = 1
    while True:
        attempt = base / f'attempt-{number:03d}'
        try:
            attempt.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            number += 1
    record = read(ROOT / 'benchmarks' / 'run-record.template.json')
    record.update({k: job[k] for k in ('case_id', 'actor', 'condition', 'seed', 'prompt', 'durations_s')})
    record.update({'attempt_id': str(attempt.relative_to(ROOT)), 'status': 'preflight',
                   'started_at_utc': now(), 'kimodo_git_commit': source_check(),
                   'model_repo_and_revision': {'repo': 'nvidia/Kimodo-SOMA-RP-v1.1', 'revision': job['model_revision']},
                   'rig_file_and_hash': {'path': 'assets/characters/cesium-man/CesiumMan.glb', 'sha256': job['rig_sha256']},
                   'scene_version_and_hash': sha256(ROOT / 'benchmarks/v0.json'),
                   'constraints_file': None})
    packages = ROOT / 'benchmarks/environment.windows.txt'
    if packages.exists():
        record['package_lock'] = {'path': str(packages), 'sha256': sha256(packages)}
    record_path = attempt / 'record.json'
    save(record_path, record)
    start = time.perf_counter()
    process = None
    try:
        import psutil
        probe = doctor(embedding_manifest=embedding_manifest) if embedding_manifest else doctor()
        save(attempt / 'hardware.json', probe)
        record['hardware_report'] = str(attempt / 'hardware.json')
        if probe['blockers']:
            record.update(status='blocked', error_category='preflight', review_notes=probe['blockers'])
            return record_path
        if sha256(ROOT / 'assets/characters/cesium-man/CesiumMan.glb').lower() != job['rig_sha256'].lower():
            raise ValueError('Character differs from benchmark plan')
        if job['benchmark_sha256'] != sha256(ROOT / 'benchmarks/v0.json'):
            raise ValueError('Benchmark changed; regenerate the plan before running')
        manifest = read(ROOT / 'models' / 'manifest.json')
        for model in read(LOCK)['models']:
            if embedding_manifest and not model['repo_id'].startswith('nvidia/'):
                continue
            entry = manifest['models'][model['repo_id']]
            if entry['revision'] != model['revision']:
                raise ValueError('Model manifest revision mismatch')
            for name, digest in entry['files_sha256'].items():
                if sha256(model_directory(entry) / name) != digest:
                    raise ValueError(f'Model checksum mismatch: {name}')
        args = list(job['argv'])
        args[args.index('--output') + 1] = str(attempt / 'source' / 'motion')
        env = offline_environment()
        if embedding_manifest:
            env['STREP_EMBEDDING_MANIFEST'] = str(Path(embedding_manifest).resolve())
            cmd = [sys.executable, str(ROOT / 'scripts/cached_generate.py'), *args]
            record['embedding_cache'] = read(embedding_manifest)
            record['baseline_qualification'] = (
                'Motion checkpoint unchanged. Original-precision encoder uses experimental streamed loading; '
                'small-model equivalence passed, full 8B resident equivalence not measured.'
                if record['embedding_cache']['kind'].startswith('offloaded_') else
                'Motion checkpoint unchanged; fixed outputs from upstream text encoder.')
        else:
            cmd = [sys.executable, '-m', 'kimodo.scripts.generate', *args]
        record.update(command_argv=cmd, status='running', checkpoint_file_hashes=manifest,
                      log_file=str(attempt / 'generation.log'),
                      encoder_device_and_dtype=record['embedding_cache']['kind'] if embedding_manifest else 'cpu / upstream bfloat16')
        (attempt / 'source').mkdir()
        save(record_path, record)
        with (attempt / 'generation.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            peak = 0
            while process.poll() is None:
                try:
                    parent = psutil.Process(process.pid)
                    peak = max(peak, sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)]))
                except psutil.Error:
                    pass
                if time.perf_counter() - start > timeout_s:
                    kill_tree(process.pid)
                    process.wait()
                    raise TimeoutError('Generation exceeded recorded timeout')
                time.sleep(1)
        record.update(exit_code=process.returncode, peak_ram_bytes=peak)
        if process.returncode:
            record.update(status='failed', error_category='generation_subprocess')
        else:
            from inspect_motion import inspect_motion
            output = attempt / 'source' / 'motion.npz'
            provenance = ('generated_original_precision_offload_experiment'
                          if record.get('embedding_cache', {}).get('kind', '').startswith('offloaded_')
                          else 'generated_baseline')
            inspected = inspect_motion(output, attempt / 'inspection', fps=30, provenance=provenance)
            record.update(status='generated_validated', source_motion_file_and_hash={'path': str(output), 'sha256': sha256(output)},
                          metrics=inspected['metrics'], preview_file=str(attempt / 'inspection/preview.html'),
                          root_track_file=str(attempt / 'inspection/root-motion.csv'),
                          contact_and_event_files={'predicted_foot_contacts': str(attempt / 'inspection/contacts.json'), 'gameplay_events': None},
                          source_skeleton_name_and_rest_pose=f'SOMA{inspected["joints"]}, upstream standard T-pose')
    except (Exception, KeyboardInterrupt) as exc:
        if process is not None and process.poll() is None:
            kill_tree(process.pid)
            process.wait()
        record.update(status='failed', error_category=type(exc).__name__, review_notes=str(exc))
    finally:
        record['elapsed_wall_seconds_including_startup'] = time.perf_counter() - start
        save(record_path, record)
    return record_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('doctor'); p.add_argument('--online', action='store_true'); p.add_argument('--embeddings', type=Path)
    p = sub.add_parser('fetch'); p.add_argument('group', choices=['motion', 'encoder'])
    p = sub.add_parser('run'); p.add_argument('--job', default='run_loop/seed-11/unprocessed/actor-A'); p.add_argument('--timeout', type=int, default=1800); p.add_argument('--embeddings', type=Path)
    args = parser.parse_args()
    if args.command == 'doctor':
        doctor(args.online, args.embeddings)
    elif args.command == 'fetch':
        acquire(args.group)
    elif args.command == 'run':
        plan = read(ROOT / 'benchmarks' / 'generated-plan.json')
        job = next(j for j in plan['jobs'] if j['id'] == args.job)
        path = run_job(job, args.timeout, args.embeddings)
        print(path)
        return 0 if read(path)['status'] == 'generated_validated' else 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
