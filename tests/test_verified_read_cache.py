"""Integrity and concurrency of completed-read reuse; no motion-quality claims."""
import os
import hashlib
import sys
import threading
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verified_read_cache import ReadDependencies, VerifiedReadCache, EvidenceChangedError


@pytest.fixture
def evidence(tmp_path):
    job = tmp_path / 'job'; job.mkdir()
    data = job / 'result.json'; data.write_bytes(b'failed')
    method = tmp_path / 'method.py'; method.write_bytes(b'method')
    return tmp_path, job, data, method, ReadDependencies((method,), (job,), (tmp_path,))


@pytest.mark.parametrize('kind', ['list', 'generator'])
def test_mutable_or_exhaustible_dependency_declarations_reject(tmp_path, kind):
    paths = [tmp_path / 'input'] if kind == 'list' else iter((tmp_path / 'input',))
    with pytest.raises(ValueError, match='Immutable tuples'):
        ReadDependencies(paths, (), (tmp_path,))


def test_changed_discovery_header_prevents_caching_an_incomplete_graph(evidence):
    root, job, data, method, _ = evidence
    seen = hashlib.sha256(data.read_bytes()).hexdigest()
    deps = ReadDependencies((method,), (job,), (root,), ((data, seen),))
    data.write_bytes(b'new graph with different references'); calls = []
    def reader(key): calls.append(key); return data.read_bytes()
    cache = VerifiedReadCache()
    assert cache.read('job', reader, deps) == cache.read('job', reader, deps) == data.read_bytes()
    assert calls == ['job', 'job'] and not cache._entries


def test_discovery_header_must_be_in_the_complete_fingerprint(evidence):
    root, _, data, method, _ = evidence
    deps = ReadDependencies((method,), (), (root,), ((data, hashlib.sha256(data.read_bytes()).hexdigest()),))
    calls = []
    def reader(key): calls.append(key); return data.read_bytes()
    cache = VerifiedReadCache()
    assert cache.read('job', reader, deps) == cache.read('job', reader, deps) == b'failed'
    assert len(calls) == 2 and not cache._entries


def test_reuse_preserves_negative_decisions_and_returns_independent_values(evidence):
    _, _, data, _, deps = evidence; calls = []
    def reader(key):
        calls.append(key); return {'pass': data.read_bytes() == b'passed', 'notes': ['original']}
    cache = VerifiedReadCache(); first = cache.read('job', reader, deps)
    first['pass'] = True; first['notes'].clear()
    assert cache.read('job', reader, deps) == {'pass': False, 'notes': ['original']}
    assert calls == ['job']


@pytest.mark.parametrize('target', ['input', 'method'])
def test_same_size_and_restored_mtime_changes_still_invalidate(evidence, target):
    _, _, data, method, deps = evidence; calls = []
    def reader(key):
        calls.append(key); return (data.read_bytes(), method.read_bytes())
    cache = VerifiedReadCache(); before = cache.read('job', reader, deps)
    changed = data if target == 'input' else method; times = changed.stat()
    changed.write_bytes(b'edited'); os.utime(changed, ns=(times.st_atime_ns, times.st_mtime_ns))
    assert cache.read('job', reader, deps) != before and len(calls) == 2


@pytest.mark.parametrize('change', ['add', 'remove', 'empty-directory'])
def test_exact_population_changes_invalidate(evidence, change):
    _, job, data, _, deps = evidence; calls = []
    def reader(key):
        calls.append(key); return sorted(p.name for p in job.iterdir())
    cache = VerifiedReadCache(); before = cache.read('job', reader, deps)
    if change == 'add': (job / 'unexpected').write_bytes(b'x')
    elif change == 'remove': data.unlink()
    else: (job / 'new-directory').mkdir()
    assert cache.read('job', reader, deps) != before and len(calls) == 2


def test_missing_explicit_dependency_does_not_return_an_old_result(evidence):
    _, _, _, method, deps = evidence
    def reader(key): return method.read_bytes()
    cache = VerifiedReadCache(); assert cache.read('job', reader, deps) == b'method'
    method.unlink()
    with pytest.raises(FileNotFoundError): cache.read('job', reader, deps)


def test_mutation_during_verification_neither_returns_nor_caches(evidence):
    _, _, data, _, deps = evidence; calls = []
    def reader(key):
        calls.append(key); value = data.read_bytes()
        if len(calls) == 1: data.write_bytes(b'edited')
        return value
    cache = VerifiedReadCache()
    with pytest.raises(EvidenceChangedError): cache.read('job', reader, deps)
    assert cache.read('job', reader, deps) == b'edited' and len(calls) == 2


def test_mutation_during_a_cache_hit_does_not_return_stale_evidence(evidence, monkeypatch):
    _, _, data, _, deps = evidence; cache = VerifiedReadCache()
    def reader(key): return data.read_bytes()
    assert cache.read('job', reader, deps) == b'failed'
    original = cache._snapshot; calls = []
    def changing(dependencies):
        snapshot = original(dependencies); calls.append(1)
        if len(calls) == 1: data.write_bytes(b'edited')
        return snapshot
    monkeypatch.setattr(cache, '_snapshot', changing)
    with pytest.raises(EvidenceChangedError): cache.read('job', reader, deps)
    monkeypatch.setattr(cache, '_snapshot', original)
    assert cache.read('job', reader, deps) == b'edited'


@pytest.mark.parametrize('limits', [{'maximum_bytes': 1}, {'maximum_paths': 1}])
def test_budget_excess_uses_full_verification_without_partial_keys(evidence, limits):
    _, _, data, _, deps = evidence; calls = []
    def reader(key): calls.append(key); return data.read_bytes()
    cache = VerifiedReadCache(**limits)
    assert cache.read('job', reader, deps) == cache.read('job', reader, deps) == b'failed'
    assert len(calls) == 2 and not cache._entries


def test_outside_scope_is_not_opened_by_fingerprinting(evidence, tmp_path, monkeypatch):
    root, _, _, _, _ = evidence; allowed = root / 'allowed'; allowed.mkdir()
    outside = root / 'private'; outside.write_bytes(b'private')
    deps = ReadDependencies((outside,), (), (allowed,)); original = Path.open
    def guarded(path, *args, **kwargs):
        assert path != outside, 'Fingerprint opened an external dependency'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    def reader(key): raise ValueError('Full verifier rejects outside scope')
    with pytest.raises(ValueError, match='outside scope'):
        VerifiedReadCache().read('job', reader, deps)


def test_failed_verification_is_not_cached(evidence):
    _, _, data, _, deps = evidence; calls = []
    def reader(key):
        calls.append(key)
        if data.read_bytes() == b'failed': raise ValueError('retained failure')
        return data.read_bytes()
    cache = VerifiedReadCache()
    with pytest.raises(ValueError): cache.read('job', reader, deps)
    data.write_bytes(b'passed'); assert cache.read('job', reader, deps) == b'passed'
    assert len(calls) == 2


def test_distinct_reader_identity_cannot_reuse_another_result(evidence):
    *_, deps = evidence; cache = VerifiedReadCache()
    first = lambda key: 'first'; second = lambda key: 'second'
    assert cache.read('job', first, deps) == 'first'
    assert cache.read('job', second, deps) == 'second'


def test_concurrent_same_key_verifies_once(evidence):
    *_, deps = evidence; entered = threading.Event(); release = threading.Event(); calls = []
    def reader(key):
        calls.append(key); entered.set(); assert release.wait(5); return {'pass': False}
    cache = VerifiedReadCache(); values = []; errors = []
    def run():
        try: values.append(cache.read('job', reader, deps))
        except BaseException as exc: errors.append(exc)
    first = threading.Thread(target=run); first.start(); assert entered.wait(5)
    second = threading.Thread(target=run); second.start(); release.set()
    first.join(5); second.join(5)
    assert not first.is_alive() and not second.is_alive() and not errors
    assert calls == ['job'] and values == [{'pass': False}, {'pass': False}] and not cache._gates


def test_entry_budget_evicts_without_retaining_unbounded_gates(evidence):
    *_, deps = evidence; calls = []
    def reader(key): calls.append(key); return key
    cache = VerifiedReadCache(maximum_entries=2)
    for key in ['one', 'two', 'three', 'one']: assert cache.read(key, reader, deps) == key
    assert calls == ['one', 'two', 'three', 'one'] and len(cache._entries) == 2 and not cache._gates


def test_distinct_keys_can_verify_without_blocking_each_other(evidence):
    *_, deps = evidence; barrier = threading.Barrier(2); values = []; errors = []
    def reader(key): barrier.wait(5); return key
    cache = VerifiedReadCache()
    def run(key):
        try: values.append(cache.read(key, reader, deps))
        except BaseException as exc: errors.append(exc)
    threads = [threading.Thread(target=run, args=(key,)) for key in ['one', 'two']]
    for thread in threads: thread.start()
    for thread in threads: thread.join(5)
    assert all(not thread.is_alive() for thread in threads) and not errors and sorted(values) == ['one', 'two']
