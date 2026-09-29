"""Test only pure policy functions, without launching or importing the study driver."""
import ast,json
from pathlib import Path
import numpy as np
import pytest
P=Path(__file__).resolve().parents[1]/'scripts/study_export_feedback.py'
tree=ast.parse(P.read_text())
namespace={'np':np}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['strengthen','exported_measurements']],type_ignores=[]),str(P),'exec'),namespace)
raw_strengthen=namespace['strengthen'];measure=namespace['exported_measurements']
def strengthen(*args):return raw_strengthen(*args,{},1.)


def layout():
 return {'point_rate:0:1':dict(bounds=[0,2],cap=2.,scale=2.,horizontal=1.)}


def test_observed_discrepancy_strengthens_only_failed_group():
 target=np.array([0.,0.,.3]);values=np.array([0.,.1,.2]);blocks=layout()
 result,notes=strengthen(target,values,blocks,{'point_rate:0:1':2.1},{'point_rate:0:1':-.05})
 np.testing.assert_allclose(result,[.0501,.0501,.3]);np.testing.assert_array_equal(target,[0.,0.,.3])
 assert notes[0]['changed'] and blocks['point_rate:0:1']['cap']==2.


def test_existing_protection_never_decreases():
 result,notes=strengthen(np.array([.2,.2]),np.array([0.,0.]),layout(),{'point_rate:0:1':2.01},{'point_rate:0:1':-.005})
 np.testing.assert_array_equal(result,[.2,.2]);assert not notes[0]['changed']


def test_passing_group_receives_no_new_target():
 result,notes=strengthen(np.zeros(2),np.zeros(2),layout(),{'point_rate:0:1':2.},{'point_rate:0:1':0.})
 assert notes==[] and not result.any()


def test_no_horizontal_room_is_retained_as_failure_not_relaxed_cap():
 blocks=layout();blocks['point_rate:0:1']['horizontal']=1.999
 result,notes=strengthen(np.zeros(2),np.zeros(2),blocks,{'point_rate:0:1':2.1},{'point_rate:0:1':-.05})
 assert not result.any() and not notes[0]['changed'] and 'No horizontal room' in notes[0]['reason']
 assert blocks['point_rate:0:1']['cap']==2.


def test_optional_margin_is_limited_by_remaining_horizontal_room():
 blocks=layout();blocks['point_rate:0:1']['horizontal']=1.99996
 result,notes=strengthen(np.zeros(2),np.zeros(2),blocks,{'point_rate:0:1':2.00002},{'point_rate:0:1':-.00001})
 assert notes[0]['discrepancy']<result[0]<notes[0]['capacity']


def test_fixed_approach_cannot_hide_new_release_failure():
 # Minimal published counterexample from the retained crawling experiment.
 cap=89.81727971614012
 before=dict(phase_rates=[{'variants':{'candidate':[0.,cap-.0001]}}],contacts=[],
   floor_nonregression={'maximum_added_depth_m':0.},preservation={'all_outside_times':{'maximum_errors':{'skin':0.}}})
 after=json.loads(json.dumps(before));after['phase_rates'][0]['variants']['candidate'][1]=89.81728132688808
 blocks={'release':dict(index=0,order=2,cap=cap,scale=cap)}
 _,a=measure(before,blocks);_,b=measure(after,blocks)
 assert [k for k,v in a.items() if v>=0 and b[k]<0]==['release']
 assert b['release']<0


def test_margin_backoff_retains_every_observed_discrepancy():
 blocks=layout();requirements={}
 target,first=raw_strengthen(np.zeros(2),np.zeros(2),blocks,{'point_rate:0:1':2.1},{'point_rate:0:1':-.05},requirements,1.)
 need=requirements['point_rate:0:1']
 backed=np.full(2,need['discrepancy']+.1*need['optional'])
 assert 0<need['discrepancy']<backed[0]<target[0]
 # A later smaller observed discrepancy must not erase the earlier one.
 result,notes=raw_strengthen(backed,np.zeros(2),blocks,{'point_rate:0:1':2.02},{'point_rate:0:1':-.01},requirements,.1)
 np.testing.assert_array_equal(result,backed)
 assert requirements['point_rate:0:1']['discrepancy']==need['discrepancy']
 assert blocks['point_rate:0:1']['cap']==2.
