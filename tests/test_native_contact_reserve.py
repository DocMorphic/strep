"""Reserve validation/copy isolation only; this does not prove engine precision."""
from pathlib import Path
from types import SimpleNamespace
import copy
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_contact_reserve import guided_problem, SCHEMA


@pytest.fixture
def problem():
    def row(identifier, space, mode):
        return dict(entry=dict(authored=dict(id=identifier, mode=mode,
            target=dict(space=space), limits=dict(position_m=.001, relative_speed_m_s=.01))),
            times=np.array([.1, .2]), ids=np.array([0, 1]), populations=[])
    def controls(value):
        result = np.asarray(value, float)
        if result.shape != (3,) or not np.isfinite(result).all(): raise ValueError('Controls')
        return result
    return SimpleNamespace(rows=[row('partner', 'actor', 'touch'), row('box', 'object', 'hold'), row('floor', 'world', 'hold')],
        initial=np.zeros(3), lower=-np.ones(3), upper=np.ones(3), edits=SimpleNamespace(controls=controls),
        caps={'actor': object()}, protected_rows=12)


def request(reserves=None):
    return dict(schema=SCHEMA, contacts_sha256='a' * 64, reserves_m={'partner': .0001} if reserves is None else reserves)


def test_tightens_only_selected_guidance_rows_and_copies_nested_intent(problem):
    original = copy.deepcopy(problem.rows)
    guide, binding = guided_problem(problem, request(), 'a' * 64)
    assert guide.rows[0]['entry']['authored']['limits']['position_m'] == .0009
    assert problem.rows[0]['entry']['authored']['limits']['position_m'] == .001
    assert guide.caps is problem.caps and guide.edits is problem.edits and guide.protected_rows == problem.protected_rows
    for old, now in zip(original, problem.rows):
        assert old['entry'] == now['entry'] and np.array_equal(old['times'], now['times'])
    for row in guide.rows:
        assert row['entry']['authored']['limits']['relative_speed_m_s'] == .01
    guide.rows[0]['entry']['authored']['target']['space'] = 'edited copy'
    guide.rows[0]['times'][0] = .5
    assert problem.rows[0]['entry']['authored']['target']['space'] == 'actor'
    assert problem.rows[0]['times'][0] == .1
    assert binding['original_acceptance_limits_unchanged'] and not binding['quality_approved'] and not binding['release_approved']


@pytest.mark.parametrize('identifier', ['partner', 'box', 'floor'])
def test_existing_actor_object_and_world_targets_can_have_explicit_reserves(problem, identifier):
    guide, binding = guided_problem(problem, request({identifier: .0002}), 'a' * 64)
    assert binding['targets'][identifier]['solver_target_m'] == .0008
    assert sum(r['entry']['authored']['limits']['position_m'] == .0008 for r in guide.rows) == 1


@pytest.mark.parametrize('reserve', [True, 0, -.0001, .001, .002, float('nan'), float('inf'), '0.0001'])
def test_invalid_or_nonpositive_reserves_never_mutate_problem(problem, reserve):
    with pytest.raises(ValueError): guided_problem(problem, request({'partner': reserve}), 'a' * 64)
    assert all(r['entry']['authored']['limits']['position_m'] == .001 for r in problem.rows)


@pytest.mark.parametrize('fault', ['unknown', 'empty', 'list', 'schema', 'digest', 'extra', 'duplicate'])
def test_exact_binding_and_population_are_required(problem, fault):
    value = request()
    if fault == 'unknown': value['reserves_m'] = {'missing': .0001}
    elif fault == 'empty': value['reserves_m'] = {}
    elif fault == 'list': value['reserves_m'] = []
    elif fault == 'schema': value['schema'] = 'wrong'
    elif fault == 'digest': value['contacts_sha256'] = 'b' * 64
    elif fault == 'extra': value['quality_approved'] = True
    else: problem.rows.append(copy.deepcopy(problem.rows[0]))
    with pytest.raises(ValueError): guided_problem(problem, value, 'a' * 64)


def test_seed_and_default_initial_arrays_are_independent_and_bounded(problem):
    seed = np.array([.1, .2, .3]); guide, _ = guided_problem(problem, request(), 'a' * 64, initial=seed)
    seed[:] = 0; assert np.array_equal(guide.initial, [.1, .2, .3])
    guide.initial[:] = .5; assert np.array_equal(problem.initial, np.zeros(3))
    guide, _ = guided_problem(problem, request(), 'a' * 64)
    guide.initial[:] = .5; assert np.array_equal(problem.initial, np.zeros(3))
    with pytest.raises(ValueError, match='bounds'): guided_problem(problem, request(), 'a' * 64, initial=[2, 0, 0])
