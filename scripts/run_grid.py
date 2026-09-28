"""Resume the 25 unprocessed v0 actor jobs; retain every attempt and failure."""
from strep import ROOT, read, save, sha256, now, run_job


def reusable(job):
    for path in sorted((ROOT / 'runs' / job['id']).glob('attempt-*/record.json'), reverse=True):
        record = read(path)
        output = record.get('source_motion_file_and_hash') or {}
        if (record['status'] == 'generated_validated'
                and record['scene_version_and_hash'] == job['benchmark_sha256']
                and record['seed'] == job['seed'] and record['prompt'] == job['prompt']
                and record['model_repo_and_revision']['revision'] == job['model_revision']
                and output and sha256(output['path']) == output['sha256']):
            return path
    return None


def main():
    jobs = [j for j in read(ROOT / 'benchmarks/generated-plan.json')['jobs'] if j['condition'] == 'unprocessed']
    path = ROOT / 'reports/grid-v0.json'
    report = {'started_at': now(), 'status': 'running', 'total_actor_jobs': len(jobs), 'jobs': [],
              'condition': 'unprocessed', 'encoder_variant': 'original_precision_streamed_cache',
              'upstream_cleanup': 'not_run: native MotionCorrection bindings unavailable',
              'quality_acceptance': 'not_implied_by_generation_success'}
    save(path, report)
    try:
        for job in jobs:
            report['current_job'] = job['id']
            save(path, report)
            prior = reusable(job)
            result = prior or run_job(job, embedding_manifest=ROOT / 'models/prompt-cache-v0-offload/manifest.json')
            outcome = read(result)
            report['jobs'].append({'id': job['id'], 'status': outcome['status'],
                                   'record': str(result), 'reused': prior is not None})
            save(path, report)
            print(f'{len(report["jobs"])}/{len(jobs)} {job["id"]}: {outcome["status"]}', flush=True)
        report['status'] = 'completed_with_failures' if any(j['status'] != 'generated_validated' for j in report['jobs']) else 'generated_all'
    finally:
        report['finished_at'] = now()
        save(path, report)


if __name__ == '__main__':
    main()
