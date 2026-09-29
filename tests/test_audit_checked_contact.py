import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_checked_contact import audit


class Rig:
    joints=[0]
    def __init__(self,candidate):self.document={'nodes':[{'name':'Hips'}],'candidate':candidate};self.binary=b''
    def vertices(self,m):return m[0,:3,3][None]


class Clock:
    def __init__(self,d,*args):self.candidate=d['candidate']
    def sample(self,t):
        m=np.eye(4)[None];m[0,0,3]=.01 if self.candidate and t>=4/30 else 0.;return m


def test_every_interval_and_outside_export_are_checked():
    pins=[dict(start_frame=a,end_frame=b,vertex_id=0,space='world',position_m=[0.,0.,0.]) for a,b in [(1,2),(3,4)]]
    spec=dict(frame_count=6,regions={'LeftFoot':dict(mode='explicit',segments=pins)})
    reference=dict(rows=[dict(region='LeftFoot',vertex_id=0,phase='hold',first_frame=a,last_frame=b,reference_ceilings=[0.,0.]) for a,b in [(1,2),(3,4)]])
    with patch('audit_checked_contact.RigAsset.load',side_effect=[Rig(False),Rig(True)]),patch('audit_checked_contact.AnimationSampler',Clock):
        result=audit('source','candidate',spec,[1,4],reference)
    assert len(result['contacts'])==2 and result['contacts'][0]['samples_over_5mm']==0
    assert result['contacts'][1]['samples_over_5mm']>0
    assert not result['all_requested_pin_samples_within_5mm'] and not result['outside_preservation_passed']
    assert result['phase_rates'][1]['candidate_excess_over_checked'][0]>0


def test_floor_regression_cannot_hide_below_source_global_peak():
    class FloorClock(Clock):
        def sample(self,t):
            m=np.eye(4)[None]
            m[0,1,3]=-.02 if t<1/30 else (-.01 if self.candidate else 0.)
            return m
    spec=dict(frame_count=3,regions={'LeftFoot':dict(mode='explicit',segments=[
        dict(start_frame=0,end_frame=2,vertex_id=0,space='world',position_m=[0.,0.,0.])])})
    with patch('audit_checked_contact.RigAsset.load',side_effect=[Rig(False),Rig(True)]),patch('audit_checked_contact.AnimationSampler',FloorClock):
        result=audit('source','candidate',spec,[0,2],dict(rows=[]))
    assert result['variants']['source']['maximum_floor_depth_m']==result['variants']['candidate']['maximum_floor_depth_m']==.02
    assert result['floor_nonregression']['maximum_added_depth_m']==.01
    assert result['floor_nonregression']['samples_over_1um_numerical_budget']==5
