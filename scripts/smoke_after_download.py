"""Finish the current download, then try the guarded encoder and one motion clip."""
import argparse
import subprocess
import sys
import time

import psutil
from strep import ROOT, LOCK, read, save, now, run_job


def main(download_pid):
    path = ROOT / 'reports/first-local-run.json'
    status = {'started_at': now(), 'stage': 'waiting_for_download', 'download_pid': download_pid}
    save(path, status)
    try:
        if psutil.pid_exists(download_pid):
            process = psutil.Process(download_pid)
            if 'python' not in process.name().lower() or 'fetch' not in process.cmdline():
                raise RuntimeError('PID does not identify the expected Python download')
            process.wait(timeout=10800)
        manifest = read(ROOT / 'models/manifest.json')['models']
        for model in read(LOCK)['models']:
            if manifest.get(model['repo_id'], {}).get('revision') != model['revision']:
                raise RuntimeError('Download ended without every pinned model being recorded')
        status['stage'] = 'encoding_prompts'
        save(path, status)
        subprocess.run([sys.executable, str(ROOT / 'scripts/guarded_encoder.py')], cwd=ROOT, check=True)
        encoded = read(ROOT / 'reports/encoder-offload.json')
        if encoded['status'] != 'complete':
            raise RuntimeError(f'Encoder stopped: {encoded["status"]}; see encoder-offload.log')
        status['stage'] = 'generating_run_loop'
        save(path, status)
        job = next(job for job in read(ROOT / 'benchmarks/generated-plan.json')['jobs']
                   if job['id'] == 'run_loop/seed-11/unprocessed/actor-A')
        result = run_job(job, embedding_manifest=ROOT / 'models/prompt-cache-v0-offload/manifest.json')
        status.update(stage=read(result)['status'], record=str(result))
    except Exception as error:
        status.update(stage='failed', error_type=type(error).__name__, message=str(error))
    status['finished_at'] = now()
    save(path, status)
    print(status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-pid', type=int, required=True)
    main(parser.parse_args().download_pid)
