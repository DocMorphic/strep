"""A later solve status cannot override measured native/priority failures."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partner_depth_restore as module
from test_native_partner_depth_restore import fixture


def solver(monkeypatch,points,status='AlmostSolved'):
    import clarabel
    calls=[]
    class Solver:
        __version__=clarabel.__version__
        NonnegativeConeT=clarabel.NonnegativeConeT
        SecondOrderConeT=clarabel.SecondOrderConeT
        DefaultSettings=clarabel.DefaultSettings
        @staticmethod
        def DefaultSolver(*args):
            index=len(calls);calls.append(1)
            return SimpleNamespace(solve=lambda:SimpleNamespace(status=status,x=points[index],iterations=1))
    monkeypatch.setattr(module,'solver_module',lambda:Solver)
    return calls


@pytest.mark.parametrize('status',['Solved','AlmostSolved'])
def test_bad_depth_in_minimum_norm_phase_keeps_verified_surface_point(monkeypatch,status):
    solver(monkeypatch,[[.025,.3,3.],[.025,.3,1.9],[.0255,.3,1.9]],status)
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta[0]==pytest.approx(.0005,abs=1e-16) and info['selected_phase']=='surface'
    assert info['phase_checks'][-1]['accepted'] is False and 'depth_priority' in info['phase_checks'][-1]['rejections']
    assert info['predicted_partner_depth_deficit']<=info['depth_phase_optimum']+info['phase_lock_tolerance']


def test_bad_surface_priority_keeps_previous_feasible_point(monkeypatch):
    solver(monkeypatch,[[.025,.5,3.],[.05,.5,1.8],[0.,.5,2.]])
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta[0]==pytest.approx(.001,abs=1e-16) and info['selected_phase']=='surface'
    assert 'surface_priority' in info['phase_checks'][-1]['rejections']
    assert info['full_affine_surface_excess']<=info['surface_phase_optimum']+info['phase_lock_tolerance']


def test_bad_second_phase_does_not_lock_its_false_surface_optimum(monkeypatch):
    calls=solver(monkeypatch,[[.025,.3,3.],[.025,.3,1.8]])
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta[0]==pytest.approx(.0005,abs=1e-16) and info['selected_phase']=='depth' and len(calls)==2
    assert info['minimum_norm_phase_status']=='not-run' and 'surface_epigraph' in info['phase_checks'][-1]['rejections']


def test_solved_first_phase_with_native_violation_returns_no_direction(monkeypatch):
    calls=solver(monkeypatch,[[.8,10.,10.]],'Solved')
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta is None and len(calls)==1 and info['status']=='UnverifiedDepthPhase' and info['selected_phase'] is None
    assert 'native_conditions' in info['phase_checks'][0]['rejections']


@pytest.mark.parametrize('point',[[.025,.2,3.],[.025,.3,1.],[float('nan'),.3,3.],[.025,.3],[2.,10.,10.]])
def test_invalid_or_underreported_first_phase_cannot_become_a_fallback(monkeypatch,point):
    calls=solver(monkeypatch,[point],'Solved');args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta is None and len(calls)==1 and info['selected_phase'] is None and not info['phase_checks'][0]['accepted']


def test_native_failure_in_later_phase_cannot_replace_a_good_primary(monkeypatch):
    solver(monkeypatch,[[.025,10.,10.],[.8,10.,10.]])
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta[0]==pytest.approx(.0005,abs=1e-16) and info['selected_phase']=='depth'
    assert 'native_conditions' in info['phase_checks'][-1]['rejections']


def test_feasible_minimum_norm_phase_is_still_selected(monkeypatch):
    solver(monkeypatch,[[.025,.3,3.],[.025,.3,1.9],[.025,.3,1.9]],'Solved')
    args,kwargs=fixture();delta,info,_=module.direction(*args,**kwargs)
    assert delta is not None and info['selected_phase']=='minimum-norm' and all(r['accepted'] for r in info['phase_checks'])
