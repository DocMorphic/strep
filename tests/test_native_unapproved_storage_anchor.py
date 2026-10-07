"""Changed absolute storage choices retain actual payloads and original bounds."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_unapproved_storage_anchor as module
from native_unapproved_storage_anchor import assemble
from native_stored_pair_job import Job
from native_rotation_storage_repair import StorageAdjustedEdits
from native_scene_norms import rows
from test_native_static_reference_job import prepare
from test_native_unapproved_anchor import candidate as unchanged_storage_candidate
from strep import read, save, sha256


def candidate(tmp_path, continuous=False, two=False):
    path, _ = prepare(tmp_path)
    job = Job(path)
    rotation = next(e for e in job.edits.actors['A']['tracks'] if e['path'] == 'rotation')
    choices = [dict(actor='A', node=rotation['node'], key_index=int(rotation['ids'][0]), component=3, step=1)]
    if two:
        choices.append(dict(choices[0], key_index=int(rotation['ids'][1])))
    cp = tmp_path / 'choices.json'
    save(cp, choices)
    value = job.value.copy()
    if continuous:
        value[0] += 1e-9
    controls = tmp_path / 'next-controls.npz'
    np.savez(controls, controls=value)
    editor = StorageAdjustedEdits(job.edits.base, read(job.roles['storage_policy']), choices)
    files = {}
    for name in editor.actors:
        target = tmp_path / ('next-' + name + '.glb')
        editor.export(name, value, target)
        files[name] = target
    return path, job, controls, cp, files


@pytest.mark.parametrize('continuous', [False, True])
def test_actual_changed_storage_reopens_original_static_caps_and_all_native_worlds(tmp_path, continuous):
    path, old, controls, cp, files = candidate(tmp_path, continuous)
    inputs = dict(old.inputs, **{str(p): sha256(p) for p in (controls, cp, *files.values())})
    with np.load(controls, allow_pickle=False) as z:
        value = z['controls'].copy()
    out = tmp_path / 'internal'
    result = assemble(path, controls, files, out, corrections_path=cp)
    job = Job(out / 'job.json')
    assert result['schema'] == module.SCHEMA
    assert result['status'] == read(out / 'pipeline.json')['status'] == 'complete'
    assert result['continuous_controls_changed'] is continuous
    assert result['absolute_storage_choices_changed'] and result['new_absolute_choices'] == 1
    assert result['absolute_choices_within_original_storage_envelope']
    assert result['unchanged_original_non_anchor_fields'] and result['original_selected']
    assert not any(result[k] for k in ('geometry_assessed', 'geometry_approved', 'quality_approved', 'release_approved'))
    assert result['native_conditions_pass'] and result['reference_bounds']['passed']
    assert {k: v for k, v in old.request.items() if k != 'anchor'} == {k: v for k, v in job.request.items() if k != 'anchor'}
    assert old.static_reference_keys == job.static_reference_keys == {('A', 0, 'rotation')}
    assert job.request['anchor']['corrections'] == read(cp)
    assert read(out / 'inputs.json') == inputs
    assert (out / 'source-job.json').read_bytes() == path.read_bytes()
    assert (out / 'corrections.json').read_bytes() == cp.read_bytes()
    residual, worlds = old.problem.decoded(files, value)
    native = rows(old.problem, value, worlds)
    again, reopened = job.problem.decoded(job.files, job.value)
    np.testing.assert_array_equal(residual, again)
    with np.load(out / 'observations.npz', allow_pickle=False) as z:
        np.testing.assert_array_equal(value, z['controls'])
        np.testing.assert_array_equal(residual, z['residual'])
        for key in ('vectors', 'caps', 'scales'):
            np.testing.assert_array_equal(getattr(native, key), z[key])
        for name, world in worlds.items():
            np.testing.assert_array_equal(world, reopened[name])
            np.testing.assert_array_equal(world, z[name + '_worlds'])
    assert result['reference_bounds'] == old.reference_bounds(files, worlds)
    for name in files:
        assert files[name].read_bytes() == job.files[name].read_bytes()
        assert files[name].read_bytes() != old.files[name].read_bytes()
    for p, h in inputs.items():
        assert sha256(p) == h
    for p, h in result['files_sha256'].items():
        assert sha256(out / p) == h
    with pytest.raises(ValueError, match='Fresh'):
        assemble(path, controls, files, out, corrections_path=cp)


@pytest.mark.parametrize('fault', ['duplicate', 'step', 'bool-step', 'component', 'node', 'actor', 'key',
                                 'too-many', 'bool-controls', 'nonfinite', 'shape', 'missing-array',
                                 'trust', 'actors', 'payload', 'immutable-parent', 'relative-role'])
def test_false_or_out_of_contract_candidates_reject_before_output(tmp_path, fault):
    path, job, controls, cp, files = candidate(tmp_path)
    choices = read(cp)
    with np.load(controls, allow_pickle=False) as z:
        value = z['controls'].copy()
    if fault == 'duplicate': choices *= 2
    elif fault == 'step': choices[0]['step'] = 2
    elif fault == 'bool-step': choices[0]['step'] = True
    elif fault == 'component': choices[0]['component'] = 4
    elif fault == 'node': choices[0]['node'] = 1000
    elif fault == 'actor': choices[0]['actor'] = 'B'
    elif fault == 'key': choices[0]['key_index'] = 0
    elif fault == 'too-many': choices *= 65
    elif fault == 'bool-controls': value = value.astype(bool)
    elif fault == 'nonfinite': value[0] = np.nan
    elif fault == 'shape': value = value[:-1]
    elif fault == 'trust': value[0] += .03
    elif fault == 'actors': files['B'] = files['A']
    elif fault == 'payload': choices[0]['step'] = -1
    elif fault == 'immutable-parent': save(tmp_path / 'result.json', dict(status='original'))
    elif fault == 'relative-role':
        request = read(path)
        request['source_scene']['path'] = Path(request['source_scene']['path']).name
        save(path, request)
    save(cp, choices)
    np.savez(controls, **{('other' if fault == 'missing-array' else 'controls'): value})
    out = tmp_path / 'internal'
    with pytest.raises(ValueError):
        assemble(path, controls, files, out, corrections_path=cp)
    assert not out.exists()


def test_reordering_identical_choices_cannot_manufacture_a_changed_seed(tmp_path):
    path, job, controls, cp, files = candidate(tmp_path, two=True)
    request = copy.deepcopy(job.request)
    pin = lambda p: dict(path=str(p), sha256=sha256(p))
    request['anchor'].update(controls=pin(controls), corrections=read(cp), actor_files={n: pin(p) for n, p in files.items()})
    new_path = tmp_path / 'reordered-job.json'
    save(new_path, request)
    save(cp, list(reversed(read(cp))))
    out = tmp_path / 'internal'
    with pytest.raises(ValueError, match='Changed controls or storage'):
        assemble(new_path, controls, files, out, corrections_path=cp)
    assert not out.exists()


def test_v1_changed_controls_with_explicit_unchanged_storage_keep_original_contract(tmp_path):
    path, job, controls, files = unchanged_storage_candidate(tmp_path)
    cp = tmp_path / 'choices.json'
    save(cp, job.request['anchor']['corrections'])
    out = tmp_path / 'internal'
    result = assemble(path, controls, files, out, corrections_path=cp)
    reopened = Job(out / 'job.json')
    assert result['continuous_controls_changed'] and not result['absolute_storage_choices_changed']
    assert result['native_conditions_pass'] and result['reference_bounds']['passed']
    assert result['prior_absolute_choices'] == result['new_absolute_choices'] == 0
    assert {k: v for k, v in job.request.items() if k != 'anchor'} == {k: v for k, v in reopened.request.items() if k != 'anchor'}
    assert not reopened.static_reference_keys and not result['geometry_approved']


def test_exact_storage_payload_that_breaks_original_rate_limits_is_rejected(tmp_path):
    path, job, controls, cp, files = candidate(tmp_path)
    value = job.value.copy()
    value[1] = -.02
    np.savez(controls, controls=value)
    editor = StorageAdjustedEdits(job.edits.base, read(job.roles['storage_policy']), read(cp))
    for name in files:
        files[name] = tmp_path / ('rate-violation-' + name + '.glb')
        editor.export(name, value, files[name])
        assert editor.audit(name, files[name], job.scene.actors[name]['animation_index'], value=value)['passed']
    residual, _ = job.problem.decoded(files, value)
    assert np.any(residual > 0)
    out = tmp_path / 'internal'
    with pytest.raises(ValueError, match='Every original decoded'):
        assemble(path, controls, files, out, corrections_path=cp)
    assert not out.exists()


def test_input_mutation_after_preflight_preserves_failed_terminal_and_expected_pins(tmp_path, monkeypatch):
    path, job, controls, cp, files = candidate(tmp_path)
    original = cp.read_bytes()
    expected = sha256(cp)
    real = module.shutil.copyfile
    mutated = []
    def copy_and_mutate(source, target, *args, **kwargs):
        if not mutated:
            cp.write_bytes(original + b' ')
            mutated.append(True)
        return real(source, target, *args, **kwargs)
    monkeypatch.setattr(module.shutil, 'copyfile', copy_and_mutate)
    out = tmp_path / 'internal'
    with pytest.raises(ValueError, match='Input bytes changed'):
        assemble(path, controls, files, out, corrections_path=cp)
    assert read(out / 'failure.json')['status'] == read(out / 'pipeline.json')['status'] == 'failed'
    assert read(out / 'inputs.json')[str(cp)] == expected and sha256(cp) != expected
    assert not (out / 'result.json').exists()
