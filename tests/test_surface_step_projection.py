from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_step_projection import project_steps


@pytest.mark.parametrize('count', [2, 6, 8])
def test_all_steps_bound_first_pose_fixed_and_inputs_unchanged(count):
    values = np.random.default_rng(412+count).normal(size=(count, 12))*.1
    original = values.copy()
    result = project_steps(values, root_step_m=.025, rotation_step_degrees=5.,
                           root_reserve_m=1e-5, rotation_reserve_radians=1e-5)
    np.testing.assert_array_equal(values, original)
    np.testing.assert_array_equal(result[0], original[0])
    steps = np.linalg.norm(np.diff(result, axis=0).reshape(count-1, -1, 3), axis=2)
    assert np.all(steps[:, 0] < .025)
    assert np.all(np.rad2deg(steps[:, 1:]) < 5.)
    # Each moved block lies on the segment from its corrected predecessor to
    # the original desired block, so it cannot overshoot that original block.
    for index in range(1, count):
        start = result[index-1].reshape(-1, 3)
        desired = original[index].reshape(-1, 3)-start
        moved = result[index].reshape(-1, 3)-start
        np.testing.assert_allclose(np.cross(desired, moved), 0., atol=1e-16)
        assert np.all(np.sum(desired*moved, axis=1) >= 0)
        assert np.all(np.linalg.norm(moved, axis=1) <= np.linalg.norm(desired, axis=1)+1e-15)


def test_feasible_input_and_unmodified_blocks_are_byte_exact():
    values = np.array([[.1, .2, .3, -.02, .03, .04]]*6)
    values[:, 0] += np.arange(6)*.001
    result = project_steps(values, root_step_m=.025, rotation_step_degrees=5.)
    assert result.tobytes() == values.tobytes()
    assert not np.shares_memory(result, values)
    values[-1, 3] += .5
    result = project_steps(values, root_step_m=.025, rotation_step_degrees=5.)
    np.testing.assert_array_equal(result[:, :3], values[:, :3])
    np.testing.assert_array_equal(result[:-1], values[:-1])


def test_step_feasibility_does_not_confer_contact_acceptance():
    from test_surface_pose_working_floor import MovingFloor
    from surface_pose_working_floor import WorkingFloorConstraints
    values = np.zeros((2, 6)); values[:, 1] = [.02, .12]
    constraints = WorkingFloorConstraints(MovingFloor(), angles_degrees=[45.],
        root_horizontal_m=.2, root_vertical_m=.5, floor_depth_m=.005,
        contact_error_m=.02, floor_reserve_m=.001, contact_reserve_m=.001,
        contacts=[dict(vertex=2, target_m=[0., .11, 0.])])
    constraints.grow(values[1], batch_size=1)
    assert constraints.assess(values[1])['numerical_constraints_pass']
    result = project_steps(values, root_step_m=.025, rotation_step_degrees=5.,
                           root_reserve_m=1e-5)
    assert np.linalg.norm(result[1, :3]-result[0, :3]) < .025
    assessment = constraints.assess(result[1])
    assert not assessment['numerical_constraints_pass']
    assert assessment['maximum_contact_error_m'] > .07


@pytest.mark.parametrize('fault', ['one_pose', 'nine_poses', 'width', 'nan', 'overflow',
    'root_zero', 'angle_zero', 'angle_large', 'negative_reserve', 'root_reserve',
    'angle_reserve', 'boolean', 'infinite', 'complex', 'string'])
def test_invalid_shapes_and_budgets_reject(fault):
    values = np.zeros((3, 6))
    options = dict(root_step_m=.025, rotation_step_degrees=5.)
    if fault == 'one_pose': values = values[:1]
    if fault == 'nine_poses': values = np.zeros((9, 6))
    if fault == 'width': values = np.zeros((3, 7))
    if fault == 'nan': values[1, 2] = np.nan
    if fault == 'overflow': values[0, 0], values[1, 0] = -1e308, 1e308
    if fault == 'root_zero': options['root_step_m'] = 0.
    if fault == 'angle_zero': options['rotation_step_degrees'] = 0.
    if fault == 'angle_large': options['rotation_step_degrees'] = 181.
    if fault == 'negative_reserve': options['root_reserve_m'] = -1e-5
    if fault == 'root_reserve': options['root_reserve_m'] = .025
    if fault == 'angle_reserve': options['rotation_reserve_radians'] = np.deg2rad(5.)
    if fault == 'boolean': options['root_step_m'] = True
    if fault == 'infinite': options['rotation_step_degrees'] = np.inf
    if fault == 'complex': options['root_step_m'] = .025+0j
    if fault == 'string': options['root_step_m'] = '.025'
    with pytest.raises(ValueError): project_steps(values, **options)
