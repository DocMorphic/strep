"""Metadata read closure only; no synthetic manifest substitutes motion evidence."""
import json
import sys
import shutil
from types import SimpleNamespace
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from studio_transition_fit_read_cache import _Graph, CacheIneligible
from verified_read_cache import VerifiedReadCache
import studio_transition_fit_read_cache as provider


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))


@pytest.fixture
def layout(tmp_path):
    root = tmp_path / 'reports'; root.mkdir(); scripts = tmp_path / 'scripts'; scripts.mkdir()
    (scripts / 'method.py').write_bytes(b'method')
    data = root / 'original.glb'; data.write_bytes(b'fixture payload, not a GLB')
    original = root / 'original-recipe.json'; save(original, {})
    actor = root / 'actor'; scene = root / 'scene'; prior = root / 'prior'; job = root / 'job'
    def artifact(folder, schema, recipe, **extra):
        save(folder / 'prepared.json', dict(schema=schema, recipe_base=str(root), recipe_original_path=str(original), **extra))
        save(folder / 'recipe.json', dict(schema=schema, **recipe))
    artifact(actor, 'strep-native-rig-transition-v1', {}, inputs_sha256={str(data): 'bound', str(original): 'bound'})
    artifact(scene, 'strep-native-scene-transition-v1', {'actors': {'A': {'kind': 'transition', 'folder': str(actor)}}}, inputs={str(data): {}})
    def fit(folder, parent=None):
        save(folder / 'request.json', dict(inputs_sha256={str(data): 'bound'}, source_inputs_sha256={str(original): 'bound'}, resume=None if parent is None else {'source_directory': str(parent)}))
    fit(root / 'ancestor-fit')
    def correction(folder, parent=None):
        artifact(folder, 'strep-native-transition-scene-fit-v1', {'source': {'folder': str(scene)}}, recipe_original=str(original), resume_source=None if parent is None else {'folder': str(parent)})
        fit(folder / 'fit', parent)
    correction(prior, root / 'ancestor-fit'); correction(job / 'candidate', prior / 'fit')
    save(job / 'pipeline.json', {'status': 'complete'})
    save(job / 'request.json', {'schema': 'strep-studio-native-transition-fit-v1', 'source': {'folder': 'scene'}, 'resume_from': {'folder': 'prior'}})
    def graph():
        value = _Graph(root); value.visit('studio', job); return value
    return root, scripts, data, original, actor, scene, prior, job, graph


def test_complete_actor_and_resume_folders_and_external_originals_are_signed(layout):
    root, scripts, data, original, actor, scene, prior, job, factory = layout; graph = factory()
    assert {job, job / 'candidate', job / 'candidate/fit', scene, actor, prior, prior / 'fit', root / 'ancestor-fit'} <= graph.trees
    assert {data, original} <= graph.files
    deps = graph.dependencies(('method.py',), scripts)
    assert scripts / 'method.py' in deps.files and len(deps.discovery_sha256) == len(graph.headers)


@pytest.mark.parametrize('member', ['actor', 'original', 'ancestor', 'candidate', 'method'])
def test_every_dependency_kind_invalidates_a_previously_verified_value(layout, member):
    root, scripts, data, original, actor, scene, prior, job, factory = layout
    target = {'actor': actor / 'new-library.glb', 'original': data,
              'ancestor': root / 'ancestor-fit/new-probe.bin', 'candidate': job / 'candidate/new-output', 'method': scripts / 'method.py'}[member]
    cache = VerifiedReadCache(); calls = []
    def reader(key): calls.append(key); return {'parent_pass': False}
    assert cache.read('job', reader, factory().dependencies(('method.py',), scripts)) == {'parent_pass': False}
    target.write_bytes(b'changed source')
    assert cache.read('job', reader, factory().dependencies(('method.py',), scripts)) == {'parent_pass': False}
    assert calls == ['job', 'job']


def test_root_support_recurses_to_original_transition(layout):
    root, _, _, original, actor, scene, _, _, factory = layout
    supported = root / 'root-supported'
    save(supported / 'prepared.json', {'schema': 'strep-native-transition-root-support-v1', 'recipe_base': str(root), 'recipe_original_path': str(original)})
    save(supported / 'recipe.json', {'schema': 'strep-native-transition-root-support-v1', 'source': {'folder': str(actor)}})
    recipe = json.loads((scene / 'recipe.json').read_text()); recipe['actors']['A'] = {'kind': 'root-support', 'folder': str(supported)}; save(scene / 'recipe.json', recipe)
    assert {supported, actor} <= factory().trees


def test_discovery_change_before_fingerprinting_uses_uncached_full_reader(layout):
    root, scripts, *_rest, job, factory = layout; graph = factory()
    request = json.loads((job / 'request.json').read_text()); request['resume_from'] = None; save(job / 'request.json', request)
    calls = []
    def reader(key): calls.append(key); return {'parent_pass': False}
    cache = VerifiedReadCache(); deps = graph.dependencies(('method.py',), scripts)
    cache.read('job', reader, deps); cache.read('job', reader, deps)
    assert len(calls) == 2 and not cache._entries


def test_cycles_and_node_budget_never_produce_partial_graphs(layout):
    root, _, _, _, _, _, prior, job, factory = layout
    request = json.loads((root / 'ancestor-fit/request.json').read_text()); request['resume'] = {'source_directory': str(prior / 'fit')}; save(root / 'ancestor-fit/request.json', request)
    with pytest.raises(CacheIneligible, match='cycle'): factory()
    with pytest.raises(CacheIneligible, match='budget'): _Graph(root, maximum_nodes=1).visit('studio', job)


def test_outside_metadata_is_rejected_before_reading(layout, monkeypatch):
    root, scripts, _, _, _, scene, _, _, factory = layout
    outside = scripts / 'private'; outside.mkdir()
    recipe = json.loads((scene / 'recipe.json').read_text()); recipe['actors']['A']['folder'] = str(outside); save(scene / 'recipe.json', recipe)
    original = Path.read_bytes
    def guarded(path):
        assert not path.is_relative_to(outside), 'Collector read private metadata'
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    with pytest.raises(CacheIneligible, match='outside'): factory()


@pytest.mark.parametrize('fault', ['unknown-schema', 'processing', 'missing-ancestor'])
def test_unrecognized_or_incomplete_layouts_are_ineligible(layout, fault):
    root, _, _, _, actor, _, _, job, factory = layout
    if fault == 'unknown-schema':
        value = json.loads((actor / 'prepared.json').read_text()); value['schema'] = 'new-version'; save(actor / 'prepared.json', value)
    elif fault == 'processing': save(job / 'pipeline.json', {'status': 'processing'})
    else: (root / 'ancestor-fit/request.json').unlink()
    with pytest.raises((CacheIneligible, FileNotFoundError)): factory()


@pytest.fixture
def transport(layout, monkeypatch):
    root, scripts, data, *_middle, job, _ = layout; calls = []
    for name in ('verified_read_cache.py', 'studio_transition_fit_read_cache.py'):
        shutil.copyfile(Path(provider.__file__).parent / name, scripts / name)
    def full_reader(key):
        calls.append(key)
        status = json.loads((job / 'pipeline.json').read_text())['status']
        return {'status': status, 'retained_failure': data.read_bytes(), 'notes': ['metadata-only stub']}
    stub = SimpleNamespace(ROOT=root.parent, SCRIPT_ROOT=scripts, METHODS=('method.py',),
                           folder_for=lambda key: job, manifest=full_reader)
    monkeypatch.setitem(sys.modules, 'studio_native_transition_scene_fit', stub)
    monkeypatch.setattr(provider, '_CACHE', VerifiedReadCache())
    return layout, calls, stub


def test_public_adapter_reuses_only_full_reader_values_and_invalidates_inputs(transport):
    layout, calls, _ = transport; _, _, data, *_ = layout
    first = provider.manifest('job'); first['notes'].clear()
    assert provider.manifest('job')['notes'] == ['metadata-only stub'] and calls == ['job']
    data.write_bytes(b'changed original input')
    assert provider.manifest('job')['retained_failure'] == b'changed original input'
    assert calls == ['job', 'job']


@pytest.mark.parametrize('fault', ['processing', 'unknown-schema'])
def test_public_adapter_keeps_ineligible_requests_with_the_full_reader(transport, fault):
    layout, calls, _ = transport; _, _, _, _, actor, _, _, job, _ = layout
    if fault == 'processing': save(job / 'pipeline.json', {'status': 'processing'})
    else:
        prepared = json.loads((actor / 'prepared.json').read_text()); prepared['schema'] = 'future'; save(actor / 'prepared.json', prepared)
    assert provider.dependencies('job') is None
    provider.manifest('job'); provider.manifest('job')
    assert calls == ['job', 'job'] and not provider._CACHE._entries


@pytest.fixture
def publication(transport, monkeypatch):
    import hashlib
    layout, calls, stub = transport
    *_, job, _ = layout
    artifact = job / 'candidate/actors/0.glb'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b'not a GLB; metadata-only publication fixture')
    stub.NAMESPACE = 'native-transition-fit-jobs'
    def require(ok, message):
        if not ok: raise ValueError(message)
    stub.require = require
    stub.sha256 = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    original = stub.manifest
    def full(key):
        value = original(key)
        value['files_sha256'] = {'candidate/actors/0.glb': stub.sha256(artifact)}
        return value
    stub.manifest = full
    return layout, calls, stub, artifact


def test_published_resolver_retains_exact_contained_paths_and_cached_review(publication):
    _, calls, _, artifact = publication
    relative = 'native-transition-fit-jobs/job/candidate/actors/0.glb'
    assert provider.served_file(relative) == artifact.resolve()
    assert provider.served_file(relative) == artifact.resolve()
    assert calls == ['job']


@pytest.mark.parametrize('path', ['wrong/job/candidate/actors/0.glb',
    'native-transition-fit-jobs/job/../candidate/actors/0.glb',
    'native-transition-fit-jobs/job/candidate//actors/0.glb',
    'native-transition-fit-jobs/job/candidate/actors/0.glb?x=1',
    'native-transition-fit-jobs/job/candidate/actors/0.glb#x',
    'native-transition-fit-jobs/job/candidate/actors/%30.glb',
    'native-transition-fit-jobs/job/candidate\\actors/0.glb'])
def test_invalid_published_paths_reject_before_any_review(publication, path):
    _, calls, _, _ = publication
    with pytest.raises(ValueError, match='Contained published'):
        provider.served_file(path)
    assert not calls


def test_unpublished_and_processing_artifacts_never_resolve(publication):
    layout, _, _, _ = publication
    with pytest.raises(ValueError, match='Unpublished'):
        provider.served_file('native-transition-fit-jobs/job/request.json')
    *_, job, _ = layout
    save(job / 'pipeline.json', {'status': 'processing'})
    with pytest.raises(ValueError, match='Unpublished'):
        provider.served_file('native-transition-fit-jobs/job/candidate/actors/0.glb')


def test_selected_payload_change_after_manifest_rejects(publication, monkeypatch):
    _, _, _, artifact = publication
    value = provider.manifest('job')
    artifact.write_bytes(b'changed after the verified read')
    monkeypatch.setattr(provider, 'manifest', lambda _: value)
    with pytest.raises(ValueError, match='changed after review'):
        provider.served_file('native-transition-fit-jobs/job/candidate/actors/0.glb')
