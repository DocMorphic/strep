"""Pinned multi-time orchestration on actual placed meshes and stored exports."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_pair_clearance_guides_job as module
from native_pair_clearance_guides_job import run, SCHEMA
from native_stored_pair_job import Job
from native_scene_norms import rows
from native_scene_geometry import faces_for
from native_observation_archive import verify
from test_native_stored_pair_job import prepare
from strep import read, save, sha256


def request(tmp_path, axis_mode='explicit'):
    job = prepare(tmp_path)
    guides = [dict(actor_a='A', vertices_a=[0, 1], actor_b='B', vertices_b=[0, 2, 3],
                   time_s=1., axis_world=[-1., 0., 0.], clearance_m=.0001, scale_m=.03),
              dict(actor_a='B', vertices_a=[0, 2, 3], actor_b='A', vertices_b=[0, 1],
                   time_s=2., axis_world=[1., 0., 0.], clearance_m=0., scale_m=.007)]
    if axis_mode == 'rank-patch':
        for guide in guides:
            guide['vertices_a'] = guide['vertices_b'] = [0, 1, 2, 3]
    guide_path = tmp_path / 'guides.json'
    save(guide_path, guides)
    pin = lambda p: dict(path=str(p), sha256=sha256(p))
    spec = dict(schema=SCHEMA, job=pin(job), guides=pin(guide_path),
                families=['original-norms', 'event-key-preserved'], event_times_s=[0.], axis_mode=axis_mode)
    path = tmp_path / 'request.json'
    save(path, spec)
    return path


def points_gaps(job, worlds, guides):
    points, gaps = [], []
    for guide in guides:
        frame = int(np.flatnonzero(job.problem.times == guide['time_s'])[0])
        pair = []
        for name, key in ((guide['actor_a'], 'vertices_a'), (guide['actor_b'], 'vertices_b')):
            actor = job.scene.actors[name]
            p, r = actor['placement']
            pair.append(actor['rig'].vertices(worlds[name][frame])[guide[key]] @ r.T + p)
        points.append(np.concatenate(pair).ravel())
        axis = np.array(guide['axis_world'])
        gaps.append(((pair[1] @ axis)[None, :] - (pair[0] @ axis)[:, None]).ravel())
    return np.concatenate(points), np.concatenate(gaps)


@pytest.mark.parametrize('mode', ['explicit', 'rank-patch', 'controlled-export-paths'])
def test_actual_multitime_model_exports_original_norms_and_full_selection(tmp_path, mode, monkeypatch):
    controlled = mode == 'controlled-export-paths'
    if controlled:
        mode = 'explicit'
        calls = []
        # Test the acceptance paths on real payloads, without requiring a
        # particular floating-point optimizer to propose these two directions.
        # The unchanged clip is motion-feasible. Deepening its original
        # vertical descent exceeds its source speed caps at fixed bounds.
        def proposals(native, jac, guide, guide_jac, value, *args, **kw):
            delta = np.zeros_like(value)
            if calls:
                delta[1] = -.02
            calls.append(delta.copy())
            return delta, dict(status='controlled-orchestration-test')
        monkeypatch.setattr(module, 'direction', proposals)
    path = request(tmp_path, mode)
    spec = read(path)
    job = Job(spec['job']['path'])
    before = dict(job.inputs, **{str(path): sha256(path), spec['guides']['path']: spec['guides']['sha256']})
    out = tmp_path / 'output'
    result = run(path, out)
    guides = read(out / 'guides.json')
    assert result['status'] == read(out / 'pipeline.json')['status'] == 'complete'
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert result['axis_mode'] == mode and result['guide_count'] == 2
    assert result['guide_rows'] == (12 if mode == 'explicit' else 32)
    assert read(out / 'input-guides.json') == read(spec['guides']['path'])
    _, worlds = job.problem.decoded(job.files, job.value)
    native = rows(job.problem, job.value, worlds)
    pt, gaps = points_gaps(job, worlds, guides)
    with np.load(out / 'system.npz', allow_pickle=False) as z:
        for key in ('vectors', 'caps', 'scales'):
            np.testing.assert_array_equal(z[key], getattr(native, key))
        np.testing.assert_array_equal(z['guide_points'], pt)
        np.testing.assert_array_equal(z['gaps_m'], gaps)
        assert z['parameter_rows'].shape == (3, 3)
    identity = read(out / 'model.json')
    assert identity['guide_row_offsets'] == [0, result['guide_rows'] // 2, result['guide_rows']]
    assert len(list((out / 'stencils').glob('*.npz'))) == identity['column_proxy_evaluations']
    choices = read(out / 'axis-choices.json')
    assert len(choices) == (2 if mode == 'rank-patch' else 0)
    for guide, choice in zip(guides, choices):
        assert len(choice['tests']) == choice['complete_requested_axis_tests'] - 2 * choice['exact_zero_edge_crosses_omitted']
        selected = min(range(len(choice['tests'])), key=lambda i: (
            choice['tests'][i]['squared_negative_part'], -choice['tests'][i]['minimum_gap_m']))
        assert selected == choice['selected_index']
        assert guide['axis_world'] == choice['tests'][selected]['axis_world']
        for name, key, face_key in ((guide['actor_a'], 'vertices_a', 'left_faces'),
                                   (guide['actor_b'], 'vertices_b', 'right_faces')):
            lookup = {v: i for i, v in enumerate(guide[key])}
            faces = [[lookup[int(v)] for v in f] for f in faces_for(job.scene.actors[name]['rig'])[0]
                     if all(int(v) in lookup for v in f)]
            assert choice[face_key] == faces and faces
    solvers = {f: read(out / (f + '-solver.json')) for f in spec['families']}
    for solver in solvers.values():
        if solver['delta'] is None:
            assert isinstance(solver['result']['status'], str) and solver['result']['status']
            assert not solver['result']['quality_approved'] and not solver['result']['release_approved']
    expected = [f + f'-fraction-{i:02d}' for f, s in solvers.items() if s['delta'] is not None
                for i in range(len(job.request['settings']['fractions']))]
    assert [r['label'] for r in result['records']] == expected
    if controlled:
        assert len(expected) == 2 and len(calls) == 2
    scales = np.concatenate([np.full(len(g['vertices_a']) * len(g['vertices_b']), g['scale_m']) for g in guides])
    clearances = np.concatenate([np.full(len(g['vertices_a']) * len(g['vertices_b']), g['clearance_m']) for g in guides])
    for record in result['records']:
        folder = out / record['label']
        assert read(folder / 'result.json') == record
        with np.load(folder / 'observations.npz', allow_pickle=False) as z:
            value = z['controls'].copy()
            actual, actual_worlds = job.problem.decoded({'A': folder / 'A.glb'}, value)
            actual_native = rows(job.problem, value, actual_worlds)
            np.testing.assert_array_equal(actual, z['residual'])
            for key in ('vectors', 'caps', 'scales'):
                np.testing.assert_array_equal(getattr(actual_native, key), z[key])
            for name, world in actual_worlds.items():
                np.testing.assert_array_equal(world, z[name + '_worlds'])
            point, gap = points_gaps(job, actual_worlds, guides)
            np.testing.assert_array_equal(point, z['guide_points'])
            np.testing.assert_array_equal(gap, z['actual_gaps_m'])
        deficit = np.minimum((gap - clearances) / scales, 0.)
        assert record['actual_guide_squared_negative_part'] == float(deficit @ deficit)
        assert record['native_conditions_pass'] is bool(np.all(actual <= 0) and np.all(actual_native.residual() <= 0))
        assert record['reference_bounds'] == job.reference_bounds({'A': folder / 'A.glb'}, actual_worlds)
        assert [q['time_s'] for q in record['guide_frame_queries']] == [g['time_s'] for g in guides]
        assert record['guide_frame_triangle_records'] == sum(len(q['surface']['records']) for q in record['guide_frame_queries'])
        assert record['guide_frame_maximum_partner_depth_m'] == max(q['maximum_partner_depth_m'] for q in record['guide_frame_queries'])
        assert not any(record[k] for k in ('retained', 'quality_approved', 'release_approved'))
        if record['full_geometry_assessed']:
            verify(folder / 'geometry-observations.npz')
    eligible = [r for r in result['records'] if r['original_step_box_pass'] and r['native_conditions_pass'] and r['reference_bounds']['passed']]
    selected = min(eligible, key=lambda r: (r['guide_frame_maximum_partner_depth_m'], r['guide_frame_triangle_records'])) if eligible else None
    assert result['full_geometry_selection'] == (None if selected is None else selected['label'])
    assert sum(r['full_geometry_assessed'] for r in result['records']) == (selected is not None)
    if controlled:
        assert result['records'][0]['native_conditions_pass']
        assert result['records'][0]['full_geometry_assessed']
        assert not result['records'][1]['native_conditions_pass']
        assert not result['records'][1]['full_geometry_assessed']
    for file, digest in before.items():
        assert sha256(file) == digest
    for file, digest in result['files_sha256'].items():
        assert sha256(out / file) == digest
    with pytest.raises(ValueError, match='Fresh'):
        run(path, out)


@pytest.mark.parametrize('fault', ['schema', 'extra', 'pin', 'mode', 'bool-mode', 'empty', 'too-many',
                                 'family', 'duplicate-family', 'event-required', 'event-unwanted',
                                 'event-bool', 'event-off-clock', 'event-duplicate', 'immutable-parent'])
def test_bad_requests_reject_before_output(tmp_path, fault):
    path = request(tmp_path)
    r = read(path)
    if fault == 'schema': r['schema'] = 'other'
    elif fault == 'extra': r['extra'] = True
    elif fault == 'pin': r['guides']['sha256'] = 'a' * 64
    elif fault == 'mode': r['axis_mode'] = 'inferred'
    elif fault == 'bool-mode': r['axis_mode'] = True
    elif fault in ('empty', 'too-many'):
        guide = Path(r['guides']['path'])
        save(guide, [] if fault == 'empty' else read(guide) * 33)
        r['guides']['sha256'] = sha256(guide)
    elif fault == 'family': r['families'] = ['unknown']
    elif fault == 'duplicate-family': r['families'] = ['original-norms'] * 2
    elif fault == 'event-required': r['event_times_s'] = []
    elif fault == 'event-unwanted': r['families'] = ['original-norms']
    elif fault == 'event-bool': r['event_times_s'] = [True]
    elif fault == 'event-off-clock': r['event_times_s'] = [.1234567]
    elif fault == 'event-duplicate': r['event_times_s'] = [0., 0.]
    elif fault == 'immutable-parent': save(tmp_path / 'result.json', dict(status='retained original'))
    save(path, r)
    out = tmp_path / 'output'
    with pytest.raises(ValueError):
        run(path, out)
    assert not out.exists()


@pytest.mark.parametrize('fault', ['invalid-last', 'duplicate', 'rank-missing-faces', 'rank-invalid-axis'])
def test_descriptor_or_rank_failure_retains_terminal_failure(tmp_path, fault, monkeypatch):
    path = request(tmp_path, 'rank-patch' if fault.startswith('rank') else 'explicit')
    r = read(path)
    file = Path(r['guides']['path'])
    guides = read(file)
    if fault == 'invalid-last': guides[-1]['vertices_a'] = [True]
    elif fault == 'duplicate': guides[-1] = copy.deepcopy(guides[0])
    elif fault == 'rank-missing-faces': guides[-1]['vertices_a'] = [0, 1]
    else:
        original = module.choose_axis
        def malformed(*a, **kw):
            axis, choice = original(*a, **kw)
            choice['tests'][-1]['axis_world'] = [0., 0., 0.]
            return axis, choice
        monkeypatch.setattr(module, 'choose_axis', malformed)
    save(file, guides)
    r['guides']['sha256'] = sha256(file)
    save(path, r)
    out = tmp_path / 'output'
    with pytest.raises(ValueError):
        run(path, out)
    assert read(out / 'failure.json')['status'] == read(out / 'pipeline.json')['status'] == 'failed'
    assert read(out / 'input-guides.json') == guides and not (out / 'result.json').exists()


def test_pinned_input_mutation_during_solver_rejects(tmp_path, monkeypatch):
    path = request(tmp_path)
    r = read(path)
    file = Path(r['guides']['path'])
    original = file.read_bytes()
    def mutate(*a, **kw):
        file.write_bytes(original + b' ')
        return None, dict(status='controlled-no-candidate')
    monkeypatch.setattr(module, 'direction', mutate)
    out = tmp_path / 'output'
    with pytest.raises(ValueError, match='input bytes changed'):
        run(path, out)
    assert read(out / 'failure.json')['status'] == 'failed' and not (out / 'result.json').exists()
    assert read(out / 'input-guides.json') == read(file)
    assert read(out / 'request.json')['guides']['sha256'] == r['guides']['sha256']
