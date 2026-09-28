import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_response_study import angle, descriptors, direction_screen


def fixture():
    names=['Hips','Neck1','RightArm','RightForeArm','RightLeg','RightShin','RightFoot','LeftLeg','LeftShin','LeftFoot']
    xyz=[[0,1,0],[0,2,0],[.2,1.8,0],[.2,1.4,0],[.1,1,0],[.1,.5,0],[.1,0,0],[-.1,1,0],[-.1,.5,0],[-.1,0,0]]
    p=np.broadcast_to(np.asarray(xyz),(121,10,3)).copy()
    theta=np.linspace(0,np.pi/3,len(p))
    p[:,3]=p[:,2]+np.column_stack([.4*np.sin(theta),-.4*np.cos(theta),np.zeros(len(p))])
    return p,names


def test_measured_shoulder_excursion_known_and_stationary_knees():
    p,names=fixture();r=descriptors(p,names)
    assert r['wave']==pytest.approx(54)
    assert r['squat']==pytest.approx(0)
    assert r['kick']==pytest.approx(0)


def test_descriptor_uses_real_soma_joint_names():
    from inspect_motion import skeleton_metadata
    actual=skeleton_metadata(77)[0]
    p,names=fixture()
    assert set(names)<=set(actual)
    full=np.zeros((len(p),len(actual),3))
    for i,name in enumerate(names):full[:,actual.index(name)]=p[:,i]
    assert descriptors(full,actual)==descriptors(p,names)


def test_descriptors_ignore_global_rotation_translation_and_uniform_scale():
    p,names=fixture();expected=descriptors(p,names)
    moved=3*p@Rotation.from_rotvec([.2,-.8,.4]).as_matrix().T+[30,-7,4]
    assert descriptors(moved,names)==pytest.approx(expected,abs=1e-5)


def test_degenerate_and_nonfinite_measurements_fail_instead_of_zero_score():
    with pytest.raises(ValueError):angle([[0,0,0]],[[0,1,0]])
    p,names=fixture();p[0,0,0]=np.nan
    with pytest.raises(ValueError):descriptors(p,names)


def rows():
    return [dict(condition=c,seed=s,primary_excursion_degrees=v) for c,v in [('plain',100),('low',10),('middle',20),('high',30)] for s in [1,2,3]]


def test_ordered_numeric_response_never_grants_semantic_approval():
    r=direction_screen(rows())
    assert r['numerical_direction_screen_pass']
    assert r['medians_degrees']['plain']==100
    assert not r['semantic_review_complete'] and not r['style_response_validated']


def test_margin_equality_and_missing_pairs_rejected():
    data=rows()
    for r in data:
        if r['condition']=='middle':r['primary_excursion_degrees']=12
        if r['condition']=='high':r['primary_excursion_degrees']=15
    assert not direction_screen(data)['numerical_direction_screen_pass']
    with pytest.raises(ValueError):direction_screen(data[:-1])
    with pytest.raises(ValueError):direction_screen(data+[data[0]])


def test_median_order_alone_is_insufficient():
    data=rows()
    for r in data:
        if r['condition']=='middle':r['primary_excursion_degrees']=11
        if r['condition']=='high':r['primary_excursion_degrees']=12 if r['seed']<3 else 30
    result=direction_screen(data)
    assert result['median_order_pass'] and not result['numerical_direction_screen_pass']
