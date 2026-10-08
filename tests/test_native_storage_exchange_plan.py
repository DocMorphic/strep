"""Policy-preserving proposals at capacity, without any motion approval."""
from pathlib import Path
import copy
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_storage_exchange_plan import exchange_plan, apply_exchange


def row(index, step=1, actor='A'):
    return dict(actor=actor, node=6, key_index=index, component=3, step=step)


def test_every_at_capacity_restoration_is_preserved_in_original_order():
    seed = [row(i, -1 if i % 2 else 1, 'A' if i < 32 else 'B') for i in range(64)]
    options = [row(100, -1), row(100, 1)]
    before = copy.deepcopy((seed, options))
    plan = exchange_plan(seed, options, 64)
    assert len(plan) == 128
    assert [p['restored'] for p in plan[:64]] == seed
    assert [p['restored'] for p in plan[64:]] == seed
    assert [p['choice'] for p in plan] == [options[0]]*64 + [options[1]]*64
    outputs = [apply_exchange(seed, p, 64) for p in plan]
    assert all(len(o) == 64 for o in outputs)
    assert all(o[-1] == p['choice'] and p['restored'] not in o for o,p in zip(outputs,plan))
    assert len({tuple(tuple(r.values()) for r in output) for output in outputs}) == 128
    assert (seed, options) == before


def test_direct_restore_reversal_and_addition_keep_original_absolute_values():
    seed = [row(0), row(1, -1)]
    options = [row(0, 0), row(1, 1), row(2, -1)]
    plan = exchange_plan(seed, options, 3)
    assert all(p['restored'] is None for p in plan)
    assert [apply_exchange(seed, p, 3) for p in plan] == [
        [row(1, -1)], [row(0), row(1)], [row(0), row(1, -1), row(2, -1)]]
    assert exchange_plan([], [], 1) == []
    assert apply_exchange([], exchange_plan([], [row(0)], 1)[0], 1) == [row(0)]


def test_mixed_options_retain_every_direct_and_swap_proposal():
    seed = [row(0), row(1, -1)]
    options = [row(0, 0), row(5), row(1, 1), row(6, -1)]
    plan = exchange_plan(seed, options, 2)
    assert [p['choice'] for p in plan] == [options[i] for i in (0,1,1,2,3,3)]
    assert [p['restored'] for p in plan] == [None, seed[0], seed[1], None, seed[0], seed[1]]
    assert all(len(apply_exchange(seed,p,2)) <= 2 for p in plan)


def test_complete_population_budget_rejects_instead_of_returning_a_prefix():
    seed = [row(i) for i in range(64)]
    with pytest.raises(ValueError, match='Complete exchange population'):
        exchange_plan(seed, [row(100),row(101)], 64, maximum_candidates=127)
    assert len(exchange_plan(seed, [row(100),row(101)], 64, maximum_candidates=128)) == 128


def test_returned_proposals_and_outputs_do_not_alias_inputs():
    seed = [row(0)]
    option = row(1)
    plan = exchange_plan(seed, [option], 1)
    output = apply_exchange(seed, plan[0], 1)
    output[0]['node'] = 99
    plan[0]['restored']['node'] = 99
    plan[0]['choice']['node'] = 99
    assert seed == [row(0)] and option == row(1)


@pytest.mark.parametrize('seed,options,limit', [
    ([row(0),row(0)], [], 2), ([row(0)], [], 0), ([], [], True),
    ([], [], 65), ([row(0),row(1)], [], 1), ((), [], 1),
    ([], (), 1), ([], [row(0),row(0)], 1), ([], [row(0,0)], 1),
    ([row(0)], [row(0)], 1), ([row(0,0)], [], 1),
    ([dict(row(0),step=True)], [], 1), ([], [dict(row(0),component=4)], 1),
    ([], [dict(row(0),key_index=-1)], 1), ([], [dict(row(0),node=True)], 1),
    ([], [dict(row(0),actor='')], 1), ([], [dict(row(0),extra=1)], 1),
    ([], [dict(row(0),step=2)], 1), ([], [{'actor':'A'}], 1),
    ([], [row(i) for i in range(1025)], 1),
])
def test_malformed_complete_inputs_reject(seed, options, limit):
    with pytest.raises(ValueError):
        exchange_plan(seed, options, limit)


@pytest.mark.parametrize('budget', [True, 0, -1, 16385, 1.5])
def test_explicit_candidate_budget_required(budget):
    with pytest.raises(ValueError):
        exchange_plan([], [], 1, maximum_candidates=budget)


@pytest.mark.parametrize('proposal', [
    {'choice':row(2),'restored':row(0,-1)},
    {'choice':row(2),'restored':row(8)},
    {'choice':row(0,0),'restored':row(1)},
    {'choice':row(0,-1),'restored':row(1)},
    {'choice':row(2),'restored':None},
    {'choice':row(2),'restored':row(0),'extra':False},
])
def test_stale_unrelated_or_over_budget_proposals_reject(proposal):
    with pytest.raises(ValueError):
        apply_exchange([row(0),row(1)], proposal, 2)


def test_restoration_below_capacity_is_not_a_declared_swap():
    with pytest.raises(ValueError, match='at-capacity'):
        apply_exchange([row(0)], {'choice':row(1),'restored':row(0)}, 2)


def test_real_glb_exchange_restores_old_component_and_exports_one_new_neighbor(tmp_path):
    import numpy as np
    from test_native_rotation_storage_repair import fixture
    from native_rotation_storage_repair import StorageAdjustedEdits
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    base, policy, original = fixture(tmp_path)
    policy['maximum_corrections'] = 1
    choice = dict(original, component=2, step=-1)
    proposal = exchange_plan([original], [choice], 1)[0]
    candidate = apply_exchange([original], proposal, 1)
    assert candidate == [choice]
    value = base.initial.copy()
    value[0] = .01
    adjusted = StorageAdjustedEdits(base, policy, candidate)
    target = tmp_path/'exchange.glb'
    adjusted.export('A', value, target)
    report = adjusted.audit('A', target, 0, value=value)
    assert report['passed'] and not report['native_conditions_assessed'] and not report['release_approved']
    rig = RigAsset.load(target)
    decoder = NativeSupportSampler(rig.document, rig.binary, 0)
    raw = next(c[3] for c in decoder.channels if c[:2] == (original['node'], 'rotation'))
    expected = base.values('A', value)[original['node'], 'rotation'].copy()
    index = original['key_index']
    expected[index, 2] = np.nextafter(np.float32(expected[index,2]), np.float32(-np.inf))
    np.testing.assert_array_equal(raw, expected)
    assert raw[index,3] == base.values('A',value)[original['node'],'rotation'][index,3]
