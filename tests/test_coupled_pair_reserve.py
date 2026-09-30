import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_pair_reserve import empirical_reserve, tightened_radii, conservative_refresh


def test_reserve_protects_each_row_against_positive_observed_error():
    predicted = np.array([[1., 2., 3., 4.], [1., 2., 3., 4.]])
    exported = np.array([[1.1, 2.01, 2.9, 4.3], [1.2, 1.9, 3.04, 4.1]])
    kinds = np.array(['edit', 'speed', 'acceleration', 'acceleration'])
    reserve, error = empirical_reserve(predicted, exported, kinds)
    np.testing.assert_allclose(error, [.2, .01, .04, .3])
    np.testing.assert_allclose(reserve, [0., .02, .08, .6])
    original = np.array([1., 3., 4., 5.])
    np.testing.assert_allclose(tightened_radii(original, reserve, kinds), [1., 2.98, 3.92, 4.4])
    np.testing.assert_array_equal(original, [1., 3., 4., 5.])


def test_improvement_does_not_create_negative_reserves():
    reserve, _ = empirical_reserve([[2.]], [[1.]], ['speed'])
    np.testing.assert_array_equal(reserve, [0.])


def test_impossible_or_misaligned_reserves_are_not_silently_clipped():
    with pytest.raises(ValueError, match='exceeds'):
        tightened_radii([.1], [.2], ['speed'])
    with pytest.raises(ValueError, match='edit budgets'):
        tightened_radii([1.], [.1], ['edit'])
    with pytest.raises(ValueError, match='Matching'):
        empirical_reserve([[1., 2.]], [[1.]], ['speed', 'speed'])
    with pytest.raises(ValueError, match='Finite'):
        empirical_reserve([[np.nan]], [[1.]], ['speed'])


def test_empirical_reserve_does_not_certify_a_new_direction():
    reserve, _ = empirical_reserve([[1.]], [[1.01]], ['speed'])
    assert reserve[0] == pytest.approx(.02)
    # A later direction can have a larger error; final exported checks are required.
    later_prediction, later_export = .97, 1.001
    assert later_prediction <= tightened_radii([1.], reserve, ['speed'])[0]
    assert later_export > 1.+1e-5


def test_refresh_retains_old_margins_and_only_tightens_motion_rows():
    reserve,_=conservative_refresh([0,.1,.01],[[1.,2.,3.]],[[1.2,2.01,3.02]],['edit','speed','acceleration'])
    np.testing.assert_allclose(reserve,[0,.1,.04])


def test_refresh_rejects_a_prior_native_edit_margin():
    with pytest.raises(ValueError,match='prior motion'):
        conservative_refresh([.1],[[1.]],[[1.]],['edit'])


def test_angular_margins_tighten_individual_rows_without_changing_edit_budget():
    kinds = ['edit', 'angular_speed', 'angular_acceleration']
    reserve, _ = empirical_reserve([[1., 2., 3.], [1., 2., 3.]], [[1.1, 2.001, 3.01], [1., 1.999, 3.02]], kinds)
    np.testing.assert_allclose(reserve, [0., .002, .04])
    caps = np.array([1., 2., 3.]); tightened = tightened_radii(caps, reserve, kinds)
    np.testing.assert_allclose(tightened, [1., 1.998, 2.96])
    np.testing.assert_array_equal(caps, [1., 2., 3.])
    with pytest.raises(ValueError, match='exceeds'):
        tightened_radii([.001], [.002], ['angular_speed'])
