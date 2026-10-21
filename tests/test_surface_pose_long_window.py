"""Check later-interval indexing against independent native interpolation."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from test_surface_pose_interpolation import (
    SurfacePoseModel, InterpolatedPoseMap, SampledPoseWindow, CoupledPoseWindow,
    fixture, world_from_local, native_local, independent_points, problem,
)


@pytest.mark.parametrize('count', [3, 6, 8])
def test_long_window_every_interval_matches_native_skin_and_full_derivatives(count):
    rig, world = fixture()
    world[2, :3, :3] = np.eye(3)
    original = SurfacePoseModel(rig, world, 1, [1, 2])
    models = []
    for index in range(count):
        local = original.local.copy()
        local[1, :3, 3] += [index*.013, index*.004, -index*.006]
        for node in [1, 2]:
            local[node, :3, :3] = local[node, :3, :3] @ Rotation.from_rotvec(
                np.array([.021, -.013, .017])*index*node).as_matrix()
        models.append(SurfacePoseModel(rig, world_from_local(local, rig.parents), 1, [1, 2]))
    keys = CoupledPoseWindow([problem(m) for m in models], root_step_m=.025,
                             rotation_step_degrees=5.)
    samples = []
    for index, (left, right) in enumerate(zip(models[:-1], models[1:])):
        for fraction in [.25, .75]:
            sampled = SurfacePoseModel(rig, world_from_local(
                native_local(left.local, right.local, fraction), rig.parents), 1, [1, 2])
            samples.append((index, InterpolatedPoseMap(left, right, sampled, fraction),
                            problem(sampled)))
    window = SampledPoseWindow(keys, samples)
    rng = np.random.default_rng(837 + count)
    values = rng.normal(size=window.size)*.009
    window.grow(values, batch_size=1)
    rows, jac = window.pair(values)
    np.testing.assert_allclose(rows, window.values(values), atol=1e-12, rtol=0)
    poses = values.reshape(count, keys.width)
    for index, mapping, constraint in samples:
        correction = mapping.parameters(poses[index:index+2].ravel(), derivatives=False)[0]
        actual = constraint.model.evaluate(correction, derivatives=False)[2]
        expected = independent_points(models[index], models[index+1],
                                      poses[index:index+2].ravel(), mapping.fraction)
        np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=0)
    # Include directions in every pose separately: a missed late column cannot
    # be hidden by derivatives that happen to cancel in one global direction.
    for index in range(count):
        direction = np.zeros((count, keys.width))
        direction[index] = rng.normal(size=keys.width)
        direction = direction.ravel()/np.linalg.norm(direction)
        numerical = (window.values(values+1e-6*direction)
                     - window.values(values-1e-6*direction))/2e-6
        np.testing.assert_allclose(jac@direction, numerical, atol=3e-6, rtol=1e-7)
    # A sample in the last interval must reject an accidental first-interval
    # assignment even though all endpoint models have identical layouts.
    _, mapping, constraint = samples[-1]
    with pytest.raises(ValueError, match='exact endpoint'):
        SampledPoseWindow(keys, [(0, mapping, constraint)])
