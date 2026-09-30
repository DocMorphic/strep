import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from continuous_terminal_hand import solve


def test_individual_constraints_preserve_all_witnesses_and_signed_separation(monkeypatch):
    def minimize(fun, initial, **kwargs):
        value = kwargs['constraints'][0]['fun'](initial)
        # One physical margin followed by one row per witness, including the
        # separated witness. Its positive clearance must not become a gate.
        np.testing.assert_allclose(value, [1., 0., .25, 1.5])
        return SimpleNamespace(x=initial, success=True, status=0, message='fixture', nit=1, nfev=1)
    monkeypatch.setattr('continuous_terminal_hand.minimize', minimize)
    best, _, _ = solve(lambda c: (.02, np.ones(1), [.02, .015, -.01]), np.ones(5),
                       [np.zeros(5)], individual_witnesses=True)
    assert best['motion_domain_feasible'] and best['witness_peak_m'] == .02


def test_actual_solve_balances_competing_witnesses_and_keeps_physical_limit():
    def evaluate(c):
        depths = .02 * np.array([1+c[0], 1-c[0]-c[1], -.3])
        return max(0., depths.max()), np.array([.8-c[1]]), depths
    best, _, _ = solve(evaluate, np.ones(5), [np.zeros(5)], iterations=40, individual_witnesses=True)
    assert .012 <= best['witness_peak_m'] < .01201
    assert best['controls'][1] <= .8
    assert best['controls'][0] == pytest.approx(-.4, abs=1e-3)


def test_all_separated_witnesses_allow_zero_peak():
    best, _, _ = solve(lambda c: (0., [1.], [-.01, -.02]), np.ones(5), [np.zeros(5)],
                       iterations=2, individual_witnesses=True)
    assert best['witness_peak_m'] == 0


@pytest.mark.parametrize('depths', [[], [[.02]], [float('nan')], [.03]])
def test_bad_witness_population_or_peak_rejected(depths):
    with pytest.raises(ValueError):
        solve(lambda c: (.02, [1.], depths), np.ones(5), [np.zeros(5)], individual_witnesses=True)


def test_population_cannot_change_during_solve():
    def evaluate(c):
        return .02, [1.], [.02] if np.any(c) else [.02, .01]
    with pytest.raises(ValueError, match='population'):
        solve(evaluate, np.ones(5), [np.zeros(5)], individual_witnesses=True)
