import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT
from gltf_tools import read_glb,accessor
from pace_controls import retime_glb,contact_intervals


@pytest.mark.parametrize('speed',[2.4,3.0,3.6])
def test_export_clock_sets_speed_without_changing_any_pose(speed):
    d,b=read_glb(ROOT/'reports/periodic-controls-v1/takes/arm-45-lean-10-seed-11/soma.glb')
    old_times=accessor(d,b,d['animations'][0]['samplers'][0]['input']).copy()
    result,payload,timing=retime_glb(d,b,speed)
    times=accessor(result,payload,result['animations'][0]['samplers'][0]['input'])
    assert abs(timing['cycle_displacement_m'][2]*4/times[-1]-speed)<1e-5
    for a,c in zip(d['animations'][0]['samplers'],result['animations'][0]['samplers']):
        np.testing.assert_array_equal(accessor(d,b,a['output']),accessor(result,payload,c['output']))
    np.testing.assert_array_equal(old_times,accessor(d,b,d['animations'][0]['samplers'][0]['input']))
    assert np.all(np.diff(times)>0)


def test_contact_intervals_respect_clip_boundaries_and_seconds():
    contacts=np.array([[1,0],[1,1],[0,1],[1,0],[1,1]],dtype=bool)
    events=contact_intervals(contacts,np.arange(5)*.2,['left','right'])
    assert [(e['joint'],e['start_frame'],e['end_frame_exclusive']) for e in events]==[('left',0,2),('right',1,3),('left',3,4)]
    assert events[0]['clipped_at_start'] and events[-1]['clipped_at_end']
    assert events[-1]['end_s']==.8
    fast=contact_intervals(contacts,np.arange(5)*.1,['left','right'])
    assert fast[1]['end_s']==events[1]['end_s']/2


@pytest.mark.parametrize('speed',[0,-1,float('nan'),float('inf')])
def test_invalid_pace_is_rejected(speed):
    with pytest.raises(ValueError):retime_glb({},b'',speed)
