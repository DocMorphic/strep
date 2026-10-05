"""Explicit backend provenance with full closed-curve retention/replay gates."""
from pathlib import Path
import sys, subprocess
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import contact_backend_refinement as flow
import verify_contact_backend_refinement as replay
import action_worker_lock as locks
import checked_native_proposal as checked_proposals
from test_cumulative_coupled_contacts import fixture, solve_small, independently_check
from test_warm_coupled_contacts import start, check_fallback
from strep import read, save, sha256


BACKENDS = ['continuous-native', 'stored-native']


@pytest.mark.parametrize('backend', BACKENDS)
@pytest.mark.parametrize('status', ['MaxTime', 'NoFeasibleImprovingStep'])
def test_explicit_backend_records_complete_identity_and_keeps_start_without_new_progress(tmp_path, monkeypatch, backend, status):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path / 'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status=status)))
    monkeypatch.setattr(flow, 'evaluate_to_cache', lambda *a, **k: pytest.fail('No new improvement'))
    result = flow.run(*paths, output, proposal_backend=backend, start_controls=seed, iterations=1)
    check_fallback(output, result, seed)
    request = read(output / 'request.json'); model = read(output / 'iteration-1/model.json')
    assert request['schema'] == 'strep-contact-backend-refinement-request-v1'
    assert result['schema'] == 'strep-contact-backend-refinement-result-v1'
    assert request['proposal_backend'] == result['proposal_backend'] == model['proposal_backend'] == backend
    expected = flow.BACKENDS[backend].__module__ + '.' + flow.BACKENDS[backend].__qualname__
    assert request['proposal_factory_class'] == result['proposal_factory_class'] == expected
    assert model['native']['difference_source'] == ('stored' if backend == 'stored-native' else 'continuous')
    assert model['contact']['difference_source'] == 'continuous'
    assert 'contact_backend_refinement.py' in request['implementation_sha256']
    assert 'stored_native_coupled_contacts.py' in request['implementation_sha256']
    assert result['provisional_steps'] == 0 and not result['geometry_checked']
    verified = replay.run(output, tmp_path / 'replay')
    assert verified['proposal_backend'] == backend and verified['retained_claim_reproduced']
    assert verified['geometry'] is None and not verified['release_approved']


@pytest.mark.parametrize('backend', BACKENDS)
def test_further_refinement_rebuilds_selected_backend_and_replays_every_tiny_geometry_array(tmp_path, monkeypatch, backend):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path / 'out'; origins = []
    factory = flow.BACKENDS[backend]; original = factory.linearize
    def observe(self, value, *args, **kwargs):
        origins.append(value.copy())
        return original(self, value, *args, **kwargs)
    monkeypatch.setattr(factory, 'linearize', observe)
    monkeypatch.setattr(checked_proposals, 'legacy_direction', solve_small)
    result = flow.run(*paths, output, proposal_backend=backend, start_controls=seed, iterations=2, backoffs=1)
    assert result['retained_new_improvement'] and result['complete_geometry_pass']
    np.testing.assert_array_equal(origins, [[1e-7, 0, 0], [2e-7, 0, 0]])
    np.testing.assert_array_equal(np.load(output / 'retained-controls.npy'), [3e-7, 0, 0])
    independently_check(paths, output, result)
    checked = replay.run(output, tmp_path / 'replay')
    assert checked['proposal_backend'] == backend and checked['retained_claim_reproduced']
    assert checked['geometry']['geometry_queries_rerun'] and checked['geometry']['all_numeric_geometry_outputs_exact']
    for name, digest in result['files_sha256'].items(): assert sha256(output / name) == digest


@pytest.mark.parametrize('backend', BACKENDS)
def test_failed_full_geometry_preserves_start_for_either_backend(tmp_path, monkeypatch, backend):
    paths = fixture(tmp_path, monkeypatch, unsafe_floor=True); seed = start(tmp_path); output = tmp_path / 'out'
    monkeypatch.setattr(checked_proposals, 'legacy_direction', solve_small)
    result = flow.run(*paths, output, proposal_backend=backend, start_controls=seed, iterations=1)
    check_fallback(output, result, seed)
    assert result['geometry_checked'] and not result['complete_geometry_pass']
    checked = replay.run(output, tmp_path / 'replay')
    assert not checked['geometry']['sampled_conditions_pass'] and checked['retained_claim_reproduced']


@pytest.mark.parametrize('backend', BACKENDS)
def test_exported_native_failure_is_preserved_as_rejection_not_accepted_affine_success(tmp_path, monkeypatch, backend):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path / 'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (np.array([.001, 0, 0]), dict(status='test-external-proposal')))
    result = flow.run(*paths, output, proposal_backend=backend, start_controls=seed, iterations=1, backoffs=1)
    check_fallback(output, result, seed)
    assert read(output / 'iteration-1/backoff-0/decision.json')['native_failed_rows'] > 0
    # This deliberately injected unchecked direction tests the downstream gate.
    # It cannot be presented as a fully replayed affine proposal.
    with pytest.raises(AssertionError): replay.run(output, tmp_path / 'replay')


@pytest.mark.parametrize('backend', [None, True, '', 'unknown', 'stored', 1])
def test_invalid_backend_rejects_before_reading_assets_or_creating_output(tmp_path, backend):
    output = tmp_path / 'out'
    with pytest.raises(ValueError, match='explicit'):
        flow.run(*[tmp_path / 'absent'] * 4, output, proposal_backend=backend)
    assert not output.exists()


def test_cli_requires_explicit_backend(tmp_path):
    command = [sys.executable, str(Path(flow.__file__)), *[str(tmp_path / 'absent')] * 5]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2 and '--proposal-backend' in result.stderr
    assert not (tmp_path / 'absent').exists()


@pytest.mark.parametrize('backend', BACKENDS)
def test_busy_worker_and_existing_outputs_are_not_overwritten(tmp_path, monkeypatch, backend):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path / 'out'
    with locks.worker_lock(), pytest.raises(RuntimeError, match='Another'):
        flow.run(*paths, output, proposal_backend=backend)
    assert not output.exists()
    output.mkdir(); save(output / 'sentinel.json', dict(keep=True))
    with pytest.raises(ValueError, match='Fresh'): flow.run(*paths, output, proposal_backend=backend)
    assert read(output / 'sentinel.json') == dict(keep=True)


@pytest.mark.parametrize('fault', ['request-backend', 'factory', 'result-backend', 'model-backend',
    'native-source', 'contact-source', 'storage-bound-claim'])
def test_rebound_inventory_cannot_hide_backend_or_derivative_source_forgery(tmp_path, monkeypatch, fault):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path / 'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status='MaxTime')))
    flow.run(*paths, output, proposal_backend='stored-native', start_controls=start(tmp_path), iterations=1)
    result = read(output / 'result.json')
    if fault in ('request-backend', 'factory'):
        request = read(output / 'request.json')
        if fault == 'request-backend': request['proposal_backend'] = 'continuous-native'
        else: request['proposal_factory_class'] = 'wrong.Factory'
        save(output / 'request.json', request)
        result['request_sha256'] = sha256(output / 'request.json')
    elif fault == 'result-backend': result['proposal_backend'] = 'continuous-native'
    else:
        path = output / 'iteration-1/model.json'; model = read(path)
        if fault == 'model-backend': model['proposal_backend'] = 'continuous-native'
        if fault == 'native-source': model['native']['difference_source'] = 'continuous'
        if fault == 'contact-source': model['contact']['difference_source'] = 'stored'
        if fault == 'storage-bound-claim': model['uniform_quantization_error_bound'] = True
        save(path, model)
    result['files_sha256'] = {n: sha256(output / n) for n in result['files_sha256']}
    save(output / 'result.json', result)
    with pytest.raises(AssertionError): replay.run(output, tmp_path / 'replay')


@pytest.mark.parametrize('fault', ['world', 'native', 'contact', 'controls', 'source-cap',
    'model-vector', 'model-cap', 'retained-controls', 'retention-flag'])
def test_rebound_numeric_evidence_is_recomputed_instead_of_trusting_new_hashes(tmp_path, monkeypatch, fault):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path / 'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status='MaxTime')))
    flow.run(*paths, output, proposal_backend='stored-native', start_controls=start(tmp_path), iterations=1)
    result = read(output / 'result.json')
    if fault == 'retention-flag': result['retained_new_improvement'] = True
    elif fault == 'retained-controls':
        path = output / 'retained-controls.npy'; value = np.load(path); value[0] += .001; np.save(path, value)
    else:
        path = output / 'start/conditions.npz'
        if fault == 'source-cap': path = output / 'source.npz'
        if fault in ('model-vector', 'model-cap'): path = output / 'iteration-1/model.npz'
        with np.load(path, allow_pickle=False) as archive: values = {n: archive[n] for n in archive.files}
        if fault == 'world': values['world_A'][0, 0, 0, 3] += .001
        if fault == 'native': values['native'][0] += .001
        if fault == 'contact': values['contact'][0] += .001
        if fault == 'controls': values['controls'][0] += .001
        if fault == 'source-cap': values['A_metric_0'][0, 0] += .001
        if fault == 'model-vector': values['vectors'][0, 0] += .001
        if fault == 'model-cap': values['caps'][0] += .001
        np.savez_compressed(path, **values)
    result['files_sha256'] = {n: sha256(output / n) for n in result['files_sha256']}
    save(output / 'result.json', result)
    with pytest.raises(AssertionError): replay.run(output, tmp_path / 'replay')


@pytest.mark.parametrize('backend', BACKENDS)
def test_actual_bounded_conic_pipeline_can_be_replayed_without_quality_claims(tmp_path, monkeypatch, backend):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path / 'out'
    result = flow.run(*paths, output, proposal_backend=backend, start_controls=start(tmp_path),
        iterations=1, backoffs=3, phase_seconds=1., maximum_iterations=30)
    checked = replay.run(output, tmp_path / 'replay')
    assert checked['schema'] == 'strep-contact-backend-refinement-replay-v1'
    assert checked['proposal_backend'] == backend and checked['retained_claim_reproduced']
    assert not checked['quality_approved'] and not checked['release_approved']
    assert not result['quality_approved'] and not result['release_approved']
