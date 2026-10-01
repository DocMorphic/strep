import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from palm_contact_region import region, candidates, rebind_surface_point


def cube():
    import trimesh
    mesh = trimesh.creation.box(extents=[.04, .04, .04])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def test_disconnected_nearby_surface_does_not_enter_region():
    p = np.array([[0., 0, 0], [.01, 0, 0], [0, .01, 0], [0, 0, .0001], [.01, 0, .0001], [0, .01, .0001]])
    ids, distance, _ = region(p, np.array([[0, 1, 2], [3, 4, 5]]), 0, .02)
    assert ids.tolist() == [0, 1, 2] and np.isinf(distance[3:]).all()


def test_surface_path_radius_excludes_euclidean_shortcut():
    # Opposite corners across a missing diagonal require two boundary edges.
    p = np.array([[0., 0, 0], [.01, 0, 0], [0, .01, 0], [.01, .01, 0]])
    ids, d, _ = region(p, np.array([[0, 1, 2], [1, 3, 2]]), 0, .015)
    assert 3 not in ids and np.isinf(d[3])
    ids, d, _ = region(p, np.array([[0, 1, 2], [1, 3, 2]]), 0, .021)
    assert 3 in ids and d[3] == pytest.approx(.02)


def test_front_facing_cone_excludes_back_side():
    p, f = cube(); ids, _, n = region(p, f, 0, .2, facing_degrees=30.)
    assert np.all(n[ids]@n[0] >= np.cos(np.deg2rad(30.))-1e-12)
    assert len(ids) < len(p)


def test_candidates_stay_in_region_and_support_whole_surface():
    p, f = cube(); result = candidates(p, f, 0, .2, normal_tolerance_degrees=80.)
    assert result['candidates']
    for row in result['candidates']:
        assert row['vertex'] in result['region_vertices']
        assert np.max((p-p[row['vertex']])@row['support_normal']) <= 1e-8
        assert row['normal_error_degrees'] <= 80.
    assert not result['quality_approved'] and result['new_authored_condition']


def test_support_choice_is_rigid_transform_invariant():
    from scipy.spatial.transform import Rotation
    p, f = cube(); r = Rotation.from_rotvec([.3, -.2, .4]).as_matrix()
    a = candidates(p, f, 0, .2, normal_tolerance_degrees=80.)
    b = candidates(p@r.T+[2, 3, 4], f, 0, .2, normal_tolerance_degrees=80.)
    assert set(a['region_vertices']) == set(b['region_vertices'])
    assert {v['vertex'] for v in a['candidates']} == {v['vertex'] for v in b['candidates']}


def test_invalid_region_inputs_fail_closed():
    p, f = cube()
    for radius in (0, -1, float('nan')):
        with pytest.raises(ValueError): region(p, f, 0, radius)
    with pytest.raises(ValueError): region(p, f, 99, .04)
    with pytest.raises(ValueError): region(p, np.array([[0, 0, 1]]), 0, .04)
    with pytest.raises(ValueError): candidates(p, f, 0, .04, normal_tolerance_degrees=90.)


def test_rebinding_discards_stale_point_geometry_without_mutating_source():
    source = dict(joint='LeftHand', space='actor', actor='B', surface_vertex=4,
        offset_m=[1, 2, 3], palm_normal_local=[0, 0, 1], center_local_m=[2, 3, 4])
    changed = rebind_surface_point(source, 7)
    assert changed['surface_vertex'] == 7 and changed['actor'] == 'B' and changed['joint'] == 'LeftHand'
    assert changed['status'] == 'anatomical_review_pending'
    assert not {'offset_m', 'palm_normal_local', 'center_local_m'}.intersection(changed)
    assert source['surface_vertex'] == 4 and source['offset_m'] == [1, 2, 3]
    for bad in (-1, True, 2.5):
        with pytest.raises(ValueError): rebind_surface_point(source, bad)
