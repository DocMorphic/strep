"""Analytical imported binding/clock/contact checks, without an engine or model."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_engine_contacts import (features, match_bindings, matrices, clocks, packed_weights,
    checked_clock, imported_bindings, imported_world, contact)


def gd_matrix():
    return [[1,0,0],[0,1,0],[0,0,1],[0,0,0]]


def test_matrix_columns_and_translation_not_transposed():
    value=gd_matrix(); value[3]=[2,3,4]
    found=matrices(value)
    assert np.array_equal(found[:3,3],[2,3,4])
    assert np.array_equal(found[:3,:3],np.eye(3))
    with pytest.raises(ValueError): matrices([[float('nan')]*3]*4)


def test_reordered_influences_and_vertices_match_by_binding():
    nodes=np.array([[0,1],[1,0]])
    weights=np.array([[.25,.75],[.6,.4]])
    points=np.array([[[0,1,2,1],[3,4,5,1]],[[2,3,4,1],[5,6,7,1]]],float)
    a=features(nodes,weights,points,2)
    b=features(nodes[::-1,::-1],weights[::-1,::-1],points[::-1,::-1],2)
    indices,error,count=match_bindings(a,b)
    assert indices.tolist()==[1,0] and error==0 and count==[1,1]
    expected=np.einsum('bij,vbj->vi',np.tile(np.eye(4)[None,:3,:],(2,1,1)),a)
    assert np.allclose(expected,np.sum(points[:,:,:3]*weights[:,:,None],axis=1))


def test_equivalent_split_influences_and_duplicate_vertices():
    a=features(np.array([[0,0]]),np.array([[.3,.7]]),np.array([[[1,2,3,1],[1,2,3,1]]]),1)
    b=np.concatenate([a,a])
    indices,error,count=match_bindings(a,b)
    assert indices.tolist()==[0] and error==0 and count==[2]


def test_quantized_identity_preserves_weight_deficit_for_engine_measurement():
    weights=np.array([[.3,.7]])
    packed=packed_weights(weights)
    assert packed.sum()<1 and np.max(np.abs(packed-weights))<1/65535
    points=np.array([[[1,2,3,1],[1,2,3,1]]]); nodes=np.array([[0,0]])
    bound=features(nodes,packed,points,1,quantized=True)
    assert bound[0,0,3]==packed.sum()
    assert bound[0,0,0]<1
    # Raw weights and packed weights are different functions; no silent
    # normalization is used to make the engine population look identical.
    original=features(nodes,weights,points,1)
    assert not np.array_equal(bound,original)


def test_large_weight_loss_not_excused_as_quantization():
    with pytest.raises(ValueError):
        features(np.array([[0,0]]),np.array([[.5,0.]]),np.ones((1,2,4)),1,quantized=True)


def test_coarse_bind_centroid_collision_does_not_hide_wrong_bone():
    a=np.zeros((1,2,4)); a[0,0]=[1,2,3,1]
    b=np.zeros_like(a); b[0,1]=a[0,0]
    with pytest.raises(ValueError,match='binding changed'): match_bindings(a,b)


@pytest.mark.parametrize('fault',['weight','nan','bone','shape'])
def test_invalid_skin_populations_rejected(fault):
    nodes=np.array([[0,0]]); weights=np.array([[1.,0.]]); points=np.ones((1,2,4))
    if fault=='weight': weights[0,0]=.5
    if fault=='nan': points[0,0,0]=np.nan
    if fault=='bone': nodes[0,1]=1
    if fault=='shape': points=points[:,:,:3]
    with pytest.raises(ValueError): features(nodes,weights,points,1)


def test_native_and_regular_populations_kept_separate():
    row=dict(stance_s=[.5,.75],clock=np.array([.5,.50000001,.65,.75]))
    result=clocks(row)
    assert .50000001 in result['native_keys'] and .50000001 not in result['stance_120hz']
    assert len(result['stance_120hz'])==31
    assert result['native_keys'].tolist()==[.5,.50000001,.65,.75]


@pytest.mark.parametrize('times',[[0,0],[1,0],[0,np.nan],[-1,0],[0,2]])
def test_invalid_sample_clocks_rejected(times):
    with pytest.raises(ValueError): checked_clock(times,1)


def observed():
    return dict(bone_names=['root'],meshes=[dict(node='mesh',surface=0,
        positions=[[1,2,3]],weights=[1,0,0,0],bones=[0,0,0,0],
        binds=[dict(bone=0,pose=gd_matrix())])],frames=[dict(
        requested_time_s=0.,actual_time_s=0.,bones=[gd_matrix()],
        skeleton_world=gd_matrix(),mesh_world=[dict(node='mesh',matrix=gd_matrix())])])


def test_imported_bind_mapping_and_world_matrices():
    data=observed(); bound,refs,order=imported_bindings(data,['root'])
    assert bound.shape==(1,1,4) and refs==[['mesh',0,0]] and order.tolist()==[0]
    world=imported_world(data,[0],order)
    assert np.array_equal(world[0,0],np.eye(4))
    assert np.allclose(np.einsum('tbij,vbj->tvi',world[:,:,:3,:],bound),[[[1,2,3]]])


@pytest.mark.parametrize('fault',['names','weights','bind','time','nan_time','mesh_space','mesh_missing','frame_missing'])
def test_unsupported_or_incomplete_import_rejected(fault):
    data=observed()
    if fault=='names': data['bone_names']=['root','root']
    if fault=='weights': data['meshes'][0]['weights'][0]=.5
    if fault=='bind': data['meshes'][0]['binds'][0]['bone']=5
    if fault=='time': data['frames'][0]['actual_time_s']=.1
    if fault=='nan_time': data['frames'][0]['actual_time_s']=float('nan')
    if fault=='mesh_space': data['frames'][0]['mesh_world'][0]['matrix'][3][0]=.01
    if fault=='mesh_missing': data['frames'][0]['mesh_world']=[]
    if fault=='frame_missing': data['frames']=[]
    with pytest.raises(ValueError):
        _,_,order=imported_bindings(data,['root']); imported_world(data,[0],order)


def test_original_anchor_does_not_reset_to_candidate_start():
    row=dict(up=np.array([0.,1.,0.]),offset=0.,clearance=.00025,maximum_height=.005)
    points=np.array([[[.002,.001,0]],[[.002,.001,0]]])
    result=contact(points,np.array([[0,.001,0]]),row,[0,1],[0],dict(anchor=.001,speed=.005))
    assert result['maximum_patch_anchor_error_m']==.002
    assert result['maximum_patch_vertex_tangential_drift_m']==0
    assert not result['contact_limits_pass']


def test_contact_speed_strict_overlimit_remains_failure():
    row=dict(up=np.array([0.,1.,0.]),offset=0.,clearance=.00025,maximum_height=.005)
    points=np.array([[[0,.001,0]],[[.00050000001,.001,0]]])
    result=contact(points,points[0],row,[0,.1],[0],dict(anchor=.001,speed=.005))
    assert result['maximum_patch_vertex_tangential_speed_m_s']>.005
    assert not result['contact_limits_pass']


def test_tiny_endpoint_interval_retains_failure_and_explains_amplification():
    row=dict(up=np.array([0.,1.,0.]),offset=0.,clearance=.00025,maximum_height=.005)
    points=np.array([[[0,.001,0]],[[0,.001,0]],[[2e-8,.001,0]]])
    times=[0,1,1+1e-7]
    result=contact(points,points[0],row,times,[0],dict(anchor=.001,speed=.005))
    assert result['maximum_patch_vertex_tangential_speed_m_s']==pytest.approx(.2)
    assert result['minimum_velocity_interval_s']==pytest.approx(1e-7)
    assert result['peak_speed_pair']['times_s']==times[1:]
    assert result['peak_speed_pair']['tangential_distance_m']==pytest.approx(2e-8)
    assert not result['contact_limits_pass']
