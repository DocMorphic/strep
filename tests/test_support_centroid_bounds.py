"""Necessary geometry bounds, including attainable relaxed-bound witnesses."""
import copy
import math
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from support_centroid_bounds import bound


def evaluate(points, **changes):
    args=dict(target=[0.,0.,0.], normal=[0.,1.,0.], plane_offset=0., clearance=.001,
        horizontal_tolerance=.003, maximum_displacement=.03)
    args.update(changes)
    return bound(points, **args)


def test_combined_vertical_and_horizontal_need_exceeds_budget_when_each_alone_does_not():
    report=evaluate([[.027,-.023,0.]])
    assert report['required_tangent_m']==pytest.approx(.024)
    assert report['required_normal_m']==pytest.approx(.024)
    assert report['minimum_required_vertex_max_displacement_m']==pytest.approx(math.hypot(.024,.024))
    assert report['status']=='incompatible_support_target'
    assert not report['feasibility_proven'] and not report['quality_approved']


def test_equal_height_population_attains_the_relaxed_bound_by_translation():
    points=[[.04,-.009,-.01],[.04,-.009,.01]]; report=evaluate(points)
    shift=[-.037,.01,0.]; changed=[[x+d for x,d in zip(p,shift)] for p in points]
    assert math.hypot(*shift)==pytest.approx(report['centroid_displacement_lower_bound_m'])
    assert evaluate(changed)['minimum_required_vertex_max_displacement_m']==pytest.approx(0.)


def test_individual_clearance_cannot_be_hidden_by_a_safe_centroid():
    report=evaluate([[0.,-.1,0.],[0.,.1,0.]])
    assert report['centroid_displacement_lower_bound_m']==pytest.approx(.001)
    assert report['individual_clearance_lower_bound_m']==pytest.approx(.101)
    assert report['status']=='incompatible_support_target'


def test_rotation_translation_and_target_normal_component_invariance():
    points=[[.04,-.009,-.01],[.04,-.009,.01]]
    original=evaluate(points)
    # Rotate x/y by 90 degrees and translate by (2,3,4).
    transformed=[[-p[1]+2,p[0]+3,p[2]+4] for p in points]
    report=evaluate(transformed,target=[-8,3,4],normal=[-1.,0.,0.],plane_offset=-2.)
    assert report['minimum_required_vertex_max_displacement_m']==pytest.approx(original['minimum_required_vertex_max_displacement_m'])
    assert report['status']==original['status']


def test_equality_and_roundoff_reserve_do_not_claim_a_conflict_or_feasibility():
    for x in [.033,.033+1e-10]:
        report=evaluate([[x,.001,0.]])
        assert report['status']=='not_ruled_out' and not report['feasibility_proven']
    assert evaluate([[.033+1e-7,.001,0.]])['status']=='incompatible_support_target'


def test_zero_radius_zero_movement_and_immutable_population():
    points=[[0.,.001,0.]]; before=copy.deepcopy(points)
    assert evaluate(points,horizontal_tolerance=0.,maximum_displacement=0.)['status']=='not_ruled_out'
    assert points==before
    assert evaluate(points,target=[.01,0.,0.],horizontal_tolerance=0.,maximum_displacement=0.)['status']=='incompatible_support_target'


@pytest.mark.parametrize('changes', [dict(normal=[0.,2.,0.]),dict(normal=[0.,0.,0.]),dict(clearance=-1.),
    dict(horizontal_tolerance=True),dict(maximum_displacement=float('nan')),dict(target=[float('inf'),0,0]),
    dict(plane_offset='0'),dict(normal=[0,1]),dict(maximum_displacement=-.01)])
def test_invalid_geometry_rejected(changes):
    with pytest.raises(ValueError):evaluate([[0.,0.,0.]],**changes)


@pytest.mark.parametrize('points',[[],[[True,0,0]],[[0,0]],[[1001,0,0]],[[0,float('nan'),0]]])
def test_invalid_or_incomplete_population_rejected(points):
    with pytest.raises(ValueError):evaluate(points)
