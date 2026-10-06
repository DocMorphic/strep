"""Independent analytic cases for strict interior witness, never clearance."""
import copy
from fractions import Fraction
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from exact_triangle_crossing_witness import witness, verify

A = [[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]]
B = [[.5, .2, -1.], [.5, .2, 1.], [.5, 1.2, 0.]]


def test_exact_witness_is_strictly_in_both_planes_and_interiors():
    result = witness(A, B)
    assert result['strict_interior_crossing_proved'] is True
    assert [Fraction(x) for x in result['witness_world_rational']] == [Fraction(1,2), (Fraction(.2)+Fraction(1.2))/2, Fraction(0)]
    assert result['plane_residuals_rational'] == ['0', '0']
    for weights in result['barycentric_rational']:
        rational = [Fraction(x) for x in weights]
        assert sum(rational) == 1 and min(rational) > 0
    assert verify(result) == result and not result['whole_scene_certified']


@pytest.mark.parametrize('scale,offset',[(1., 0.), (.000000000001, 0.), (1024., 2**40)])
@pytest.mark.parametrize('reverse', [False, True])
def test_winding_swap_and_representable_scale_translation(scale, offset, reverse):
    a, b = [[[x*scale+offset for x in row] for row in t] for t in (A, B)]
    if reverse: a, b = b[::-1], a[::-1]
    result = witness(a, b)
    assert result['kind'] == 'proper_crossing'
    assert verify(result) == result and not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('b,kind',[
    ([[.5,.2,0.],[.5,.2,1.],[.5,1.2,0.]],'no_strict_straddle'),
    ([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]],'parallel_or_coplanar'),
    ([[0.,0.,1.],[1.,0.,1.],[0.,1.,1.]],'parallel_or_coplanar'),
    ([[3.,.2,-1.],[3.,.2,1.],[3.,1.2,0.]],'no_strict_straddle'),
    ([[.5,3.,-1.],[.5,3.,1.],[.5,4.,0.]],'no_positive_interval'),
    ([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]],'degenerate'),
])
def test_boundary_coplanar_disjoint_and_degenerate_are_never_clearance(b,kind):
    result = witness(A, b)
    assert result['kind'] == kind and not result['strict_interior_crossing_proved']
    assert 'witness_world_rational' not in result and not result['whole_scene_certified']
    assert verify(result) == result


@pytest.mark.parametrize('fault',['coordinate','witness','barycentric','approval','boolean-alias'])
def test_altered_serialized_certificate_rejects(fault):
    result = copy.deepcopy(witness(A, B))
    if fault == 'coordinate': result['input_binary_float_hex'][0][0][0] = '0x1p+4'
    elif fault == 'witness': result['witness_world_rational'][0] = '0'
    elif fault == 'barycentric': result['barycentric_rational'][0][0] = '0'
    elif fault == 'approval': result['quality_approved'] = True
    else: result['strict_interior_crossing_proved'] = 1
    with pytest.raises(ValueError): verify(result)


@pytest.mark.parametrize('value',[None, [], [[0.,0.,0.]]*2, [[True,0.,0.]]*3, [[float('nan'),0.,0.]]*3, [['0',0.,0.]]*3])
def test_malformed_or_nonfinite_input_rejects(value):
    with pytest.raises(ValueError): witness(value, B)
