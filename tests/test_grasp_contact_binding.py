import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from grasp_contact_binding import apply_contact_binding, apply_region_binding


def fixture():
    return SimpleNamespace(names=['LeftHand', 'LeftHandIndex1', 'RightHand'], parents=[-1, 0, -1],
        skin=dict(lbs_indices=np.array([[0], [1], [1], [2], [2], [2]]), lbs_weights=np.ones((6, 1)), faces=np.array([[0, 1, 2], [3, 4, 5]])),
        contacts=[dict(region='LeftHand', vertex=0, target=[1, 2, 3]), dict(region='RightHand', vertex=3, target=[4, 5, 6])],
        normals=[('left-grip', np.array([[0, 1, 2]]), np.array([0, 0, 1])), ('right-grip', np.array([[3, 4, 5]]), np.array([0, 0, -1]))],
        recipe={'original_vertex': 0}, config={'point_tolerance_m': .005}, cache='old')


def test_binding_changes_only_selected_surface_and_normal_neighborhood():
    p = fixture(); target = p.contacts[0]['target']; other = p.contacts[1]; normal = p.normals[0][2]
    record = apply_contact_binding(p, 'LeftHand', 1)
    assert p.contacts[0]['vertex'] == 1 and p.contacts[0]['target'] is target and p.contacts[1] is other
    assert p.normals[0][2] is normal and p.recipe == {'original_vertex': 0} and p.config == {'point_tolerance_m': .005}
    assert record['original_vertex'] == 0 and not record['anatomical_approval'] and p.cache is None


@pytest.mark.parametrize('vertex', [True, -1, 6, 3])
def test_bad_or_other_hand_binding_is_rejected_without_mutation(vertex):
    p = fixture()
    with pytest.raises(ValueError): apply_contact_binding(p, 'LeftHand', vertex)
    assert p.contacts[0]['vertex'] == 0 and p.cache == 'old'


def test_region_normal_uses_only_declared_triangles_and_validates_membership():
    p = fixture(); patch = dict(hand='LeftHand', face_ids=[0], vertices=[0, 1, 2])
    record = apply_region_binding(p, 'LeftHand', 2, patch)
    assert p.contacts[0]['vertex'] == 2 and record['face_ids'] == [0] and not record['anatomical_approval']
    np.testing.assert_array_equal(p.normals[0][1], [[0, 1, 2]])
    with pytest.raises(ValueError): apply_region_binding(p, 'LeftHand', 3, patch)
    with pytest.raises(ValueError): apply_region_binding(p, 'LeftHand', 1, dict(patch, vertices=[1, 2]))
