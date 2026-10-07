"""Distinct auxiliary hard coverage in conics and every strict ray sample."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_material_component_support_step import args as original_args
from native_component_separation_guards import ComponentSeparationGuards
import native_material_component_guarded_support_step as step


def args():
    a,kw=original_args();left=list(range(4));right=list(range(10,14));time=.75;axis=[1.,0.,0.]
    group=dict(time_s=time,actors=['A','B'],left_vertex_ids=left,right_vertex_ids=right,
               row_indices=list(range(16)),axis_world=axis,clearance_m=.001)
    descriptors=[dict(kind='component-separation-guard',group_index=0,time_s=time,actors=['A','B'],
        left_vertex=l,right_vertex=r,axis_world=axis,clearance_m=.001) for l in left for r in right]
    report=dict(schema='strep-native-component-separation-guards-v1',controls=1,guard_rows=16,component_samples=1,
        source_vertex_ids={'A':left,'B':right},times_s=[time],complete_component_pair_rows=True,
        full_mesh_pair_partition=False,continuous_coverage=False)
    kw['component_separation_guards']=ComponentSeparationGuards(np.full(16,.01),sparse.csr_matrix((16,1)),
        np.full(16,.001),descriptors,[group],report)
    return a,kw


def tighten(guard):
    guard.gaps_m.fill(.0002);guard.clearances_m.fill(.0001);guard.groups[0]['clearance_m']=.0001
    for d in guard.descriptors:d['clearance_m']=.0001
    guard.jacobian=sparse.csr_matrix(-np.ones((16,1)))


def fake(monkeypatch,status='InsufficientProgress',point=(.025,.1,.1,.1)):
    class Settings:pass
    solver=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,
        DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(step,'solver_module',lambda:solver)


def test_auxiliary_positive_rows_are_hard_and_keep_distinct_coverage():
    a,kw=args();tighten(kw['component_separation_guards']);delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0001
    assert info['selected_auxiliary_component_guard_maximum_excess_m']<=0
    assert info['selected_native_maximum_excess']<=0 and info['selected_separation_guard_maximum_excess_m']<=0
    assert info['auxiliary_component_guard_rows']==16 and info['complete_separation_guard_rows']==1
    assert info['separation_guard_partition']['complete_pair_partition']
    assert not info['auxiliary_component_guard_coverage']['full_mesh_pair_partition']
    assert not info['quality_approved'] and not info['release_approved']


def test_each_auxiliary_pair_has_a_conic_hard_row_without_an_objective_slack():
    a,kw=args();tighten(kw['component_separation_guards']);captured=[]
    delta,info=step.direction(*a,**kw,solver_sink=captured.append)
    assert delta is not None
    model=captured[0];np.testing.assert_array_equal(model['linear'],[0.,1.,1.,1.])
    np.testing.assert_array_equal(model['matrix'][17:33].toarray(),np.tile([4.,0.,0.,0.],(16,1)))
    np.testing.assert_array_equal(model['rhs'][17:33],np.full(16,.02))
    np.testing.assert_array_equal(model['matrix'][33:85,1:].toarray(),-np.repeat(np.eye(3),[16,20,16],axis=0))


def test_auxiliary_guard_retreat_checks_every_row_and_preserves_solver_status(monkeypatch):
    a,kw=args();tighten(kw['component_separation_guards']);fake(monkeypatch)
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0001
    assert info['solver_status']=='InsufficientProgress' and info['selected_fraction']==.125
    assert all(r['auxiliary_component_guard_maximum_excess_m']>0 for r in info['records'][:-1])
    assert info['records'][-1]['auxiliary_component_guard_maximum_excess_m']<=0


def test_full_mesh_guards_still_force_retreat_when_auxiliary_rows_pass(monkeypatch):
    a,kw=args();fake(monkeypatch);g=kw['separation_guards']
    g.gaps_m[0]=.0002;g.clearances_m[0]=.0001;g.jacobian=sparse.csr_matrix([[-1.]])
    delta,info=step.direction(*a,**kw)
    assert delta is not None and delta[0]<=.0001
    assert all(r['separation_guard_maximum_excess_m']>0 for r in info['records'][:-1])
    assert all(r['auxiliary_component_guard_maximum_excess_m']<0 for r in info['records'])


def test_native_caps_and_parameter_equalities_are_retained():
    a,kw=args();a[0].caps[0]=.00001
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.00001
    kw['parameter_rows']=np.ones((1,1));delta,info=step.direction(*a,**kw)
    if delta is not None:assert abs(delta[0])<=1e-9 and info['parameter_maximum_absolute_residual']<=1e-9


def test_auxiliary_nonpassing_anchor_stops_before_solver(monkeypatch):
    a,kw=args();g=kw['component_separation_guards'];g.gaps_m[0]=.0005
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Guard anchor is not passing'))
    delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='OriginalAuxiliaryComponentGuardAnchorNotPassing'


def test_capture_mutation_cannot_change_auxiliary_guard_metadata_or_iterate():
    a,kw=args();before=copy.deepcopy(kw['component_separation_guards'])
    def sink(model):
        model['rhs'].fill(np.nan);model['record']['auxiliary_component_guard_groups'].clear()
        model['record']['auxiliary_component_guard_descriptors'].clear()
    delta,info=step.direction(*a,**kw,solver_sink=sink)
    assert delta is not None
    assert kw['component_separation_guards'].groups==before.groups
    assert kw['component_separation_guards'].descriptors==before.descriptors
    assert info['auxiliary_component_guard_groups'] and len(info['auxiliary_component_guard_descriptors'])==16


@pytest.mark.parametrize('fault',['wrong-type','mesh-label','continuous-label','controls','shape','nan','margin',
    'missing-group','missing-row','repeated-row','wrong-kind','wrong-pair','bool-pair','wrong-time','wrong-axis',
    'nonunit-axis','wrong-actor','wrong-source','nonuniform-margin','wrong-group-index','wrong-clock',
    'uncovered-row','group-row-out-of-range','unordered-source'])
def test_mislabelled_or_incomplete_auxiliary_guards_never_reach_solver(monkeypatch,fault):
    a,kw=args();g=kw['component_separation_guards']
    if fault=='wrong-type':kw['component_separation_guards']=kw['separation_guards']
    elif fault=='mesh-label':g.report['full_mesh_pair_partition']=True
    elif fault=='continuous-label':g.report['continuous_coverage']=True
    elif fault=='controls':g.report['controls']=2
    elif fault=='shape':g.jacobian=sparse.csr_matrix((16,2))
    elif fault=='nan':g.gaps_m[0]=np.nan
    elif fault=='margin':g.clearances_m[0]=0
    elif fault=='missing-group':g.groups=[]
    elif fault=='missing-row':g.groups[0]['row_indices'].pop()
    elif fault=='repeated-row':g.groups[0]['row_indices'][1]=0
    elif fault=='wrong-kind':g.descriptors[0]['kind']='triangle-separation'
    elif fault=='wrong-pair':g.descriptors[0]['left_vertex']=1
    elif fault=='bool-pair':g.descriptors[0]['left_vertex']=False
    elif fault=='wrong-time':g.descriptors[0]['time_s']=.6
    elif fault=='wrong-axis':g.descriptors[0]['axis_world']=[-1.,0.,0.]
    elif fault=='nonunit-axis':g.groups[0]['axis_world']=[2.,0.,0.]
    elif fault=='wrong-actor':g.groups[0]['actors']=['A','A']
    elif fault=='wrong-source':g.report['source_vertex_ids']['B']=[20,21,22,23]
    elif fault=='nonuniform-margin':g.clearances_m[0]=.0001
    elif fault=='wrong-group-index':g.descriptors[0]['group_index']=1
    elif fault=='wrong-clock':g.report['times_s']=[.8]
    elif fault=='uncovered-row':g.groups[0]['row_indices'][-1]=14
    elif fault=='group-row-out-of-range':g.groups[0]['row_indices'][-1]=16
    elif fault=='unordered-source':g.groups[0]['left_vertex_ids']=[3,2,1,0]
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Invalid auxiliary guard'))
    with pytest.raises(ValueError):step.direction(*a,**kw)


def test_non_motion_solver_status_is_preserved_before_any_ray(monkeypatch):
    a,kw=args();fake(monkeypatch,status='PrimalInfeasible')
    delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='NotMotionIterateStatus' and info['solver_status']=='PrimalInfeasible'
