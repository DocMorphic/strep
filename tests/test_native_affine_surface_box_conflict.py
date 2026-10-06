"""Independent exact-arithmetic checks of the affine-only box diagnostic."""
import copy
from fractions import Fraction as F
from pathlib import Path
import sys
import itertools
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_affine_surface_box_conflict import diagnose, verify_witness


def exact_maximum(gap, coefficients, lower, upper):
    return F.from_float(float(gap))+sum(
        max(F.from_float(float(a))*F.from_float(float(l)),
            F.from_float(float(a))*F.from_float(float(u)))
        for a, l, u in zip(coefficients, lower, upper))


def rational(value):
    return F(int(value['numerator']), int(value['denominator']))


def fixture():
    return [np.array([-.8, -2.]), sparse.csr_matrix([[2., -3.], [.2, -.1]]),
            np.array([-.1, -.2]), np.array([.3, .1])]


def test_mixed_sign_endpoints_give_exact_certificate_and_complete_scan():
    args = fixture(); saved = [a.copy() for a in args]
    bounds, report = diagnose(*args)
    assert report['status'] == 'CertifiedAffineRowConflict'
    assert report['certified_individual_conflict_rows'] == 1 and len(bounds) == 2
    witness = report['witness']; assert witness['row_index'] == 1
    np.testing.assert_array_equal(witness['maximizing_delta'], [.3, -.2])
    maximum = exact_maximum(args[0][1], args[1].toarray()[1], args[2], args[3])
    assert rational(witness['maximum_gap_exact']) == maximum
    assert rational(witness['normalized_surface_excess_lower_bound_exact']) == -maximum/F.from_float(.005)
    checked = verify_witness(report, *args)
    assert checked['selected_exact_row_conflict_verified'] and not checked['aggregate_screening_count_independently_verified']
    assert not report['native_feasibility_checked'] and not report['nonlinear_geometry_infeasibility_proven']
    for original, previous in zip(args, saved):
        np.testing.assert_array_equal(original.toarray() if sparse.issparse(original) else original,
                                      previous.toarray() if sparse.issparse(previous) else previous)


@pytest.mark.parametrize('magnitude', [1e-300, 1e-12, 1., 1e200])
def test_every_outward_bound_encloses_independent_exact_maximum(magnitude):
    rng = np.random.default_rng(793)
    gaps = rng.normal(size=37)*magnitude; jac = rng.normal(size=(37, 7))*magnitude
    jac[rng.random(jac.shape) < .6] = 0.
    lower = rng.uniform(-.4, 0., 7); upper = rng.uniform(0., .4, 7)
    bounds, report = diagnose(gaps, sparse.csc_matrix(jac), lower, upper)
    count = 0
    for i in range(len(gaps)):
        exact = exact_maximum(gaps[i], jac[i], lower, upper)
        assert F.from_float(float(bounds[i])) >= exact
        if bounds[i] < 0:
            assert exact < 0; count += 1
    assert report['certified_individual_conflict_rows'] == count


def test_exact_certificate_matches_every_corner_of_a_small_box():
    args = fixture(); _, report = diagnose(*args); index = report['witness']['row_index']
    corners = itertools.product(*zip(args[2], args[3]))
    maxima = [F.from_float(float(args[0][index]))+sum(F.from_float(float(a))*F.from_float(float(x))
              for a, x in zip(args[1].toarray()[index], corner)) for corner in corners]
    assert max(maxima) == rational(report['witness']['maximum_gap_exact'])


def test_late_row_and_last_control_are_included():
    gaps = np.ones(257); gaps[-1] = -2.
    jac = sparse.csr_matrix(([.5], ([256], [95])), shape=(257, 96))
    bounds, report = diagnose(gaps, jac, np.zeros(96), np.ones(96))
    assert report['original_rows'] == 257 and report['controls'] == 96
    assert report['witness']['row_index'] == 256 and bounds[-1] < 0.
    assert rational(report['witness']['maximum_gap_exact']) == F(-3, 2)


def test_zero_width_box_and_exact_clearance_boundary():
    _, report = diagnose([0.], [[1.]], [0.], [0.])
    assert report['witness'] is None and report['status'] == 'NoCertifiedIndividualRowConflict'
    _, report = diagnose([0.], [[1.]], [0.], [0.], clearance=.1, scale=.2)
    assert rational(report['witness']['normalized_surface_excess_lower_bound_exact']) == F(1, 2)


def test_no_individual_conflict_does_not_imply_joint_feasibility():
    # Each row can attain >= 0, but x >= .75 and x <= -.75 are incompatible.
    _, report = diagnose([-.75, -.75], [[1.], [-1.]], [-1.], [1.])
    assert report['witness'] is None and report['certified_individual_conflict_rows'] == 0
    assert not report['quality_approved'] and not report['release_approved']
    with pytest.raises(ValueError): verify_witness(report, [-.75, -.75], [[1.], [-1.]], [-1.], [1.])


def test_larger_box_can_remove_local_conflict_without_changing_row():
    _, small = diagnose([-1.], [[1.]], [0.], [.1])
    _, large = diagnose([-1.], [[1.]], [0.], [2.])
    assert small['witness'] is not None and large['witness'] is None
    with pytest.raises(ValueError, match='Bound'): verify_witness(small, [-1.], [[1.]], [0.], [2.])


def test_subnormal_product_and_cancellation_do_not_create_false_conflict():
    tiny = np.nextafter(0., 1.)
    gaps = [-tiny, -1.]; jac = [[tiny], [1.]]
    bounds, report = diagnose(gaps, jac, [0.], [1.])
    assert np.all(bounds >= 0) and report['witness'] is None
    for i in range(2): assert F.from_float(float(bounds[i])) >= exact_maximum(gaps[i], jac[i], [0.], [1.])


def test_overflow_cannot_certify_positive_unbounded_upper():
    bounds, report = diagnose([-1e308], [[1e308, 1e308]], [0., 0.], [1e308, 1e308])
    assert np.isposinf(bounds[0]) and report['unbounded_upper_rows'] == 1 and report['witness'] is None


def test_negative_overflow_has_valid_outward_bound_and_exact_rational_witness():
    bounds, report = diagnose([-1e308], [[-1e308]], [1e308], [1e308])
    exact = exact_maximum(-1e308, [-1e308], [1e308], [1e308])
    assert F.from_float(float(bounds[0])) >= exact and bounds[0] < 0
    assert rational(report['witness']['maximum_gap_exact']) == exact
    assert verify_witness(report, [-1e308], [[-1e308]], [1e308], [1e308])['selected_exact_row_conflict_verified']


@pytest.mark.parametrize('change', ['row', 'maximum', 'point', 'digest', 'gap', 'other_gap', 'matrix',
                                   'box', 'clearance', 'scale', 'approval', 'nonlinear', 'row_boolean'])
def test_tampered_or_rebound_witness_is_rejected(change):
    args = fixture(); _, report = diagnose(*args); report = copy.deepcopy(report); options = {}
    if change == 'row': report['witness']['row_index'] = 0
    elif change == 'maximum': report['witness']['maximum_gap_exact']['numerator'] = '-10'
    elif change == 'point': report['witness']['maximizing_delta'][0] = 0.
    elif change == 'digest': report['affine_inputs_sha256'] = '0'*64
    elif change == 'gap': args[0][1] += .01
    elif change == 'other_gap': args[0][0] += .01
    elif change == 'matrix': args[1] = sparse.csr_matrix([[2., -3.], [.1, -.1]])
    elif change == 'box': args[3][1] += .01
    elif change == 'clearance': options['clearance'] = .01
    elif change == 'scale': options['scale'] = .01
    elif change == 'approval': report['quality_approved'] = 0
    elif change == 'nonlinear': report['nonlinear_geometry_infeasibility_proven'] = True
    else: report['witness']['row_index'] = True
    with pytest.raises(ValueError): verify_witness(report, *args, **options)


@pytest.mark.parametrize('change', ['nan', 'infinity', 'empty', 'shape', 'order', 'complex', 'duplicate',
                                   'clearance_boolean', 'clearance_negative', 'scale_zero', 'scale_nan', 'controls'])
def test_invalid_population_box_or_policy_rejects(change):
    args = fixture(); options = {}
    if change == 'nan': args[0][0] = np.nan
    elif change == 'infinity': args[2][0] = -np.inf
    elif change == 'empty': args[0] = np.array([])
    elif change == 'shape': args[1] = sparse.csr_matrix((1, 2))
    elif change == 'order': args[2][0] = 1.
    elif change == 'complex': args[1] = args[1].astype(complex)
    elif change == 'duplicate': args[1] = sparse.csr_matrix(([1., 1.], [0, 0], [0, 2, 2]), shape=(2, 2))
    elif change == 'clearance_boolean': options['clearance'] = True
    elif change == 'clearance_negative': options['clearance'] = -.1
    elif change == 'scale_zero': options['scale'] = 0.
    elif change == 'scale_nan': options['scale'] = float('nan')
    else: args = [np.array([0.]), sparse.csr_matrix((1, 97)), np.zeros(97), np.ones(97)]
    with pytest.raises(ValueError): diagnose(*args, **options)
