"""The independent audit must catch errors between native animation keys."""
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_carrier_support import audit


class Rig:
    joints=[0]
    def __init__(self,candidate):
        self.document={'nodes':[{'name':'Hips'}],'candidate':candidate}
        self.binary=b''
    def vertices(self,matrices):
        return np.array([[0.,0.,0.],[1.,0.,0.]])+matrices[0,:3,3]


class Clock:
    def __init__(self,document,*args):self.candidate=document['candidate']
    def sample(self,time):
        matrix=np.eye(4)[None]
        # Exact native poses agree; intermediate poses exceed the pin tolerance.
        matrix[0,0,3]=.006*np.sin(np.pi*30*time)**2 if self.candidate else 0.
        return matrix


def test_between_key_contact_and_window_regression_are_visible():
    spec={'regions':{name:dict(mode='explicit',segments=[dict(vertex_id=i,
        start_frame=0,end_frame=2,position_m=[float(i),0.,0.])])
        for i,name in enumerate(['LeftFoot','RightFoot'])}}
    with patch('study_carrier_support.RigAsset.load',side_effect=[Rig(False),Rig(True)]), \
         patch('study_carrier_support.AnimationSampler',Clock):
        result=audit('source','candidate',spec,[1,1],3)
    assert result['samples']==9
    assert all(pin['samples_over_5mm']==0 for pin in result['variants']['source']['pins'])
    for pin in result['variants']['candidate']['pins']:
        assert pin['samples_over_5mm']==2
        assert np.isclose(pin['max_error_m'],.006)
        assert pin['speed_max_m_s']>0
    assert not result['preservation']['all_outside_times']['within_numerical_tolerance']
    assert result['variants']['candidate']['maximum_floor_depth_m']==0
    assert result['quality_approved'] is False
