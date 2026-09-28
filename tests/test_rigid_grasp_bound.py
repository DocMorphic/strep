import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rigid_grasp_bound import clearance_upper_bound
from grasp_orientation import align_direction, unit


def test_single_vertex_extremum_is_attainable():
    r = .03*np.array([np.sin(np.pi/3), 0., np.cos(np.pi/3)])
    target = np.array([0., 0., -.25]); center = np.zeros(3)
    rotated = Rotation.from_rotvec([0, np.deg2rad(10), 0]).apply(r)
    farthest = target+rotated; farthest += .005*unit(farthest)
    upper = clearance_upper_bound(r[None], [0, 0, 1], target, [0, 0, 1], center, .25, .005, 10)[0]
    np.testing.assert_allclose(upper, np.linalg.norm(farthest)-.25, atol=1e-14)


def test_bound_covers_random_constrained_rigid_transforms():
    rng = np.random.default_rng(812); offsets = rng.normal(size=(20, 3))*.04
    source = unit([1, 2, 3]); normal = unit([-1, 3, 2]); target = np.array([.1, .2, .3]); center = np.array([.2, -.1, .1])
    bound = clearance_upper_bound(offsets, source, target, normal, center, .25, .005, 10)
    for _ in range(100):
        axis = unit(np.cross(normal, rng.normal(size=3)))
        tilted = Rotation.from_rotvec(axis*rng.uniform(0, np.deg2rad(10))).apply(normal)
        matrix = Rotation.from_rotvec(tilted*rng.uniform(-np.pi, np.pi)).as_matrix()@align_direction(source, tilted)
        point = target+unit(rng.normal(size=3))*rng.uniform(0, .005)
        actual = np.linalg.norm(offsets@matrix.T+point-center, axis=1)-.25
        assert np.all(actual <= bound+1e-12)


def test_contact_at_sphere_center_and_zero_offset():
    result = clearance_upper_bound([[0, 0, 0], [.1, 0, 0]], [0, 0, 1], [0, 0, 0], [0, 0, 1], [0, 0, 0], .25, .005, 10)
    np.testing.assert_allclose(result, [-.245, -.145])
