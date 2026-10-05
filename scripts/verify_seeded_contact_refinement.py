"""Replay explicit-seed refinement, closed conditions and full geometry.

The decoder and geometry kernel are shared; scalar/key arithmetic and uncached
contact sampling are recomputed. Saved derivative columns are not recomputed.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_surface_model import include_times
from native_contact_norms import ContactNorms
from coupled_restoration_oracles import oracles, rate_values
from verify_coupled_restoration import score, condition_summary, check_summary, geometry_replay


def projected_controls(value, raw, lower, upper, trust, fraction):
    """Independent exact-box arithmetic for a saved affine/serialized backoff."""
    value, raw, lower, upper = [np.asarray(a, float) for a in (value, raw, lower, upper)]
    assert value.ndim == 1 and value.shape == raw.shape == lower.shape == upper.shape
    assert np.isfinite(np.r_[value, raw, lower, upper, trust, fraction]).all()
    assert trust > 0 and 0 < fraction <= 1 and np.all(lower < upper)
    assert np.all(value >= lower) and np.all(value <= upper)
    used = np.clip(raw, np.maximum(lower-value, -trust), np.minimum(upper-value, trust))
    candidate = np.clip(value+fraction*used, lower, upper)
    for _ in range(2):
        bad = abs(candidate-value) > fraction*trust
        if not np.any(bad): break
        candidate[bad] = np.nextafter(candidate[bad], value[bad])
    assert np.all(candidate >= lower) and np.all(candidate <= upper)
    assert np.all(abs(candidate-value) <= fraction*trust)
    return candidate


def affine_selection(proposal, vectors, caps, scales, jac, value, lower, upper, trust, hard, backoffs):
    """Recompute every recorded affine trial without calling its selector."""
    checked = proposal.get('checked_affine_proposal')
    if checked is None:
        assert not proposal.get('returned_direction_available', False)
        return None
    assert checked['schema'] == 'strep-checked-affine-proposal-v1'
    assert checked['complete_rows'] == len(caps) and checked['protected_rows'] == hard
    assert checked['soft_rows'] == len(caps)-hard and checked['requested_affine_backoffs'] == backoffs
    assert checked['trust_control_fraction'] == trust
    assert checked['strict_affine_feasibility_checked'] and checked['decoded_animation_required']
    assert not any(checked[k] for k in ('protected_slack_added', 'authored_boxes_changed', 'caps_changed',
                                       'quality_approved', 'release_approved'))
    base = (np.linalg.norm(vectors, axis=1)-caps)/scales
    assert np.isfinite(base).all()
    raw = np.asarray(checked['raw_delta'], float)
    assert raw.shape == value.shape and np.isfinite(raw).all()
    assert checked['raw_maximum_control_step'] == float(abs(raw).max())
    assert checked['origin_soft_score'] == score(base[hard:])
    failed = int((base[:hard] > 0).sum())
    assert checked['origin_protected_failed_rows'] == failed
    expected_trials = []; selected = None; selected_index = None; selected_candidate = None
    if not failed:
        for i in range(backoffs):
            fraction = .5**i
            candidate = projected_controls(value, raw, lower, upper, trust, fraction)
            delta = candidate-value
            residual = (np.linalg.norm(vectors+np.asarray(jac@delta).reshape(-1, 3), axis=1)-caps)/scales
            assert np.isfinite(residual).all()
            before, after = score(base[hard:]), score(residual[hard:])
            protected = bool(np.all(residual[:hard] <= 0))
            improves = bool(after[0] <= before[0] and after[1] < before[1]-1e-12)
            expected_trials.append(dict(index=i, fraction=fraction, complete_rows_recomputed=len(caps),
                protected_failed_rows=int((residual[:hard] > 0).sum()),
                protected_maximum_excess=float(residual[:hard].max()) if hard else None,
                soft_score=after, maximum_control_step=float(abs(delta).max()),
                candidate_controls=candidate.tolist(), delta=delta.tolist(), protected_rows_pass=protected,
                soft_objective_improves=improves, chosen=bool(protected and improves)))
            if protected and improves:
                selected = delta; selected_index = i; selected_candidate = candidate; break
    assert checked['trials'] == expected_trials
    assert checked['selected_backoff'] == selected_index
    assert checked['selected_delta'] == (None if selected is None else selected.tolist())
    assert checked['selected_controls'] == (None if selected_candidate is None else selected_candidate.tolist())
    expected_status = 'InfeasibleAffineAnchor' if failed else ('Selected' if selected is not None else 'NoFeasibleImprovingStep')
    assert checked['selection_status'] == expected_status
    assert proposal['returned_direction_available'] == (selected is not None)
    assert proposal['returned_step_maximum_control_fraction'] == (None if selected is None else float(abs(selected).max()))
    assert proposal['independently_decoded_candidate_required']
    return selected


def decoded_decision(before, after, original_contact, label, fraction):
    old, new = condition_summary(before), condition_summary(after)
    regression = after['contact']-np.maximum(before['contact'], 0.)
    guard = bool(np.all(regression <= 0))
    original_guard = bool(np.all(after['contact'] <= np.maximum(original_contact, 0.)))
    improves = bool(new['contact_score'][0] <= old['contact_score'][0]
                    and new['contact_score'][1] < old['contact_score'][1]-1e-12)
    okay = bool(old['native_pass'] and new['native_pass'] and guard and improves and original_guard)
    return dict(**new, individual_contact_guard_pass=guard,
        maximum_contact_regression=float(np.maximum(regression, 0.).max()), objective_improves=improves,
        provisional_native_contact_progress=okay, full_geometry_checked=False, retained=False,
        label=label, fraction=fraction, static_edit_audit_pass=True,
        original_contact_guard_pass=original_guard, controls_relative_to_original_source=True)


def run(study, output, *, progress=None):
    study, output = [Path(p).resolve() for p in (study, output)]
    if output.exists(): raise ValueError('Fresh warm verification output required')
    with worker_lock(), threadpool_limits(limits=1):
        result, request = read(study/'result.json'), read(study/'request.json')
        assert result['schema'] == 'strep-seeded-contact-refinement-result-v1' and result['status'] == 'complete'
        assert request['schema'] == 'strep-seeded-contact-refinement-request-v1'
        factories = {
            'continuous-native': 'central_coupled_contacts.CentralCoupledContactModel',
            'stored-native': 'stored_native_coupled_contacts.StoredNativeCoupledContactModel',
        }
        backend = request['proposal_backend']
        assert backend in factories
        assert request['proposal_factory_class'] == result['proposal_factory_class'] == factories[backend]
        assert result['proposal_backend'] == backend
        assert 'seeded_contact_refinement.py' in request['implementation_sha256']
        assert 'stored_native_coupled_contacts.py' in request['implementation_sha256']
        assert request['iterations'] == 1
        assert request['proposal_source'] == result['proposal_source'] == 'explicit-seed-direction'
        assert not request['conic_solver_executed'] and not result['conic_solver_executed']
        seed_path = Path(request['seed_direction'])
        assert str(seed_path) in request['inputs_sha256']
        assert result['original_selected'] and request['rotation_storage_policy'] == 'source-scale'
        assert request['original_source_caps_and_authored_limits_preserved']
        assert not request['intermediate_geometry_approved'] and request['maximum_final_geometry_audits'] == 1
        assert not any(result[k] for k in ('quality_approved', 'release_approved', 'human_reviewed',
            'imported_skin_checked', 'self_or_continuous_collision_checked', 'geometry_queries_rerun_by_independent_verifier'))
        assert result['request_sha256'] == sha256(study/'request.json')
        extras = {'result.json', 'pipeline.json', 'study.json', 'driver.py'}
        actual_files = {p.relative_to(study).as_posix() for p in study.rglob('*')
                        if p.is_file() and p.relative_to(study).as_posix() not in extras}
        assert set(result['files_sha256']) == actual_files
        bindings = {str(study/'result.json'): sha256(study/'result.json')}
        bindings.update({str(study/n): d for n, d in result['files_sha256'].items()})
        bindings.update(request['inputs_sha256'])
        for n, digest in request['implementation_sha256'].items():
            bindings[str(ROOT/'scripts'/n)] = digest; bindings[str(study/'implementation'/n)] = digest
        if (study/'study.json').exists():
            wrapper = read(study/'study.json')
            assert wrapper['result_sha256'] == sha256(study/'result.json')
            assert wrapper['driver_sha256'] == sha256(study/'driver.py')
            bindings.update({str(study/n): sha256(study/n) for n in ('study.json', 'driver.py')})
            bindings.update(wrapper['prerequisite_sha256'])
        else:
            assert not (study/'driver.py').exists()
        helpers = [Path(__file__).resolve(), ROOT/'scripts/coupled_restoration_oracles.py',
                   ROOT/'scripts/verify_coupled_restoration.py']
        for path in helpers: bindings[str(path)] = sha256(path)
        def check():
            if any(sha256(path) != digest for path, digest in bindings.items()):
                raise ValueError('Warm study inputs, methods or saved evidence changed')
        check(); output.mkdir(parents=True)
        for path in helpers:
            shutil.copyfile(path, output/path.name); bindings[str(output/path.name)] = sha256(path)
        save(output/'request.json', dict(at=now(), source_bindings_sha256=bindings,
            decoder_shared_with_producer=True, uncached_surface_contact=True,
            all_derivative_columns_recomputed=False, full_affine_selector_recomputed=True))
        try:
            spec, permissions = read(study/'source-contacts.json'), read(study/'permissions.json')
            digest = sha256(study/'source-contacts.json')
            assert digest == permissions['contacts_sha256']
            source = SceneContacts(spec, request['source_base'])
            problem = SceneProblem(source, SceneEdits(permissions, source, digest, rotation_storage_policy='source-scale'))
            include_times(problem, np.asarray(request['geometry_times']))
            with np.load(study/'source.npz', allow_pickle=False) as archive:
                saved = {n: archive[n] for n in archive.files}
            clock, uniform = saved['times_s'], saved['rate_times_s']
            np.testing.assert_array_equal(clock, problem.times); np.testing.assert_array_equal(clock, request['motion_times'])
            np.testing.assert_array_equal(uniform, problem.uniform); np.testing.assert_array_equal(uniform, request['uniform_rate_times'])
            caps = {n: v for n, v in saved.items() if '_metric_' in n}
            source_world = {n: np.array([a['sampler'].sample(float(t)) for t in clock]) for n, a in source.actors.items()}
            ids = np.searchsorted(clock, uniform); dt = uniform[1]-uniform[0]
            for n, world in source_world.items(): np.testing.assert_array_equal(world, saved['world_'+n])
            for n in permissions['actors']:
                for i, value in enumerate(rate_values(source_world[n][ids], source.actors[n]['rig'].joints, dt)):
                    order = 1 if i in (0, 2) else 2
                    stamps = uniform[1:-1] if i == 3 else (uniform[:-order]+uniform[order:])/2
                    bins = np.searchsorted(np.linspace(0, source.duration, 5)[1:-1], stamps, side='right')
                    expected = np.empty_like(value)
                    for b in np.unique(bins): expected[bins == b] = value[bins == b].max(axis=0)
                    np.testing.assert_allclose(expected, caps[f'{n}_metric_{i}'], atol=2e-10, rtol=0)
            native_oracle, key_oracle, vector_oracle = oracles(source, problem, permissions, source_world, clock, uniform, caps)
            contact = ContactNorms(problem, read(study/'surface-policy.json'), digest, maximum_rows=50000)
            original_contact = contact.residual(source_world)
            np.testing.assert_allclose(original_contact, saved['contact'], atol=1e-8, rtol=0)
            np.testing.assert_array_equal(original_contact > 0, saved['contact'] > 0)
            initial_native = native_oracle(problem.initial, source_world)
            np.testing.assert_allclose(initial_native, saved['native'], atol=1e-7, rtol=0)
            np.testing.assert_array_equal(initial_native > 0, saved['native'] > 0)
            assert np.all(initial_native <= 0); check_summary(result['original'], saved)
            populations = []; key_count = 0
            def population(folder):
                nonlocal key_count
                with np.load(folder/'conditions.npz', allow_pickle=False) as archive:
                    obs = {n: archive[n] for n in archive.files}
                value = problem.edits.controls(obs['controls'])
                assert np.all(value >= problem.lower) and np.all(value <= problem.upper)
                current_spec = copy.deepcopy(spec)
                for n, entry in current_spec['actors'].items():
                    path = folder/(n+'.glb') if n in permissions['actors'] else Path(request['source_base'])/entry['glb']
                    entry['glb'] = str(path.resolve()); entry['sha256'] = sha256(path)
                current = SceneContacts(current_spec, folder)
                worlds = {n: np.array([a['sampler'].sample(float(t)) for t in clock]) for n, a in current.actors.items()}
                key_count += key_oracle(current, value)
                for n, world in worlds.items():
                    np.testing.assert_array_equal(world, obs['world_'+n])
                    old, new = source.actors[n]['rig'], current.actors[n]['rig']
                    for k in ('nodes', 'skins', 'meshes', 'materials', 'images', 'textures', 'scenes', 'scene'):
                        assert old.document.get(k) == new.document.get(k)
                    assert old.binary == new.binary[:len(old.binary)]
                native = native_oracle(value, worlds)
                np.testing.assert_allclose(native, obs['native'], atol=1e-7, rtol=0)
                np.testing.assert_array_equal(native > 0, obs['native'] > 0)
                computed = contact.residual(worlds)
                np.testing.assert_allclose(computed, obs['contact'], atol=1e-8, rtol=0)
                np.testing.assert_array_equal(computed > 0, obs['contact'] > 0)
                audits = {n: problem.edits.audit(n, folder/(n+'.glb'), source.actors[n]['animation_index']) for n in permissions['actors']}
                assert audits == read(folder/'edit-audits.json') and all(a['passed'] for a in audits.values())
                populations.append(folder.relative_to(study).as_posix())
                if progress: progress(dict(stage='closed-population', population=populations[-1], status='processing'))
                return obs, worlds, current, current_spec
            start, start_worlds, start_scene, start_spec = population(study/'start')
            seed = np.load(seed_path, allow_pickle=False)
            assert seed.shape == problem.initial.shape and np.isfinite(seed).all()
            assert np.any(seed != 0) and np.max(abs(seed)) <= request['trust']
            start_path = None if request['start_controls'] is None else Path(request['start_controls'])
            assert start_path is None or str(start_path) in request['inputs_sha256']
            control_inputs = {Path(p) for p in request['inputs_sha256'] if Path(p).suffix.lower() == '.npy'}
            assert control_inputs == {p for p in (seed_path, start_path) if p is not None}
            expected_start = np.load(start_path, allow_pickle=False) if start_path is not None else problem.initial
            np.testing.assert_array_equal(start['controls'], expected_start)
            assert np.all(start['native'] <= 0) and np.all(start['contact'] <= np.maximum(original_contact, 0.))
            check_summary(result['start'], start)
            base, worlds, current, current_spec = start, start_worlds, start_scene, start_spec
            x = base['controls']; steps = 0
            assert result['history'] == read(study/'history.json') and len(result['history']) <= request['iterations']
            for iteration, item in enumerate(result['history'], 1):
                assert item['iteration'] == iteration
                folder = study/f'iteration-{iteration}'; meta = read(folder/'model.json')
                assert meta['proposal_backend'] == backend
                assert meta['native']['difference_source'] == ('stored' if backend == 'stored-native' else 'continuous')
                assert meta['native']['difference_scheme'] == 'central'
                assert meta['native']['decoded_base_anchor']
                assert meta['contact']['difference_source'] == 'continuous'
                assert meta['contact']['difference_scheme'] == 'central'
                if backend == 'stored-native':
                    assert meta['native_difference_keys_quantized']
                    assert not meta['contact_difference_keys_quantized']
                    assert meta['finite_storage_secants']
                    assert not meta['uniform_quantization_error_bound']
                    assert not meta['nonlinear_feasibility_certified']
                with np.load(folder/'model.npz', allow_pickle=False) as archive:
                    vectors, bounds, scales = [archive[n] for n in ('vectors', 'caps', 'scales')]
                    jac = sparse.csc_matrix((archive['jac_data'], archive['jac_indices'], archive['jac_indptr']), shape=tuple(archive['jac_shape']))
                n, c = len(base['native']), len(base['contact']); hard = n+c
                assert vectors.shape == (n+2*c, 3) and jac.shape == (3*(n+2*c), problem.size)
                assert np.isfinite(np.r_[vectors.ravel(), bounds, scales, jac.data]).all() and np.all(scales > 0)
                v, b, s = vector_oracle(x, worlds)
                np.testing.assert_allclose(vectors[:n], v, atol=1e-12, rtol=0)
                np.testing.assert_array_equal(bounds[:n], b); np.testing.assert_array_equal(scales[:n], s)
                np.testing.assert_array_equal(vectors[n:hard], vectors[hard:])
                np.testing.assert_array_equal(scales[n:hard], scales[hard:])
                assert (jac[3*n:3*hard] != jac[3*hard:]).nnz == 0
                orientation, gaps, _ = contact.sample(worlds); m = len(orientation.caps)
                assert c == 3*m
                np.testing.assert_allclose(vectors[hard:hard+m], orientation.vectors, atol=1e-12, rtol=0)
                np.testing.assert_array_equal(bounds[hard:hard+m], orientation.caps)
                np.testing.assert_array_equal(scales[hard:hard+m], orientation.scales)
                side = jac[3*(hard+m):][::3]
                extent = np.maximum(np.minimum(request['trust'], problem.upper-x), np.minimum(request['trust'], x-problem.lower))
                offsets = np.maximum(1., gaps+np.asarray(abs(side)@extent).ravel()+1.)
                np.testing.assert_allclose(bounds[hard+m:], offsets, atol=1e-12, rtol=0)
                np.testing.assert_allclose(vectors[hard+m:, 0], offsets-gaps, atol=1e-12, rtol=0)
                np.testing.assert_array_equal(vectors[hard+m:, 1:], np.zeros((2*m, 2)))
                np.testing.assert_array_equal(scales[hard+m:], np.full(2*m, .005))
                np.testing.assert_array_equal(bounds[n:hard], np.maximum(bounds[hard:], np.linalg.norm(vectors[hard:], axis=1)))
                affine_base = (np.linalg.norm(vectors, axis=1)-bounds)/scales
                np.testing.assert_allclose(affine_base[:n], base['native'], atol=1e-9, rtol=1e-12)
                np.testing.assert_allclose(affine_base[hard:], base['contact'], atol=1e-9, rtol=1e-12)
                np.testing.assert_array_equal(meta['guard']['contact_baseline_residual'], base['contact'])
                assert meta['hard_rows'] == meta['guard']['hard_rows'] == hard
                assert meta['complete_native_rows'] == n and meta['complete_surface_contact_rows'] == c
                assert meta['source_caps_unchanged'] and meta['authored_limits_unchanged']
                proposal, trials = read(folder/'proposal.json'), read(folder/'trials.json')
                assert proposal['status'] == item['solver_status'] == 'ExplicitSeedDirection' and len(trials) == item['trials']
                assert proposal['proposal_source'] == 'explicit-seed-direction' and not proposal['conic_solver_executed']
                np.testing.assert_array_equal(proposal['checked_affine_proposal']['raw_delta'], seed)
                selected = affine_selection(proposal, vectors, bounds, scales, jac, x, problem.lower, problem.upper,
                                            request['trust'], hard, request['backoffs'])
                chosen = None
                if selected is None:
                    assert not trials and not (folder/'direction.npy').exists() and not (folder/'raw-direction.npy').exists()
                else:
                    assert trials
                    raw = np.load(folder/'raw-direction.npy', allow_pickle=False)
                    np.testing.assert_array_equal(raw, selected)
                    delta = np.clip(raw, np.maximum(problem.lower-x, -request['trust']), np.minimum(problem.upper-x, request['trust']))
                    np.testing.assert_array_equal(np.load(folder/'direction.npy', allow_pickle=False), delta)
                    lo, hi = np.maximum(problem.lower-x, -request['trust']), np.minimum(problem.upper-x, request['trust'])
                    expected_projection = dict(raw_maximum_control_step=float(abs(raw).max()),
                        raw_step_box_excess=float(np.maximum(np.maximum(lo-raw, raw-hi), 0.).max()),
                        projected_maximum_control_step=float(abs(delta).max()), changed_components=int((raw != delta).sum()),
                        maximum_projection_change=float(abs(raw-delta).max()), exact_step_box_projection=True,
                        authored_limits_relaxed=False, projected_affine_feasibility_certified=False,
                        independent_export_audit_required=True)
                    assert read(folder/'direction-projection.json') == expected_projection
                    assert len(trials) <= request['backoffs']
                    for i, trial in enumerate(trials):
                        assert trial['label'] == f'backoff-{i}' and trial['fraction'] == .5**i
                        obs, newworlds, newscene, new_spec = population(folder/trial['label'])
                        expected_controls = projected_controls(x, delta, problem.lower, problem.upper, request['trust'], .5**i)
                        np.testing.assert_array_equal(obs['controls'], expected_controls)
                        decision = decoded_decision(base, obs, original_contact, trial['label'], trial['fraction'])
                        if trial != decision or read(folder/trial['label']/'decision.json') != decision:
                            raise ValueError('Warm decoded decision contradicts the full population')
                        if decision['provisional_native_contact_progress']:
                            assert i == len(trials)-1
                            chosen = trial['label']; base, worlds, current, current_spec = obs, newworlds, newscene, new_spec
                            steps += 1; break
                assert chosen == item['provisional_step']; x = base['controls']
                if chosen is None: assert iteration == len(result['history'])
            np.testing.assert_array_equal(np.load(study/'provisional-controls.npy', allow_pickle=False), x)
            assert result['provisional_steps'] == steps; check_summary(result['final'], base)
            def selected_files(specification):
                return {n: dict(path=specification['actors'][n]['glb'], sha256=specification['actors'][n]['sha256']) for n in permissions['actors']}
            assert result['candidate_files'] == selected_files(current_spec)
            final = decoded_decision(start, base, original_contact, 'final', 1.)
            eligible = final['provisional_native_contact_progress']
            assert result['geometry_checked'] == eligible
            if eligible: assert read(study/'candidate-contacts.json') == current_spec
            geometry = geometry_replay(study, current, worlds, clock, request, progress) if eligible else None
            keep = bool(eligible and geometry['sampled_conditions_pass']) if geometry else False
            assert result['retained_new_improvement'] == keep and result['prior_best_fallback_preserved'] == (not keep)
            assert result['original_contact_guard_pass'] == final['original_contact_guard_pass']
            assert result['complete_geometry_pass'] == (geometry['sampled_conditions_pass'] if geometry else None)
            np.testing.assert_array_equal(np.load(study/'retained-controls.npy', allow_pickle=False), x if keep else start['controls'])
            assert result['retained_files'] == selected_files(current_spec if keep else start_spec)
            check()
            replay = dict(schema='strep-seeded-contact-refinement-replay-v1', at=now(), status='complete',
                study_result_sha256=sha256(study/'result.json'), source_rate_caps_reconstructed=True,
                complete_closed_populations=populations, editable_keys_reconstructed=key_count,
                native_scalar_and_vector_arithmetic_recomputed=True, uncached_full_surface_contact_recomputed=True,
                paired_guard_rows_and_jacobians_checked=True, all_derivative_columns_recomputed=False,
                full_affine_selector_recomputed=True, condition_summaries_and_closed_decisions_reduced=True,
                proposal_backend=backend, proposal_factory_class=factories[backend],
                conic_solver_executed=False, explicit_seed_binding_reproduced=True,
                decoder_shared_with_producer=True, geometry=geometry, retained_claim_reproduced=True,
                engine_or_human_quality_checked=False, quality_approved=False, release_approved=False)
            save(output/'result.json', replay); save(output/'pipeline.json', dict(status='complete')); return replay
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.study, args.output, progress=lambda value: print(value, flush=True))
