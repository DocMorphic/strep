from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_piecewise_derivative import check_direction


def evaluation(x, bad=False):
    candidates = [x[0], -x[0]+4e-7]; active = int(np.argmin(candidates))
    return 0., np.zeros(1), np.array([candidates[active]]), np.array([[10. if bad else (1.,-1.)[active]]])


def signature(x):
    return int(np.argmin([x[0],-x[0]+4e-7]))


def test_smaller_step_selected_only_for_actual_branch_change():
    row = check_direction(evaluation, signature, np.zeros(1), np.ones(1))
    assert row['passed'] and row['selected_step'] == 1e-7
    assert [r['stable_branch'] for r in row['trials']] == [False,True]


def test_wrong_derivative_still_fails_stable_branch():
    row = check_direction(lambda x: evaluation(x,True), signature, np.zeros(1), np.ones(1))
    assert not row['passed'] and row['constraint_error'] > 8.


def test_true_kink_never_claims_smooth_derivative():
    row = check_direction(evaluation, signature, np.array([2e-7]), np.ones(1))
    assert not row['passed'] and row['selected_step'] is None
