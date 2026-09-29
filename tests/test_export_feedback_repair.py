"""Selection invariants for the reusable, export-measured correction driver."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import export_feedback_repair as repair


def evidence(slacks=None, serial=None, flags=None):
    return dict(slacks=slacks or {'approach': -.1, 'release': .1, 'floor': 0.},
                serial=np.array([-.1, .1] if serial is None else serial),
                flags=[] if flags is None else flags)


def test_export_improvement_cannot_move_failure_to_passing_group():
    before = evidence()
    after = evidence({'approach': .1, 'release': -1e-8, 'floor': 0.})
    verdict = repair.acceptance(before, after)
    assert verdict['export_worst_strictly_improved']
    assert verdict['export_regressions'] == ['release']
    assert not verdict['accepted']


def test_serialized_row_or_body_regression_rejects_better_export():
    before = evidence()
    after = evidence({'approach': -.01, 'release': .1, 'floor': 0.}, serial=[.1, -1e-12])
    assert not repair.acceptance(before, after)['accepted']
    after['serial'] = np.array([.1, .1])
    after['flags'] = ['LeftFoot_surface_slide_regression']
    assert not repair.acceptance(before, after)['accepted']


def test_retained_failure_is_not_quality_approval_or_false_convergence():
    before = evidence(flags=['old'])
    after = evidence({'approach': -.01, 'release': .1, 'floor': 0.}, flags=['old'])
    assert repair.acceptance(before, after)['accepted']
    assert not repair.acceptance(after, copy.deepcopy(after))['accepted']


def test_passing_exports_require_serialized_improvement():
    before = evidence({'approach': .1, 'release': .1, 'floor': 0.})
    after = evidence(dict(before['slacks']), serial=[-.01, .1])
    assert repair.acceptance(before, after)['accepted']
    after['slacks']['floor'] = -1e-14
    assert not repair.acceptance(before, after)['accepted']


@pytest.mark.parametrize('mutation', [
    lambda e: e.update(slacks={}),
    lambda e: e['slacks'].pop('release'),
    lambda e: e['slacks'].update(unknown=0.),
    lambda e: e['slacks'].update(approach=float('nan')),
    lambda e: e['slacks'].update(approach=float('inf')),
    lambda e: e['slacks'].update(approach=True),
    lambda e: e.update(serial=[]),
    lambda e: e.update(serial=[0.]),
    lambda e: e.update(serial=[False, True]),
    lambda e: e.update(serial=[0., float('nan')]),
    lambda e: e.pop('flags'),
    lambda e: e.update(flags=''),
])
def test_missing_or_changed_evidence_is_rejected(mutation):
    before, after = evidence(), evidence()
    mutation(after)
    with pytest.raises(ValueError):
        repair.acceptance(before, after)


class SmallProblem:
    start = np.array([-1e-6])
    bounds = np.array([.1])

    def evaluate(self, x, jacobian=True):
        return x.copy(), np.ones((1, 1)), {}


def setup_small(monkeypatch):
    monkeypatch.setattr(repair, 'rate_layout', lambda p: {
        'rate': dict(bounds=[0, 1], cap=1., scale=1., horizontal=0.)})
    calls = []

    def inspect(x, label):
        calls.append((label, x.copy()))
        return dict(slacks={'rate': float(x[0]), 'floor': 0.},
                    peaks={'rate': 1.-float(x[0])}, serial=x.copy(), flags=[], label=label)
    return calls, inspect


def test_real_linear_solver_reduces_optional_margin_without_moving_limit(monkeypatch):
    calls, inspect = setup_small(monkeypatch)
    x, selected, report = repair.repair(SmallProblem(), inspect)
    assert x[0] >= 0 and report['export_and_native_screen']
    assert report['optional_margin_fraction'] < 1
    assert not report['quality_approved']
    assert selected['label'].startswith('trial-')
    assert calls[0][0] == 'restored-seed'
    assert report['history'][0]['optional_margin_trials'][0]['result']['success'] is False


def test_rejected_export_retains_seed_and_trial_evidence(monkeypatch):
    calls, inspect = setup_small(monkeypatch)

    def with_regression(x, label):
        measured = inspect(x, label)
        if label != 'restored-seed':
            measured['slacks']['floor'] = -1e-12
        return measured
    x, selected, report = repair.repair(SmallProblem(), with_regression)
    np.testing.assert_array_equal(x, SmallProblem.start)
    assert selected['label'] == 'restored-seed'
    assert len(calls) > 1 and not report['export_and_native_screen']
    assert all(not t['accepted'] for h in report['history'] for t in h['trials'])


def test_failed_export_exception_is_not_silently_selected(monkeypatch):
    _, inspect = setup_small(monkeypatch)

    def broken(x, label):
        if label != 'restored-seed':
            raise RuntimeError('export failed')
        return inspect(x, label)
    with pytest.raises(RuntimeError, match='export failed'):
        repair.repair(SmallProblem(), broken)


@pytest.mark.parametrize('options', [dict(attempts=0), dict(backtracks=True), dict(trust=float('nan'))])
def test_invalid_search_options_fail_before_export(monkeypatch, options):
    calls, inspect = setup_small(monkeypatch)
    with pytest.raises(ValueError):
        repair.repair(SmallProblem(), inspect, **options)
    assert not calls
