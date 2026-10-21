from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_pose_model import SurfacePoseModel
from rig_asset import RigAsset


def fixture():
    world = np.repeat(np.eye(4)[None], 4, axis=0)
    world[0, :3, :3] = Rotation.from_rotvec([.2, .1, -.3]).as_matrix()
    world[1, :3, 3] = [.2, .8, -.1]
    world[2, :3, 3] = [.5, 1., -.1]
    # Keep tolerated affine drift rather than silently projecting the input.
    world[2, 0, 0] += 2e-7
    inverse = np.repeat(np.eye(4)[None], 3, axis=0)
    inverse[1, 3, 3] = 1.000001
    points = np.array([[.1, .2, .3], [-.2, .4, .1], [0., .2, -.1]])
    rig = SimpleNamespace(parents=[-1, 0, 1, -1], joints=[0, 1, 2], inverse=inverse,
        primitives=[dict(node=3, positions=points, joints=np.array([[0, 1, 2], [0, 1, 2], [0, 1, 2]]),
            weights=np.array([[.2, .3, .5], [0., .4, .6000001], [1e-14, 0., 1.]])),
            dict(node=3, positions=points[:1], joints=None, weights=None)])
    rig.vertices = lambda pose: RigAsset.vertices(rig, pose)
    return rig, world


@pytest.mark.parametrize('amplitude', [0., 1e-7, .3, 1.1])
def test_complete_jacobian_against_independent_scalar_perturbations(amplitude):
    rig, world = fixture()
    model = SurfacePoseModel(rig, world, 1, [1, 2])
    values = np.linspace(-amplitude, amplitude, model.size)
    actual, _, vertices, jac = model.evaluate(values)
    np.testing.assert_allclose(vertices, rig.vertices(actual), atol=1e-12, rtol=0)
    for axis in range(model.size):
        offset = np.zeros(model.size); offset[axis] = 1e-6
        plus = rig.vertices(model.evaluate(values+offset, derivatives=False)[0])
        minus = rig.vertices(model.evaluate(values-offset, derivatives=False)[0])
        np.testing.assert_allclose(jac[:, :, axis], (plus-minus)/2e-6, atol=2e-9, rtol=0)
    np.testing.assert_array_equal(jac[-1], 0)


def test_identity_and_inputs_preserved_and_world_root_translation_is_explicit():
    rig, world = fixture(); original = world.copy()
    model = SurfacePoseModel(rig, world, 1, [1, 2])
    values = np.zeros(model.size)
    np.testing.assert_allclose(model.evaluate(values)[0], original, atol=1e-14, rtol=0)
    values[:3] = [.01, -.03, .04]
    moved = model.evaluate(values)[0]
    np.testing.assert_allclose(moved[1, :3, 3]-original[1, :3, 3], values[:3], atol=1e-14, rtol=0)
    np.testing.assert_array_equal(world, original)


@pytest.mark.parametrize('root,rotations', [(1, [0]), (1, [1, 1]), (1, []), (True, [1]), (1, [True])])
def test_invalid_edit_hierarchy_rejected(root, rotations):
    rig, world = fixture()
    with pytest.raises(ValueError): SurfacePoseModel(rig, world, root, rotations)


def test_nonfinite_or_wrong_parameter_population_rejected():
    rig, world = fixture(); model = SurfacePoseModel(rig, world, 1, [1])
    for values in [[0.], [float('nan')]*model.size]:
        with pytest.raises(ValueError): model.evaluate(values)
