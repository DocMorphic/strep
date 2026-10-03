"""Ablations never change original serialized acceptance or select an asset."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_foot_plant import setup
from native_plant_rate_diagnosis import DiagnosticPlantProblem, MODES, run, original_rate_details
from native_joint_plant import JointPlantProblem
from native_support_feasibility import colored_jacobian
from native_joint_plant_job import authored_audit
from native_foot_plant import propose
from strep import save, read, sha256
from sampled_motion_caps import features, measures
import native_plant_rate_diagnosis as diagnostic


@pytest.mark.parametrize('mode', tuple(MODES))
def test_only_named_rate_rows_are_omitted_with_raw_and_shadow_models(tmp_path, mode):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    p = DiagnosticPlantProblem(rig, reader, rows, limits, reader, mode=mode)
    original = JointPlantProblem(rig, reader, rows, limits, reader)
    x = p.initial.copy()
    x[p.data[0]['ids'][2, 1]] = [.0003, -.0001, .0002]
    values, _ = p.rotations(x)
    world = p.world(values)
    np.testing.assert_array_equal(p.original_constraints(values, world), original.constraints(values, world))
    for shadow in (False, True):
        baseline = original.model(x, quantized=True, native_roundtrip=shadow)
        actual = p.model(x, quantized=True, native_roundtrip=shadow)
        expected = baseline.copy()
        count = len(expected) // (2 if shadow else 1)
        for copy in range(2 if shadow else 1):
            for metric in MODES[mode]:
                section = p.rate_slices()[metric]
                expected[copy * count + section.start:copy * count + section.stop] = 0.
        np.testing.assert_array_equal(actual, expected)
        pattern = p.sparsity(native_roundtrip=shadow)
        assert pattern.shape == (len(actual), len(x))
        for copy in range(2 if shadow else 1):
            for metric in MODES[mode]:
                section = p.rate_slices()[metric]
                assert pattern[copy * count + section.start:copy * count + section.stop].nnz == 0
        retained = expected != 0
        np.testing.assert_array_equal(pattern[retained].toarray(),
                                      original.sparsity(native_roundtrip=shadow)[retained].toarray())
    assert all(np.array_equal(a, b) for a, b in zip(p.caps.caps, original.caps.caps))


def test_omitted_rate_graph_still_covers_actual_contact_and_support_derivatives(tmp_path):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    p = DiagnosticPlantProblem(rig, reader, rows, limits, reader, mode='omit_all_rates')
    pattern = p.sparsity(native_roundtrip=True)
    function = lambda x: p.model(x, quantized=True, native_roundtrip=True)
    x = p.initial.copy()
    grouped = colored_jacobian(function, x, p.lower, p.upper, pattern, step=1e-5).toarray()
    full = np.column_stack([(function(x + np.eye(1, len(x), k=j).ravel() * 1e-5)
                             - function(x)) / 1e-5 for j in range(len(x))])
    np.testing.assert_allclose(grouped, full, atol=1e-7, rtol=0)


def test_original_rate_locations_use_unchanged_all_joint_bins_even_if_omitted(tmp_path):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    p = DiagnosticPlantProblem(rig, reader, rows, limits, reader, mode='omit_all_rates')
    x = p.initial.copy()
    x[p.data[0]['ids'][2, 1]] = [.003, -.001, .002]
    values, _ = p.rotations(x)
    world = p.world(values)
    actual = measures(features(world[p.rate_ids], rig.joints), p.caps.dt)
    details = original_rate_details(p, world)
    assert any(row['failed_rows'] for row in details)
    for metric, row in enumerate(details):
        excess = actual[metric] - p.caps.caps[metric] - p.caps.tolerance
        assert row['failed_rows'] == np.count_nonzero(excess > 0)
        if row['failed_rows']:
            sample, col = np.unravel_index(np.argmax(excess), excess.shape)
            assert row['worst']['node'] == rig.joints[col]
            assert row['worst']['actual'] == actual[metric][sample, col]
            assert row['worst']['source_bin_cap'] == p.caps.caps[metric][sample, col]
            assert row['worst']['excess'] == excess[sample, col]
        else:
            assert row['worst'] is None


@pytest.mark.parametrize('options', [dict(mode=None), dict(mode='auto'), dict(mode=[]),
    dict(iterations=True), dict(iterations=0), dict(trust=float('nan')), dict(trust=.03)])
def test_bad_diagnostic_options_fail_before_reading_inputs(options):
    with pytest.raises(ValueError):
        run(None, None, None, None, None, **options)


@pytest.mark.parametrize('mode', ('original', 'omit_all_rates'))
def test_real_serialized_probes_keep_original_gates_and_never_select(tmp_path, mode):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    seed = tmp_path / 'seed.glb'
    propose(rig, reader, rig, reader, rows, seed)
    policy_path = tmp_path / 'policy.json'
    save(policy_path, policy)
    output = tmp_path / 'diagnosis'
    result = run(source, source, draft, policy_path, output, seed=seed, mode=mode, iterations=1)
    assert read(output / 'pipeline.json')['status'] == 'complete'
    assert result['retained_input'] and result['candidate_sha256'] == sha256(source)
    assert (output / 'candidate.glb').read_bytes() == source.read_bytes()
    assert result['original_raw_audit'] == authored_audit(source, output / 'diagnostic.glb', spec, limits)
    assert [r['failed_rows'] for r in result['final_probe']['original_raw_rate_details']] == result['original_raw_audit']['support_screens']['source_rate_failed_rows']
    assert result['diagnostic_only'] and not result['authored_limits_changed']
    assert not result['quality_approved'] and not result['training_admitted'] and not result['release_approved']
    assert not result['engine_contacts_verified'] and not result['native_npz_conversion_verified']
    assert read(output / 'request.json')['policy'] == policy
    hashes = set()
    for probe in result['probes']:
        for path_key, hash_key in (('file', 'sha256'), ('preview_file', 'preview_sha256')):
            assert sha256(output / probe[path_key]) == probe[hash_key]
            hashes.add(probe[hash_key])
        if mode == 'original':
            assert probe['diagnostic_merit'] == probe['original_merit']
    assert result['independently_decoded_unique_glbs'] == len(hashes)
    assert (output / 'implementation/native_plant_rate_diagnosis.py').is_file()
    with pytest.raises(ValueError, match='fresh'):
        run(source, source, draft, policy_path, output, mode=mode)


def test_even_a_passing_satisfactory_source_remains_unapproved_diagnostic(tmp_path):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path, moving=False)
    policy_path = tmp_path / 'policy.json'
    save(policy_path, policy)
    result = run(source, source, draft, policy_path, tmp_path / 'diagnosis', mode='omit_all_rates', iterations=1)
    assert result['original_raw_audit']['passed']
    assert result['final_probe']['diagnostic_model_constraints_pass']
    assert result['retained_input'] and result['diagnostic_only'] and not result['quality_approved']


def test_input_mutation_is_terminal_and_does_not_publish_result(tmp_path, monkeypatch):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path, moving=False)
    policy_path = tmp_path / 'policy.json'
    save(policy_path, policy)
    restore = diagnostic.restore
    def mutate(*args, **kwargs):
        result = restore(*args, **kwargs)
        policy_path.write_bytes(policy_path.read_bytes() + b'\n')
        return result
    monkeypatch.setattr(diagnostic, 'restore', mutate)
    output = tmp_path / 'diagnosis'
    with pytest.raises(ValueError, match='changed'):
        run(source, source, draft, policy_path, output, iterations=1)
    assert read(output / 'pipeline.json')['status'] == 'failed'
    assert not (output / 'result.json').exists()
