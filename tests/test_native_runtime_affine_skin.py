"""Nonunit weight algebra exposes errors hidden by identical world bones."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_runtime_affine_skin import AffineSkin,compare
from test_native_scene_engine import serialized


def fixture(total=.75):
    identity=np.eye(4)
    mesh=dict(node='mesh',positions=[[1.,2.,3.]],bones=[0,0,0,0],weights=[total,0.,0.,0.],
              binds=[dict(bone=0,pose=serialized(identity))])
    observed=dict(bone_names=['root'],meshes=[mesh])
    embedded=dict(time_s=0.,bones=[serialized(identity)],skeleton_world=serialized(identity),mesh_world={'mesh':serialized(identity)})
    moved=identity.copy();moved[:3,3]=[2.,-1.,.3]
    extracted=copy.deepcopy(embedded);extracted.update(skeleton_world=serialized(moved),mesh_world={'mesh':serialized(moved)})
    return observed,embedded,extracted,moved


@pytest.mark.parametrize('total',[.75,1.-5/65535])
def test_same_world_bones_different_actor_translation_exposes_raw_weight_deficit(total):
    observed,embedded,extracted,moved=fixture(total)
    before=copy.deepcopy(observed)
    skin=AffineSkin(observed)
    difference=skin.positions(extracted)-skin.positions(embedded)
    np.testing.assert_allclose(difference,(1-total)*moved[None,:3,3],atol=1e-15,rtol=0)
    result,arrays=compare(observed,observed,[embedded],[extracted],[extracted],[0.],1e-4)
    assert not result['passed'] and result['maximum_mode_affine_skin_difference_m']>1e-4
    assert observed==before and not result['weights_renormalized']
    assert all(v.dtype==np.dtype('<f8') for v in arrays.values())


def test_unit_weights_preserve_affine_translation_parity():
    observed,embedded,extracted,_=fixture(1.)
    result,_=compare(observed,observed,[embedded],[extracted],[extracted],[0.],1e-4)
    assert result['passed'] and result['maximum_mode_affine_skin_difference_m']<1e-14


def test_duplicate_surface_vertices_keep_independent_mesh_world_transforms():
    observed,embedded,_,_=fixture(1.)
    other=copy.deepcopy(observed['meshes'][0]);other['node']='other';observed['meshes'].append(other)
    transform=np.eye(4);transform[:3,3]=[4.,5.,6.]
    embedded['mesh_world']['other']=serialized(transform)
    positions=AffineSkin(observed).positions(embedded)
    assert positions.shape==(2,3)
    np.testing.assert_array_equal(positions[1]-positions[0],transform[:3,3])


@pytest.mark.parametrize('fault',['mesh-missing','mesh-extra','skeleton-singular','bone-missing','nan-transform'])
def test_incomplete_or_invalid_pose_graph_rejects(fault):
    observed,embedded,_,_=fixture()
    if fault=='mesh-missing':embedded['mesh_world'].clear()
    if fault=='mesh-extra':embedded['mesh_world']['other']=serialized(np.eye(4))
    if fault=='skeleton-singular':embedded['skeleton_world'][0]=[0.,0.,0.]
    if fault=='bone-missing':embedded['bones'].clear()
    if fault=='nan-transform':embedded['mesh_world']['mesh'][3][0]=np.nan
    with pytest.raises(ValueError):AffineSkin(observed).positions(embedded)


def test_reordered_or_changed_surface_data_cannot_hide_in_comparison():
    observed,embedded,_,_=fixture()
    changed=copy.deepcopy(observed);changed['meshes'][0]['weights'][0]+=.01
    with pytest.raises(ValueError,match='surface ordering/data'):
        compare(observed,changed,[embedded],[embedded],[],[0.],1e-4)
