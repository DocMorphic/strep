from fractions import Fraction
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_normal_box import SurfaceNormalBox

POINTS = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0]])
FACES = np.array([[0, 1, 2]])


def normal_box(points=POINTS, faces=FACES, group=(0,)):
    return SurfaceNormalBox(points, faces, group)


def test_zero_radius_exact_orientation_and_boundary():
    patch = normal_box()
    assert not patch.bound([0, 0, -1], 0, minimum_alignment_cosine=1)['exact_geometric_conflict']
    assert patch.bound([0, 0, 1], 0, minimum_alignment_cosine=0)['exact_geometric_conflict']
    # Nonunit target directions are handled without rounded normalization.
    assert not patch.bound([0, 0, -2], 0, minimum_alignment_cosine=1)['exact_geometric_conflict']
    assert not patch.bound([1, 0, -1], 0, minimum_alignment_cosine=.5)['exact_geometric_conflict']
    assert patch.bound([1, 0, -1], 0, minimum_alignment_cosine=.75)['exact_geometric_conflict']


def test_cosine_boundary_uses_strict_exact_arithmetic():
    patch = normal_box()
    at = patch.bound([0, 0, -1], 0, minimum_alignment_cosine=1)
    assert Fraction(at['squared_alignment_gap_exact']) == 0
    assert not at['exact_geometric_conflict']
    almost = patch.bound([1e-15, 0, -1], 0, minimum_alignment_cosine=1)
    assert Fraction(almost['squared_alignment_gap_exact']) > 0
    assert almost['exact_geometric_conflict']


def test_large_box_can_include_valid_rotated_triangle():
    result = normal_box().bound([0, 0, 1], 1, minimum_alignment_cosine=.96)
    assert not result['exact_geometric_conflict']
    flipped = POINTS.copy(); flipped[2, 1] = -1
    assert np.max(abs(flipped-POINTS)) == 2
    assert not normal_box().bound([0, 0, 1], 2, minimum_alignment_cosine=.96)['exact_geometric_conflict']


def test_all_incident_faces_once_even_if_group_shares_vertices():
    points = np.vstack((POINTS, [0, 0, 1]))
    faces = np.array([[0, 1, 2], [0, 3, 1], [1, 3, 2]])
    patch = normal_box(points, faces, [0, 1])
    result = patch.bound([0, -1, -1], 0, minimum_alignment_cosine=.1)
    expected = np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]]).sum(0)
    assert result['incident_faces'] == [0, 1, 2]
    assert list(map(Fraction, result['cross_sum_center_exact'])) == list(map(Fraction, expected))


def test_disconnected_nonincident_faces_do_not_change_group_normal():
    points = np.vstack((POINTS, POINTS+10))
    result = normal_box(points, np.array([[0, 1, 2], [3, 5, 4]])).bound([0, 0, -1], 0, minimum_alignment_cosine=1)
    assert result['incident_faces'] == [0]
    assert not result['exact_geometric_conflict']


def test_arithmetic_reserve_expands_enclosure_and_never_approves():
    patch = normal_box()
    assert patch.bound([0, 0, 1], 0, minimum_alignment_cosine=.96)['exact_geometric_conflict']
    result = patch.bound([0, 0, 1], 0, minimum_alignment_cosine=.96, cross_sum_reserve_m2=[0, 0, 2])
    assert not result['exact_geometric_conflict']
    for key in ['vertex_boxes_certified', 'pose_reachability_proven', 'normal_availability_proven', 'quality_approved', 'release_approved']:
        assert result[key] is False


def test_zero_cross_sum_is_inconclusive_not_available_normal():
    result = normal_box(np.zeros((3, 3))).bound([0, 0, 1], 0, minimum_alignment_cosine=1)
    assert not result['exact_geometric_conflict'] and not result['normal_availability_proven']


def test_input_mutation_cannot_change_patch():
    points, faces, group = POINTS.copy(), FACES.copy(), np.array([0])
    patch = normal_box(points, faces, group)
    before = patch.bound([0, 0, -1], 0, minimum_alignment_cosine=1)
    points[:] = 4; faces[:] = 0; group[:] = 2
    assert patch.bound([0, 0, -1], 0, minimum_alignment_cosine=1) == before


def test_per_vertex_scalar_and_xyz_radii_agree():
    patch = normal_box()
    assert patch.bound([0, 0, 1], .1, minimum_alignment_cosine=.7) == patch.bound(
        [0, 0, 1], [.1]*3, minimum_alignment_cosine=.7) == patch.bound(
        [0, 0, 1], [[.1]*3]*3, minimum_alignment_cosine=.7)


def test_every_exact_random_perturbation_is_enclosed_and_valid_pose_never_excluded():
    rng = np.random.default_rng(3456)
    for _ in range(45):
        points = rng.normal(size=(5, 3))*.1
        faces = np.array([[0, 1, 2], [0, 2, 3], [0, 3, 4]])
        radii = rng.random((5, 3))*.02
        candidate = points+rng.uniform(-1, 1, (5, 3))*radii
        patch = normal_box(points, faces)
        summed = [Fraction(0)]*3
        for f in faces:
            exact = [[Fraction.from_float(float(x)) for x in candidate[i]] for i in f]
            a = [y-x for x, y in zip(exact[0], exact[1])]
            b = [y-x for x, y in zip(exact[0], exact[2])]
            cross = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
            summed = [x+y for x, y in zip(summed, cross)]
        # Candidate float rounding can exceed a box by an ulp: explicitly
        # enlarge to the actual exact component displacement before asserting.
        exact_radii = np.maximum(radii, np.nextafter(abs(candidate-points), np.inf))
        target = -np.array(list(map(float, summed)))
        result = patch.bound(target, exact_radii, minimum_alignment_cosine=.9)
        for value, interval in zip(summed, result['cross_sum_intervals_exact']):
            lo, hi = map(Fraction, interval)
            assert lo <= value <= hi
        assert not result['exact_geometric_conflict']


@pytest.mark.parametrize('radius', [-1, np.nan, np.inf, True, [0, 0], [[0, 0, 0]]])
def test_bad_radii_rejected(radius):
    with pytest.raises(ValueError): normal_box().bound([0, 0, -1], radius, minimum_alignment_cosine=.96)


@pytest.mark.parametrize('target', [[0, 0, 0], [1, 2], [np.nan, 0, 1], ['0', '0', '1']])
def test_bad_targets_rejected(target):
    with pytest.raises(ValueError): normal_box().bound(target, 0, minimum_alignment_cosine=.96)


@pytest.mark.parametrize('cosine', [-.1, 1.1, np.nan, True, [.5]])
def test_bad_cosine_rejected(cosine):
    with pytest.raises(ValueError): normal_box().bound([0, 0, -1], 0, minimum_alignment_cosine=cosine)


@pytest.mark.parametrize('reserve', [-1, np.nan, True, [0, 1], [0, -1, 0]])
def test_bad_reserve_rejected(reserve):
    with pytest.raises(ValueError): normal_box().bound([0, 0, -1], 0, minimum_alignment_cosine=.96, cross_sum_reserve_m2=reserve)


@pytest.mark.parametrize('faces,group', [([[0, 1, 3]], [0]), ([[0., 1, 2]], [0]),
    ([[0, 1, 2]], [0, 0]), ([[0, 1, 2]], [3]), ([[0, 1, 2]], [True]),
    ([[0, 1, 2]], [0.]), ([], [0])])
def test_bad_topology_or_group_rejected(faces, group):
    with pytest.raises(ValueError): normal_box(faces=faces, group=group)


def test_integer_geometry_cannot_be_silently_rounded_to_binary64():
    with pytest.raises(ValueError): normal_box(np.array([[2**53+1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int64))


def test_bound_does_not_modify_caller_arrays():
    target = np.array([1., 0, -1]); radii = np.full((3, 3), .01); reserve = np.ones(3)*.0001
    originals = [a.copy() for a in (target, radii, reserve)]
    normal_box().bound(target, radii, minimum_alignment_cosine=.96, cross_sum_reserve_m2=reserve)
    assert all(np.array_equal(a, b) for a, b in zip((target, radii, reserve), originals))
