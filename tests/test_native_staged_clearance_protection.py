"""Earlier clearances survive pose changes through complete fresh point columns."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_triangle_separation_guards import SeparationGuards
from native_staged_clearance_protection import IndexedPointFrame,transport


def example():
    times=[0.,1.,3.];actors=['A','B'];frames=[]
    for actor in actors:
        for t in times:
            ids=[2,5,100] if t==1. else [2,5]
            points=np.array([[.004+t+v*.001,0,0] for v in ids])
            if actor=='B':points[:,0]-=.003
            jets=np.zeros((len(ids),3,2));jets[:,0,1]=1. if actor=='A' else 0.
            frames.append(IndexedPointFrame(actor,t,ids,points,jets))
    def descriptor(t,vertex=2):return dict(actors=['A','B'],time_s=t,left_vertex=vertex,right_vertex=vertex,axis_world=[1.,0.,0.],clearance_m=.001,origin='immutable original')
    d=descriptor(0.);g=float((frames[0].points_world[0]-frames[3].points_world[0])@np.array(d['axis_world']))
    fresh=SeparationGuards(np.array([g]),sparse.csr_matrix([[0.,1.]]),np.array([.001]),[d],dict(controls=2,complete_pair_partition=True,guard_rows=1))
    return [fresh,[descriptor(1.,100),descriptor(3.,5)],np.array([.001,.001]),frames,times,actors]


def test_every_original_axis_margin_order_and_last_control_survive():
    a=example();out=transport(*a)
    assert out.descriptors==a[0].descriptors+a[1]
    np.testing.assert_array_equal(out.clearances_m,[.001,.001,.001])
    np.testing.assert_array_equal(out.jacobian.toarray(),[[0.,1.],[0.,1.],[0.,1.]])
    for k,d in enumerate(out.descriptors):
        left=next(f for f in a[3] if f.actor=='A' and f.time_s==d['time_s'])
        right=next(f for f in a[3] if f.actor=='B' and f.time_s==d['time_s'])
        i=left.vertex_ids.index(d['left_vertex']);j=right.vertex_ids.index(d['right_vertex'])
        assert out.gaps_m[k]==float((left.points_world[i]-right.points_world[j])@np.array(d['axis_world']))
    assert out.report['carried_original_guard_rows']==2 and out.report['complete_point_frames']==6
    assert not any(out.report[k] for k in ('old_point_or_guard_derivatives_reused','source_provenance_verified','nonlinear_or_export_certificate','quality_approved','release_approved'))


def test_new_pose_and_new_columns_replace_prior_measurements_without_relaxing_margin():
    a=example();before=transport(*a)
    a[3][2].points_world[:,0]+=.01;a[3][2].point_jacobian[:,0,1]=3.
    after=transport(*a)
    assert after.gaps_m[-1]>before.gaps_m[-1]
    np.testing.assert_array_equal(after.jacobian.toarray()[-1],[0.,3.])
    assert after.descriptors==before.descriptors
    np.testing.assert_array_equal(after.clearances_m,before.clearances_m)


@pytest.mark.parametrize('fault',['last-nan-point','last-nan-column','missing-frame','duplicate-frame','wrong-clock',
    'bool-clock','unsorted-clock','missing-last-vertex','bool-vertex','duplicate-id','missing-column',
    'late-axis','late-time','late-actor','changed-margin','negative-margin','missing-margin','bool-axis',
    'stale-fresh-gap','stale-fresh-column','wrong-fresh-coverage','bool-controls','boolean-points',
    'row-budget','point-budget','missing-actor'])
def test_incomplete_or_stale_population_returns_no_partial_protection(fault):
    a=example();kw={}
    if fault=='last-nan-point':a[3][-1].points_world[-1,-1]=np.nan
    elif fault=='last-nan-column':a[3][-1].point_jacobian[-1,-1,-1]=np.nan
    elif fault=='missing-frame':a[3].pop()
    elif fault=='duplicate-frame':a[3][-1]=copy.deepcopy(a[3][0])
    elif fault=='wrong-clock':a[3][-1].time_s=2.
    elif fault=='bool-clock':a[4][0]=False
    elif fault=='unsorted-clock':a[4][:]=[0.,3.,1.]
    elif fault=='missing-last-vertex':a[1][-1]['right_vertex']=100
    elif fault=='bool-vertex':a[1][-1]['right_vertex']=True
    elif fault=='duplicate-id':a[3][-1].vertex_ids[:]=[2,2]
    elif fault=='missing-column':a[3][-1].point_jacobian=a[3][-1].point_jacobian[...,:1]
    elif fault=='late-axis':a[1][-1]['axis_world']=[2.,0.,0.]
    elif fault=='late-time':a[1][-1]['time_s']=2.
    elif fault=='late-actor':a[1][-1]['actors']=['A','C']
    elif fault=='changed-margin':a[1][-1]['clearance_m']=.0001
    elif fault=='negative-margin':a[2][-1]=-.001
    elif fault=='missing-margin':a[2]=a[2][:1]
    elif fault=='bool-axis':a[1][-1]['axis_world']=[True,0.,0.]
    elif fault=='stale-fresh-gap':a[0].gaps_m[0]=np.nextafter(a[0].gaps_m[0],np.inf)
    elif fault=='stale-fresh-column':a[0].jacobian=sparse.csr_matrix([[0.,2.]])
    elif fault=='wrong-fresh-coverage':a[0].report['complete_pair_partition']=False
    elif fault=='bool-controls':a[0].report['controls']=True
    elif fault=='boolean-points':a[3][-1].points_world=a[3][-1].points_world.astype(bool)
    elif fault=='row-budget':kw['maximum_rows']=2
    elif fault=='point-budget':kw['maximum_elements']=40
    elif fault=='missing-actor':a[5].pop()
    with pytest.raises(ValueError):transport(*a,**kw)


def test_inputs_and_metadata_do_not_alias_returned_model():
    a=example();saved=copy.deepcopy(a);out=transport(*a)
    out.gaps_m.fill(0);out.clearances_m.fill(0);out.jacobian.data.fill(0)
    out.descriptors[-1]['axis_world'][0]=0;out.report['guard_rows']=0
    assert a[0].report==saved[0].report and a[1]==saved[1]
    np.testing.assert_array_equal(a[0].jacobian.toarray(),saved[0].jacobian.toarray())
    np.testing.assert_array_equal(a[2],saved[2])


def test_no_archived_rows_and_zero_fresh_rows_are_explicit_complete_cases():
    a=example();a[1]=[];a[2]=np.array([]);out=transport(*a)
    assert out.jacobian.shape==(1,2) and out.report['carried_original_guard_rows']==0
    a=example();a[0]=SeparationGuards(np.array([]),sparse.csr_matrix((0,2)),np.array([]),[],dict(controls=2,complete_pair_partition=True,guard_rows=0))
    out=transport(*a);assert out.jacobian.shape==(2,2) and len(out.descriptors)==2
