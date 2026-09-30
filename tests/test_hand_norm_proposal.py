import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_norm_proposal import rate_vectors, measurement, linearize, assemble, backtrack
from sampled_motion_caps import measures


def sample(x):
    return dict(vectors=np.array([[1., x[0], 0.], [0., 0., 0.]]), caps=np.array([1., 1.]),
                scales=np.ones(2), margins=np.array([1.-x[0]]), depths=np.array([.02-.01*x[0], -.01]))


def test_rate_vectors_match_original_measures_with_changing_rotation_axes():
    rng = np.random.default_rng(42)
    p = rng.normal(size=(13, 4, 3))
    r = Rotation.from_rotvec(rng.normal(size=(52, 3))*.08).as_matrix().reshape(13, 4, 3, 3)
    payload = dict(positions=p, rotations=r)
    for vector, scalar in zip(rate_vectors(payload, 1/120), measures(payload, 1/120)):
        np.testing.assert_array_equal(np.linalg.norm(vector, axis=2), scalar)


@pytest.mark.parametrize('dt', [0., -1., float('nan'), float('inf')])
def test_invalid_clock_rejected(dt):
    with pytest.raises(ValueError, match='sample interval'): rate_vectors({}, dt)


def test_ambiguous_angular_step_is_not_smoothed_away():
    r = Rotation.from_rotvec([[0., 0., 0.], [np.pi, 0., 0.]]).as_matrix()[:, None]
    with pytest.raises(ValueError, match='Ambiguous'):
        rate_vectors(dict(positions=np.zeros((2, 1, 3)), rotations=r), 1/120)


def test_cone_catches_tangential_acceleration_that_scalar_linearization_misses():
    model = linearize(sample, sample, np.zeros(1))
    a, b, meta = assemble(model, .01)
    z = np.array([1., 1.]); slack = b-a@z
    assert meta['retained_norm_rows'] == [0] and meta['omitted_norm_rows'] == 1
    assert np.min(slack[:meta['linear_rows']]) >= -1e-14
    cone = slack[meta['linear_rows']:]
    np.testing.assert_allclose(cone, [1., 1., .01, 0.])
    assert np.linalg.norm(cone[1:]) > cone[0]
    assert measurement(sample(np.array([.01])))['minimum_margin'] < 0
    # Scalar norm has derivative zero along this direction at the source.
    derivative = (np.linalg.norm(sample([1e-4])['vectors'][0])-np.linalg.norm(sample([-1e-4])['vectors'][0]))/2e-4
    assert derivative == 0


def test_actual_base_values_are_retained_when_smooth_model_differs():
    def rounded(x):
        result = sample(x); result['vectors'][0, 0] = .999
        return result
    model = linearize(rounded, sample, np.zeros(1))
    assert model['base']['vectors'][0, 0] == .999
    np.testing.assert_allclose(model['jacobian']['vectors'][0, :, 0], [0., 1., 0.])
    a, b, meta = assemble(model, .1)
    slack = b-a@np.array([.4, 1.])
    np.testing.assert_allclose(slack[meta['linear_rows']:], [1., .999, .04, 0.])


def test_fixed_original_caps_required_during_derivatives_and_acceptance():
    def changed(x):
        result = sample(x); result['caps'][0] += .001
        return result
    with pytest.raises(ValueError, match='caps'): linearize(sample, changed, np.zeros(1))
    with pytest.raises(ValueError, match='caps'): backtrack(changed, np.zeros(1), np.array([.01]), sample([0]))


def test_exact_acceptance_rejects_improved_contact_when_motion_fails():
    candidate, records = backtrack(sample, np.zeros(1), np.array([.01]), sample([0]))
    assert candidate is None and len(records) == 8
    assert all(r['minimum_margin'] < 0 and not r['accepted'] for r in records)


def test_exact_acceptance_can_back_off_but_cannot_relax_a_cap():
    def exact(x):
        result = sample(x); result['vectors'][0] = [.99999, x[0], 0.]
        return result
    candidate, records = backtrack(exact, np.zeros(1), np.array([.01]), exact([0]))
    np.testing.assert_array_equal(candidate, [.0025])
    assert [r['accepted'] for r in records] == [False, False, True]
    assert records[-1]['minimum_margin'] >= 0


def test_zero_or_worse_contact_improvement_is_not_accepted():
    candidate, _ = backtrack(sample, np.zeros(1), np.zeros(1), sample([0]))
    assert candidate is None


def test_central_probes_cannot_silently_clip_at_control_boundary():
    with pytest.raises(ValueError, match='Interior'):
        linearize(sample, sample, np.ones(1))


def test_affine_omission_bounds_hold_over_all_box_corners():
    rng = np.random.default_rng(75); width = 3
    base = dict(vectors=rng.normal(size=(30, 3))*.1, caps=np.ones(30), scales=np.ones(30),
                margins=np.ones(1), depths=np.array([.01]))
    jac = dict(vectors=rng.normal(size=(30, 3, width)), margins=np.zeros((1, width)), depths=np.zeros((1, width)))
    model = dict(base=base, jacobian=jac, point=np.array([.99, -.99, 0.]))
    _, _, record = assemble(model, .1)
    omitted = np.setdiff1d(np.arange(30), record['retained_norm_rows'])
    assert len(omitted) > 0
    import itertools
    for corner in itertools.product(*[[-.1, .01], [-.01, .1], [-.1, .1]]):
        assert np.all(np.linalg.norm(base['vectors'][omitted]+jac['vectors'][omitted]@corner, axis=1) <= 1.)
