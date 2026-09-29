"""Read-only integrity check of a completed contact study's frozen evidence.

Uses saved implementation copies, never imports them or compares them to today's
solver. Hash consistency is not authenticity, a rerun, or motion-quality approval.
Original external inputs must still be available at their recorded locations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def read(path):
    return json.loads(Path(path).read_bytes())


def bound_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError('Archive member escapes its folder: ' + str(name))
    return path


def check_hash(path, digest):
    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
        raise ValueError('Invalid SHA256: ' + str(path))
    with Path(path).open('rb') as stream:
        hasher = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
        actual = hasher.hexdigest()
    if actual != digest:
        raise ValueError('Archived artifact changed: ' + str(path))


def check_members(root, mapping):
    for name, digest in mapping.items():
        check_hash(bound_path(root, name), digest)


def verify_job(folder, implementation, mesh_hashes):
    frozen = read(folder / 'checked-freeze.json')
    if frozen['implementation'] != implementation:
        raise ValueError('Job and study method snapshots differ')
    if frozen['mesh_sha256'] not in mesh_hashes:
        raise ValueError('Job mesh is not a verified study input')
    check_members(folder / 'implementation', frozen['implementation'])
    check_members(folder, frozen['inputs'])


def verify_archive(suite, followup):
    suite, followup = Path(suite).resolve(), Path(followup).resolve()
    frozen = read(suite / 'freeze.json')
    check_hash(suite / 'protocol.json', frozen['protocol_sha256'])
    check_members(suite / 'implementation', frozen['implementation'])
    for path, digest in frozen['inputs'].items():
        check_hash(Path(path), digest)
    if read(suite / 'pipeline.json')['status'] != 'numerical_batch_complete':
        raise ValueError('Numerical study is not complete')
    if read(followup / 'pipeline.json')['status'] != 'complete':
        raise ValueError('Engine follow-up is not complete')
    completion = read(followup / 'completion.json')
    for path, digest in completion['inputs'].items():
        check_hash(Path(path), digest)
    declared = [row['id'] for row in read(suite / 'protocol.json')['cases']]
    actual = [row['case'] for row in completion['cases']]
    if not declared or len(set(declared)) != len(declared) or actual != declared:
        raise ValueError('Completion does not cover the declared cases exactly')
    poses, passes = 0, 0
    for row in completion['cases']:
        case_id = row['case']
        case_path = bound_path(suite / 'cases', case_id + '.json')
        if str(case_path) not in row['files']:
            raise ValueError('Case result missing from completion hashes')
        for path, digest in row['files'].items():
            check_hash(Path(path), digest)
        case = read(case_path)
        if case['status'] != 'complete' or case['id'] != case_id:
            raise ValueError('Case result is incomplete or mismatched')
        fit, repair = Path(case['fit_job']), Path(case['repair_job'])
        for folder in [fit, repair]:
            verify_job(folder, frozen['implementation'], set(frozen['inputs'].values()))
            if read(folder / 'pipeline.json')['status'] != 'complete':
                raise ValueError('Archived job is incomplete')
        if read(repair / 'completion.json') != case['repair']:
            raise ValueError('Repair completion differs from case result')
        check_members(repair, case['repair']['files'])
        trials = read(fit / 'result/summary.json')['trials']
        if len(trials) != 1:
            raise ValueError('Expected one retained fitted candidate')
        seed = bound_path(fit / 'result/takes', trials[0]['id'])
        check_members(seed, trials[0]['hashes'])
        engine = bound_path(suite / 'engine', case_id)
        engine_path = engine / 'verification.json'
        recheck = bound_path(followup / 'rechecks', case_id)
        for path in [engine_path, engine / 'request.json', engine / 'engine-output.json', recheck / 'verification.json']:
            if str(path) not in row['files']:
                raise ValueError('Engine record missing from completion hashes')
        evidence = read(engine_path)
        for path, digest in evidence['files'].items():
            check_hash(Path(path), digest)
        check_members(engine / 'project', evidence['runtime'])
        for name in ['request.json', 'engine-output.json']:
            check_hash(recheck / name, row['files'][str(engine / name)])
        count = sum(check['pose_observations'] for check in evidence['checks'])
        passed = case['repair']['checked_contact_export_screen_passed']
        if not row['engine_passed'] or not evidence['engine_passed'] or not all(c['passed'] for c in evidence['checks']):
            raise ValueError('Engine verification did not pass')
        if row['pose_observations'] != count or row['contact_screen'] != passed:
            raise ValueError('Aggregate case counters differ from evidence')
        poses += count
        passes += bool(passed)
    if (completion['cases_verified'], completion['engine_pose_observations'], completion['contact_screen_passes']) != (len(declared), poses, passes):
        raise ValueError('Completion counters differ from evidence')
    return dict(integrity_verified=True, cases=len(declared), engine_pose_observations=poses,
                contact_screen_passes=passes, current_solver_compared=False,
                study_rerun=False, quality_approved=False,
                scope='Saved snapshots and recorded artifact hashes; not authenticity, replay or human review.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', type=Path)
    parser.add_argument('followup', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.suite, args.followup), indent=2))
