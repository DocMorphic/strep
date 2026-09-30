import copy
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from window_triangle_objective import compile_window, finger_support
from triangle_separation_objective import gaps


A=np.array([[-2.,-1.,0.],[2.,-1.,0.],[0.,2.,0.]])
B=np.array([[0.,0.,-1.],[0.,0.,1.],[0.,1.,0.]])


def data():
    return dict(times=[0.,1.,2.],samples=[dict(time_s=float(t),proper=[[0,0]]) for t in range(3)],
        faces=[np.array([[0,1,2]]),np.array([[0,1,2]])],points=[[A.copy(),B.copy()] for _ in range(3)],
        support=[[np.full(3,t==1),np.zeros(3,bool)] for t in range(3)])


def test_all_times_and_fixed_pairs_remain_with_explicit_control_scope():
    value=compile_window(**data())
    assert value['all_crossing_pairs']==3 and value['potentially_editable_pairs']==1
    assert [r['potentially_editable'] for r in value['rows']]==[False,True,False]
    assert [r['unaffected_pairs'] for r in value['summary']]==[1,0,1]
    for row in value['rows']:
        assert row['fixed_axis_violation_m']==pytest.approx(max(0.,1e-8-gaps(A[None],B[None],np.array(row['axis'])[None]).min()))


def test_empty_timestamp_is_retained_without_inventing_a_crossing():
    args=data();args['samples'][1]['proper']=[]
    value=compile_window(**args)
    assert len(value['summary'])==3 and value['summary'][1]['crossing_pairs']==0
    assert value['all_crossing_pairs']==2


@pytest.mark.parametrize('kind',['duplicate','missing','clock','mask','bounds','nan'])
def test_inconsistent_or_truncated_population_fails(kind):
    args=data()
    if kind=='duplicate':args['samples'][0]['proper']*=2
    if kind=='missing':args['points'].pop()
    if kind=='clock':args['samples'][0]['time_s']=.1
    if kind=='mask':args['support'][0][0]=np.zeros(2,bool)
    if kind=='bounds':args['samples'][0]['proper']=[[2,0]]
    if kind=='nan':args['points'][0][0][0,0]=np.nan
    with pytest.raises(ValueError):compile_window(**args)


def test_support_uses_all_positive_skin_influences_descendants_and_native_clock():
    entry=dict(node=1,clock=np.array([0.,1.,2.]),ids=np.array([1]),weights=np.array([[1.]]))
    model=SimpleNamespace(model=SimpleNamespace(entries=[entry]),rig=SimpleNamespace(parents=[-1,0,1,0]))
    skin=SimpleNamespace(nodes=np.array([[0,2],[1,3],[3,0],[0,2]]),weights=np.array([[1.-1e-10,1e-10],[0.,1.],[1.,0.],[.5,.5]]))
    result=finger_support(model,skin,np.array([0.,.5,1.,1.5,2.]))
    np.testing.assert_array_equal(result[[0,4]],np.zeros((2,4),bool))
    np.testing.assert_array_equal(result[1:4],np.tile([True,False,False,True],(3,1)))


def test_compilation_copies_evidence_without_changing_inputs():
    args=data();saved=copy.deepcopy(args);value=compile_window(**args)
    value['rows'][0]['vertices'][0][0]=99
    np.testing.assert_array_equal(args['faces'][0],saved['faces'][0])
    for current,old in zip(args['points'],saved['points']):
        for a,b in zip(current,old):np.testing.assert_array_equal(a,b)
