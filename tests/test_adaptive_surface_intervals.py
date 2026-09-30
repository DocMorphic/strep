import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from adaptive_surface_intervals import audit


def actor(mesh, position=lambda t: np.zeros(3), speed=lambda a, b: 0.):
    def vertices(t): return mesh.vertices+position(t)
    def interval(a, b):
        return dict(start_s=a, end_s=b, center_s=(a+b)/2, center_vertices=vertices((a+b)/2),
                    radius_m=np.full(len(mesh.vertices), speed(a, b)*(b-a)/2+1e-10))
    return dict(vertices=vertices, interval=interval, faces=mesh.faces)


def pulse_pair():
    left = actor(trimesh.creation.box(extents=[4, .5, .5]))
    def position(t): return np.array([3-12*t if t <= .25 else (12*(t-.25) if t < .5 else 3), 0., 0.])
    right = actor(trimesh.creation.box(extents=[.5, 4, 1]), position, lambda a, b: 12. if a < .5 else 0.)
    return left, right


def test_subdivision_finds_crossing_missed_by_start_middle_and_end():
    result = audit(*pulse_pair(), 0., 1., max_depth=3)
    assert result['nodes'][0]['outcome'] == 'subdivided'
    assert result['outcome'] == 'intersection_observed'
    crossing = next(row for row in result['poses'] if row['outcome'] == 'crossing_observed')
    assert crossing['time_s'] == .25
    assert crossing['crossing_witness']['kind'] == 'proper_crossing'
    assert result['leaf_counts'] == {'crossing_observed': 1, 'surface_separation_bound': 1}
    assert not result['entire_partition_has_surface_bounds']
    assert not result['collision_free_certified']


def test_containment_is_detected_even_with_no_swept_surface_candidates():
    left, right = [actor(trimesh.creation.box(extents=[s, s, s])) for s in [.5, 2.]]
    result = audit(left, right, 0., 1.)
    assert result['nodes'][0]['candidate_pairs'] == 0
    assert result['leaf_counts'] == {'interior_vertex_observed': 1}
    assert result['poses'][0]['containment'][0]['max_depth_m'] > .5


def test_surface_separation_retains_explicit_containment_observation():
    mesh = trimesh.creation.box()
    result = audit(actor(mesh), actor(mesh, lambda t: np.array([3., 0, 0])), 0., 1.)
    assert result['outcome'] == 'surface_separation_bound'
    assert result['entire_partition_has_surface_bounds']
    assert result['poses'][0]['outcome'] == 'no_intersection_observed'
    assert all(row['max_depth_m'] == 0 for row in result['poses'][0]['containment'])


def test_touching_coplanar_contact_stays_unresolved_at_depth_budget():
    mesh = trimesh.creation.box()
    result = audit(actor(mesh), actor(mesh, lambda t: np.array([1., 0, 0])), 0., 1., max_depth=1)
    assert result['outcome'] == 'unresolved'
    assert result['leaf_counts'] == {'unresolved': 2}
    assert all(row['reason'] == 'depth_budget' for row in result['leaves'])


def test_interval_budget_preserves_unvisited_children_in_partition():
    result = audit(*pulse_pair(), 0., 1., max_intervals=1)
    assert result['evaluated_intervals'] == 1
    assert [(row['start_s'], row['end_s']) for row in result['leaves']] == [(0., .5), (.5, 1.)]
    assert all(row['reason'] == 'interval_budget' for row in result['leaves'])
    assert result['outcome'] == 'unresolved'


def test_bound_center_must_match_actual_placed_mesh():
    left, right = pulse_pair(); original = right['interval']
    def bad(a, b):
        value = original(a, b); value['center_vertices'] = value['center_vertices']+[0, 0, 1]
        return value
    right['interval'] = bad
    with pytest.raises(ValueError, match='center'): audit(left, right, 0., 1.)


def test_open_mesh_is_not_used_for_containment():
    left, right = pulse_pair(); right['faces'] = right['faces'][:-1]
    with pytest.raises(ValueError, match='Closed'): audit(left, right, 0., 1.)


@pytest.mark.parametrize('options', [dict(max_depth=-1), dict(max_depth=True), dict(max_intervals=0),
                                    dict(max_intervals=4096), dict(tolerance_m=0)])
def test_invalid_budgets_rejected(options):
    with pytest.raises(ValueError): audit(*pulse_pair(), 0., 1., **options)
