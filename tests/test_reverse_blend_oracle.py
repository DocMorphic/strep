import sys
from pathlib import Path
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_reverse_blends import crossings


def fixture(tmp_path):
    path=tmp_path/'metadata.json';path.write_text(json.dumps(dict(period_frames=40)))
    markers=[dict(name=n,phase_frame=f,first_cycle=0) for n,f in [('zero',0),('before',9),('tie1',10),('tie2',10),('end',20),('after',21)]]
    return dict(a=dict(metadata=str(path),probe_markers=markers),b=dict(metadata=str(path),probe_markers=markers),start_a=0,start_b=0,duration_frames=20)


def test_dominance_tie_and_reverse_total_order(tmp_path):
    case=fixture(tmp_path)
    got=crossings(case,'dominant',21,0,True)
    assert [(e['source_clip'],e['name']) for e in got]==[('b','end'),('b','tie2'),('b','tie1'),('a','before'),('a','zero')]
    assert [e['source_weight'] for e in got]==[1.,.5,.5,.55,1.]
    assert all(e['direction']==-1 for e in got)


def test_silent_blend_inclusive_end_but_incoming_afterward(tmp_path):
    case=fixture(tmp_path)
    assert [e['name'] for e in crossings(case,'silent',22,19,True)]==['after']
    assert crossings(case,'silent',20,0,True)==[]


def test_default_reverse_silent_and_direction_change_boundaries(tmp_path):
    case=fixture(tmp_path)
    assert crossings(case,'incoming',22,0,False)==[]
    assert [e['name'] for e in crossings(case,'incoming',9,10,True)]==['tie1','tie2']
    assert [e['name'] for e in crossings(case,'incoming',10,9,True)]==['before']
    assert crossings(case,'incoming',10,10,True)==[]
