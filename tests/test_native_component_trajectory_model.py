"""Full-clock objectives preserve late collisions and initially clear samples."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_component_trajectory_model as trajectory


def example(times=(0.,1.,3.)):
    p=np.array([[-.5,-.5,-.5],[.5,-.5,-.5],[.5,.5,-.5],[-.5,.5,-.5],
                [-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]])
    f=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]])
    points={'A':np.repeat(p[None],len(times),axis=0),
            'B':np.array([p+[offset,0,0] for offset in np.linspace(1.5,.9,len(times))])}
    j={n:np.zeros((*v.shape,2)) for n,v in points.items()}
    j['A'][...,0,0]=1.;j['B'][...,0,1]=1.
    return dict(vertices=points,point_jacobians=j,local_faces={'A':f,'B':f},
        source_vertex_ids={'A':list(range(56,64)),'B':list(range(96,104))},
        times_s=list(times),required_times_s=list(times))


def test_late_collision_is_present_beyond_the_legacy4096_row_limit():
    m=example(tuple(np.linspace(0,1,70)));g=trajectory.build(**m)
    assert g.gaps_m.shape==(4480,) and g.jacobian.shape==(4480,2)
    assert len(g.groups)==70 and g.groups[-1]['first_row']==4416 and g.groups[-1]['stop_row']==4480
    np.testing.assert_array_equal(trajectory.observe(g,m['vertices']),g.gaps_m)
    review=trajectory.deficits(g,g.gaps_m)
    assert review['per_sample_m'][0]==0 and review['per_sample_m'][-1]>.099
    assert g.report['required_times_exact'] and not g.report['continuous_coverage']
    assert not g.report['full_mesh_pair_partition'] and not g.report['release_approved']


def test_irregular_clock_weights_match_trapezoidal_deficit_integral():
    m=example();g=trajectory.build(**m)
    np.testing.assert_array_equal(g.weights_s,[.5,1.5,1.])
    assert g.weights_s.sum()==3.
    review=trajectory.deficits(g,g.gaps_m)
    d=review['per_sample_m']
    expected=float((d[0]+d[1])/2+(d[1]+d[2]))
    assert review['integral_m_s']==expected
    assert review['sum_m']==d.sum() and review['maximum_m']==d.max()
    assert [group['quadrature_weight_s'] for group in g.groups]==g.weights_s.tolist()


def test_all_control_columns_match_actual_rigid_translation_and_clear_margin_is_capped():
    m=example();m['vertices']['B'][0]=m['vertices']['A'][0]+[1.000000004,0,0]
    g=trajectory.build(**m);step=np.array([.002,-.001])
    moved={n:v+np.einsum('fvcn,n->fvc',m['point_jacobians'][n],step) for n,v in m['vertices'].items()}
    np.testing.assert_allclose(trajectory.observe(g,moved),g.gaps_m+g.jacobian@step,atol=5e-16,rtol=0)
    assert g.groups[0]['starts_positive'] and g.groups[0]['clearance_m']==g.gaps_m[:64].min()<1e-8
    assert not g.groups[-1]['starts_positive'] and g.groups[-1]['clearance_m']==1e-8
    assert trajectory.deficits(g,trajectory.observe(g,moved))['per_sample_m'][0]>0


def test_unequal_components_and_single_clock_keep_every_original_pair():
    m=example((.7,));tetra=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
    m['vertices']['A']=tetra[None];m['vertices']['B']+=[3,0,0]
    m['point_jacobians']['A']=np.zeros((1,4,3,2))
    m['local_faces']['A']=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    m['source_vertex_ids']['A']=[10,20,30,40]
    g=trajectory.build(**m);assert g.gaps_m.shape==(32,) and g.jacobian.shape==(32,2)
    assert g.groups[0]['left_vertex_ids']==[10,20,30,40] and g.weights_s.tolist()==[1.]
    np.testing.assert_array_equal(trajectory.observe(g,m['vertices']),g.gaps_m)


def test_vertex_and_time_dependent_derivatives_preserve_pair_and_column_order():
    m=example();rng=np.random.default_rng(719)
    m['point_jacobians']={n:rng.normal(size=(*v.shape,5)) for n,v in m['vertices'].items()}
    g=trajectory.build(**m);step=np.array([1e-5,-2e-5,3e-5,-4e-5,5e-5])
    moved={n:v+np.einsum('fvcn,n->fvc',m['point_jacobians'][n],step) for n,v in m['vertices'].items()}
    np.testing.assert_allclose(trajectory.observe(g,moved),g.gaps_m+g.jacobian@step,atol=2e-15,rtol=0)


def test_model_metadata_and_arrays_do_not_mutate_or_alias_inputs():
    m=example();before=copy.deepcopy(m);g=trajectory.build(**m)
    for n in m['vertices']:
        np.testing.assert_array_equal(m['vertices'][n],before['vertices'][n])
        np.testing.assert_array_equal(m['point_jacobians'][n],before['point_jacobians'][n])
    g.report['source_vertex_ids']['A'].clear();g.groups[0]['right_vertex_ids'].clear()
    assert m['source_vertex_ids']==before['source_vertex_ids']


@pytest.mark.parametrize('budget',[{'maximum_groups':2},{'maximum_rows':191},
    {'maximum_elements':383},{'maximum_groups':True},{'maximum_rows':400001}])
def test_budget_rejects_entire_population_before_support_queries(monkeypatch,budget):
    def forbidden(*args,**kwargs):raise AssertionError('Budget rejection must precede support queries')
    monkeypatch.setattr(trajectory,'support_pair',forbidden)
    with pytest.raises(ValueError):trajectory.build(**example(),**budget)


@pytest.mark.parametrize('fault',['missing-actor','short-clock','subsample-clock','reverse-clock','nan-time',
    'duplicate-time','negative-time','duplicate-id','unsorted-id','bool-id','short-points','nan-point',
    'nan-column','unequal-columns','open-late-component','nonconvex-late-component','bool-face',
    'nan-clearance','zero-clearance'])
def test_incomplete_clock_or_component_never_returns_a_partial_model(fault):
    m=example();kw={}
    if fault=='missing-actor':del m['local_faces']['B']
    elif fault=='short-clock':m['required_times_s']=m['required_times_s'][:-1]
    elif fault=='subsample-clock':m['required_times_s']=[0.,.5,1.,3.]
    elif fault=='reverse-clock':m['times_s']=m['required_times_s']=[3.,1.,0.]
    elif fault=='nan-time':m['times_s']=m['required_times_s']=[0.,np.nan,3.]
    elif fault=='duplicate-time':m['times_s']=m['required_times_s']=[0.,0.,3.]
    elif fault=='negative-time':m['times_s']=m['required_times_s']=[-1.,1.,3.]
    elif fault=='duplicate-id':m['source_vertex_ids']['A'][1]=56
    elif fault=='unsorted-id':m['source_vertex_ids']['A'].reverse()
    elif fault=='bool-id':m['source_vertex_ids']['A'][0]=True
    elif fault=='short-points':m['vertices']['A']=m['vertices']['A'][:-1]
    elif fault=='nan-point':m['vertices']['B'][-1,0,0]=np.nan
    elif fault=='nan-column':m['point_jacobians']['A'][-1,0,0,0]=np.nan
    elif fault=='unequal-columns':m['point_jacobians']['A']=m['point_jacobians']['A'][...,:1]
    elif fault=='open-late-component':m['local_faces']['B']=m['local_faces']['B'][:-1]
    elif fault=='nonconvex-late-component':m['vertices']['B'][-1,6]=m['vertices']['B'][-1].mean(axis=0)
    elif fault=='bool-face':m['local_faces']['B']=m['local_faces']['B'].astype(bool)
    elif fault=='nan-clearance':kw['clearance_m']=np.nan
    elif fault=='zero-clearance':kw['clearance_m']=0.
    with pytest.raises(ValueError):trajectory.build(**m,**kw)


@pytest.mark.parametrize('fault',['wrong-type','missing','short','nan','short-gaps','nan-gaps'])
def test_observation_and_merit_require_the_complete_finite_population(fault):
    m=example();g=trajectory.build(**m)
    if fault=='wrong-type':g=object()
    elif fault=='missing':del m['vertices']['A']
    elif fault=='short':m['vertices']['B']=m['vertices']['B'][:-1]
    elif fault=='nan':m['vertices']['B'][-1,0,0]=np.nan
    with pytest.raises(ValueError):
        if fault=='short-gaps':trajectory.deficits(g,g.gaps_m[:-1])
        elif fault=='nan-gaps':trajectory.deficits(g,np.full(g.gaps_m.shape,np.nan))
        else:trajectory.observe(g,m['vertices'])
