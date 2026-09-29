import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from bounded_root_coordinates import BoundedRootCoordinates
from support_contact_v5 import bounded_lift


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_same_legacy_starting_pose_and_local_derivative(dtype):
    initial = torch.tensor([0., .000022, .011, .11, .219, .22], dtype=dtype)
    coordinate = BoundedRootCoordinates(initial, .22)
    params = coordinate.initial_parameters().requires_grad_()
    legacy = bounded_lift(torch.logit((initial/.22).clamp(1e-4, 1-1e-4)), .22)
    assert torch.equal(coordinate(params), legacy)
    gradient, = torch.autograd.grad(coordinate(params).sum(), params)
    torch.testing.assert_close(gradient, torch.ones_like(gradient))
    record = coordinate.record()
    assert record['initial_lift_m'] == legacy.tolist()
    assert record['limit_m'] == .22


def test_finite_differences_match_the_rescaled_objective_gradient():
    coordinate = BoundedRootCoordinates(torch.zeros(3, dtype=torch.float64), .22)
    params = coordinate.initial_parameters().requires_grad_()
    target = torch.tensor([.01, .02, .04], dtype=params.dtype)
    def objective(p):
        lift = coordinate(p)
        return (lift-target).square().sum() + (lift[1]-lift[0]).square()
    gradient, = torch.autograd.grad(objective(params), params)
    step = 1e-9
    for j in range(3):
        direction = torch.zeros_like(params); direction[j] = step
        finite = (objective(params+direction)-objective(params-direction))/(2*step)
        torch.testing.assert_close(finite, gradient[j], rtol=1e-7, atol=1e-9)


def test_extreme_finite_coordinates_cannot_expand_root_bounds():
    coordinate = BoundedRootCoordinates(torch.zeros(5, dtype=torch.float64), .22)
    values = torch.tensor([-1e50, -.001, 0., .001, 1e50], dtype=torch.float64)
    lift = coordinate(values)
    assert torch.isfinite(lift).all() and (lift >= 0).all() and (lift <= .22).all()
    assert torch.all(torch.diff(lift) >= 0)


def test_invalid_reference_and_parameter_layouts_are_rejected():
    for initial in [torch.tensor([float('nan')]), torch.tensor([1]), torch.empty(0), torch.ones((2, 1)), torch.ones(2, requires_grad=True)]:
        with pytest.raises(ValueError, match='initial lifts'):
            BoundedRootCoordinates(initial, .22)
    for limit in [0., -1., float('inf'), True]:
        with pytest.raises(ValueError, match='root limit'):
            BoundedRootCoordinates(torch.zeros(2), limit)
    coordinate = BoundedRootCoordinates(torch.zeros(2, dtype=torch.float64), .22)
    for params in [torch.zeros(3, dtype=torch.float64), torch.zeros(2), torch.full((2,), float('nan'), dtype=torch.float64)]:
        with pytest.raises(ValueError, match='layout'):
            coordinate(params)


def test_solver_and_cli_reject_unknown_mode_before_loading_assets():
    from support_contact_v8 import refine
    from fit_scene_regions import run
    with pytest.raises(ValueError, match='root coordinate mode'):
        refine(None, None, None, root_coordinate_mode='unknown')
    with pytest.raises(ValueError, match='root coordinate mode'):
        run(None, 'A', [], None, root_coordinate_mode='unknown')
