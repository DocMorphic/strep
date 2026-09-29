import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from region_contact_objective import RegionInequalities, family_reduction


def legacy_balanced(g, n):
    x = torch.relu(g).square()
    groups = [x[:n].mean(), x[n:n+3].mean(), x[n+3:n+6].mean(), x[n+6:n+9].mean()]
    groups.extend(x[n+9:])
    return torch.stack(groups).sum() * 100


def test_initial_loss_and_gradients_match_legacy_balanced_penalty():
    a = torch.linspace(-.31, .44, 18, dtype=torch.float64, requires_grad=True)
    b = torch.linspace(.41, -.24, 20, dtype=torch.float64, requires_grad=True)
    original = (legacy_balanced(a, 5) + legacy_balanced(b, 7)) / 2
    model = RegionInequalities([5, 7])
    new = model.loss([a, b])
    torch.testing.assert_close(new, original)
    for x, y in zip(torch.autograd.grad(new, [a, b], retain_graph=True),
                    torch.autograd.grad(original, [a, b])):
        torch.testing.assert_close(x, y)
    assert torch.autograd.gradcheck(lambda x, y: model.loss([x, y]), (a, b))


def test_updates_use_latest_accepted_residuals_and_remain_fixed_during_line_search():
    model = RegionInequalities([3])
    g = torch.full((16,), -.1, dtype=torch.float64)
    trial = g.clone(); trial[-1] = 2.
    model.loss([trial])
    assert model.multipliers[0].count_nonzero() == 0
    accepted = g.clone(); accepted[-2] = .02
    model.loss([accepted])  # Solver evaluates its accepted point before update.
    model.advance(4)
    assert model.penalty == 800
    assert model.multipliers[0][-1] == 0
    assert model.multipliers[0][-2] == 4
    assert model.multipliers[0].count_nonzero() == 1
    assert not model.multipliers[0].requires_grad
    current = g.clone().requires_grad_()
    grad = torch.autograd.grad(model.loss([current]), current)[0]
    assert grad.count_nonzero() == 0  # Far inside feasible set, no attraction.


def test_repeated_violation_grows_pressure_without_changing_residual():
    model = RegionInequalities([3])
    g = torch.full((16,), -.1, dtype=torch.float64); g[-2] = .01
    g.requires_grad_()
    before = torch.autograd.grad(model.loss([g]), g)[0][-2]
    model.advance(4)
    after = torch.autograd.grad(model.loss([g]), g)[0][-2]
    assert after > before
    assert model.diagnostics()['maximum_normalized_violation'] == .01


@pytest.mark.parametrize('shape,n', [((15,), 3), ((1, 16), 3), ((15,), 2)])
def test_layout_is_checked_before_broadcast(shape, n):
    with pytest.raises(ValueError):
        family_reduction(torch.zeros(shape), n)


def test_bad_stage_order_and_growth_rejected():
    model = RegionInequalities([3])
    with pytest.raises(ValueError): model.advance(4)
    model.loss([torch.zeros(16)])
    for growth in [True, 1, float('nan')]:
        with pytest.raises(ValueError): model.advance(growth)
    with pytest.raises(ValueError): model.loss([torch.zeros(16), torch.zeros(16)])
