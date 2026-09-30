import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_temporal_neighbor import bounded_neighbor
from paired_temporal_neighbor import BODY,smooth_export,rotation_channels
from gltf_tools import append_accessor,write_glb,read_glb,accessor


def test_small_neighbor_spike_reduced_with_full_norm_cap():
    identity=np.eye(3);middle=Rotation.from_rotvec([.2,.1,.3]).as_matrix()
    result=bounded_neighbor(identity,middle,identity,1.,.04)
    delta=(Rotation.from_matrix(middle).inv()*Rotation.from_matrix(result)).magnitude()
    assert delta==pytest.approx(.04)
    assert Rotation.from_matrix(result).magnitude()<Rotation.from_matrix(middle).magnitude()


def test_constant_rotation_rate_across_wrap_is_unchanged():
    rotations=Rotation.from_euler('z',[170,179,188],degrees=True).as_matrix()
    np.testing.assert_allclose(bounded_neighbor(*rotations,.25,.1),rotations[1],atol=1e-14)


def test_zero_weight_preserves_rotation_and_invalid_budget_rejected():
    r=Rotation.from_rotvec([.1,.2,-.3]).as_matrix()
    np.testing.assert_allclose(bounded_neighbor(np.eye(3),r,np.eye(3),0,.1),r,atol=1e-14)
    with pytest.raises(ValueError):bounded_neighbor(r,r,r,.2,-1.)


@pytest.mark.parametrize('include_fingers',[False,True])
def test_export_keeps_contact_and_unselected_channels_exact(tmp_path,include_fingers):
    names=BODY+[f'LeftHandTest{i}' for i in range(19)]+['RightArm']
    animation=dict(channels=[],samplers=[])
    doc=dict(asset=dict(version='2.0'),nodes=[dict(name=n) for n in names],
             animations=[animation],accessors=[],bufferViews=[],buffers=[dict(byteLength=0)])
    binary=bytearray();clock=append_accessor(doc,binary,np.arange(150,dtype=np.float32)/30,'SCALAR')
    angles=np.zeros(150);angles[74]=.2;angles[75]=.1
    quaternions=Rotation.from_euler('z',angles).as_quat()
    for node in range(len(names)):
        output=append_accessor(doc,binary,quaternions,'VEC4')
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path='rotation')))
        animation['samplers'].append(dict(input=clock,output=output,interpolation='LINEAR'))
    translations=append_accessor(doc,binary,np.arange(450).reshape(150,3)/100,'VEC3')
    animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=0,path='translation')))
    animation['samplers'].append(dict(input=clock,output=translations,interpolation='LINEAR'))
    source,target=tmp_path/'source.glb',tmp_path/'target.glb'
    write_glb(source,doc,binary);before,raw=read_glb(source)
    record=smooth_export(source,target,include_fingers)
    after,payload=read_glb(target);a,b=rotation_channels(before,raw),rotation_channels(after,payload)
    locked=np.setdiff1d(np.arange(150),record['frames'])
    assert len(locked)==142 and 75 in locked
    for node,name in enumerate(names):
        if name in record['selected_joints']:
            np.testing.assert_array_equal(a[node][2][locked],b[node][2][locked])
            assert not np.array_equal(a[node][2][74],b[node][2][74])
        else:np.testing.assert_array_equal(a[node][2],b[node][2])
    np.testing.assert_array_equal(accessor(before,raw,translations),accessor(after,payload,translations))
    assert before['nodes']==after['nodes']
