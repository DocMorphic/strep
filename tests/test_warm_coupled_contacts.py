"""Warm runs preserve the serialized start unless further closed progress passes."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import warm_coupled_contacts as flow
import action_worker_lock as locks
from test_cumulative_coupled_contacts import fixture, solve_small, independently_check
from strep import read, save, sha256


def start(tmp_path):
    path = tmp_path/'best.npy'
    np.save(path, [1e-7, 0., 0.])
    return path


def check_fallback(output, result, seed):
    assert not result['retained_new_improvement']
    assert result['prior_best_fallback_preserved']
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'), np.load(seed))
    assert result['retained_files']['A']['path'] == str(output/'start/A.glb')
    assert result['retained_files']['A']['sha256'] == sha256(output/'start/A.glb')
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('status', ['MaxTime', 'NoFeasibleImprovingStep'])
def test_no_direction_keeps_prior_best_without_recounting_old_progress(tmp_path, monkeypatch, status):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path/'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status=status)))
    monkeypatch.setattr(flow, 'evaluate_to_cache', lambda *a, **k: pytest.fail('No new improvement'))
    result = flow.run(*paths, output, start_controls=seed, iterations=1)
    check_fallback(output, result, seed)
    assert result['provisional_steps'] == 0 and not result['geometry_checked']
    assert result['start']['contact_score'] == result['final']['contact_score']
    assert result['start']['contact_score'][1] < result['original']['contact_score'][1]
    assert read(output/'request.json')['inputs_sha256'][str(seed)] == sha256(seed)


def test_further_serialized_improvement_needs_complete_geometry_and_rebuilt_models(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path/'out'; origins = []
    linearize = flow.CentralCoupledContactModel.linearize
    def observe(self, x, *args, **kwargs):
        origins.append(x.copy())
        return linearize(self, x, *args, **kwargs)
    monkeypatch.setattr(flow.CentralCoupledContactModel, 'linearize', observe)
    monkeypatch.setattr(flow, 'direction', solve_small)
    result = flow.run(*paths, output, start_controls=seed, iterations=2, backoffs=1)
    assert result['retained_new_improvement'] and not result['prior_best_fallback_preserved']
    assert result['complete_geometry_pass'] and result['provisional_steps'] == 2
    np.testing.assert_array_equal(origins, [[1e-7, 0., 0.], [2e-7, 0., 0.]])
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'), [3e-7, 0., 0.])
    assert result['retained_files'] == result['candidate_files']
    independently_check(paths, output, result)
    for name, digest in result['files_sha256'].items():
        assert sha256(output/name) == digest


def test_failed_fresh_geometry_preserves_prior_best_not_original_source(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch, unsafe_floor=True); seed = start(tmp_path); output = tmp_path/'out'
    monkeypatch.setattr(flow, 'direction', solve_small)
    result = flow.run(*paths, output, start_controls=seed, iterations=1)
    check_fallback(output, result, seed)
    assert result['provisional_steps'] == 1 and result['geometry_checked'] and not result['complete_geometry_pass']
    assert result['candidate_files'] != result['retained_files']
    assert (output/'iteration-1/backoff-0/A.glb').exists()


def test_decoded_native_failure_cannot_replace_best(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); output = tmp_path/'out'
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (np.array([.001, 0., 0.]), dict(status='test')))
    result = flow.run(*paths, output, start_controls=seed, iterations=1, backoffs=1)
    check_fallback(output, result, seed)
    assert not result['geometry_checked']
    assert read(output/'iteration-1/backoff-0/decision.json')['native_failed_rows'] > 0


@pytest.mark.parametrize('seed_value', [[.5, 0., 0.], [-1e-7, 0., 0.]])
def test_infeasible_or_regressing_start_rejects_and_keeps_raw_files(tmp_path, monkeypatch, seed_value):
    paths = fixture(tmp_path, monkeypatch); seed = start(tmp_path); np.save(seed, seed_value); output = tmp_path/'out'
    with pytest.raises(ValueError, match='Serialized start'):
        flow.run(*paths, output, start_controls=seed)
    assert (output/'start/A.glb').exists() and read(output/'pipeline.json')['status'] == 'failed'
    assert not (output/'result.json').exists()


def test_busy_worker_or_existing_output_never_overwrites(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path/'out'
    with locks.worker_lock(), pytest.raises(RuntimeError, match='Another'):
        flow.run(*paths, output)
    assert not output.exists()
    output.mkdir(); save(output/'sentinel.json', {'keep': True})
    with pytest.raises(ValueError, match='Fresh'):
        flow.run(*paths, output)
    assert read(output/'sentinel.json') == {'keep': True}


def test_real_cpu_solver_records_checked_proposal_without_claiming_release(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path/'out'
    result = flow.run(*paths, output, start_controls=start(tmp_path), iterations=1,
                      backoffs=3, phase_seconds=1., maximum_iterations=30)
    proposal = read(output/'iteration-1/proposal.json')
    assert result['status'] == 'complete' and not result['quality_approved'] and not result['release_approved']
    if proposal['checked_affine_proposal'] is not None:
        assert proposal['checked_affine_proposal']['requested_affine_backoffs'] == 3
    if result['retained_new_improvement']:
        independently_check(paths, output, result)
    else:
        check_fallback(output, result, tmp_path/'best.npy')
