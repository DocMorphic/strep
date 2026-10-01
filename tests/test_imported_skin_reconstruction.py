import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from imported_skin_reconstruction import ImportedSkin
from test_imported_skin_evidence import fixture


def test_original_vertex_order_bind_offsets_and_observed_bone_mapping():
    skin = ImportedSkin(*fixture())
    bones = np.zeros((2,4,3)); bones[:,:3] = np.eye(3); bones[0,3,0] = .5
    points = skin.vertices(bones,['B','A'])
    np.testing.assert_allclose(points,[[0,0,0],[.75,0,0],[1.45,0,0]],atol=1e-15)
    # Serialized engine basis is column-major, not row-major.
    rotation = np.array([[0.,-1,0],[1,0,0],[0,0,1]])
    bones[0,:3] = rotation.T
    np.testing.assert_allclose(skin.vertices(bones,['B','A']),[[0,0,0],[.5,.25,0],[.7,.75,0]],atol=1e-15)


def test_raw_imported_weight_sum_is_preserved_not_renormalized():
    args = list(fixture()); args[-1]['weights'][0] -= 1e-5
    skin = ImportedSkin(*args)
    bones = np.zeros((2,4,3)); bones[:,:3] = np.eye(3); bones[0,3,0] = .5
    assert skin.weights[1].sum() == 1-1e-5
    assert skin.vertices(bones,['B','A'])[1,0] == .75*(1-1e-5)


def test_unmatched_or_invalid_bone_evidence_cannot_be_reconstructed():
    args = list(fixture()); args[-1]['binds'][0]['pose'][3][0] += .05
    with pytest.raises(ValueError,match='Passing'): ImportedSkin(*args)
    skin = ImportedSkin(*fixture()); bones = np.zeros((2,4,3))
    with pytest.raises(ValueError,match='Complete'): skin.vertices(bones,['B','B'])
    bones[0,0,0] = np.nan
    with pytest.raises(ValueError,match='Complete'): skin.vertices(bones,['B','A'])
