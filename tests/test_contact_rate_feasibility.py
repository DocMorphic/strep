from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_rate_feasibility import assemble, analyze, certificate


def request(target=0., speed=1., acceleration=1.):
    track = np.zeros((37, 3))  # 10 native frames, 120 Hz audit clock.
    pins = [dict(space='world', start_frame=4, end_frame=5, position_m=[target, 0, 0])]
    rates = [dict(phase=p, first_frame=a, last_frame=b, reference_ceilings=[speed, acceleration])
             for p, a, b in [('approach', 2, 4), ('hold', 4, 5), ('release', 5, 7)]]
    return track, pins, rates, [2, 7]


def test_static_feasible_track_never_proves_conflict():
    report, _ = analyze(*request())
    assert not report['any_verified_conflict'] and not report['quality_approved']
    assert all(r['solver_status'] == 0 for r in report['axes'])


def test_acceleration_detects_conflict_missed_by_distance_over_speed():
    # 2 native frames give 66.7 mm travel at 1 m/s, enough for this 15 mm
    # minimum travel. But near-zero acceleration cannot leave the held rest.
    report, arrays = analyze(*request(target=.02, acceleration=.001))
    assert report['any_verified_conflict'] and report['axes'][0]['conflict_verified']
    assert not any(r['conflict_verified'] for r in report['axes'][1:])
    check = certificate(arrays['matrix'], arrays['rhs'][:, 0], arrays['radius'], arrays['multipliers'][0])
    assert check['contradiction_upper_bound_m'] < 0
    assert check['contradiction_upper_bound_exact'] == report['axes'][0]['contradiction_upper_bound_exact']


def test_rate_phase_boundary_stencils_include_preserved_neighbor():
    matrix, rhs, _, labels = assemble(*request())
    index = next(i for i, label in enumerate(labels) if label == dict(kind='acceleration', phase='approach', frame=2., sign=1))
    np.testing.assert_array_equal(matrix[index].indices, [7, 8, 9])
    np.testing.assert_array_equal(matrix[index].data, [1, -2, 1])
    assert rhs[index, 0] > 1/120**2  # Conservative diagnostic reserve.
    assert not any(label['kind'] == 'held' and label['frame'] in [2, 7] for label in labels)


def test_multiple_pins_on_same_track_cannot_ignore_a_conflicting_interval():
    track, pins, rates, window = request()
    pins.append(dict(space='world', start_frame=4, end_frame=5, position_m=[.02, 0, 0]))
    report, _ = analyze(track, pins, rates, window)
    assert report['any_verified_conflict']


def test_translation_does_not_create_or_remove_certificate():
    args = request(target=.02, acceleration=.001)
    report, _ = analyze(*args)
    track, pins, rates, window = args
    track += [2., -1., 3.]
    pins[0]['position_m'] = [2.02, -1., 3.]
    translated, _ = analyze(track, pins, rates, window)
    assert translated['any_verified_conflict'] == report['any_verified_conflict']


def test_no_conflict_claim_from_nonzero_stationarity_without_bound_charge():
    # A nearly zero weighted RHS is negative, but the permitted coordinate
    # domain can explain it. Ignoring A^T y would falsely claim infeasibility.
    proof = certificate(csr_matrix([[1.]]), [-1e-12], 1., [1.])
    assert not proof['conflict_verified'] and proof['contradiction_upper_bound_m'] > 0


def test_exact_certificate_of_inconsistent_scalar_bounds():
    proof = certificate(csr_matrix([[1.], [-1.]]), [0., -1.], 1000., [.5, .5])
    assert proof['conflict_verified'] and proof['contradiction_upper_bound_exact'] == '-1/2'
    assert proof['stationarity_residual_l1_exact'] == '0'


@pytest.mark.parametrize('weights', [[-1., 1.], [float('nan'), 1.], [float('inf'), 0.]])
def test_invalid_certificate_weights_rejected(weights):
    with pytest.raises(ValueError):certificate(csr_matrix([[1.], [-1.]]), [0., -1.], 1., weights)


def test_incomplete_rate_coverage_rejected():
    track, pins, rates, window = request()
    with pytest.raises(ValueError, match='coverage'):assemble(track, pins, rates[1:], window)


@pytest.mark.parametrize('bad', [-1, float('nan'), float('inf'), True])
def test_invalid_rate_cap_rejected(bad):
    track, pins, rates, window = request();rates[0]['reference_ceilings'][0] = bad
    with pytest.raises(ValueError):assemble(track, pins, rates, window)
