"""Complete scalar slopes, unchanged native bounds and actual fixture witnesses."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_pair_surface_model as pairs
from native_compact_surface_rows import CompactSurfaceRows, build
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_scene_norms import NormRows, rows as native_rows
from native_surface_model import include_times
from test_native_partner_surface_rows import scene_fixture


def tied_block():
    scene = SimpleNamespace(actors={n:dict(skin=SimpleNamespace(nodes=[0, 1, 2]),
        placement=(np.zeros(3), np.eye(3)), sampler=SimpleNamespace(sample=lambda time:None),
        rig=SimpleNamespace(vertices=lambda pose, actor=n:np.array([[0., 0, 0], [0, 1, 0], [0, 0, 1]]) if actor == 'A' else np.zeros((3, 3))))
        for n in ('A', 'B')}, check_inputs=lambda:None)
    row = dict(kind='triangle-support-separation', time_s=0., normal_world=[1., 0, 0],
        left=dict(actor='A', vertices=[0, 1, 2]), right=dict(actor='B', vertices=[0, 1, 2]))
    return CompactSurfaceRows(scene, [row], {})


def test_tied_support_retains_opposite_slopes_in_all_nine_pairs():
    compact = tied_block(); expanded = pairs.PairSurfaceRows(compact, 9)
    def vertices(x):
        return lambda actor, time:np.array([[x, 0, 0], [-x, 1, 0], [0, 0, 1]]) if actor == 'A' else np.zeros((3, 3))
    h = .001
    assert (compact.gaps(vertices(h))-compact.gaps(vertices(-h)))[0] == 0.
    derivative = (expanded.gaps(vertices(h))-expanded.gaps(vertices(-h)))/(2*h)
    np.testing.assert_array_equal(derivative, [1, 1, 1, -1, -1, -1, 0, 0, 0])
    assert expanded.count == 9 and expanded.report['affine_linearization_equivalence']


def test_actual_expansion_matches_every_original_pair_and_other_witness(tmp_path):
    scene, policy, digest = scene_fixture(tmp_path)
    compact = build(scene, policy, digest); expanded = pairs.PairSurfaceRows(compact, 400000)
    full, reduced = expanded.gaps(), compact.gaps()
    assert expanded.count == compact.report['expanded_total_rows']
    for i, row in enumerate(compact.rows):
        population = full[expanded.offsets[i]:expanded.offsets[i+1]]
        assert population.min() == pytest.approx(reduced[i], abs=1e-14)
        if row['kind'] == 'triangle-support-separation':
            points = []
            for entry in (row['left'], row['right']):
                actor = scene.actors[entry['actor']]; p, r = actor['placement']
                points.append((actor['rig'].vertices(actor['sampler'].sample(row['time_s'])) @ r.T+p)[entry['vertices']])
            expected = [(a-b) @ np.asarray(row['normal_world']) for a in points[0] for b in points[1]]
            np.testing.assert_allclose(population, expected, atol=1e-14, rtol=0)
        else:
            assert len(population) == 1
    with pytest.raises(ValueError, match='resource budget'):
        pairs.PairSurfaceRows(compact, expanded.count-1)
    with pytest.raises(ValueError, match='population'):
        expanded.gaps(lambda *args:np.zeros((1, 3)))


def test_actual_model_preserves_native_prefix_and_expanded_surface_jacobian(tmp_path):
    scene, policy, digest = scene_fixture(tmp_path)
    permission = dict(schema='strep-native-scene-edit-v1', contacts_sha256=digest, actors={'A':dict(
        window_s=[0., 2.], protected_s=[], knots_s=[0., 1., 2.],
        tracks=[dict(node=0, path='translation', maximum_change=.02)], maximum_joint_displacement_m=.02)})
    problem = SceneProblem(scene, SceneEdits(permission, scene, digest)); include_times(problem, policy['clock']['times_s'])
    before = native_rows(problem, problem.initial)
    native, jac, guides, gaps, scalar, report = pairs.model(problem, problem.initial, scene, policy, digest, .02)
    for name in ('vectors', 'caps', 'scales'):
        np.testing.assert_array_equal(getattr(native, name), getattr(before, name))
    np.testing.assert_allclose(native.residual(), problem.model(problem.initial), atol=1e-9, rtol=0)
    np.testing.assert_array_equal(gaps, guides.gaps())
    assert scalar.shape == (guides.count, problem.size) and jac.shape == (native.vectors.size, problem.size)
    assert len(report['surface_differences']) == problem.size and scalar.nnz == report['surface_nonzeros']
    assert report['affine_nine_pair_equivalence'] and report['native_acceptance_unchanged']
    assert not report['quality_approved'] and not report['release_approved']


def mock_problem(monkeypatch, *, changed_caps=False):
    original = NormRows([[0., 0, 0]], [1.], [1.])
    monkeypatch.setattr(pairs, 'linearize', lambda *args, **kw:(original, sparse.csc_matrix((3, 1)), {}))
    monkeypatch.setattr(pairs, 'native_rows', lambda *args:NormRows([[.1, 0, 0]], [2. if changed_caps else 1.], [1.]))
    monkeypatch.setattr(pairs, 'build', lambda *args, **kw:tied_block())
    monkeypatch.setattr(pairs, 'surface_points', lambda problem, worlds:worlds)
    def worlds(x, **kw):
        return lambda actor, time:np.array([[x[0], 0, 0], [-x[0], 1, 0], [0, 0, 1]]) if actor == 'A' else np.zeros((3, 3))
    return SimpleNamespace(edits=SimpleNamespace(controls=lambda x:np.asarray(x, float)),
        lower=np.array([-1.]), upper=np.array([1.]), worlds=worlds)


def test_model_keeps_tied_derivatives_in_sparse_columns_and_rejects_partial_budget(monkeypatch):
    problem = mock_problem(monkeypatch)
    _, _, guides, _, jac, report = pairs.model(problem, [0.], None, None, None, .02)
    np.testing.assert_array_equal(jac.toarray().ravel(), [1, 1, 1, -1, -1, -1, 0, 0, 0])
    assert report['surface_nonzeros'] == 6
    with pytest.raises(ValueError, match='Jacobian exceeds resource budget'):
        pairs.model(problem, [0.], None, None, None, .02, maximum_nonzeros=5)
    with pytest.raises(ValueError, match='surface rows exceed resource budget'):
        pairs.model(problem, [0.], None, None, None, .02, maximum_rows=8)


def test_changed_decoded_native_cap_rejects(monkeypatch):
    problem = mock_problem(monkeypatch, changed_caps=True)
    with pytest.raises(ValueError, match='caps'):
        pairs.model(problem, [0.], None, None, None, .02, decoded_worlds={})


@pytest.mark.parametrize('settings', [dict(trust=True), dict(trust=.021), dict(step=True), dict(step=0),
    dict(maximum_rows=400001), dict(maximum_rows=True), dict(maximum_nonzeros=0), dict(clearance=-.1), dict(difference_scheme='guess')])
def test_invalid_settings_reject_before_query(settings):
    with pytest.raises(ValueError):
        pairs.model(None, None, None, None, None, **{'trust':.02, **settings})
