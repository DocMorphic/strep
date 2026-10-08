import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

from native_storage_exchange_index import ExchangeIndex
from native_storage_exchange_plan import apply_exchange, exchange_plan


def row(key, step=1, actor='A'):
    return dict(actor=actor, node=6, key_index=key, component=3, step=step)


class ExchangeIndexTests(unittest.TestCase):
    def compare(self, seed, options, capacity):
        expected = exchange_plan(seed, options, capacity)
        indexed = ExchangeIndex(seed, options, capacity)
        self.assertEqual([indexed.proposal_at(i) for i in range(len(indexed))], expected)
        groups = []
        cursor = 0
        for option in options:
            count = sum(proposal['choice'] == option for proposal in expected)
            groups.append(list(range(cursor, cursor + count)))
            cursor += count
        order = [g[(turn+i) % len(g)] for turn in range(max(map(len, groups), default=0))
                 for i, g in enumerate(groups) if turn < len(g)]
        self.assertEqual(list(indexed.diagonal_indices()), order)
        self.assertEqual(sorted(order), list(range(len(expected))))
        for i in order:
            self.assertLessEqual(len(apply_exchange(seed, indexed.proposal_at(i), capacity)), capacity)

    def test_complete_mixed_population_matches_existing_planner(self):
        self.compare([row(0), row(1, -1)], [row(0, 0), row(0, -1), row(2), row(2, -1), row(1, 0)], 2)

    def test_below_capacity_is_direct(self):
        self.compare([row(0)], [row(1), row(0, 0), row(0, -1)], 3)

    def test_one_correction_capacity_distinguishes_restore_from_direct(self):
        self.compare([row(0)], [row(0, 0), row(0, -1), row(1), row(1, -1)], 1)

    def test_empty_seed_additions(self):
        self.compare([], [row(0), row(1, -1)], 2)

    def test_empty_options(self):
        index = ExchangeIndex([row(0)], [], 1)
        self.assertEqual(len(index), 0)
        self.assertEqual(list(index.diagonal_indices()), [])
        with self.assertRaises(ValueError):
            index.proposal_at(0)

    def test_largest_complete_population_without_proposal_allocation(self):
        seed = [row(i) for i in range(64)]
        options = [row(i+64) for i in range(1024)]
        index = ExchangeIndex(seed, options, 64)
        self.assertEqual(len(index), 65536)
        order = list(index.diagonal_indices())
        self.assertEqual(sorted(order), list(range(65536)))
        for i in [0, 63, 64, 32768, 65535]:
            proposal = index.proposal_at(i)
            self.assertEqual(proposal, dict(choice=options[i//64], restored=seed[i%64]))
            result = apply_exchange(seed, proposal, 64)
            self.assertEqual(len(result), 64)
            self.assertEqual(result[-1], options[i//64])
            self.assertNotIn(seed[i%64], result)

    def test_complete_budget_rejects_instead_of_truncating(self):
        seed = [row(i) for i in range(64)]
        options = [row(i+64) for i in range(400)]
        with self.assertRaises(ValueError):
            ExchangeIndex(seed, options, 64, maximum_candidates=16384)
        index = ExchangeIndex(seed, options, 64, maximum_candidates=25600)
        self.assertEqual(len(index), 25600)
        with self.assertRaises(ValueError):
            ExchangeIndex(seed, options, 64, maximum_candidates=25599)

    def test_copy_boundaries(self):
        seed, options = [row(0), row(1)], [row(2), row(0, -1)]
        before_seed, before_options = copy.deepcopy(seed), copy.deepcopy(options)
        index = ExchangeIndex(seed, options, 2)
        seed[0]['step'] = -1
        options[0]['key_index'] = 999
        output = index.proposal_at(0)
        output['choice']['step'] = -1
        output['restored']['key_index'] = 999
        self.assertEqual(index.proposal_at(0), dict(choice=before_options[0], restored=before_seed[0]))

    def test_repeated_iterators_are_stable_and_independent(self):
        index = ExchangeIndex([row(0), row(1)], [row(2), row(3)], 2)
        first, second = index.diagonal_indices(), index.diagonal_indices()
        self.assertEqual(next(first), next(second))
        self.assertEqual(list(first), list(second))

    def test_invalid_indices(self):
        index = ExchangeIndex([row(0)], [row(1)], 1)
        for value in [-1, 1, True, 0.0, '0', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                index.proposal_at(value)

    def test_malformed_options_and_seed(self):
        bad_options = [[row(0)], [row(2, 0)], [row(2), row(2)],
                       [dict(row(2), component=4)], [dict(row(2), step=True)],
                       [dict(row(2), actor='')], [dict(row(2), extra=1)]]
        for options in bad_options:
            with self.subTest(options=options), self.assertRaises(ValueError):
                ExchangeIndex([row(0)], options, 1)
        for seed in [[row(0), row(0)], [row(0, 0)], [dict(row(0), node=True)]]:
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                ExchangeIndex(seed, [], 2)

    def test_invalid_budgets_populations_and_types(self):
        for capacity in [0, 65, True, 1.0]:
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                ExchangeIndex([], [], capacity)
        for budget in [0, 65537, True, 1.0]:
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                ExchangeIndex([], [], 1, maximum_candidates=budget)
        for options in [None, (), [row(i) for i in range(1025)]]:
            with self.subTest(population_type=type(options).__name__), self.assertRaises(ValueError):
                ExchangeIndex([], options, 1)


if __name__ == '__main__':
    unittest.main()
