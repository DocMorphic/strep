import numpy as np
import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scipy.spatial.transform import Rotation
from audit_scene_timing import rates,support_edge,summary


def test_world_joint_rates_scale_with_time_without_losing_individual_joints():
    t=np.arange(9)/120
    m=np.broadcast_to(np.eye(4),(9,2,4,4)).copy()
    m[:,0,0,3]=3*t*t
    m[:,1,0,3]=t
    m[:,1,:3,:3]=Rotation.from_rotvec(np.c_[t*0,t*2,t*0]).as_matrix()
    a=rates(m,1/120,['root','hand']);b=rates(m,1/60,['root','hand'])
    assert a[0]['peak_acceleration_m_s2']==pytest.approx(6)
    assert a[1]['peak_angular_speed_rad_s']==pytest.approx(2)
    for j,k in zip(a,b):
        assert k['peak_speed_m_s']==pytest.approx(j['peak_speed_m_s']/2)
        assert k['peak_acceleration_m_s2']==pytest.approx(j['peak_acceleration_m_s2']/4)
        assert k['peak_angular_speed_rad_s']==pytest.approx(j['peak_angular_speed_rad_s']/2)


def test_support_uses_same_material_vertex_despite_lowest_point_switch():
    a=np.array([[0,0,0],[1,.01,0.]])
    b=np.array([[.001,.01,0],[1.001,0,0.]])
    row=support_edge([a,a],[b,b],{'foot':np.array([0,1])},[.01,.005])[0]
    assert row['vertex']==0
    assert row['source_slide_m_s']==pytest.approx(.1)
    assert row['candidate_slide_m_s']==pytest.approx(.2)


def test_airborne_penetrating_and_fast_patches_are_not_ground_hypotheses():
    for height,speed in [(.1,0),(-.1,0),(0,.4)]:
        a=np.array([[0,height,0.]])
        b=a+np.array([speed*.01,0,0])
        assert not support_edge([a,a],[b,b],{'foot':np.array([0])},[.01,.01])
