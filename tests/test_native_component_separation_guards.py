"""Complete time/vertex populations and preservation of initially clear poses."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_component_separation_guards import build, observe, ComponentSeparationGuards
from native_triangle_separation_guards import SeparationGuards


def model():
    p = np.array([[-.5,-.5,-.5],[.5,-.5,-.5],[.5,.5,-.5],[-.5,.5,-.5],
                  [-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]])
    f = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                  [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]])
    vertices = {'A':np.array([p,p]), 'B':np.array([p+[1.5,0,0],p+[1.000000004,0,0]])}
    j = {name:np.zeros((*v.shape, 2)) for name,v in vertices.items()}
    j['A'][...,0,0] = 1.; j['B'][...,1,1] = 1.
    return dict(vertices=vertices, point_jacobians=j, local_faces={'A':f,'B':f},
                source_vertex_ids={'A':list(range(56,64)), 'B':list(range(96,104))}, times_s=[.5,1.19])


def test_every_sample_and_original_vertex_pair_has_a_distinct_hard_row():
    inputs=model(); g=build(**inputs)
    assert isinstance(g,ComponentSeparationGuards) and not isinstance(g,SeparationGuards)
    assert g.gaps_m.shape==(128,) and g.jacobian.shape==(128,2)
    assert [d['row_indices'] for d in g.groups]==[list(range(64)),list(range(64,128))]
    for frame in range(2):
        group=g.groups[frame]; rows=g.descriptors[frame*64:(frame+1)*64]
        assert [(d['left_vertex'],d['right_vertex']) for d in rows]==[(a,b) for a in range(56,64) for b in range(96,104)]
        assert all(d['group_index']==frame and d['time_s']==inputs['times_s'][frame] for d in rows)
        assert group['support_report']['complete_vertex_pair_rows']==64
    np.testing.assert_array_equal(observe(g,inputs['vertices']),g.gaps_m)
    assert np.all(g.clearances_m[:64]==1e-8)
    assert np.all(g.clearances_m[64:]==g.gaps_m[64:].min())
    assert not g.report['full_mesh_pair_partition'] and not g.report['continuous_coverage']
    assert not g.report['quality_approved'] and not g.report['release_approved']


def test_affine_translation_columns_match_actual_points_and_detect_lost_clear_sample():
    inputs=model(); g=build(**inputs)
    delta=np.array([.001,.002]); moved={n:v+np.einsum('fvcn,n->fvc',inputs['point_jacobians'][n],delta) for n,v in inputs['vertices'].items()}
    np.testing.assert_allclose(observe(g,moved),g.gaps_m+g.jacobian@delta,atol=5e-16,rtol=0)
    excess=g.clearances_m-observe(g,moved)
    assert excess[:64].max()<0 and excess[64:].max()>0


def test_complete_derivatives_inputs_and_returned_metadata_do_not_alias():
    inputs=model(); before=copy.deepcopy(inputs); g=build(**inputs)
    for n in inputs['vertices']:
        np.testing.assert_array_equal(inputs['vertices'][n],before['vertices'][n])
        np.testing.assert_array_equal(inputs['point_jacobians'][n],before['point_jacobians'][n])
    g.groups[0]['left_vertex_ids'].clear();g.report['source_vertex_ids']['B'].clear()
    assert inputs['source_vertex_ids']==before['source_vertex_ids']


def test_unequal_complete_components_keep_every_cartesian_pair():
    m=model()
    tetra=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
    m['vertices']['A']=np.array([tetra,tetra])
    m['vertices']['B']+=np.array([3.,0,0])
    m['point_jacobians']['A']=np.zeros((2,4,3,2))
    m['local_faces']['A']=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    m['source_vertex_ids']['A']=[10,20,30,40]
    g=build(**m)
    assert g.gaps_m.shape==(64,) and g.jacobian.shape==(64,2)
    assert all(len(group['row_indices'])==32 for group in g.groups)
    assert [(d['left_vertex'],d['right_vertex']) for d in g.descriptors[:32]]==[(a,b) for a in [10,20,30,40] for b in range(96,104)]
    np.testing.assert_array_equal(observe(g,m['vertices']),g.gaps_m)


@pytest.mark.parametrize('fault',['missing-actor','empty-time','repeated-time','reverse-time','negative-time','nan-time',
    'duplicate-id','unsorted-id','bool-id','wrong-point-count','nan-point','nan-derivative','missing-column',
    'missing-face','bool-face','nonconvex','nonpositive-first','nonpositive-later','row-budget','element-budget',
    'group-budget','bool-budget','nan-clearance','zero-clearance'])
def test_incomplete_invalid_or_nonpositive_population_never_returns_a_partial_guard(fault):
    m=model();kw={}
    if fault=='missing-actor':del m['local_faces']['B']
    elif fault=='empty-time':m['times_s']=[]
    elif fault=='repeated-time':m['times_s']=[.5,.5]
    elif fault=='reverse-time':m['times_s']=[1.,.5]
    elif fault=='negative-time':m['times_s']=[-.5,1.]
    elif fault=='nan-time':m['times_s']=[.5,np.nan]
    elif fault=='duplicate-id':m['source_vertex_ids']['A'][1]=56
    elif fault=='unsorted-id':m['source_vertex_ids']['A'].reverse()
    elif fault=='bool-id':m['source_vertex_ids']['A'][0]=True
    elif fault=='wrong-point-count':m['vertices']['A']=m['vertices']['A'][:,:7]
    elif fault=='nan-point':m['vertices']['A'][0,0,0]=np.nan
    elif fault=='nan-derivative':m['point_jacobians']['A'][0,0,0,0]=np.nan
    elif fault=='missing-column':m['point_jacobians']['B']=m['point_jacobians']['B'][...,:1]
    elif fault=='missing-face':m['local_faces']['A']=m['local_faces']['A'][:-1]
    elif fault=='bool-face':m['local_faces']['A']=m['local_faces']['A'].astype(bool)
    elif fault=='nonconvex':m['vertices']['A'][0,6]=[0,0,0]
    elif fault=='nonpositive-first':m['vertices']['B'][0,:,0]-=.6
    elif fault=='nonpositive-later':m['vertices']['B'][1,:,0]-=.1
    elif fault=='row-budget':kw['maximum_guard_rows']=127
    elif fault=='element-budget':kw['maximum_elements']=255
    elif fault=='group-budget':kw['maximum_groups']=1
    elif fault=='bool-budget':kw['maximum_groups']=True
    elif fault=='nan-clearance':kw['clearance_m']=np.nan
    elif fault=='zero-clearance':kw['clearance_m']=0.
    with pytest.raises(ValueError):build(**m,**kw)


@pytest.mark.parametrize('fault',['type','missing','shape','nan'])
def test_actual_observer_requires_complete_finite_declared_components(fault):
    m=model();g=build(**m);v=m['vertices']
    if fault=='type':g=object()
    elif fault=='missing':del v['B']
    elif fault=='shape':v['A']=v['A'][:1]
    elif fault=='nan':v['B'][0,0,0]=np.nan
    with pytest.raises(ValueError):observe(g,v)
