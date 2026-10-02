"""Frame-key geometry bounds, not animation quality or actual human corrections."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_motion_edit import edit_native, LIMITS

NAMES=['Joint'+str(j) for j in range(77)]


def motion():
    local=np.tile(np.eye(3,dtype=np.float32),(31,77,1,1))
    local[:,4]=Rotation.from_euler('z',np.linspace(0,30,31),degrees=True).as_matrix()
    roots=np.zeros((31,3),np.float32);roots[:,0]=np.arange(31)/30
    return local,roots


def spec():
    return dict(joint='Joint4',rotation_vector_degrees=[15,0,0],root_offset_m=[0,.06,0],
                start_frame=5,peak_frame=15,end_frame=25)


def test_joint_local_rotation_world_root_and_exact_untouched_channels():
    local,roots=motion();a,b,report=edit_native(local,roots,local,roots,NAMES,spec())
    assert a.dtype==b.dtype==np.float32
    np.testing.assert_array_equal(a[:,np.arange(77)!=4],local[:,np.arange(77)!=4])
    for frame in list(range(6))+list(range(25,31)):
        np.testing.assert_array_equal(a[frame],local[frame]);np.testing.assert_array_equal(b[frame],roots[frame])
    expected=local[15,4]@Rotation.from_euler('x',15,degrees=True).as_matrix()
    np.testing.assert_allclose(a[15,4],expected,atol=3e-8)
    np.testing.assert_array_equal(b[15]-roots[15],np.array([0,.06,0],np.float32))
    assert report['changed_rotation_frame_keys']==report['changed_root_frame_keys']==19
    assert report['measured']['joint_from_original_degrees']==pytest.approx(15,abs=1e-5)
    assert all(report[k] is False for k in ('quality_approved','training_admitted','release_approved'))
    np.testing.assert_array_equal(local,motion()[0]);np.testing.assert_array_equal(roots,motion()[1])


def test_smoothstep_weights_and_independent_root_only_operation():
    local,roots=motion();value=spec();value['rotation_vector_degrees']=[0,0,0]
    a,b,_=edit_native(local,roots,local,roots,NAMES,value)
    np.testing.assert_array_equal(a,local)
    weight=.1*.1*(3-2*.1)
    assert b[6,1]==pytest.approx(.06*weight)
    assert b[24,1]==pytest.approx(b[6,1])


@pytest.mark.parametrize('fault',['missing','extra','unknown','start_bool','peak_fraction','order','outside',
                                  'nonfinite','vector_bool','vector_length','degrees_cap','root_cap','zero'])
def test_invalid_specs_rejected(fault):
    local,roots=motion();value=spec()
    if fault=='missing':del value['joint']
    if fault=='extra':value['quality_approved']=True
    if fault=='unknown':value['joint']='not_a_joint'
    if fault=='start_bool':value['start_frame']=False
    if fault=='peak_fraction':value['peak_frame']=15.5
    if fault=='order':value['peak_frame']=value['end_frame']
    if fault=='outside':value['end_frame']=31
    if fault=='nonfinite':value['root_offset_m'][0]=float('nan')
    if fault=='vector_bool':value['rotation_vector_degrees'][0]=True
    if fault=='vector_length':value['root_offset_m']=[0,0]
    if fault=='degrees_cap':value['rotation_vector_degrees']=[40,40,0]
    if fault=='root_cap':value['root_offset_m']=[.2,.2,0]
    if fault=='zero':value.update(rotation_vector_degrees=[0,0,0],root_offset_m=[0,0,0])
    with pytest.raises(ValueError):edit_native(local,roots,local,roots,NAMES,value)


@pytest.mark.parametrize('fault',['double','improper','nonfinite','frames','different_clock'])
def test_invalid_motion_rejected(fault):
    local,roots=motion();candidate=local.copy();r=roots.copy()
    if fault=='double':candidate=candidate.astype(float)
    if fault=='improper':candidate[0,0,0,0]=2
    if fault=='nonfinite':r[0,0]=np.inf
    if fault=='frames':local=local[:2];roots=roots[:2];candidate=candidate[:2];r=r[:2]
    if fault=='different_clock':candidate=candidate[:-1];r=r[:-1]
    with pytest.raises(ValueError):edit_native(local,roots,candidate,r,NAMES,spec())


@pytest.mark.parametrize('fault',['rotation','root','rotation_step','root_step','external_other_joint'])
def test_cumulative_original_relative_bounds_cannot_be_bypassed(fault):
    local,roots=motion();value=spec();candidate=local.copy();r=roots.copy()
    if fault=='rotation':
        candidate[:,4]=local[:,4]@Rotation.from_euler('x',40,degrees=True).as_matrix()
    if fault=='root':r[:,1]=.24
    if fault=='rotation_step':value.update(start_frame=14,peak_frame=15,end_frame=16)
    if fault=='root_step':value.update(rotation_vector_degrees=[0,0,0],start_frame=14,peak_frame=15,end_frame=16)
    if fault=='external_other_joint':candidate[:,20]=Rotation.from_euler('y',46,degrees=True).as_matrix()
    with pytest.raises(ValueError,match='Cumulative'):edit_native(local,roots,candidate,r,NAMES,value)


def test_repeated_operations_measured_against_original_not_last_candidate():
    local,roots=motion();value=spec();value.update(root_offset_m=[0,0,0])
    a,b,_=edit_native(local,roots,local,roots,NAMES,value)
    a,b,report=edit_native(local,roots,a,b,NAMES,value)
    assert report['measured']['joint_from_original_degrees']==pytest.approx(30,abs=1e-5)
    assert report['limits']==LIMITS
    value['rotation_vector_degrees']=[16,0,0]
    with pytest.raises(ValueError,match='Cumulative'):edit_native(local,roots,a,b,NAMES,value)
