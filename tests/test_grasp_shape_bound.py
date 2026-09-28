import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_shape_bound import radial_clearance_upper
from rigid_grasp_bound import clearance_upper_bound


def test_radial_specialization_matches_general_geometric_bound():
    rng = np.random.default_rng(120)
    offsets = np.r_[rng.normal(size=(500, 3))*.04, [[0, 0, 0], [0, 0, -.03], [0, 0, .03]]]
    for degrees in [0., 10.0001, 90., 180.]:
        expected = clearance_upper_bound(offsets, [0, 0, 1], [0, 0, -.25], [0, 0, 1], [0, 0, 0], .25, .005001, degrees)
        actual = radial_clearance_upper(torch.tensor(offsets), torch.tensor([0., 0., 1.], dtype=torch.float64), .25, .25, .005001, degrees)
        np.testing.assert_allclose(actual.numpy(), expected, atol=2e-15)


def test_offset_gradient_matches_finite_difference_and_zero_offset_is_finite():
    x = torch.tensor([[.03, .02, .01], [.01, .01, -.03], [0., 0., 0.]], dtype=torch.float64, requires_grad=True)
    normal = torch.tensor([0., 0., 1.], dtype=torch.float64)
    fn = lambda value: radial_clearance_upper(value, normal, .25, .25, .005, 10).sum()
    gradient = torch.autograd.grad(fn(x), x)[0].numpy()
    assert np.isfinite(gradient).all()
    direction = np.array([[.2, -.4, .1], [.3, .1, -.2], [0, 0, 0]])
    h = 1e-6
    fd = float((fn(x.detach()+h*torch.tensor(direction))-fn(x.detach()-h*torch.tensor(direction)))/(2*h))
    np.testing.assert_allclose(np.sum(gradient*direction), fd, atol=1e-8)
