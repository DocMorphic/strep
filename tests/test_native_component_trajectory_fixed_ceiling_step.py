"""Original material limits survive staged relinearization and strict retreat."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_component_trajectory_step import args,positive_last
import native_component_trajectory_fixed_ceiling_step as step
import native_component_trajectory_step as original


def fixed_args():
    a,kw=args()
    kw.update(material_depth_ceiling_m=.003,material_triangle_deficit_ceiling_m=.0041)
    return a,kw


def fake(monkeypatch,point=(.025,.1,.1,.1),status='InsufficientProgress'):
    class Settings:pass
    solver=SimpleNamespace(__version__='0.11.1',NonnegativeConeT=lambda n:n,
        SecondOrderConeT=lambda n:n,ZeroConeT=lambda n:n,DefaultSettings=Settings,
        DefaultSolver=lambda *a:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=point,iterations=1)))
    monkeypatch.setattr(step,'solver_module',lambda:solver)


@pytest.mark.parametrize('row',[0,9])
def test_frozen_ceiling_allows_verified_headroom_without_resetting_to_new_anchor(row):
    a,kw=fixed_args();kw['material_gaps_m'][:9 if row==0 else 0]+=.0003
    if row==9:kw['material_gaps_m'][row]+=.0003
    kw['material_gap_jacobian']=sparse.csr_matrix(([-1.],([row],[0])),shape=(10,1))
    delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0003
    assert info['original_material_depth_ceiling_m']==.003
    assert info['original_triangle_deficit_ceiling_m']==.0041
    assert not info['material_ceilings_recomputed_from_anchor']
    assert not info['ceiling_provenance_verified']
    assert not info['quality_approved'] and not info['release_approved']
    # The old one-pose solver derives a tighter limit from the newer anchor.
    old_kw={k:v for k,v in kw.items() if k not in ('material_depth_ceiling_m','material_triangle_deficit_ceiling_m')}
    old_delta,old_info=original.direction(*a,**old_kw)
    if old_delta is not None:assert old_delta[0]<delta[0]
    assert old_info['original_material_depth_ceiling_m']<=info['original_material_depth_ceiling_m']
    assert old_info['original_triangle_deficit_ceiling_m']<=info['original_triangle_deficit_ceiling_m']


@pytest.mark.parametrize('row',[0,9])
def test_anchor_above_original_ceiling_stops_before_solver(monkeypatch,row):
    a,kw=fixed_args();kw['material_gaps_m'][row]=np.nextafter(kw['material_gaps_m'][row],-np.inf)
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Rejected original ceiling'))
    delta,info=step.direction(*a,**kw)
    assert delta is None and info['status']=='OriginalMaterialCeilingsNotPassingAtAnchor'


@pytest.mark.parametrize('key',['material_depth_ceiling_m','material_triangle_deficit_ceiling_m'])
@pytest.mark.parametrize('value',[True,None,'0.01',float('nan'),float('inf'),-.001,.100001])
def test_invalid_explicit_ceiling_rejected_before_solver(monkeypatch,key,value):
    a,kw=fixed_args();kw[key]=value
    monkeypatch.setattr(step,'solver_module',lambda:pytest.fail('Invalid ceiling'))
    with pytest.raises(ValueError,match='ceiling'):step.direction(*a,**kw)


@pytest.mark.parametrize('row',[0,9])
def test_every_strict_ray_checks_frozen_ceiling_and_keeps_solver_status(monkeypatch,row):
    a,kw=fixed_args();kw['material_gaps_m'][row]+=.0001
    kw['material_gap_jacobian']=sparse.csr_matrix(([-1.],([row],[0])),shape=(10,1))
    fake(monkeypatch);delta,info=step.direction(*a,**kw)
    assert delta is not None and 0<delta[0]<=.0001
    assert info['solver_status']=='InsufficientProgress' and info['selected_fraction']==.125
    field='material_peak_depth_m' if row==9 else 'worst_legacy_triangle_deficit_m'
    cap=kw['material_depth_ceiling_m'] if row==9 else kw['material_triangle_deficit_ceiling_m']
    assert all(r[field]>cap for r in info['records'][:-1])
    assert info['records'][-1][field]<=cap


def test_complete_clock_and_last_positive_group_remain_hard():
    a,kw=args(tuple(np.linspace(0,1,70)));kw.update(material_depth_ceiling_m=.003,material_triangle_deficit_ceiling_m=.0041)
    positive_last(a);seen=[]
    delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    assert delta is not None and 0<delta[0]<=.0001
    assert info['complete_component_rows']==4480 and info['positive_component_rows']==64
    assert info['selected_native_maximum_excess']<=0
    assert info['selected_separation_guard_maximum_excess_m']<=0
    assert info['selected_positive_component_maximum_excess_m']<=0
    assert seen[0]['matrix'].shape[1]==71


def test_explicit_hard_material_rhs_uses_original_limits_without_objective_slack():
    a,kw=fixed_args();kw['material_gaps_m']+=.0001;seen=[]
    delta,info=step.direction(*a,**kw,solver_sink=seen.append)
    assert delta is not None
    np.testing.assert_array_equal(seen[0]['matrix'][6:16,1:].toarray(),np.zeros((10,3)))
    np.testing.assert_array_equal(seen[0]['rhs'][6:7],(kw['material_gaps_m'][9:]+.003)/.005)
    np.testing.assert_array_equal(seen[0]['rhs'][7:16],(kw['material_gaps_m'][:9]-kw['material_clearances_m'][:9]+.0041)/.005)


def test_zero_original_ceiling_can_be_explicitly_enforced():
    a,kw=fixed_args();kw['material_gaps_m'][:9]=.0001;kw['material_gaps_m'][9]=0.
    kw.update(material_depth_ceiling_m=0.,material_triangle_deficit_ceiling_m=0.)
    delta,info=step.direction(*a,**kw)
    assert delta is not None
    assert info['selected_material_peak_depth_m']==info['selected_worst_legacy_triangle_deficit_m']==0.


def test_both_original_limits_are_required_and_old_api_is_unchanged():
    a,kw=fixed_args();del kw['material_depth_ceiling_m']
    with pytest.raises(TypeError):step.direction(*a,**kw)
    a,old_kw=args();_,info=original.direction(*a,**old_kw)
    assert info['schema']=='strep-native-component-trajectory-step-v1'
    assert 'material_ceilings_recomputed_from_anchor' not in info
