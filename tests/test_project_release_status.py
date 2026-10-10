import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from project_release_status import inventory, write_inventory


@pytest.fixture
def project(tmp_path):
    matrix = dict(capabilities=[dict(id='motions', status='in_progress',
                                    development_evidence=['reports/passing-tests.json'], release_evidence=[])],
                  evaluation_design=dict(status='not_frozen', held_out_fixtures=None),
                  gates=dict(status='not_frozen', contact_max=.03, transition_thresholds=None),
                  completion=dict(achieved=False), status='in_progress')
    path = tmp_path / 'benchmarks/matrix.json'; path.parent.mkdir()
    path.write_text(json.dumps(matrix)); return tmp_path, path, matrix


def store(project, change):
    root, path, matrix = project; revised = copy.deepcopy(matrix); change(revised)
    path.write_text(json.dumps(revised)); return root, path


def test_development_passes_do_not_create_release_evidence(project):
    root, path, _ = project
    result = inventory(root, path)
    assert result['capabilities'][0]['development_references'] == 1
    assert result['capabilities'][0]['release_references'] == 0
    assert {g['kind'] for g in result['gaps']} == {'no_release_evidence', 'held_out_fixtures_unbound', 'unset_acceptance_gate'}
    assert not result['quality_approved'] and not result['release_approved']


def test_relocated_complete_inventory_still_does_not_approve_contents(project, tmp_path):
    root, path, matrix = project
    report = root / 'reports/result.json'; report.parent.mkdir(); report.write_text('{"release_approved": true}')
    fixture = root / 'benchmarks/fixtures.json'; fixture.write_text('{}')
    matrix['capabilities'][0].update(status='complete', release_evidence=['reports/result.json'])
    matrix['evaluation_design'].update(status='frozen', held_out_fixtures='benchmarks/fixtures.json')
    matrix['gates'].update(status='frozen', transition_thresholds={})
    matrix['completion']['achieved'] = True; path.write_text(json.dumps(matrix))
    result = inventory(root, path)
    assert len(result['inputs_sha256']) == 3
    assert result['declared_complete']
    assert not result['capabilities'][0]['approval_verified']
    assert not result['held_out_fixtures']['contents_validated']
    assert not result['release_approved']
    assert result['gaps'] == [dict(kind='completion_claim_requires_independent_validation')]


def test_missing_report_is_preserved_as_gap(project):
    result = inventory(*store(project, lambda m: m['capabilities'][0].update(release_evidence=['reports/missing.json'])))
    assert result['capabilities'][0]['release_evidence'][0]['sha256'] is None
    assert any(g['kind'] == 'missing_release_file' for g in result['gaps'])


@pytest.mark.parametrize('reference', ['../secret.json', 'C:/secret.json', '/secret.json', 'reports\\secret.json', 'reports/token.env'])
def test_unsafe_reference_rejected_before_read(project, reference):
    with pytest.raises(ValueError):
        inventory(*store(project, lambda m: m['capabilities'][0].update(release_evidence=[reference])))


def test_duplicate_capability_and_evidence_rejected(project):
    with pytest.raises(ValueError):
        inventory(*store(project, lambda m: m['capabilities'].append(copy.deepcopy(m['capabilities'][0]))))
    with pytest.raises(ValueError):
        inventory(*store(project, lambda m: m['capabilities'][0].update(release_evidence=['reports/x.json'] * 2)))


def test_ambiguous_json_and_nonfinite_gates_rejected(project):
    root, path, _ = project
    path.write_text('{"capabilities": [], "capabilities": [1]}')
    with pytest.raises(ValueError, match='Duplicate'): inventory(root, path)
    path.write_text('{"gates": NaN}')
    with pytest.raises(ValueError, match='Nonfinite'): inventory(root, path)


def test_boolean_completion_cannot_be_truthy_string(project):
    with pytest.raises(ValueError, match='Boolean'):
        inventory(*store(project, lambda m: m['completion'].update(achieved='false')))


def test_fixture_reference_must_be_portable_json(project):
    with pytest.raises(ValueError):
        inventory(*store(project, lambda m: m['evaluation_design'].update(held_out_fixtures='../fixture.json')))
    with pytest.raises(ValueError, match='JSON'):
        inventory(*store(project, lambda m: m['evaluation_design'].update(held_out_fixtures='benchmarks/token.env')))


def test_read_race_rejected(project, monkeypatch):
    import project_release_status as module
    root, path, _ = project; original = module.digest; calls = []
    def changing(p):
        calls.append(p)
        if len(calls) == 2: path.write_text(path.read_text() + ' ')
        return original(p)
    monkeypatch.setattr(module, 'digest', changing)
    with pytest.raises(ValueError, match='changed'): inventory(root, path)


def test_existing_or_external_output_preserved(project):
    root, path, _ = project; output = root / 'reports/status.json'
    result = write_inventory(root, path, output); before = output.read_bytes()
    assert not result['release_approved']
    with pytest.raises(ValueError): write_inventory(root, path, output)
    with pytest.raises(ValueError): write_inventory(root, path, root / 'benchmarks/status.json')
    assert output.read_bytes() == before
