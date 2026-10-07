"""Complete-clock conics, hard clear samples and strict original conditions."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_component_trajectory_model import example
from native_component_trajectory_model import build
from native_scene_norms import NormRows
from native_triangle_separation_guards import SeparationGuards
import native_component_trajectory_step as step


def args(times=(0.,1.,3.)):
    m=example(times);m['point_jacobians']={n:np.zeros((*v.shape,1)) for n,v in m['vertices'].items()}
    m['vertices']['B']=m['vertices']['A']+[.999,0,0]
    m['point_jacobians']['A'][...,0,0]=-1.
    g=build(**m)
    a=[NormRows([[0.,0.,0.]],[.01],[1.]),sparse.csr_matrix([[1.],[0.],[0.]]),g,
       np.zeros(1),-np.ones(1),np.ones(1),.02]
    guard=SeparationGuards(np.array([.01]),sparse.csr_matrix((1,1)),np.array([.0001]),[{}],
        dict(controls=1,complete_pair_partition=True))
    kw=dict(separation_guards=guard,material_gaps_m=np.r_[np.full(9,-.004),-.003],
        material_gap_jacobian=sparse.csr_matrix((10,1)),
        material_witnesses=[dict(kind='triangle-separation') for _ in range(9)]+[dict(kind='penetrating-vertex')],
        material_clearances_m=np.r_[np.full(9,.0001),0.])
    return a,kw


def positive_last(a,margin=.0001,gap=.0002):
    g=a[2];first=g.groups[-1]['first_row'];g.gaps_m[first:]=gap
    g.clearances_m[first:]=margin;g.jacobian=g.jacobian.tolil();g.jacobian[first:,0]=-1.;g.jacobian=g.jacobian.tocsr()
    for k,group in enumerate(g.groups):
        smallest=float(g.gaps_m[group['first_row']:group['stop_row']].min())
        group.update(starting_minimum_support_gap_m=smallest,starts_positive=smallest>0,clearance_m=margin)
        g.clearances_m[group['first_row']:group['stop_row']]=margin
    g.report['requested_clearance_m']=margin;g.report['positive_sample_indices']=[len(g.groups)-1]


def fake(monkeypatch,status='InsufficientProgress',point=(.025,.1,.1,.1)):
    class Settings:pass
    solver=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,
        DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(step,'solver_module',lambda:solver)


def test_complete_large_clock_is_solved_without_legacy_material_subsampling():
    a,kw=args(tuple(np.linspace(0,1,70)));delta,info=step.direction(*a,**kw)
    assert delta is not None and delta[0]>.000999
    assert info['complete_component_rows']==4480 and info['component_group_count']==70 and info['material_rows']==10
    assert info['selected_deficit_integral_m_s']<info['initial_deficit_integral_m_s']
    assert info['selected_native_maximum_excess']<=0 and info['selected_separation_guard_maximum_excess_m']<=0
    assert not info['quality_approved'] and not info['release_approved']


def test_conic_contains_every_pair_but_one_clock_weighted_slack_per_group():
    a,kw=args();captured=[];delta,info=step.direction(*a,**kw,solver_sink=captured.append)
    assert delta is not None;model=captured[0]
    np.testing.assert_array_equal(model['linear'],[0.,1/6,1/2,1/3])
    # box2 + native4 + containment1 + triangle9 + fullmeshguard1 precede192 trajectory rows.
    np.testing.assert_array_equal(model['matrix'][17:209,1:].toarray(),-np.repeat(np.eye(3),64,axis=0))
    np.testing.assert_array_equal(model['rhs'][17:209],(a[2].gaps_m-a[2].clearances_m)/.005)
    assert info['original_material_depth_ceiling_m']==.003 and info['original_triangle_deficit_ceiling_m']==.0041


def test_each_initially_positive_pair_is_hard_without_epigraph_slack():
    a,kw=args();positive_last(a);captured=[];delta,info=step.direction(*a,**kw,solver_sink=captured.append)
    assert delta is not None and 0<delta[0]<=.0001
    assert info['positive_component_rows']==64 and info['selected_positive_component_maximum_excess_m']<=0
    np.testing.assert_array_equal(captured[0]['matrix'][17:81].toarray(),np.tile([4.,0.,0.,0.],(64,1)))
    np.testing.assert_array_equal(captured[0]['rhs'][17:81],np.full(64,.02))


def test_strict_retreat_preserves_late_clear_sample_and_nonoptimal_status(monkeypatch):
    a,kw=args();positive_last(a);fake(monkeypatch);delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0001 and info['solver_status']=='InsufficientProgress'
    assert info['selected_fraction']==.125 and all(r['positive_component_maximum_excess_m']>0 for r in info['records'][:-1])
    assert info['records'][-1]['positive_component_maximum_excess_m']<=0


def test_full_mesh_guard_forces_retreat_independently_of_component_objective(monkeypatch):
    a,kw=args();fake(monkeypatch);g=kw['separation_guards']
    g.gaps_m[0]=.0002;g.clearances_m[0]=.0001;g.jacobian=sparse.csr_matrix([[-1.]])
    delta,info=step.direction(*a,**kw)
    assert delta is not None and delta[0]<=.0001
    assert all(r['separation_guard_maximum_excess_m']>0 for r in info['records'][:-1])


def test_native_caps_equalities_and_cumulative_box_remain_hard():
    a,kw=args();a[0].caps[0]=.00001;a[5][0]=.000007
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.000007 and np.all(a[0].residual(a[1],delta)<=0)
    kw['parameter_rows']=np.ones((1,1));delta,info=step.direction(*a,**kw)
    if delta is not None:assert abs(delta[0])<=1e-9 and info['parameter_maximum_absolute_residual']<=1e-9


@pytest.mark.parametrize('row',[0,9])
def test_legacy_triangle_and_containment_ceilings_have_no_objective_slack(row):
    a,kw=args();kw['material_gap_jacobian']=kw['material_gap_jacobian'].tolil();kw['material_gap_jacobian'][row,0]=-1.
    kw['material_gap_jacobian']=kw['material_gap_jacobian'].tocsr();seen=[]
    delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    np.testing.assert_array_equal(seen[0]['matrix'][6:16,1:].toarray(),np.zeros((10,3)))
    if delta is not None:
        assert info['selected_material_peak_depth_m']<=info['original_material_depth_ceiling_m']
        assert info['selected_worst_legacy_triangle_deficit_m']<=info['original_triangle_deficit_ceiling_m']


def test_source_metadata_and_solver_callback_do_not_alias_inputs():
    a,kw=args();before=copy.deepcopy(a[2])
    def sink(model):model['rhs'].fill(np.nan);model['record']['component_groups'].clear()
    delta,info=step.direction(*a,**kw,solver_sink=sink)
    assert delta is not None and a[2].groups==before.groups and a[2].report==before.report
    assert len(info['component_groups'])==3


@pytest.mark.parametrize('fault',['wrong-type','mesh-label','continuous-label','required-clock','controls','bool-controls',
    'rows','groups','missing-group','shape','nan','margin','nonuniform-margin','clock','bool-clock','axis','row-first',
    'row-stop','bool-row','wrong-source','bool-source','wrong-actors','starting-gap','positive-label','omitted-positive',
    'bool-positive','weights','group-weight','legacy-kind','legacy-size','positive-containment','parameter-columns'])
def test_invalid_complete_population_is_rejected_before_solver(monkeypatch,fault):
    a,kw=args();positive_last(a);g=a[2]
    if fault=='wrong-type':a[2]=kw['separation_guards']
    elif fault=='mesh-label':g.report['full_mesh_pair_partition']=True
    elif fault=='continuous-label':g.report['continuous_coverage']=True
    elif fault=='required-clock':g.report['required_times_exact']=False
    elif fault=='controls':g.report['controls']=2
    elif fault=='bool-controls':g.report['controls']=True
    elif fault=='rows':g.report['rows']=191
    elif fault=='groups':g.report['component_samples']=2
    elif fault=='missing-group':g.groups.pop()
    elif fault=='shape':g.jacobian=sparse.csr_matrix((192,2))
    elif fault=='nan':g.gaps_m[0]=np.nan
    elif fault=='margin':g.clearances_m[0]=0
    elif fault=='nonuniform-margin':g.clearances_m[0]*=2
    elif fault=='clock':g.report['times_s'][0]=.1
    elif fault=='bool-clock':g.report['times_s'][0]=False
    elif fault=='axis':g.groups[0]['axis_world']=[2.,0.,0.]
    elif fault=='row-first':g.groups[0]['first_row']=1
    elif fault=='row-stop':g.groups[0]['stop_row']=63
    elif fault=='bool-row':g.groups[0]['first_row']=False
    elif fault=='wrong-source':g.groups[0]['left_vertex_ids']=[1,2,3,4]
    elif fault=='bool-source':g.groups[0]['left_vertex_ids'][0]=False;g.report['source_vertex_ids']['A'][0]=False
    elif fault=='wrong-actors':g.groups[0]['actors']=['B','A']
    elif fault=='starting-gap':g.groups[0]['starting_minimum_support_gap_m']=0.
    elif fault=='positive-label':g.groups[-1]['starts_positive']=False
    elif fault=='omitted-positive':g.report['positive_sample_indices']=[]
    elif fault=='bool-positive':g.report['positive_sample_indices']=[True]
    elif fault=='weights':g.weights_s[0]*=2
    elif fault=='group-weight':g.groups[0]['quadrature_weight_s']*=2
    elif fault=='legacy-kind':kw['material_witnesses'][0]['kind']='component-separation'
    elif fault=='legacy-size':kw['material_gaps_m']=np.zeros(4097)
    elif fault=='positive-containment':kw['material_gaps_m'][-1]=.1
    elif fault=='parameter-columns':kw['parameter_rows']=np.ones((1,2))
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Invalid complete model'))
    with pytest.raises(ValueError):step.direction(*a,**kw)


@pytest.mark.parametrize('status,point,expected',[
    ('PrimalInfeasible',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('NumericalError',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('Solved',[np.nan,.1,.1,.1],'InvalidReturnedPoint'),
    ('Solved',[0.],'InvalidReturnedPoint'),
    ('InsufficientProgress',[2.,.1,.1,.1],'IterateOutsideOriginalBox')])
def test_invalid_solver_results_keep_status_and_never_enter_ray(monkeypatch,status,point,expected):
    a,kw=args();fake(monkeypatch,status,point)
    class Forbidden:
        def __iter__(self):pytest.fail('Invalid solver point')
    monkeypatch.setattr(step,'FRACTIONS',Forbidden());delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']==expected and info['solver_status']==status


def test_nonpassing_original_native_or_mesh_guard_stops_before_solver(monkeypatch):
    a,kw=args();a[0].vectors[0,0]=.1
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Nonpassing original native anchor'))
    delta,info=step.direction(*a,**kw);assert delta is None and info['status']=='OriginalAnchorNotStrictlyPassing'
    a[0].vectors.fill(0);kw['separation_guards'].gaps_m[0]=0.
    delta,info=step.direction(*a,**kw);assert delta is None and info['status']=='OriginalSeparationGuardAnchorNotPassing'
