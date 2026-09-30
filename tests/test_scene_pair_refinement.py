import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_scene_pair_refinement import refine_knots


def test_nested_curves_preserve_multiple_joints_on_an_irregular_clock():
    knots = np.array([.13, .21, .66, 1.1, 1.47]); refined, mapping = refine_knots(knots, 2)
    coarse = np.random.default_rng(91).normal(size=(2, 3, 3))*.001
    fine = (mapping@coarse.ravel()).reshape(2, 7, 3)
    times = np.r_[np.linspace(knots[0], knots[-1], 113), knots, refined]
    for joint in range(2):
        for axis in range(3):
            before = np.interp(times, knots, np.r_[0., coarse[joint, :, axis], 0.])
            after = np.interp(times, refined, np.r_[0., fine[joint, :, axis], 0.])
            np.testing.assert_allclose(before, after, atol=1e-18, rtol=0)
    assert np.linalg.norm(fine, axis=2).max() <= np.linalg.norm(coarse, axis=2).max()


@pytest.mark.parametrize('knots', [[0, 1], [0, .5, .5, 1], [0, np.nan, 1], list(range(7))])
def test_refinement_rejects_invalid_or_unsupported_knot_layout(knots):
    with pytest.raises(ValueError): refine_knots(knots, 2)


def test_refinement_preserves_native_protected_keys_and_embedded_motion():
    from test_timed_rotation_edit import fixture
    from timed_rotation_edit import TimedRotationEdit
    doc, binary = fixture(); times = np.arange(181)/120
    old = TimedRotationEdit(doc, binary, ['Arm', 'Twin'], times, [.1, 1.3], [[.713, .713]])
    knots, mapping = refine_knots(old.knots, 2)
    fine = TimedRotationEdit(doc, binary, ['Arm', 'Twin'], times, [.1, 1.3], [[.713, .713]], knots=knots)
    control = np.random.default_rng(19).normal(size=old.size)*.01
    np.testing.assert_allclose(old.world(control), fine.world(mapping@control), atol=1e-12, rtol=0)
    for left, right in zip(old.entries, fine.entries):
        np.testing.assert_array_equal(left['ids'], right['ids'])
        frozen = np.setdiff1d(np.arange(len(right['source'])), right['ids'])
        np.testing.assert_array_equal(fine.quaternions(mapping@control)[right['node']][frozen], right['source'][frozen])


def test_refined_angular_rows_keep_original_spans_caps_and_coarse_motion():
    from test_timed_rotation_edit import fixture
    from timed_rotation_edit import TimedRotationEdit
    from angular_motion_rows import AngularMotionRows
    from scene_pair_angular_constraints import linearize_angular
    doc,binary=fixture();times=np.arange(181)/120
    old=TimedRotationEdit(doc,binary,['Arm','Twin'],times,[.1,1.3],[[.713,.713]])
    policy=AngularMotionRows(old,doc['skins'][0]['joints'])
    knots,mapping=refine_knots(old.knots,2)
    fine=TimedRotationEdit(doc,binary,['Arm','Twin'],times,[.1,1.3],[[.713,.713]],knots=knots)
    original_caps=policy.radii.copy();original_knots=policy.knots.copy()
    empty=dict(gap_jacobian=np.zeros((1,fine.size)),vectors=np.empty((0,3)),jacobians=np.empty((0,3,fine.size)),radii=np.empty(0),kinds=np.array([],dtype='U24'))
    linear,proof=linearize_angular([dict(name='actor',model=fine)],[policy],empty)
    np.testing.assert_array_equal(linear['radii'],original_caps)
    np.testing.assert_array_equal(policy.knots,original_knots)
    assert len(policy.knots)<len(fine.knots) and proof[0]['rows']==len(original_caps)
    controls=np.random.default_rng(27).normal(size=old.size)*.001
    np.testing.assert_allclose(policy.values(old.world(controls))[0],policy.values(fine.world(mapping@controls))[0],atol=1e-9,rtol=0)
