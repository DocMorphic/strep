"""Real serialized curves and geometry gate repeated source-relative proposals."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import cumulative_coupled_contacts as flow
import action_worker_lock as locks
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_contact_norms import ContactNorms
from native_scene_geometry import evaluate
from native_observation_archive import verify
from test_native_contact_norms import prepared
from test_native_scene_geometry import policy as geometry_policy
from strep import read, save, sha256


def fixture(tmp_path, monkeypatch, *, unsafe_floor=False):
    _, surface, digest = prepared(tmp_path)
    source = tmp_path/'contacts.json'
    permissions = dict(schema='strep-native-scene-edit-v1', contacts_sha256=digest,
        actors=dict(A=dict(window_s=[0., 2.], protected_s=[], knots_s=[0., 1., 2.],
            tracks=[dict(node=3, path='rotation', maximum_change=5.)], maximum_joint_displacement_m=.02)))
    p = tmp_path/'permissions.json'; save(p, permissions)
    s = tmp_path/'surface.json'; save(s, surface)
    policy = geometry_policy(source, planes=dict(floor=dict(normal_world=[0., 1., 0.], offset_m=100. if unsafe_floor else -10.)))
    g = tmp_path/'geometry.json'; save(g, policy)
    monkeypatch.setattr(locks, 'ROOT', tmp_path/'lock-root')
    return source, p, s, g


def solve_small(*args, **kwargs):
    return np.array([1e-7, 0., 0.]), dict(status='test-external-proposal')


def independently_check(paths, output, result):
    source, p, s, _ = paths; spec = read(source); digest = sha256(source)
    scene = SceneContacts(spec, source.parent)
    problem = SceneProblem(scene, SceneEdits(read(p), scene, digest, rotation_storage_policy='source-scale'))
    original = ContactNorms(problem, read(s), digest).residual(problem.source_world)
    controls = np.load(output/'provisional-controls.npy', allow_pickle=False)
    files = {n: Path(v['path']) for n, v in result['candidate_files'].items()}
    native, worlds = problem.decoded(files, controls)
    after = ContactNorms(problem, read(s), digest).residual(worlds)
    assert np.all(native <= 0) and np.all(after <= np.maximum(original, 0))
    assert result['final']['contact_score'] == flow.conditions(native, after)['contact_score']
    candidate = read(output/'candidate-contacts.json'); policy = read(output/'candidate-geometry-policy.json')
    expected, arrays = evaluate(SceneContacts(candidate, output), policy, sha256(output/'candidate-contacts.json'))
    assert read(output/'geometry/geometry.json') == expected
    archive = output/'geometry/observations.npz'; verify(archive)
    with np.load(archive, allow_pickle=False) as a:
        for key, value in arrays.items():
            np.testing.assert_array_equal(a[key], value)


@pytest.mark.parametrize('name,value', [
    ('iterations', 0), ('iterations', True), ('iterations', 5), ('backoffs', 0), ('backoffs', 11),
    ('trust', 0.), ('trust', True), ('trust', float('nan')), ('trust', .2),
    ('difference_step', 0.), ('difference_step', .1), ('phase_seconds', 0.), ('phase_seconds', 301.),
    ('maximum_iterations', 0), ('maximum_iterations', 501), ('maximum_iterations', True),
    ('maximum_array_bytes', 0), ('maximum_logical_bytes', 1), ('maximum_logical_bytes', True)])
def test_invalid_settings_reject_before_creating_output(tmp_path, name, value):
    output = tmp_path/'out'
    with pytest.raises(ValueError, match='bounded'):
        flow.run(*[tmp_path/'absent']*4, output, **{name: value})
    assert not output.exists()


@pytest.mark.parametrize('fault', ['nan', 'empty', 'dimensions', 'population'])
def test_partial_or_nonfinite_conditions_cannot_authorize_progress(fault):
    native = np.array([-1., 0.]); contact = np.array([1., -1.]); after = np.array([.9, -.5])
    if fault == 'nan': after[0] = np.nan
    if fault == 'empty': after = after[:0]
    if fault == 'dimensions': after = after[None]
    if fault == 'population': after = after[:1]
    with pytest.raises(ValueError): flow.provisional(native, native, contact, after)


@pytest.mark.parametrize('fault', ['native', 'contact', 'stalled'])
def test_tiny_native_violation_each_contact_regression_and_stall_reject(fault):
    native = np.array([-1., 0.]); after_native = native.copy()
    before = np.array([1., .1, -.1]); after = np.array([.9, .05, -.05])
    if fault == 'native': after_native[-1] = 1e-15
    if fault == 'contact': after[-1] = 1e-15
    if fault == 'stalled': after = before.copy()
    assert not flow.provisional(native, after_native, before, after)['provisional_native_contact_progress']


def test_two_steps_reuse_original_caps_and_require_real_complete_final_geometry(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); monkeypatch.setattr(flow, 'direction', solve_small)
    output = tmp_path/'out'; events = []
    result = flow.run(*paths, output, iterations=2, progress=events.append)
    assert result['provisional_steps'] == 2 and result['retained_partial_improvement']
    assert result['geometry_checked'] and result['complete_geometry_pass']
    assert result['final']['surface_failed_rows'] > 0
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'), [2e-7, 0., 0.])
    for folder in ('iteration-1', 'iteration-2'):
        d = read(output/folder/'backoff-0/decision.json')
        assert d['provisional_native_contact_progress'] and not d['retained'] and not d['full_geometry_checked']
    assert events[-1]['stage'] == 'final-complete-geometry' and events[-1]['completed_samples'] == 3
    assert 'geometry/result.json' in result['files_sha256']
    for name, digest in result['files_sha256'].items():
        assert sha256(output/name) == digest
    independently_check(paths, output, result)


def test_failed_geometry_keeps_every_provisional_clip_but_retains_original(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch, unsafe_floor=True); monkeypatch.setattr(flow, 'direction', solve_small)
    output = tmp_path/'out'; result = flow.run(*paths, output, iterations=1)
    assert result['provisional_steps'] == 1 and result['geometry_checked']
    assert not result['complete_geometry_pass'] and not result['retained_partial_improvement']
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'), np.zeros(3))
    assert (output/'iteration-1/backoff-0/A.glb').exists()
    independently_check(paths, output, result)


def test_timeout_without_direction_cannot_invent_candidate_geometry_or_retention(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status='MaxTime')))
    output = tmp_path/'out'; result = flow.run(*paths, output)
    assert result['provisional_steps'] == 0 and not result['geometry_checked']
    assert result['complete_geometry_pass'] is None and not result['retained_partial_improvement']
    assert not (output/'geometry').exists() and len(result['history']) == 1


def test_stalled_second_step_still_audits_the_previous_provisional_improvement(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); calls = []
    def solve(*a, **k):
        calls.append(k)
        return solve_small() if len(calls) == 1 else (None, dict(status='MaxTime'))
    monkeypatch.setattr(flow, 'direction', solve)
    result = flow.run(*paths, tmp_path/'out', iterations=2)
    assert result['provisional_steps'] == 1 and result['retained_partial_improvement']
    assert result['history'][-1]['solver_status'] == 'MaxTime'


def test_seed_controls_are_source_relative_and_remain_provisional_until_geometry(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); seed = tmp_path/'seed.npy'; np.save(seed, [1e-7, 0., 0.])
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status='MaxTime')))
    output = tmp_path/'out'; result = flow.run(*paths, output, start_controls=seed)
    assert result['provisional_steps'] == 0 and result['retained_partial_improvement']
    assert read(output/'request.json')['inputs_sha256'][str(seed)] == sha256(seed)
    independently_check(paths, output, result)


@pytest.mark.parametrize('fault', ['source', 'candidate'])
def test_source_or_audited_candidate_mutation_cannot_approve_a_result(tmp_path, monkeypatch, fault):
    paths = fixture(tmp_path, monkeypatch); monkeypatch.setattr(flow, 'direction', solve_small)
    output = tmp_path/'out'; changed = False
    def mutate(record):
        nonlocal changed
        if record['stage'] == 'bounded-conic-proposal' and not changed:
            target = paths[1] if fault == 'source' else output/'start/A.glb'
            target.write_bytes(target.read_bytes() + b' '); changed = True
    with pytest.raises(ValueError, match='changed'):
        flow.run(*paths, output, iterations=1, progress=mutate)
    assert read(output/'pipeline.json')['status'] == 'failed' and not (output/'result.json').exists()


def test_busy_worker_and_existing_output_reject_without_overwrite(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); output = tmp_path/'out'
    with locks.worker_lock(), pytest.raises(RuntimeError, match='Another'):
        flow.run(*paths, output)
    assert not output.exists()
    output.mkdir(); (output/'sentinel').write_text('keep')
    with pytest.raises(ValueError, match='Fresh'): flow.run(*paths, output)
    assert (output/'sentinel').read_text() == 'keep'


@pytest.mark.parametrize('seed', [[2., 0., 0.], [np.nan, 0., 0.], [0., 0.]])
def test_invalid_seed_controls_reject_before_output(tmp_path, monkeypatch, seed):
    paths = fixture(tmp_path, monkeypatch); p = tmp_path/'seed.npy'; np.save(p, seed)
    with pytest.raises(ValueError): flow.run(*paths, tmp_path/'out', start_controls=p)
    assert not (tmp_path/'out').exists()


def test_actual_decoded_native_failure_rejects_an_improving_orientation_proposal(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (np.array([.001, 0., 0.]), dict(status='test-external-proposal')))
    output = tmp_path/'out'; result = flow.run(*paths, output, iterations=1, backoffs=1)
    decision = read(output/'iteration-1/backoff-0/decision.json')
    assert decision['objective_improves'] and decision['native_failed_rows'] > 0
    assert not decision['provisional_native_contact_progress'] and not result['geometry_checked']
    assert not result['retained_partial_improvement']
    assert (output/'iteration-1/backoff-0/A.glb').exists()


@pytest.mark.parametrize('seed', [[.5, 0., 0.], [-1e-7, 0., 0.]])
def test_failed_native_or_original_contact_guard_seed_is_preserved_and_rejected(tmp_path, monkeypatch, seed):
    paths = fixture(tmp_path, monkeypatch); path = tmp_path/'seed.npy'; np.save(path, seed)
    output = tmp_path/'out'
    with pytest.raises(ValueError, match='Serialized start'):
        flow.run(*paths, output, start_controls=path)
    assert (output/'start/A.glb').exists() and read(output/'pipeline.json')['status'] == 'failed'
    assert not (output/'result.json').exists()


def test_identical_saved_motion_reuses_complete_geometry_donor_without_queries(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); monkeypatch.setattr(flow, 'direction', solve_small)
    first = tmp_path/'first'; result = flow.run(*paths, first, iterations=1)
    assert result['retained_partial_improvement']
    monkeypatch.setattr(flow, 'direction', lambda *a, **k: (None, dict(status='MaxTime')))
    import native_scene_geometry as kernel
    monkeypatch.setattr(kernel, 'evaluate', lambda *a, **k: pytest.fail('Exact donor must avoid fresh queries'))
    second = tmp_path/'second'
    result = flow.run(*paths, second, start_controls=first/'retained-controls.npy', geometry_donor=first/'geometry')
    assert result['retained_partial_improvement'] and result['provisional_steps'] == 0
    cache = read(second/'geometry/result.json')
    assert cache['complete_samples'] == cache['reused_samples'] == 3 and cache['fresh_samples'] == 0
    assert read(first/'geometry/geometry.json') == read(second/'geometry/geometry.json')


def test_command_runs_real_cpu_solver_and_records_measured_outcome(tmp_path, monkeypatch):
    import subprocess
    import os
    paths = fixture(tmp_path, monkeypatch); output = tmp_path/'command'
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
    command = [sys.executable, str(Path(flow.__file__)), *map(str, paths), str(output),
               '--iterations', '1', '--phase-seconds', '1', '--maximum-iterations', '30']
    completed = subprocess.run(command, capture_output=True, text=True, env=env, timeout=90)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = read(output/'result.json'); proposal = read(output/'iteration-1/proposal.json')
    assert result['status'] == 'complete' and result['history'][0]['solver_status'] == proposal['status']
    assert proposal['phase_time_limit_seconds'] == 1. and proposal['phase_maximum_iterations'] == 30
    assert not result['quality_approved'] and not result['release_approved']
    if result['retained_partial_improvement']:
        independently_check(paths, output, result)
    else:
        np.testing.assert_array_equal(np.load(output/'retained-controls.npy'), np.zeros(3))


def test_rebuilding_caps_for_a_later_step_is_rejected(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch); monkeypatch.setattr(flow, 'direction', solve_small)
    original = flow.CentralCoupledContactModel.linearize; calls = []
    def reset(self, *a, **k):
        calls.append(1)
        if len(calls) == 2:
            self.problem.caps['A'].caps[0][0, 0] += 1e-8
        return original(self, *a, **k)
    monkeypatch.setattr(flow.CentralCoupledContactModel, 'linearize', reset)
    output = tmp_path/'out'
    with pytest.raises(ValueError, match='source-rate'):
        flow.run(*paths, output, iterations=2)
    assert read(output/'iteration-1/backoff-0/decision.json')['provisional_native_contact_progress']
    assert read(output/'pipeline.json')['status'] == 'failed' and not (output/'result.json').exists()


@pytest.mark.parametrize('fault', ['shape', 'nan', 'boxes', 'start', 'trust'])
def test_invalid_projection_inputs_reject_without_partial_direction(fault):
    value=np.array([.9, -.9]);delta=np.array([.03, -.03]);lower=np.array([-1., -1.]);upper=-lower;trust=.02
    if fault=='shape':delta=delta[:1]
    if fault=='nan':delta[0]=np.nan
    if fault=='boxes':lower=upper.copy()
    if fault=='start':value[0]=1.1
    if fault=='trust':trust=True
    with pytest.raises(ValueError):flow.project_direction(value,delta,lower,upper,trust)


@pytest.mark.parametrize('fraction', [1., .5, .125])
def test_exact_projection_and_rounded_backoff_preserve_original_boxes_and_trust(fraction):
    value=np.array([.1, -.1, .999, -.999]);raw=np.array([.020000000002492416, -.020000000002492416, .03, -.03])
    lower=-np.ones(4);upper=-lower;delta,report=flow.project_direction(value,raw,lower,upper,.02)
    assert report['changed_components']==4 and report['raw_step_box_excess']>0
    assert not report['authored_limits_relaxed'] and not report['projected_affine_feasibility_certified']
    assert np.all(np.abs(delta)<=.02) and np.all(delta>=lower-value) and np.all(delta<=upper-value)
    candidate=flow.backoff_controls(value,delta,lower,upper,.02,fraction)
    assert np.all(candidate>=lower) and np.all(candidate<=upper) and np.all(np.abs(candidate-value)<=fraction*.02)
    if fraction==1.:
        # Floating addition at 0.1 + 0.02 otherwise produces a larger step.
        assert .1+.02-.1>.02
        assert candidate[0]==np.nextafter(.1+.02,.1)


@pytest.mark.parametrize('fraction', [0., -1., 1.1, float('nan'), True])
def test_unbounded_or_invalid_backoff_fraction_rejects(fraction):
    with pytest.raises(ValueError):flow.backoff_controls([0.], [.02], [-1.], [1.], .02, fraction)


def test_raw_solver_overrun_is_saved_and_projected_before_actual_native_rejection(tmp_path, monkeypatch):
    paths=fixture(tmp_path,monkeypatch);raw=np.array([.020000000002492416,0.,0.])
    monkeypatch.setattr(flow,'direction',lambda *a,**k:(raw.copy(),dict(status='test-external-proposal')))
    output=tmp_path/'out';result=flow.run(*paths,output,iterations=1,backoffs=1)
    np.testing.assert_array_equal(np.load(output/'iteration-1/raw-direction.npy'),raw)
    np.testing.assert_array_equal(np.load(output/'iteration-1/direction.npy'),[.02,0.,0.])
    report=read(output/'iteration-1/direction-projection.json')
    assert report['changed_components']==1 and report['raw_step_box_excess']>0
    decision=read(output/'iteration-1/backoff-0/decision.json')
    assert not decision['native_pass'] and not decision['provisional_native_contact_progress']
    assert not result['retained_partial_improvement'] and not result['geometry_checked']
    assert 'iteration-1/raw-direction.npy' in result['files_sha256']


def test_nonfinite_raw_solver_output_is_preserved_then_rejected(tmp_path, monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(flow,'direction',lambda *a,**k:(np.array([np.nan,0.,0.]),dict(status='test-external-proposal')))
    output=tmp_path/'out'
    with pytest.raises(ValueError,match='Finite matching'):flow.run(*paths,output,iterations=1)
    assert np.isnan(np.load(output/'iteration-1/raw-direction.npy')[0])
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()
