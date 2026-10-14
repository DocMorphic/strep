"""Separate exports retain source binding and require both acceptance gates.

Orchestration mocks below are explicit; the final test runs numeric export,
authoring and replay with only the synthetic engine execution mocked.
"""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_conditioned_authoring as conditioned
from strep import read, save, sha256
from test_native_scene_authoring_job import authored


def mocks(monkeypatch, *, author_pass=True, fidelity_pass=True, fault=None):
    monkeypatch.setattr(conditioned, 'worker_busy', lambda: False)
    def author(recipe, output):
        _, paths, _, _ = conditioned.validated(recipe)
        output.mkdir(); (output/'actors-engine').mkdir()
        value = dict(status='complete', samples=3, sampled_conditions_pass=author_pass,
            artifacts=dict(active_contacts=str(paths['contacts']), active_policy=str(paths['geometry_policy']), common_policy=None))
        save(output/'result.json', value)
        if fault == 'source':
            source = Path(read(output.parent/'original-inputs/0.json')['contacts']['path'])
            source.write_bytes(source.read_bytes()+b'\n')
        return value
    def fidelity(contacts, policy, engine, originals, output):
        assert set(originals) == set(read(contacts)['actors'])
        assert all(sha256(v['path']) == v['sha256'] for v in originals.values())
        output.mkdir(); value = dict(status='complete', all_original_reference_fidelity_pass=fidelity_pass)
        save(output/'result.json', value)
        if fault == 'prior-evidence': (output.parent/'authoring/result.json').write_bytes(b'changed')
        if fault == 'audit': raise ValueError('deliberate fidelity failure')
        return value
    monkeypatch.setattr(conditioned, 'author', author); monkeypatch.setattr(conditioned, 'fidelity', fidelity)


@pytest.mark.parametrize('author_pass,fidelity_pass', [(True,True),(True,False),(False,True),(False,False)])
def test_acceptance_requires_both_gates_and_retains_originals(tmp_path, monkeypatch, author_pass, fidelity_pass):
    recipe, *inputs = authored(tmp_path)
    before = {str(p):sha256(p) for p in [recipe]+inputs}
    mocks(monkeypatch, author_pass=author_pass, fidelity_pass=fidelity_pass)
    output = tmp_path/'conditioned'; value = conditioned.run(recipe, output)
    assert value['sampled_conditions_pass'] is (author_pass and fidelity_pass)
    assert value['authoring_sampled_conditions_pass'] is author_pass
    assert value['original_reference_fidelity_pass'] is fidelity_pass
    assert value['original_selected'] and not value['studio_selection_changed'] and not value['release_approved']
    assert before == {p:sha256(p) for p in before}
    assert all(sha256(output/p) == h for p,h in value['files_sha256'].items())
    spec = read(output/'derivative-inputs/contacts.json')
    assert all(Path(v['glb']).is_relative_to(output) for v in spec['actors'].values())
    assert read(output/'derivative-inputs/geometry_policy.json')['contacts_sha256'] == sha256(output/'derivative-inputs/contacts.json')


@pytest.mark.parametrize('fault', ['source','prior-evidence','audit'])
def test_source_or_prior_evidence_drift_and_failed_audit_retain_terminal_failure(tmp_path, monkeypatch, fault):
    recipe, *_ = authored(tmp_path); mocks(monkeypatch, fault=fault); output=tmp_path/'conditioned'
    with pytest.raises(ValueError): conditioned.run(recipe, output)
    state = read(output/'pipeline.json')
    assert state['status']=='failed' and state['original_selected'] and not state['release_approved']
    assert not (output/'result.json').exists() and (output/'skin-A/original.glb').is_file()


def test_busy_or_existing_output_does_not_start_export(tmp_path, monkeypatch):
    recipe, *_ = authored(tmp_path); output=tmp_path/'conditioned'
    monkeypatch.setattr(conditioned, 'worker_busy', lambda: True)
    with pytest.raises(ValueError, match='worker'): conditioned.run(recipe, output)
    assert not output.exists()
    output.mkdir()
    with pytest.raises(ValueError, match='Fresh'): conditioned.run(recipe, output)


def test_real_numeric_object_scene_export_and_fidelity_only_engine_mocked(tmp_path, monkeypatch):
    from test_native_object_scene_engine import producers
    path, policy, _, _ = producers(tmp_path, monkeypatch)
    recipe=tmp_path/'recipe.json'
    conditioned.plan(path, policy, tmp_path/'fixture-engine', recipe)
    output=tmp_path/'conditioned'; value=conditioned.run(recipe, output)
    assert value['sampled_conditions_pass'] and value['original_reference_fidelity_pass']
    assert read(output/'authoring/replay/result.json')['all_replayed_observations_exact']
    assert read(output/'original-fidelity/result.json')['additional_engine_executions']==0
    assert not value['quality_approved'] and not value['real_time_playback_verified']
