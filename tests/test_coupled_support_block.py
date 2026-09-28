from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, sha256
from coupled_support_context import context, block, derivative_proof
from coupled_support_block import embed
from threadpoolctl import threadpool_limits
import json
from coupled_support_block import Constraints, solve


def test_sparse_embedding_keeps_frames_separate():
    row = embed(np.eye(3), 6, 12)
    assert row.nnz == 3
    assert np.array_equal(row@np.arange(12), np.arange(6, 9))


def test_numpy_objective_solver_history_is_serializable():
    class Toy:
        width = 1
        frames = np.array([0])
        initial = np.array([[.5]])
        def values(self, x): return np.asarray(x).reshape(1, 1)
        def pair(self, x):
            c = Constraints(1); c.lower([1.], [[0.]], 'feasible')
            return np.float64(x[0]**2), np.array([2*x[0]]), c, self.values(x)
        def midpoint_guard(self, values): return True, 0.
    values, result = solve(Toy(), steps=1, trusts=(.1,))
    assert result['history'][0]['accepted']
    assert values[0, 0] < .5
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('identity', ['motion-061-rig-01', 'motion-011-rig-02', 'motion-036-rig-03'])
def test_actual_three_rig_block_derivatives_and_source_feasibility(identity):
    study = ROOT/'reports/support-temporal-cleanup-v1'
    row = next(r for r in read(study/'completion.json')['rows'] if r['id'] == identity)
    assert sha256(row['selected']) == row['selected_sha256']
    with threadpool_limits(limits=1):
        ctx = context(ROOT/'reports/whole-support-breadth-v1/takes'/identity, Path(row['selected']))
        assert ctx['selection']
        p = block(ctx, ctx['selection'][0]['frames'])
        proof = derivative_proof(p)
        assert proof['passed'], proof
        assert min(proof['initial_margins'].values()) >= -1e-8, proof
        assert p.midpoint_guard(p.initial)[0]
        values = p.values(p.initial[p.frames].ravel()+1e-6)
        untouched = np.ones(len(values), bool); untouched[p.frames] = False
        assert np.array_equal(values[untouched], p.initial[untouched])
        assert not {0, 1, len(values)-2, len(values)-1}&set(p.frames)
