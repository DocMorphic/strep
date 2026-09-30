import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_vendor as source


@pytest.fixture
def project(tmp_path):
    remote = tmp_path/'source mirror'; remote.mkdir(); source.git(remote, 'init', '--quiet')
    def commit(text):
        (remote/'model.py').write_text(text, encoding='utf-8'); source.git(remote, 'add', 'model.py')
        source.git(remote, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                   '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', text)
        return source.git(remote, 'rev-parse', 'HEAD')
    pinned = commit('pinned source'); later = commit('later source')
    root = tmp_path/'project with spaces'; (root/'benchmarks').mkdir(parents=True)
    (root/'benchmarks/sources.lock.json').write_text(json.dumps(dict(kimodo_git_commit=pinned)), encoding='utf-8')
    return root, remote, pinned, later


def test_acquires_exact_pin_instead_of_remote_tip_and_reuses_without_network(project):
    root, remote, pin, _ = project
    result = source.prepare(root, remote=str(remote))
    assert result['status'] == 'prepared' and result['commit'] == pin
    target = root/'vendor/kimodo'
    assert (target/'model.py').read_text(encoding='utf-8') == 'pinned source'
    assert source.git(target, 'branch', '--show-current') == ''
    assert source.prepare(root, remote='nonexistent-mirror')['status'] == 'verified_existing'
    assert source.prepare(root, check_only=True)['status'] == 'verified_existing'
    assert sorted(p.name for p in (root/'vendor').iterdir()) == ['kimodo']


@pytest.mark.parametrize('change', ['tracked', 'untracked', 'revision'])
def test_existing_changes_are_preserved_instead_of_reset_or_cleaned(project, change):
    root, remote, pin, later = project; source.prepare(root, remote=str(remote)); target = root/'vendor/kimodo'
    if change == 'tracked': (target/'model.py').write_text('my edits', encoding='utf-8')
    elif change == 'untracked': (target/'notes.txt').write_text('my notes', encoding='utf-8')
    else:
        source.git(target, 'fetch', '--quiet', 'origin', later); source.git(target, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
    before = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
    head = source.git(target, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match='left unchanged'): source.prepare(root, remote=str(remote))
    assert {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()} == before
    assert source.git(target, 'rev-parse', 'HEAD') == head


def test_occupied_directory_is_not_replaced(project):
    root, remote, _, _ = project; target = root/'vendor/kimodo'; target.mkdir(parents=True)
    (target/'notes.txt').write_text('keep me', encoding='utf-8')
    with pytest.raises(ValueError, match='left unchanged'): source.prepare(root, remote=str(remote))
    assert (target/'notes.txt').read_text(encoding='utf-8') == 'keep me'


def test_check_only_missing_source_has_no_filesystem_side_effect(project):
    root, _, _, _ = project
    with pytest.raises(ValueError, match='missing'): source.prepare(root, check_only=True)
    assert not (root/'vendor').exists()


def test_failed_fetch_retains_staging_and_does_not_publish_incomplete_checkout(project):
    root, remote, _, _ = project
    with pytest.raises(RuntimeError, match='staged files retained'):
        source.prepare(root, remote=str(remote/'missing'))
    assert not (root/'vendor/kimodo').exists()
    assert len(list((root/'vendor').glob('.kimodo-source-*'))) == 1


def test_lock_change_during_fetch_cannot_publish_source(project, monkeypatch):
    root, remote, _, later = project; actual = source.git
    def change(folder, *args):
        result = actual(folder, *args)
        if args[0] == 'fetch':
            (root/'benchmarks/sources.lock.json').write_text(json.dumps(dict(kimodo_git_commit=later)), encoding='utf-8')
        return result
    monkeypatch.setattr(source, 'git', change)
    with pytest.raises(RuntimeError, match='staged files retained'):
        source.prepare(root, remote=str(remote))
    assert not (root/'vendor/kimodo').exists()


@pytest.mark.parametrize('pin', ['main', '--upload-pack=anything', '', None, 'g'*40])
def test_unpinned_or_invalid_revision_is_rejected_before_git(project, pin):
    root, remote, _, _ = project
    (root/'benchmarks/sources.lock.json').write_text(json.dumps(dict(kimodo_git_commit=pin)), encoding='utf-8')
    with pytest.raises(ValueError, match='full lowercase'): source.prepare(root, remote=str(remote))
    assert not (root/'vendor').exists()
