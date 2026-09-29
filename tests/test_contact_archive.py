import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_contact_archive import check_members, verify_archive, verify_job


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def archive(tmp_path):
    suite = tmp_path / 'suite'; follow = suite / 'follow'
    suite.mkdir(); follow.mkdir()
    asset = tmp_path / 'mesh'; asset.write_bytes(b'mesh')
    implementation = suite / 'implementation'; implementation.mkdir()
    (implementation / 'solver.py').write_bytes(b'old solver')
    methods = {'solver.py': digest(implementation / 'solver.py')}
    save(suite / 'protocol.json', {'cases': [{'id': 'case1'}]})
    save(suite / 'freeze.json', dict(inputs={str(asset): digest(asset)}, implementation=methods,
         protocol_sha256=digest(suite / 'protocol.json')))
    save(suite / 'pipeline.json', {'status': 'numerical_batch_complete'})
    save(follow / 'pipeline.json', {'status': 'complete'})
    for name in ['fit', 'repair']:
        job = tmp_path / name; (job / 'implementation').mkdir(parents=True)
        (job / 'implementation/solver.py').write_bytes(b'old solver')
        (job / 'source').write_bytes(b'motion')
        save(job / 'checked-freeze.json', dict(inputs={'source': digest(job / 'source')},
             implementation=methods, mesh_sha256=digest(asset)))
        save(job / 'pipeline.json', {'status': 'complete'})
    fit, repair = tmp_path / 'fit', tmp_path / 'repair'
    (fit / 'result/takes/take').mkdir(parents=True)
    (fit / 'result/takes/take/motion').write_bytes(b'fitted')
    save(fit / 'result/summary.json', {'trials': [{'id': 'take', 'hashes': {'motion': digest(fit / 'result/takes/take/motion')}}]})
    (repair / 'motion').write_bytes(b'repaired')
    result = dict(checked_contact_export_screen_passed=False, files={'motion': digest(repair / 'motion')})
    save(repair / 'completion.json', result)
    case = suite / 'cases/case1.json'
    save(case, dict(id='case1', status='complete', fit_job=str(fit), repair_job=str(repair), repair=result))
    engine = suite / 'engine/case1'; recheck = follow / 'rechecks/case1'
    for folder in [engine, recheck]:
        save(folder / 'request.json', {'requested': 3})
        save(folder / 'engine-output.json', {'observed': 3})
    (engine / 'project').mkdir()
    (engine / 'project/runtime.gd').write_bytes(b'old engine')
    save(engine / 'verification.json', dict(engine_passed=True,
         checks=[dict(passed=True, pose_observations=3)], files={str(repair / 'completion.json'): digest(repair / 'completion.json')},
         runtime={'runtime.gd': digest(engine / 'project/runtime.gd')}))
    save(recheck / 'verification.json', {'passed': True})
    files = [case, engine / 'verification.json', engine / 'request.json', engine / 'engine-output.json', recheck / 'verification.json']
    save(follow / 'completion.json', dict(inputs={}, cases=[dict(case='case1', files={str(p): digest(p) for p in files},
         engine_passed=True, pose_observations=3, contact_screen=False)],
         cases_verified=1, engine_pose_observations=3, contact_screen_passes=0))
    return suite, follow


def test_historical_check_survives_new_solver_without_importing_old_code(archive):
    suite, follow = archive
    current = suite.parent / 'scripts'; current.mkdir()
    (current / 'solver.py').write_text('raise RuntimeError("must not import current or frozen code")')
    result = verify_archive(suite, follow)
    assert result['integrity_verified'] and result['cases'] == 1
    assert result['engine_pose_observations'] == 3
    assert result['contact_screen_passes'] == 0
    assert not result['quality_approved'] and not result['study_rerun']


@pytest.mark.parametrize('member', [
    'suite/implementation/solver.py', 'fit/implementation/solver.py', 'repair/implementation/solver.py',
    'fit/source', 'repair/source', 'mesh', 'fit/result/takes/take/motion', 'repair/motion',
    'suite/cases/case1.json', 'suite/engine/case1/engine-output.json',
    'suite/engine/case1/project/runtime.gd', 'suite/follow/rechecks/case1/request.json',
])
def test_altered_evidence_is_rejected(archive, member):
    suite, follow = archive
    (suite.parent / member).write_bytes(b'changed')
    with pytest.raises(ValueError):
        verify_archive(suite, follow)


@pytest.mark.parametrize('change', ['pending', 'missing_case', 'duplicate_case', 'inflated_count', 'promoted_pass'])
def test_incomplete_or_relabelled_aggregate_rejected(archive, change):
    suite, follow = archive
    if change == 'pending':
        save(follow / 'pipeline.json', {'status': 'waiting_for_case'})
    else:
        path = follow / 'completion.json'; data = json.loads(path.read_text())
        if change == 'missing_case': data['cases'] = []
        if change == 'duplicate_case': data['cases'] *= 2
        if change == 'inflated_count': data['engine_pose_observations'] += 100
        if change == 'promoted_pass': data['cases'][0]['contact_screen'] = True
        save(path, data)
    with pytest.raises(ValueError): verify_archive(suite, follow)


def test_snapshot_member_cannot_escape_its_root(tmp_path):
    (tmp_path / 'inside').mkdir(); secret = tmp_path / 'other'; secret.write_bytes(b'unrelated')
    with pytest.raises(ValueError, match='escapes'):
        check_members(tmp_path / 'inside', {'../other': digest(secret)})
