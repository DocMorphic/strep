"""Complete Cartesian support groups, hard legacy bounds and actual conic rows."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_triangle_separation_guards import SeparationGuards
import native_material_component_support_step as step


def args():
    groups=[];witnesses=[]
    for k,(left,right) in enumerate(((list(range(4)),list(range(10,14))),
                                   (list(range(4)),list(range(10,15))),
                                   (list(range(4)),list(range(10,14))))):
        ids=[]
        for a in left:
            for b in right:
                i=len(witnesses);ids.append(i)
                witnesses.append(dict(kind='component-separation',descriptor_index=i,component_group_index=k,left_vertex=a,right_vertex=b))
        groups.append(dict(left_vertex_ids=left,right_vertex_ids=right,row_indices=ids,
                           actors=['A','B'],axis_world=[1.,0.,0.],time_s=k*.25))
    witnesses += [dict(kind='triangle-separation') for _ in range(9)]+[dict(kind='penetrating-vertex')]
    gaps=np.r_[np.full(36,-.001),np.full(16,-.02),np.full(9,-.004),-.003]
    clearances=np.r_[np.full(52,1e-8),np.full(9,.0001),0.]
    jac=sparse.csr_matrix(np.r_[np.ones(36),-np.ones(16),np.zeros(10)][:,None])
    a=[NormRows([[0.,0.,0.]],[.01],[1.]),sparse.csr_matrix([[1.],[0.],[0.]]),
       gaps,jac,witnesses,np.zeros(1),-np.ones(1),np.ones(1),.02]
    guard=SeparationGuards(np.array([.01]),sparse.csr_matrix((1,1)),np.array([.001]),[{}],
                           dict(controls=1,complete_pair_partition=True))
    return a,dict(component_groups=groups,guide_clearances_m=clearances,separation_guards=guard)


def test_unequal_complete_component_sizes_contribute_once_each():
    a,kw=args();delta,info=step.direction(*a,**kw)
    assert delta is not None and .000999<delta[0]<.001001
    assert info['component_group_sizes']==[16,20,16]
    assert info['selected_grouped_deficit_sum_m']<info['initial_grouped_deficit_sum_m']
    assert info['selected_worst_component_deficit_m']>info['initial_worst_component_deficit_m']
    assert info['original_triangle_deficit_ceiling_m']==info['selected_worst_legacy_triangle_deficit_m']==.0041
    assert info['original_material_depth_ceiling_m']==info['selected_material_peak_depth_m']==.003
    assert not any(info[k] for k in ('solver_optimality_verified','quality_approved','release_approved'))


def test_every_cartesian_pair_has_a_conic_row_but_one_group_slack():
    a,kw=args();seen=[];a[2][0]=-.003
    delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    assert delta is not None
    sample=seen[0];np.testing.assert_array_equal(sample['linear'],[0.,1.,1.,1.])
    # Box2 + native4 + containment1 + legacy9 + positiveguard1 precede52 component rows.
    np.testing.assert_array_equal(sample['matrix'][17:69,1:].toarray(),
                                  -np.repeat(np.eye(3),[16,20,16],axis=0))
    np.testing.assert_array_equal(sample['rhs'][17:69],(a[2][:52]-kw['guide_clearances_m'][:52])/.005)
    assert info['complete_guide_rows']==62 and info['component_group_count']==3


def test_non_extreme_vertex_rows_do_not_add_objective_weight():
    a,kw=args();a[2][1:16]=.1;a[2][17:36]=.1
    delta,info=step.direction(*a,**kw)
    assert delta is not None and .000999<delta[0]<.001001
    assert info['initial_group_deficits_m']==[.00100001,.00100001,.020000010000000002]


def test_native_and_positive_guard_bounds_are_both_hard():
    a,kw=args();a[0].caps[0]=.0002
    g=kw['separation_guards'];g.gaps_m[0]=.00011;g.clearances_m[0]=.0001
    g.jacobian=sparse.csr_matrix([[-1.]])
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.00011-.0001
    assert info['selected_native_maximum_excess']<=0 and info['selected_separation_guard_maximum_excess_m']<=0
    assert np.all(a[0].residual(a[1],delta)<=0)


def test_legacy_triangle_ceiling_is_hard_without_extra_objective_weight():
    a,kw=args();a[3]=a[3].tolil();a[3][52,0]=-1.;a[3]=a[3].tocsr()
    seen=[];delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    np.testing.assert_array_equal(seen[0]['matrix'][7:16,1:].toarray(),np.zeros((9,3)))
    if delta is not None:
        assert info['selected_worst_legacy_triangle_deficit_m']<=info['original_triangle_deficit_ceiling_m']
        assert delta[0]<1e-15


def test_capture_mutation_cannot_change_input_groups_or_iterate():
    a,kw=args();before=copy.deepcopy(kw['component_groups'])
    def sink(sample):
        sample['rhs'].fill(np.nan);sample['record']['component_groups'].clear();sample['record']['returned_point'].clear()
    delta,info=step.direction(*a,**kw,solver_sink=sink)
    assert delta is not None and kw['component_groups']==before
    assert len(info['component_groups'])==3 and len(info['returned_point'])==4


@pytest.mark.parametrize('fault',[
    'missing','short','duplicate-row','omitted','containment-row','bool-row','unknown-row','non-list',
    'unordered-vertices','duplicate-vertices','small-component','non-unit-axis','nan-axis','same-actor',
    'nan-time','wrong-pair','bool-pair','wrong-group','wrong-descriptor','nonuniform-clearance','duplicate-identity','reverse-duplicate-identity',
])
def test_incomplete_or_mislabelled_component_groups_never_reach_solver(monkeypatch,fault):
    a,kw=args();groups=kw['component_groups'];g=groups[0]
    if fault=='missing':kw['component_groups']=[]
    elif fault=='short':g['row_indices'].pop()
    elif fault=='duplicate-row':g['row_indices'][1]=g['row_indices'][0]
    elif fault=='omitted':groups.pop()
    elif fault=='containment-row':g['row_indices'][0]=61
    elif fault=='bool-row':g['row_indices'][0]=True
    elif fault=='unknown-row':g['row_indices'][0]=62
    elif fault=='non-list':kw['component_groups']=tuple(groups)
    elif fault=='unordered-vertices':g['left_vertex_ids'].reverse()
    elif fault=='duplicate-vertices':g['left_vertex_ids'][1]=0
    elif fault=='small-component':g['left_vertex_ids'].pop()
    elif fault=='non-unit-axis':g['axis_world']=[2.,0.,0.]
    elif fault=='nan-axis':g['axis_world'][0]=float('nan')
    elif fault=='same-actor':g['actors']=['A','A']
    elif fault=='nan-time':g['time_s']=float('nan')
    elif fault=='wrong-pair':a[4][0]['left_vertex']=3
    elif fault=='bool-pair':a[4][0]['left_vertex']=False
    elif fault=='wrong-group':a[4][0]['component_group_index']=1
    elif fault=='wrong-descriptor':a[4][0]['descriptor_index']=1
    elif fault=='nonuniform-clearance':kw['guide_clearances_m'][0]=2e-8
    elif fault=='duplicate-identity':groups[2]['time_s']=0.
    else:
        groups[2].update(time_s=0.,actors=['B','A'],left_vertex_ids=list(range(10,14)),right_vertex_ids=list(range(4)),axis_world=[-1.,0.,0.])
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Invalid complete component group'))
    with pytest.raises(ValueError):step.direction(*a,**kw)


def fake(monkeypatch,status,point):
    class Settings:pass
    solver=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,
        DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(step,'solver_module',lambda:solver)


@pytest.mark.parametrize('status,point,expected',[
    ('PrimalInfeasible',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('NumericalError',[.1,.1,.1,.1],'NotMotionIterateStatus'),
    ('Solved',[float('nan'),.1,.1,.1],'InvalidReturnedPoint'),
    ('Solved',[0.],'InvalidReturnedPoint'),
    ('InsufficientProgress',[2.,.1,.1,.1],'IterateOutsideOriginalBox'),
])
def test_invalid_iterates_are_rejected_before_ray(monkeypatch,status,point,expected):
    a,kw=args();fake(monkeypatch,status,point)
    class Forbidden:
        def __iter__(self):pytest.fail('Invalid iterate')
    monkeypatch.setattr(step,'FRACTIONS',Forbidden())
    delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']==expected and info['solver_status']==status


def test_strict_guard_retreat_preserves_original_solver_status(monkeypatch):
    a,kw=args();fake(monkeypatch,'InsufficientProgress',[.025,.1,.1,.1])
    g=kw['separation_guards'];g.gaps_m[0]=.0002;g.clearances_m[0]=.0001;g.jacobian=sparse.csr_matrix([[-1.]])
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0001 and info['selected_fraction']<1.
    assert info['records'][0]['separation_guard_maximum_excess_m']>0
    assert info['solver_status']=='InsufficientProgress' and info['selected_separation_guard_maximum_excess_m']<=0


def test_regressing_component_merit_is_rejected_for_complete_ray(monkeypatch):
    a,kw=args();fake(monkeypatch,'Solved',[-.1,.1,.1,.1])
    delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='NoStrictImprovingComponentRay' and len(info['records'])==81


def test_containment_ceiling_stays_strict_when_support_improves(monkeypatch):
    a,kw=args();a[3]=a[3].tolil();a[3][-1,0]=-1.;a[3]=a[3].tocsr()
    fake(monkeypatch,'Solved',[.1,.1,.1,.1]);delta,info=step.direction(*a,**kw)
    assert info['records'][0]['material_peak_depth_m']>.003
    if delta is not None:assert info['selected_material_peak_depth_m']<=.003


def test_no_deficit_or_failed_anchor_never_invokes_solver(monkeypatch):
    a,kw=args();monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('No eligible solve'))
    a[2][:52]=.1;delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='NoComponentDeficit'
    a,kw=args();a[0].vectors[0,0]=.02;delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='OriginalAnchorNotStrictlyPassing'


def test_parameter_rows_and_every_cap_scale_remain_explicit():
    a,kw=args();kw['parameter_rows']=np.array([[1.]])
    seen=[];delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    assert info['parameter_rows']==1 and info['original_norm_rows']==1
    np.testing.assert_array_equal(seen[0]['matrix'][2:3].toarray(),[[.02,0.,0.,0.]])
    if delta is not None:assert abs(delta[0])<=1e-9
