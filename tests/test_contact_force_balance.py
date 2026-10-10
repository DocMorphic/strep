import sys,copy,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import contact_force_balance as subject


def contact(name='floor',lever=(0,0,0),normal=(0,1,0),mu=.5,cap=100.):
    return dict(id=name,lever_from_com_world_m=list(lever),normal_into_body_world=list(normal),friction_coefficient=mu,max_force_N=cap)


def grips(cap=100.,mu=.5):
    return [contact('left',(-.2,0,0),(1,0,0),mu,cap),contact('right',(.2,0,0),(-1,0,0),mu,cap)]


def test_static_floor_support_is_checked_in_original_force_units():
    report=subject.solve([0,9.81,0],[0,0,0],[contact()])
    assert report['status']=='checked_feasible' and report['conditional_force_balance_passed']
    np.testing.assert_allclose(report['forces_world_N'],[[0,9.81,0]],atol=1e-6,rtol=0)
    assert report['replay']['maximum_force_component_error_N']<=1e-6
    assert report['quality_approved'] is False and report['release_approved'] is False
    json.dumps(report,allow_nan=False)


def test_frictionless_floor_cannot_pull_or_supply_tangential_force(monkeypatch):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('Axis exclusion does not need a solver'))
    for force in ([0,-1,0],[1,9.81,0]):
        report=subject.solve(force,[0,0,0],[contact(mu=0.)])
        assert report['status']=='infeasible_axis_bound' and not report['conditional_force_balance_passed']


def test_frictionless_positive_normal_requires_nonnegative_force():
    report=subject.solve([0,9.81,0],[0,0,0],[contact(mu=0.)])
    assert report['status']=='checked_feasible' and report['conditional_force_balance_passed']
    check=subject.inspect([0,-9.81,0],[0,0,0],[contact(mu=0.)],[[0,-9.81,0]])
    assert check['maximum_force_component_error_N']==0 and not check['conditional_force_balance_passed']


def test_opposing_hand_grips_supply_weight_with_squeeze_and_zero_net_torque():
    report=subject.solve([0,9.81,0],[0,0,0],grips())
    assert report['status']=='checked_feasible'
    forces=np.asarray(report['forces_world_N'])
    assert forces[0,0]>0 and forces[1,0]<0
    assert all(c['passed'] and c['normal_force_N']>=0 for c in report['replay']['contacts'])
    assert report['replay']['maximum_torque_component_error_Nm']<=1e-6


def test_total_force_cap_and_friction_give_stricter_vertical_capacity_than_normal_cap(monkeypatch):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('Analytic necessary bound is sufficient here'))
    report=subject.solve([0,200,0],[0,0,0],grips())
    assert report['status']=='infeasible_axis_bound' and 1 in report['violating_axes']
    assert report['axis_upper'][1]==pytest.approx(200*.5/np.hypot(1.,.5),abs=1e-9)


def test_passing_separate_axis_bounds_is_not_a_coupled_wrench_certificate():
    report=subject.solve([0,10,0],[0,0,0],[contact(lever=(1,0,0),mu=1.)])
    assert np.max(report['axis_excess'])==0
    assert report['status']=='infeasible_wrench_projection' and not report['conditional_force_balance_passed']
    assert report['projection_exclusion']['excess_N']>report['projection_exclusion']['numerical_tolerance_N']


def test_unreachable_moment_axis_is_excluded_without_solver(monkeypatch):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('Impossible moment axis'))
    report=subject.solve([0,9.81,0],[1,0,0],grips())
    assert report['status']=='infeasible_axis_bound' and 3 in report['violating_axes']


def test_zero_external_wrench_needs_no_contacts_or_solver(monkeypatch):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('No contacts'))
    report=subject.solve([0,0,0],[0,0,0],[])
    assert report['conditional_force_balance_passed'] and report['forces_world_N']==[]
    assert report['status']=='checked_zero_contact_wrench'
    assert subject.inspect([0,0,0],[0,0,0],[],json.loads(json.dumps(report))['forces_world_N'])['conditional_force_balance_passed']
    assert subject.solve([0,1,0],[0,0,0],[])['status']=='infeasible_axis_bound'


def test_force_and_torque_are_remeasured_with_original_contact_geometry():
    contacts=grips();forces=[[9.81,4.905,0],[-9.81,4.905,0]]
    assert subject.inspect([0,9.81,0],[0,0,0],contacts,forces)['conditional_force_balance_passed']
    changed=copy.deepcopy(contacts);changed[0]['lever_from_com_world_m']=[-.4,0,0]
    assert not subject.inspect([0,9.81,0],[0,0,0],changed,forces)['conditional_force_balance_passed']
    changed=copy.deepcopy(contacts);changed[0]['max_force_N']=1.
    assert not subject.inspect([0,9.81,0],[0,0,0],changed,forces)['conditional_force_balance_passed']
    changed=copy.deepcopy(contacts);changed[0]['friction_coefficient']=.1
    assert not subject.inspect([0,9.81,0],[0,0,0],changed,forces)['conditional_force_balance_passed']


@pytest.mark.parametrize('field,value',[('normal_into_body_world',[0,2,0]),('normal_into_body_world',[0,np.nan,0]),
    ('lever_from_com_world_m',[0,0]),('lever_from_com_world_m',[1001,0,0]),('friction_coefficient',-.1),
    ('friction_coefficient',True),('friction_coefficient',np.inf),('max_force_N',0),('max_force_N',True),('id','')])
def test_invalid_contact_assumptions_are_rejected_before_solver(monkeypatch,field,value):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('Invalid assumptions'))
    c=contact();c[field]=value
    with pytest.raises(ValueError):subject.solve([0,9.81,0],[0,0,0],[c])


@pytest.mark.parametrize('data',[dict(force=[np.inf,0,0]),dict(torque=[0,0]),dict(contacts=[contact(),contact()]),
    dict(contacts=[contact(str(i)) for i in range(17)]),dict(seconds=0),dict(seconds=True),
    dict(force_tolerance_N=0),dict(torque_tolerance_Nm=np.nan)])
def test_invalid_complete_problem_fails_before_solver(monkeypatch,data):
    monkeypatch.setattr(subject,'solver_module',lambda:pytest.fail('Invalid problem'))
    args=dict(force=[0,9.81,0],torque=[0,0,0],contacts=[contact()]);args.update(data)
    with pytest.raises(ValueError):subject.solve(**args)


@pytest.mark.parametrize('point',[[0,0,0],[np.nan,0,0],[0,1e100,0],[0,1e200,0],[0,9.81/100]])
def test_success_status_cannot_hide_a_false_or_invalid_force_witness(monkeypatch,point):
    actual=subject.solver_module()
    def solver(*args):return SimpleNamespace(solve=lambda:SimpleNamespace(x=point,status='Solved',iterations=1))
    monkeypatch.setattr(subject,'solver_module',lambda:SimpleNamespace(__version__=actual.__version__,DefaultSettings=actual.DefaultSettings,
        ZeroConeT=actual.ZeroConeT,NonnegativeConeT=actual.NonnegativeConeT,SecondOrderConeT=actual.SecondOrderConeT,DefaultSolver=solver))
    report=subject.solve([0,9.81,0],[0,0,0],[contact()])
    assert not report['conditional_force_balance_passed']
    json.dumps(report,allow_nan=False)


def test_declared_normal_is_canonicalized_without_mutating_inputs():
    c=contact();c['normal_into_body_world']=np.array([0.,1.+1e-11,0.]);before=c['normal_into_body_world'].copy()
    report=subject.solve([0,9.81,0],[0,0,0],[c])
    assert report['conditional_force_balance_passed']
    np.testing.assert_array_equal(c['normal_into_body_world'],before)
    assert report['contacts'][0]['normal_into_body_world']==[0.,1.,0.]
    json.dumps(report,allow_nan=False)


def test_optional_backend_version_is_pinned(monkeypatch):
    monkeypatch.setitem(sys.modules,'clarabel',SimpleNamespace(__version__='0.0.0'))
    with pytest.raises(ValueError,match='0.11.1'):subject.solver_module()


def test_projection_certificate_remeasures_complete_contact_force_model():
    contacts=[contact(lever=(1,0,0),mu=1.)]
    _,_,parsed=subject.validate([0,10,0],[0,0,0],contacts,1e-6,1e-6)
    result=subject.projection_exclusion(np.array([0,10,0,0,0,0.]),parsed,np.array([0,1,0,0,0,-1.]),1e-6,1e-6)
    assert result and result['required_projection_N']>result['upper_projection_N']
    assert subject.projection_exclusion(np.array([0,10,0,0,0,10.]),parsed,np.array([0,1,0,0,0,-1.]),1e-6,1e-6) is None


def test_finite_candidate_force_budget_prevents_overflow():
    with pytest.raises(ValueError,match='Bounded candidate'):
        subject.inspect([0,1,0],[0,0,0],[contact()],[[0,1e200,0]])


def test_finite_grip_patch_can_supply_twist_without_inflating_total_hand_capacity():
    points=grips(cap=100.)
    original=subject.solve([0,9.81,0],[1,0,0],points)
    assert not original['conditional_force_balance_passed']
    patches=[]
    for c in points:
        for sign in (-1,1):
            p=copy.deepcopy(c);p['id']+=f':{sign}';p['lever_from_com_world_m'][2]+=sign*.02;p['max_force_N']=50.
            patches.append(p)
    assert sum(c['max_force_N'] for c in patches)==sum(c['max_force_N'] for c in points)
    report=subject.solve([0,9.81,0],[1,0,0],patches)
    assert report['conditional_force_balance_passed']
    for hand in ('left','right'):
        assert sum(r['total_force_N'] for r in report['replay']['contacts'] if r['id'].startswith(hand+':'))<=100.+2e-6


def test_rounding_padding_cannot_approve_a_zero_contact_wrench_outside_original_tolerance():
    report=subject.solve([1e-6+1e-14,0,0],[0,0,0],[],force_tolerance_N=1e-6)
    assert report['status']=='not_certified' and not report['conditional_force_balance_passed']
