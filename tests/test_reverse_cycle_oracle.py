import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_reverse_cycles import expected_events,scenarios


def test_reverse_interval_and_simultaneous_inverse_order():
    markers=[dict(name='boundary',phase_frame=0,first_cycle=1),dict(name='start',phase_frame=0,first_cycle=0),dict(name='a',phase_frame=5,first_cycle=0),dict(name='b',phase_frame=5,first_cycle=0)]
    forward,reverse=expected_events(markers,10,dict(start_frame=20,destinations=[15,10,0],notify_reverse=True))
    assert not forward
    assert [(e['name'],e['cycle']) for e in reverse]==[('b',1),('a',1),('start',1),('boundary',1),('b',0),('a',0),('start',0)]
    assert all(e['direction']==-1 for e in reverse)


def test_direction_change_and_zero_step_never_repeat_origin():
    markers=[dict(name='cue',phase_frame=5,first_cycle=0)]
    f,r=expected_events(markers,10,dict(start_frame=4,destinations=[5,5,4,5,6,5],notify_reverse=True))
    assert len(f)==2 and len(r)==1
    assert f[0]['time_s']==r[0]['time_s']==5/30


def test_silent_reverse_and_declared_endpoints():
    for scenario in scenarios(45):
        assert scenario['destinations'][-1]==0
        if not scenario['notify_reverse']:
            assert expected_events([dict(name='cue',phase_frame=5,first_cycle=0)],45,scenario)==([],[])
