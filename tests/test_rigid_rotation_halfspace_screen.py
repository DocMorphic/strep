import copy
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rigid_rotation_halfspace_screen import screen, sqrt_upper, verify


def planes():
    # All six outward unit cube planes, with exact binary coordinates.
    return [
        [[1, -1, -1], [1, 1, -1], [1, -1, 1]],
        [[-1, -1, -1], [-1, -1, 1], [-1, 1, -1]],
        [[-1, 1, -1], [-1, 1, 1], [1, 1, -1]],
        [[-1, -1, -1], [1, -1, -1], [-1, -1, 1]],
        [[-1, -1, 1], [1, -1, 1], [-1, 1, 1]],
        [[-1, -1, -1], [-1, 1, -1], [1, -1, -1]],
    ]


@pytest.mark.parametrize('value', [Fraction(0), Fraction(4), Fraction(2), Fraction(1, 10**200), Fraction(10**100, 3)])
@pytest.mark.parametrize('bits', [16, 128, 256])
def test_square_root_is_exact_outward_and_minimal_grid_enclosure(value, bits):
    upper = sqrt_upper(value, bits)
    assert upper**2 >= value
    if upper > 0:
        assert (upper-Fraction(1, 2**bits))**2 < value


def test_all_planes_strict_and_zero_bound_is_inconclusive():
    r = screen([0, 0, 0], [0, 0, 0], [0, 0, 0], planes(), '1/10', '1/10')
    assert r['all_planes_strictly_containing_for_every_declared_rotation']
    assert len(r['planes']) == 6 and all(Fraction(v['plane_residual_upper_rational']) == -4 for v in r['planes'])
    assert verify(r) == r
    r = screen([1, 0, 0], [1, 0, 0], [0, 0, 0], planes(), '0', '0')
    assert not r['all_planes_strictly_containing_for_every_declared_rotation']
    assert not r['planes'][0]['strictly_behind_for_all_declared_rotations']
    assert not r['actual_mesh_interior_certified'] and not r['broader_articulated_infeasibility_proven']


def test_exact_upper_bounds_enclose_independent_sampled_rotations():
    rng = np.random.default_rng(703)
    point = np.array([.21, -.35, .17]); source = np.array([-.18, .04, .1]); target = np.array([.12, .23, -.06])
    triangles = planes()
    r = screen(point, source, target, triangles, '1/5', '3/10')
    before = copy.deepcopy(triangles)
    for _ in range(200):
        axes = rng.normal(size=(2, 3)); axes /= np.linalg.norm(axes, axis=1)[:, None]
        sa, ta = rng.uniform(0, [.2, .3])
        sr, tr = Rotation.from_rotvec(axes[0]*sa), Rotation.from_rotvec(axes[1]*ta)
        moved_point = source + sr.apply(point-source)
        for triangle, row in zip(triangles, r['planes']):
            a, b, c = np.array(triangle, float)
            n = np.cross(b-a, c-a)
            moved_a = target + tr.apply(a-target)
            residual = tr.apply(n) @ (moved_point-moved_a)
            assert residual <= float(Fraction(row['plane_residual_upper_rational'])) + 1e-13
    assert triangles == before


def test_point_at_source_pivot_has_no_source_rotation_reserve():
    r = screen([.1, .2, .3], [.1, .2, .3], [0, 0, 0], planes(), '1', '1/10')
    assert all(Fraction(row['source_rotation_reserve_rational']) == 0 for row in r['planes'])


def test_negative_normal_projection_retains_cosine_reserve():
    r = screen([-.5, .1, 0], [-.5, .1, 0], [0, 0, 0], planes()[:1], '0', '1/10')
    row = r['planes'][0]
    assert Fraction(row['target_rotation_reserve_rational']) > Fraction('0.04')


@pytest.mark.parametrize('bad', [True, .1, None, 'nan', 'inf', '-1/10', '2', '1/0'])
def test_angles_require_explicit_rational_nonnegative_bounded_strings(bad):
    with pytest.raises(ValueError):
        screen([0, 0, 0], [0, 0, 0], [0, 0, 0], planes(), bad, '0')


@pytest.mark.parametrize('bad', [[0, 0], [0, True, 0], [0, float('nan'), 0], [0, 1j, 0]])
def test_invalid_coordinates_fail_without_partial_certificate(bad):
    with pytest.raises(ValueError):
        screen(bad, [0, 0, 0], [0, 0, 0], planes(), '0', '0')


def test_declared_planes_are_complete_nondegenerate_and_not_silently_omitted():
    for family in ([], planes() + [[[0, 0, 0]]*3], [planes()[0][:2]]):
        with pytest.raises(ValueError):
            screen([0, 0, 0], [0, 0, 0], [0, 0, 0], family, '0', '0')


def test_omitting_or_tampering_any_encoded_certificate_field_is_rejected():
    r = screen([.2, .2, .2], [0, 0, 0], [0, 0, 0], planes(), '1/10', '1/10')
    for field in ('scope', 'source_point_hex', 'planes', 'exact_rational_residual_bounds'):
        changed = copy.deepcopy(r); changed.pop(field)
        with pytest.raises(ValueError):
            verify(changed)
    changed = copy.deepcopy(r); changed['planes'][0]['plane_residual_upper_rational'] = '-100'
    with pytest.raises(ValueError):
        verify(changed)
    changed = copy.deepcopy(r); changed['broader_articulated_infeasibility_proven'] = True
    with pytest.raises(ValueError):
        verify(changed)


@pytest.mark.parametrize('bad', [True, 0, 257, 16.])
def test_invalid_root_enclosure_budget_fails(bad):
    with pytest.raises(ValueError):
        sqrt_upper(Fraction(2), bad)
