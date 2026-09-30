import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from angular_motion_rows import AngularMotionRows
from timed_rotation_edit import TimedRotationEdit
from test_timed_rotation_edit import fixture


def model():
    doc, binary = fixture()
    return TimedRotationEdit(doc, binary, ['Arm'], np.arange(181)/120, [.1, 1.3], [[.713, .713]])


def test_angular_rows_cover_joint_itself_and_every_changed_stencil():
    m = model(); joints = list(range(len(m.document['nodes']))); policy = AngularMotionRows(m, joints)
    delta = np.arange(m.size)*.001; source = policy._all_values(m.source_world); edited = policy._all_values(m.world(delta))
    for (a, _), (b, _), (rows, columns, caps) in zip(source, edited, policy.specs):
        changed = np.linalg.norm(b-a, axis=2) > 1e-10; covered = np.zeros(changed.shape, bool); covered[rows, columns] = True
        assert np.all(~changed | covered)
        assert joints.index(m.nodes[0]) in columns
        assert np.all(np.linalg.norm(a[rows, columns], axis=1) <= caps+1e-10)


def test_angular_linearization_predicts_independent_native_motion_direction():
    m = model(); policy = AngularMotionRows(m, list(range(len(m.document['nodes']))))
    zero = np.zeros(m.size); world, derivatives = m.world_pair(zero); value, jacobian = policy.values(world, derivatives)
    direction = np.random.default_rng(41).normal(size=m.size)*1e-7
    actual, _ = policy.values(m.world(direction))
    np.testing.assert_allclose(actual, value+np.einsum('nid,d->ni', jacobian, direction), atol=1e-7, rtol=0)
    assert set(policy.kinds) == {'angular_speed', 'angular_acceleration'}


def test_translation_derivative_has_no_angular_effect():
    m = model(); policy = AngularMotionRows(m, list(range(len(m.document['nodes']))))
    world = m.source_world; derivative = np.zeros(world.shape+(1,)); derivative[:, :, 0, 3, 0] = 1.
    _, jacobian = policy.values(world, derivative)
    np.testing.assert_array_equal(jacobian, 0.)
