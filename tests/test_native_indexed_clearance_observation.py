"""Complete actual-point protections retain original arithmetic and populations."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_indexed_clearance_observation import PointFrame,observe
from native_staged_clearance_protection import IndexedPointFrame,transport
from native_triangle_separation_guards import SeparationGuards


def fixture():
    times=[0.,.5,1.];actors=['A','B'];frames=[]
    for actor in actors:
        for t in times:
            ids=[5,12,99,200] if t==.5 else [5,12,99]
            points=np.array([[v*.001+t,(v%7)*.002,-t] for v in ids])
            if actor=='B':points[:,0]-=.003
            frames.append(PointFrame(actor,t,ids,points))
    rows=[dict(actors=['A','B'],time_s=t,left_vertex=v,right_vertex=v,
               axis_world=[1.,0.,0.],clearance_m=.001,origin={'id':i})
          for i,(t,v) in enumerate([(1.,99),(0.,5),(.5,200),(.5,12),(1.,99)])]
    return [rows,np.array([.001]*len(rows)),frames,times,actors]


def test_exact_original_scalar_projection_and_protection_transport():
    args=fixture();result=observe(*args)
    fresh=SeparationGuards(np.empty(0),sparse.csr_matrix((0,1)),np.empty(0),[],dict(controls=1,complete_pair_partition=True))
    jets=[IndexedPointFrame(f.actor,f.time_s,f.vertex_ids,f.points_world,np.zeros((*f.points_world.shape,1))) for f in args[2]]
    legacy=transport(fresh,args[0],args[1],jets,args[3],args[4])
    np.testing.assert_array_equal(result.gaps_m,legacy.gaps_m)
    np.testing.assert_array_equal(result.clearances_m,legacy.clearances_m)
    assert result.descriptors==legacy.descriptors==args[0] and result.failed_rows.size==0
    assert result.report['complete_rows']==5 and result.report['complete_point_frames']==6
    assert all(result.report[k] is False for k in ('source_provenance_verified','full_mesh_or_time_coverage_certified','derivatives_used','collision_predicates_evaluated','quality_approved','release_approved'))


def test_shuffled_complete_frames_different_vertex_layouts_and_random_axes():
    args=fixture();rng=np.random.default_rng(617);rows=[]
    for i in range(120):
        t=args[3][i%3];axis=rng.normal(size=3);axis/=np.linalg.norm(axis)
        rows.append(dict(actors=['B','A'] if i%2 else ['A','B'],time_s=t,left_vertex=5,right_vertex=99,axis_world=axis.tolist(),clearance_m=.001))
    args[0],args[1]=rows,np.full(120,.001);args[2]=list(reversed(args[2]));result=observe(*args)
    expected=[]
    for d in rows:
        left=next(f for f in args[2] if f.actor==d['actors'][0] and f.time_s==d['time_s'])
        right=next(f for f in args[2] if f.actor==d['actors'][1] and f.time_s==d['time_s'])
        expected.append(float((left.points_world[left.vertex_ids.index(d['left_vertex'])]-right.points_world[right.vertex_ids.index(d['right_vertex'])])@np.array(d['axis_world'])))
    np.testing.assert_array_equal(result.gaps_m,expected)
    np.testing.assert_array_equal(result.failed_rows,np.flatnonzero(np.array(expected)<args[1]))
    assert result.descriptors==rows


def test_exact_boundary_and_first_representable_deficit_without_tolerance():
    args=fixture();args[0]=[args[0][1]];args[1]=np.array([.001])
    left,right=args[2][0],args[2][3]
    left.points_world[0]=[.001,0,0];right.points_world[0]=[0,0,0]
    result=observe(*args);assert result.gaps_m[0]==.001 and result.failed_rows.size==0
    left.points_world[0,0]=np.nextafter(.001,-np.inf)
    result=observe(*args);np.testing.assert_array_equal(result.failed_rows,[0])
    assert not result.report['declared_clearance_rows_pass']


def test_returned_data_are_owned_and_duplicate_rows_retained():
    args=fixture();before=copy.deepcopy(args);result=observe(*args)
    assert not np.shares_memory(result.clearances_m,args[1])
    result.descriptors[0]['origin']['id']=900;result.clearances_m[:]=4;result.gaps_m[:]=5
    assert args[0]==before[0];np.testing.assert_array_equal(args[1],before[1])
    assert len(result.descriptors)==5 and result.descriptors[4]==args[0][4]


@pytest.mark.parametrize('fault',[
    'missing-frame','duplicate-frame','unknown-actor','late-clock','bool-clock','unsorted-clock',
    'duplicate-actor','missing-vertex','bool-vertex','unsorted-vertices','duplicate-vertex',
    'unused-last-point-nan','unused-last-point-inf','boolean-points','wrong-point-shape',
    'late-axis-nan','late-axis-nonunit','bool-axis','late-row-time','same-actor','unknown-row-actor',
    'changed-margin','missing-margin','zero-margin','nan-margin','boolean-margins','wrong-margin-shape',
    'invalid-descriptor','bool-row-budget','row-budget','point-budget','bool-point-budget'])
def test_entire_population_rejects_malformed_or_missing_evidence(fault):
    a=fixture();kw={}
    if fault=='missing-frame':a[2].pop()
    elif fault=='duplicate-frame':a[2][-1]=copy.deepcopy(a[2][0])
    elif fault=='unknown-actor':a[2][-1].actor='unknown'
    elif fault=='late-clock':a[2][-1].time_s=2.
    elif fault=='bool-clock':a[3][0]=False
    elif fault=='unsorted-clock':a[3]=[0.,1.,.5]
    elif fault=='duplicate-actor':a[4]=['A','A']
    elif fault=='missing-vertex':a[0][-1]['left_vertex']=900
    elif fault=='bool-vertex':a[2][-1].vertex_ids[0]=True
    elif fault=='unsorted-vertices':a[2][-1].vertex_ids.reverse()
    elif fault=='duplicate-vertex':a[2][-1].vertex_ids[-1]=12
    elif fault=='unused-last-point-nan':a[2][1].points_world[2,-1]=np.nan
    elif fault=='unused-last-point-inf':a[2][1].points_world[2,-1]=np.inf
    elif fault=='boolean-points':a[2][-1].points_world=np.ones((3,3),bool)
    elif fault=='wrong-point-shape':a[2][-1].points_world=np.ones((3,2))
    elif fault=='late-axis-nan':a[0][-1]['axis_world'][2]=np.nan
    elif fault=='late-axis-nonunit':a[0][-1]['axis_world']=[2.,0.,0.]
    elif fault=='bool-axis':a[0][-1]['axis_world'][0]=True
    elif fault=='late-row-time':a[0][-1]['time_s']=2.
    elif fault=='same-actor':a[0][-1]['actors']=['A','A']
    elif fault=='unknown-row-actor':a[0][-1]['actors']=['A','unknown']
    elif fault=='changed-margin':a[0][-1]['clearance_m']=.002
    elif fault=='missing-margin':a[0][-1].pop('clearance_m')
    elif fault=='zero-margin':a[1][-1]=0
    elif fault=='nan-margin':a[1][-1]=np.nan
    elif fault=='boolean-margins':a[1]=np.ones(5,bool)
    elif fault=='wrong-margin-shape':a[1]=np.ones((5,1))
    elif fault=='invalid-descriptor':a[0][-1]=None
    elif fault=='bool-row-budget':kw['maximum_rows']=True
    elif fault=='row-budget':kw['maximum_rows']=4
    elif fault=='point-budget':kw['maximum_point_elements']=59
    elif fault=='bool-point-budget':kw['maximum_point_elements']=True
    with pytest.raises(ValueError):observe(*a,**kw)


def test_empty_row_population_still_validates_every_declared_point():
    a=fixture();a[0]=[];a[1]=np.empty(0);result=observe(*a)
    assert result.gaps_m.size==result.failed_rows.size==0 and result.report['complete_point_frames']==6
    a[2][-1].points_world[-1,-1]=np.nan
    with pytest.raises(ValueError):observe(*a)


def test_finite_points_with_overflowing_projection_reject():
    a=fixture();a[2][0].points_world[0,0]=np.finfo(float).max;a[2][3].points_world[0,0]=-np.finfo(float).max
    with np.errstate(over='ignore'),pytest.raises(ValueError):observe(*a)
