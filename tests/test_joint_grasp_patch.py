import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from study_joint_grasp_patch import differentiable_alignment
from grasp_orientation import align_direction


def test_alignment_matches_independent_rotation_and_preserves_orientation():
    for source in ([0., 0., 1.], [.1, -.2, 1.]):
        source = np.array(source); source /= np.linalg.norm(source)
        target = np.array([.2, .1, 1.]); target /= np.linalg.norm(target)
        actual = differentiable_alignment(torch.tensor(source), torch.tensor(target)).numpy()
        np.testing.assert_allclose(actual, align_direction(source, target), atol=1e-14)
        np.testing.assert_allclose(actual@source, target, atol=1e-14)
        assert abs(np.linalg.det(actual)-1) < 1e-14


def test_alignment_gradient_through_measured_normal_is_finite_and_correct():
    source = torch.tensor([.1, -.2, 1.], dtype=torch.float64, requires_grad=True)
    target = torch.tensor([0., 0., 1.], dtype=torch.float64)
    def value(x):
        r = differentiable_alignment(x/torch.linalg.vector_norm(x), target)
        return (r@torch.tensor([.03, -.01, .02], dtype=x.dtype))[0]
    gradient = torch.autograd.grad(value(source), source)[0]
    direction = torch.tensor([.2, -.3, .1], dtype=torch.float64); h = 1e-6
    fd = (value(source.detach()+h*direction)-value(source.detach()-h*direction))/(2*h)
    np.testing.assert_allclose(float(gradient@direction), float(fd), atol=1e-10)
