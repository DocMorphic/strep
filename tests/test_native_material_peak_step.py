"""Worst depth cannot be bought with aggregate guidance or relaxed motion."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
import native_material_peak_step as peak


def args():
    gaps=np.r_[-.006,-.001,np.full(100,-.02)]
    return [NormRows([[0.,0.,0.]],[.01],[1.]),sparse.csr_matrix([[1.],[0.],[0.]]),
        gaps,sparse.csr_matrix(np.r_[1.,-1.,np.full(100,-1.)][:,None]),
        [{'kind':'penetrating-vertex'}]*2+[{'kind':'triangle-separation'}]*100,
        np.zeros(1),-np.ones(1),np.ones(1),.02]


def test_worst_depth_has_priority_over_one_hundred_conflicting_aggregate_rows():
    a=args();delta,info=peak.direction(*a)
    assert delta is not None and .0024<delta[0]<.0026
    assert info['selected_material_peak_depth_m']<.0036<info['initial_material_peak_depth_m']
    assert info['complete_guide_rows']==102 and info['containment_rows']==[0,1]
    assert info['selected_material_peak_depth_m']<=info['verified_first_phase_depth_ceiling_m']
    assert len(info['phases'])==2 and info['all_guide_rows_retained']
    assert not info['quality_approved'] and not info['release_approved'] and not info['solver_optimality_verified']


def test_complete_native_cap_limits_peak_proposal_and_cannot_be_relaxed():
    a=args();a[0].caps[0]=.0002
    delta,info=peak.direction(*a)
    assert delta is not None and 0<delta[0]<=.0002
    assert max(a[0].residual(a[1],delta))<=0 and a[0].caps[0]==.0002


def test_homogeneous_parameter_lock_can_make_depth_improvement_unavailable():
    delta,info=peak.direction(*args(),parameter_rows=[[1.]])
    if delta is not None:
        assert abs(delta[0])<=1e-9
    assert not info['quality_approved']


def test_observer_receives_all_models_and_mutation_does_not_change_candidates():
    a=args();seen=[]
    def sink(phase,sample):
        seen.append((phase,sample['matrix'].shape,sample['quadratic'].shape,sample['cones']))
        sample['rhs'].fill(np.nan);sample['record']['returned_point'].clear()
    delta,info=peak.direction(*a,solver_sink=sink)
    assert delta is not None and len(seen)==2 and len(info['phases'][0]['returned_point'])==2
    assert seen[0][2]==(2,2) and seen[1][2]==(104,104)


@pytest.mark.parametrize('kind',['anchor','no-witnesses','zero-depth'])
def test_invalid_anchor_or_missing_positive_depth_never_requests_a_solver(monkeypatch,kind):
    a=args()
    if kind=='anchor':a[0].vectors[0,0]=.02
    elif kind=='no-witnesses':a[4]=[{'kind':'triangle-separation'}]*len(a[2])
    else:a[2][:2]=0.
    monkeypatch.setattr(peak,'solver_module',lambda:pytest.fail('No depth proposal'))
    delta,info=peak.direction(*a);assert delta is None


@pytest.mark.parametrize('fault',['native-jac','guide-jac','population','unknown-kind','gap-sign','gap-nan','cap','scale','box','trust','clearance','metric-scale','parameters','sink'])
def test_invalid_complete_inputs_reject_before_solver_calls(monkeypatch,fault):
    a=args();kw={}
    if fault=='native-jac':a[1]=sparse.eye(3)
    elif fault=='guide-jac':a[3]=sparse.eye(2)
    elif fault=='population':a[4].pop()
    elif fault=='unknown-kind':a[4][-1]={'kind':'invented'}
    elif fault=='gap-sign':a[2][0]=.001
    elif fault=='gap-nan':a[2][-1]=np.nan
    elif fault=='cap':a[0].caps[0]=-1.
    elif fault=='scale':a[0].scales[0]=0.
    elif fault=='box':a[6]=a[7].copy()
    elif fault=='trust':a[8]=True
    elif fault=='clearance':kw['clearance_m']=True
    elif fault=='metric-scale':kw['scale_m']=np.nan
    elif fault=='parameters':kw['parameter_rows']=[[1.,0.]]
    else:kw['solver_sink']=True
    monkeypatch.setattr(peak,'solver_module',lambda:pytest.fail('Invalid complete model'))
    with pytest.raises(ValueError):peak.direction(*a,**kw)


@pytest.mark.parametrize('status,point,expected',[
    ('PrimalInfeasible',[.1,.1],'NotMotionIterateStatus'),
    ('NumericalError',[.1,.1],'NotMotionIterateStatus'),
    ('Solved',[np.nan,.1],'InvalidReturnedPoint'),
    ('Solved',[0.],'InvalidReturnedPoint'),
    ('InsufficientProgress',[2.,.1],'IterateOutsideOriginalBox'),
])
def test_certificate_nonfinite_or_out_of_box_iterates_never_reach_the_ray(monkeypatch,status,point,expected):
    class Settings:pass
    fake=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(peak,'solver_module',lambda:fake)
    monkeypatch.setattr(peak,'project',lambda *a:pytest.fail('Invalid iterate'))
    delta,info=peak.direction(*args());assert delta is None and info['phases'][0]['status']==expected


@pytest.mark.parametrize('second,status',[(.13,'DepthPriorityExceeded'),(.12,'NoSecondaryImprovement')])
def test_secondary_candidate_cannot_break_depth_priority_or_replace_a_better_complete_guide_score(monkeypatch,second,status):
    first=.125 if status=='DepthPriorityExceeded' else .1
    returned=iter([SimpleNamespace(status='InsufficientProgress',x=[first,.7],iterations=1),
        SimpleNamespace(status='Solved',x=[second,.7]+[0.]*102,iterations=1)])
    class Settings:pass
    fake=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,SecondOrderConeT=lambda n:n,
        ZeroConeT=lambda n:n,DefaultSettings=Settings,DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:next(returned)))
    monkeypatch.setattr(peak,'solver_module',lambda:fake)
    delta,info=peak.direction(*args())
    assert delta is not None and delta[0]==first*.02 and info['selected_phase']=='peak'
    assert info['phases'][0]['solver_status']=='InsufficientProgress' and info['phases'][1]['status']==status
    assert not info['solver_optimality_verified']


def test_every_coupled_native_norm_and_scale_survives_peak_optimization():
    a=args();a[0]=NormRows([[0.,0.,0.],[0.,0.,0.],[.001,0.,0.]],[.01,.0002,.001],[1.,.1,1.])
    a[1]=sparse.csr_matrix([[1.],[0.],[0.],[2.],[3.],[0.],[0.],[0.],[0.]])
    delta,info=peak.direction(*a)
    assert delta is not None and np.sqrt(13)*delta[0]<=.0002
    assert np.all(a[0].residual(a[1],delta)<=0)
    assert info['original_norm_rows']==3 and info['active_original_norm_cones']==2 and info['omitted_exactly_fixed_passing_norms']==1
