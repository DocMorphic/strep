import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from support_contact_v8 import object_constraint_residuals, object_constraint_merit, inequality_merit


def test_per_vertex_gradient_reaches_multiple_collisions_and_retains_feasible_set():
    g = torch.tensor([[.02, .01, -.04], [.03, -.02, .01]], dtype=torch.float64, requires_grad=True)
    for mode, active in [('maximum', [[True, False, False], [True, False, False]]),
                         ('per_vertex', [[True, True, False], [True, False, True]])]:
        rows = object_constraint_residuals(g, mode)
        loss = object_constraint_merit(rows, torch.zeros_like(rows), 20000., mode)
        grad = torch.autograd.grad(loss, g, retain_graph=True)[0]
        assert torch.equal(grad > 0, torch.tensor(active))
        assert bool((rows <= 0).all()) == bool((g <= 0).all())
    assert torch.autograd.gradcheck(lambda x: object_constraint_merit(x, torch.zeros_like(x), 20000., 'per_vertex'), (g,))


def test_single_violation_keeps_original_weight_and_maximum_mode_matches_legacy():
    g = torch.tensor([[.01, -.03, -.01], [.02, -.01, -.03]], dtype=torch.float64)
    maximum = g.amax(1)
    original = inequality_merit(maximum, torch.zeros_like(maximum), 20000.).mean()
    for mode in ['maximum', 'per_vertex']:
        rows = object_constraint_residuals(g, mode)
        torch.testing.assert_close(object_constraint_merit(rows, torch.zeros_like(rows), 20000., mode), original)
    multiplier = torch.tensor([.3, .5], dtype=g.dtype)
    torch.testing.assert_close(object_constraint_merit(maximum, multiplier, 20000., 'maximum'),
                               inequality_merit(maximum, multiplier, 20000.).mean())


def test_independent_multiplier_rows_preserve_memory_without_pulling_feasible_vertices():
    g = torch.tensor([[.01, .02, -.1]], dtype=torch.float64)
    m = torch.relu(torch.zeros_like(g) + 20000. * g)
    candidate = torch.tensor([[-.02, .001, -.1]], dtype=g.dtype, requires_grad=True)
    loss = object_constraint_merit(candidate, m, 80000., 'per_vertex')
    grad = torch.autograd.grad(loss, candidate)[0]
    assert grad[0, 0] == grad[0, 2] == 0
    assert grad[0, 1] > 0


@pytest.mark.parametrize('shape,mode', [((0, 3), 'per_vertex'), ((2,), 'maximum'), ((2, 3), 'unknown')])
def test_bad_residual_layout_rejected(shape, mode):
    with pytest.raises(ValueError):
        object_constraint_residuals(torch.zeros(shape), mode)


def test_multiplier_broadcast_rejected():
    with pytest.raises(ValueError):
        object_constraint_merit(torch.ones(2, 3), torch.zeros(2, 1), 20000., 'per_vertex')


@pytest.mark.parametrize('values', [[[-.1, -.02], [-.01, -.04]], [[0., -.1], [-.02, 0.]], [[-.1, .001], [-.02, -.04]]])
def test_both_layouts_agree_on_constraint_feasibility(values):
    g = torch.tensor(values, dtype=torch.float64)
    for mode in ['maximum', 'per_vertex']:
        rows = object_constraint_residuals(g, mode)
        assert bool((rows <= 0).all()) == bool((g <= 0).all())


def test_per_vertex_requires_inequalities_before_loading_motion():
    from support_contact_v8 import refine
    with pytest.raises(ValueError, match='require object inequalities'):
        refine(None, None, None, object_constraint_mode='per_vertex')
