"""Exact chain-bound regressions, not motion or physical-quality evidence."""
from fractions import Fraction
import math
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rigid_chain_reach import diagnose, upper_length, GRID


def test_exact_boundary_and_next_float_outside():
    links = [[1,0,0], [2,0,0]]
    assert not diagnose([0,0,0], [3,0,0], links, 0)['outer_reach_excluded']
    assert diagnose([0,0,0], [math.nextafter(3, math.inf),0,0], links, 0)['outer_reach_excluded']
    assert not diagnose([0,0,0], [3.5,0,0], links, .5)['outer_reach_excluded']
    assert diagnose([0,0,0], [math.nextafter(3.5, math.inf),0,0], links, .5)['outer_reach_excluded']


def test_diagonal_lengths_are_rounded_outward_without_false_exclusion():
    result = diagnose([0,0,0], [2,2,0], [[1,1,0], [1,1,0]], 0)
    assert not result['outer_reach_excluded']
    assert diagnose([0,0,0], [3,3,0], [[1,1,0], [1,1,0]], 0)['outer_reach_excluded']
    for length in result['link_upper_lengths_m']:
        upper = Fraction(int(length['numerator']), int(length['denominator']))
        assert upper*upper >= 2
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']


@pytest.mark.parametrize('q', [Fraction(0), Fraction(2), Fraction(10**12),
                             Fraction.from_float(1e-300), Fraction(1,7), Fraction(9)])
def test_exact_square_root_upper_bound(q):
    upper = upper_length(q)
    assert upper*upper >= q
    if upper:
        assert (upper-Fraction(1,GRID))**2 < q


def test_fixed_anchor_translation_and_zero_length_links():
    assert not diagnose([5,6,7], [5,6,7], [[0,0,0]], 0)['outer_reach_excluded']
    assert diagnose([5,6,7], [6,6,7], [[0,0,0]], 0)['outer_reach_excluded']
    assert not diagnose([5,6,7], [5,6,7], [[100,0,0]], 0)['outer_reach_excluded']


@pytest.mark.parametrize('anchor,target,links,tolerance', [
    ([True,0,0], [0,0,0], [[1,0,0]], 0),
    ([0,0,0], [math.nan,0,0], [[1,0,0]], 0),
    ([0,0,0], [0,0,0], [[math.inf,0,0]], 0),
    ([0,0], [0,0,0], [[1,0,0]], 0),
    ([0,0,0], [1e7,0,0], [[1,0,0]], 0),
    ([0,0,0], [0,0,0], [], 0),
    ([0,0,0], [0,0,0], [[1,0,0]]*65, 0),
    ([0,0,0], [0,0,0], [[1,0,0]], True),
    ([0,0,0], [0,0,0], [[1,0,0]], -1),
    ([0,0,0], [0,0,0], [[1,0,0]], 2),
    ([0,0,0], [0,0,0], [[1,0,0]], math.nan)])
def test_reject_undeclared_or_invalid_geometry(anchor,target,links,tolerance):
    with pytest.raises(ValueError):
        diagnose(anchor,target,links,tolerance)


def test_certificate_keeps_its_original_inputs():
    anchor=[0,0,0];target=[3,0,0];links=[[1,0,0]]
    result=diagnose(anchor,target,links,0)
    anchor[0]=100;target[0]=0;links[0][0]=100
    assert result['anchor_world_m']==[0,0,0] and result['target_world_m']==[3,0,0]
    assert result['link_offsets_local_m']==[[1,0,0]] and result['outer_reach_excluded']
