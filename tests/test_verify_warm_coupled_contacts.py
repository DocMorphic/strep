"""Raw warm evidence is recomputed even when an altered inventory is rebound."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import warm_coupled_contacts as flow
import checked_native_proposal as checked
import verify_warm_coupled_contacts as replay
from test_cumulative_coupled_contacts import fixture
from test_native_contact_norms import prepared
from test_native_scene_geometry import policy as geometry_policy
from strep import read, save, sha256


def study(tmp_path, monkeypatch, *, unsafe_floor=False, timeout=False):
    paths = fixture(tmp_path, monkeypatch, unsafe_floor=unsafe_floor)
    best = tmp_path/'best.npy'; np.save(best, [1e-7, 0., 0.])
    def proposal(*args, **kwargs):
        return (None if timeout else np.array([1e-7, 0., 0.])), dict(status='MaxTime' if timeout else 'test-proposal')
    monkeypatch.setattr(checked, 'legacy_direction', proposal)
    out = tmp_path/'study'
    result = flow.run(*paths, out, start_controls=best, iterations=1, backoffs=2)
    return out, result


def rebind(out, *paths):
    result = read(out/'result.json')
    for path in paths: result['files_sha256'][path.relative_to(out).as_posix()] = sha256(path)
    save(out/'result.json', result)


@pytest.mark.parametrize('unsafe_floor', [False, True])
def test_complete_warm_population_affine_and_fresh_geometry_replay(tmp_path, monkeypatch, unsafe_floor):
    out, result = study(tmp_path, monkeypatch, unsafe_floor=unsafe_floor)
    assert result['provisional_steps'] == 1 and result['geometry_checked']
    proof = replay.run(out, tmp_path/'replay')
    assert proof['complete_closed_populations'] == ['start', 'iteration-1/backoff-0']
    assert proof['editable_keys_reconstructed'] == 18 and proof['full_affine_selector_recomputed']
    assert proof['geometry']['geometry_queries_rerun'] and proof['geometry']['complete_samples'] == 3
    assert proof['geometry']['sampled_conditions_pass'] == result['retained_new_improvement'] == (not unsafe_floor)
    assert proof['retained_claim_reproduced'] and proof['uncached_full_surface_contact_recomputed']
    assert not proof['all_derivative_columns_recomputed'] and not proof['release_approved']


def test_noop_replay_preserves_start_without_inventing_new_geometry(tmp_path, monkeypatch):
    out, result = study(tmp_path, monkeypatch, timeout=True)
    proof = replay.run(out, tmp_path/'replay')
    assert proof['complete_closed_populations'] == ['start'] and proof['geometry'] is None
    assert proof['editable_keys_reconstructed'] == 9 and result['prior_best_fallback_preserved']


@pytest.mark.parametrize('population', ['original', 'start', 'final'])
def test_false_condition_summaries_reject(tmp_path, monkeypatch, population):
    out, _ = study(tmp_path, monkeypatch)
    result = read(out/'result.json'); result[population]['surface_failed_rows'] += 1; save(out/'result.json', result)
    with pytest.raises(ValueError, match='summary'):
        replay.run(out, tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


@pytest.mark.parametrize('field', ['retained_new_improvement', 'prior_best_fallback_preserved', 'complete_geometry_pass'])
def test_forged_retention_flags_reject(tmp_path, monkeypatch, field):
    out, _ = study(tmp_path, monkeypatch)
    result = read(out/'result.json'); result[field] = not result[field]; save(out/'result.json', result)
    with pytest.raises(AssertionError): replay.run(out, tmp_path/'replay')


@pytest.mark.parametrize('fault', ['world', 'native', 'contact', 'controls', 'source-cap', 'model-vector', 'model-cap', 'guard', 'retained'])
def test_rebound_inventory_cannot_hide_altered_arithmetic(tmp_path, monkeypatch, fault):
    out, _ = study(tmp_path, monkeypatch)
    path = out/'iteration-1/backoff-0/conditions.npz'
    if fault == 'source-cap': path = out/'source.npz'
    if fault in ('model-vector', 'model-cap', 'guard'): path = out/'iteration-1/model.npz'
    if fault == 'retained':
        path = out/'retained-controls.npy'; value = np.load(path); value[0] += .001; np.save(path, value)
    else:
        with np.load(path, allow_pickle=False) as archive: arrays = {n: archive[n] for n in archive.files}
        if fault == 'world': arrays['world_A'][0, 0, 0, 3] += .001
        if fault == 'native': arrays['native'][0] += .001
        if fault == 'contact': arrays['contact'][0] += .001
        if fault == 'controls': arrays['controls'][0] += .001
        if fault == 'source-cap': arrays['A_metric_0'][0, 0] += .001
        if fault == 'model-vector': arrays['vectors'][0, 0] += .001
        if fault == 'model-cap': arrays['caps'][0] += .001
        if fault == 'guard': arrays['vectors'][-1, 0] += .001
        np.savez_compressed(path, **arrays)
    rebind(out, path)
    with pytest.raises((AssertionError, ValueError)): replay.run(out, tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


@pytest.mark.parametrize('field', ['protected_failed_rows', 'soft_score', 'complete_rows_recomputed', 'fraction'])
def test_full_affine_trial_is_recomputed_after_hashes_rebound(tmp_path, monkeypatch, field):
    out, _ = study(tmp_path, monkeypatch)
    path = out/'iteration-1/proposal.json'; proposal = read(path)
    trial = proposal['checked_affine_proposal']['trials'][0]
    if field == 'soft_score': trial[field][1] += .1
    else: trial[field] += .1
    save(path, proposal); rebind(out, path)
    with pytest.raises(AssertionError): replay.run(out, tmp_path/'replay')


def test_all_serialized_trials_and_decisions_must_be_in_inventory(tmp_path, monkeypatch):
    out, _ = study(tmp_path, monkeypatch)
    result = read(out/'result.json'); del result['files_sha256']['start/conditions.npz']; save(out/'result.json', result)
    with pytest.raises(AssertionError): replay.run(out, tmp_path/'replay')
    assert not (tmp_path/'replay').exists()


@pytest.mark.parametrize('field', ['objective_improves', 'static_edit_audit_pass', 'contact_score'])
def test_rebound_decision_still_requires_complete_decoded_population(tmp_path, monkeypatch, field):
    out, _ = study(tmp_path, monkeypatch)
    path = out/'iteration-1/trials.json'; trials = read(path)
    if field == 'contact_score': trials[0][field][1] += .1
    else: trials[0][field] = not trials[0][field]
    decision = out/'iteration-1/backoff-0/decision.json'
    save(path, trials); save(decision, trials[0]); rebind(out, path, decision)
    with pytest.raises(ValueError, match='decision'): replay.run(out, tmp_path/'replay')


def test_fallback_files_cannot_point_to_provisional_candidate(tmp_path, monkeypatch):
    out, _ = study(tmp_path, monkeypatch, unsafe_floor=True)
    result = read(out/'result.json'); result['retained_files'] = copy.deepcopy(result['candidate_files']); save(out/'result.json', result)
    with pytest.raises(AssertionError): replay.run(out, tmp_path/'replay')


def test_independent_exact_box_rounding_matches_saved_selector_without_new_slack():
    origin = np.array([.1, -.1, .999]); raw = np.array([.02, -.02, .00500000000001])
    value = replay.projected_controls(origin, raw, -np.ones(3), np.ones(3), .02, 1.)
    assert np.all(abs(value-origin) <= .02) and value[0] == np.nextafter(.1+.02, .1)


def test_rebound_start_input_must_match_actual_start_keys(tmp_path, monkeypatch):
    out, _ = study(tmp_path, monkeypatch, timeout=True)
    seed = tmp_path/'best.npy'; np.save(seed, [2e-7, 0., 0.])
    request_path = out/'request.json'; request = read(request_path)
    request['inputs_sha256'][str(seed)] = sha256(seed); save(request_path, request)
    rebind(out, request_path)
    result = read(out/'result.json'); result['request_sha256'] = sha256(request_path); save(out/'result.json', result)
    with pytest.raises(AssertionError): replay.run(out, tmp_path/'replay')


@pytest.mark.parametrize('kind', ['partner', 'moving-object'])
@pytest.mark.parametrize('hold', [False, True])
def test_partner_and_moving_object_populations_replay_without_approving_open_meshes(tmp_path, monkeypatch, kind, hold):
    paths = fixture(tmp_path, monkeypatch); source, permissions_path, surface_path, geometry_path = paths
    _, surface, digest = prepared(tmp_path, partner=kind == 'partner', hold=hold)
    spec = read(source)
    if kind == 'moving-object':
        row = spec['contacts'][0]
        normal = np.asarray(surface['contacts'][row['id']]['target_normal']['normals'][0])
        point = .2*normal; center = np.asarray(row['target']['points_m'][0])-point
        spec['objects']['grip'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.2),
            keyframes=[dict(time_s=t, translation_m=(center+shift).tolist(), rotation_xyzw=[0, 0, 0, 1])
                for t, shift in [(0., np.array([.5, 0, 0])), (.8, np.zeros(3)), (1.2, np.zeros(3)), (2., np.array([-.5, 0, 0]))]])
        row['target'] = dict(space='object', object='grip', points_m=[point.tolist()])
        surface['contacts'][row['id']]['target_normal']['space'] = 'object'
        save(source, spec); digest = sha256(source); surface['contacts_sha256'] = digest
    permissions = read(permissions_path); permissions['contacts_sha256'] = digest
    save(permissions_path, permissions); save(surface_path, surface)
    save(geometry_path, geometry_policy(source, planes=dict(floor=dict(normal_world=[0., 1., 0.], offset_m=-10.))))
    delta = np.array([0., 0., -1e-7]) if kind == 'partner' else np.array([1e-7, 0., 0.])
    monkeypatch.setattr(checked, 'legacy_direction', lambda *a, **k: (delta.copy(), dict(status='test-proposal')))
    out = tmp_path/'study'; result = flow.run(*paths, out, iterations=1, backoffs=2)
    assert result['geometry_checked'] and not result['retained_new_improvement']
    proof = replay.run(out, tmp_path/'replay')
    assert proof['retained_claim_reproduced'] and proof['geometry']['geometry_queries_rerun']
    assert proof['geometry']['object_inputs_exact'] and not proof['geometry']['sampled_conditions_pass']
    if kind == 'partner':
        assert read(source)['actors']['B']['sha256'] == sha256(source.parent/read(source)['actors']['B']['glb'])
