import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from constraint_restoration import minimax_step, restore


def tensor(x):
    return torch.tensor(x, dtype=torch.float64, requires_grad=True)


def test_coupled_pose_and_root_satisfy_constraints_with_physical_box():
    pose, root = tensor([0.]), tensor([0.])
    def constraints():
        return torch.cat([1.-pose-root, pose-.6, root-.4])
    report = restore([pose, root], constraints, [-np.inf, 0], [np.inf, .4], [1., .4], steps=4)
    assert report['final_maximum_violation'] < 2e-9
    assert abs(pose.item()-.6) < 2e-9 and 0 <= root.item() <= .4
    assert not report['quality_approved']


def test_failed_constant_constraint_returns_no_step_not_infeasibility_proof():
    step, record = minimax_step([0.], [1., -1.], [[0.], [0.]], [-1.], [1.], [.1])
    assert record['success'] and np.array_equal(step, [0.])
    x = tensor([0.])
    report = restore([x], lambda: x*0+1., [-1.], [1.], [.1])
    assert not report['proxy_feasible'] and x.item() == 0
    assert report['history'][0]['selected_fraction'] is None


def test_nonlinear_trial_rejected_then_backtracked_and_accepted():
    x = tensor([.1])
    report = restore([x], lambda: torch.cat([1.-x*x, x*x-4.]), [0.], [10.], [10.], steps=1)
    trials = report['history'][0]['trials']
    assert not trials[0]['accepted'] and trials[-1]['accepted']
    assert .1 < x.item() <= 2.
    assert all(not t['new_failures'] for t in trials if t['accepted'])


def test_new_violation_rejects_even_if_worst_violation_improves():
    x = tensor([0.])
    report = restore([x], lambda: torch.cat([1.-x, x*x]), [-1.], [1.], [1.], steps=2)
    assert x.item() == 0 and not report['proxy_feasible']
    assert all(t['new_failures'] == 1 and not t['accepted'] for t in report['history'][0]['trials'])


def test_exception_restores_last_accepted_parameters():
    x = tensor([0.])
    def constraints():
        if x.item() > 0:
            raise RuntimeError('invalid trial')
        return 1.-x
    with pytest.raises(RuntimeError, match='invalid trial'):
        restore([x], constraints, [-1.], [1.], [1.])
    assert x.item() == 0


@pytest.mark.parametrize('kwargs', [dict(trust=[0.]), dict(lower=[1.]), dict(jacobian=[[np.nan]]),
                                    dict(upper=[np.nan]), dict(residuals=[np.inf])])
def test_invalid_linear_problem_is_rejected(kwargs):
    args = dict(x=[0.], residuals=[1.], jacobian=[[-1.]], lower=[-1.], upper=[1.], trust=[.1])
    args.update(kwargs)
    with pytest.raises(ValueError):
        minimax_step(**args)


def test_restoration_checks_bounds_even_when_constraints_already_pass():
    with pytest.raises(ValueError, match='bounded'):
        restore([tensor([2.])], lambda: torch.tensor([-1.]), [-1.], [1.], [.1])


def test_constraint_without_any_parameter_dependency_is_retained():
    x = tensor([0.])
    report = restore([x], lambda: torch.tensor([1.], dtype=torch.float64), [-1.], [1.], [.1])
    assert report['final_maximum_violation'] == 1. and x.item() == 0


@pytest.mark.parametrize('kwargs', [dict(constraint_restore_steps=True), dict(constraint_restore_steps=21),
    dict(constraint_restore_steps=1), dict(constraint_restore_steps=1, scene_context={})])
def test_refine_rejects_incomplete_or_unsupported_restoration_context(kwargs):
    from support_contact_v8 import refine
    with pytest.raises(ValueError, match='restoration'):
        refine(None, None, None, **kwargs)
