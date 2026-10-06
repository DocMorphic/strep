"""Raw rejected phase capture must not affect the original phase decisions."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partner_depth_restore as owner
from native_depth_solver_trace import direction
from test_native_partner_depth_restore import fixture
from test_native_partner_depth_phase_selection import solver


@pytest.mark.parametrize('points',[
 [[.025,10.,10.],[.8,10.,10.]],
 [[.025,.3,3.],[.025,.3,1.9],[.025,.3,1.9]],
 [[.8,10.,10.]],
 [[float('nan'),.3,3.]],
 [[.025,.3,3.],[.025,.3,1.8]],
])
def test_capture_preserves_full_result_globals_and_original_solution_objects(monkeypatch,points):
    solver(monkeypatch,copy.deepcopy(points),'Solved');args,kwargs=fixture()
    expected,info,reduction=owner.direction(*args,**kwargs)
    calls=solver(monkeypatch,copy.deepcopy(points),'Solved');factory=owner.solver_module;function=owner.direction
    actual,observed,certificate,records=direction(*args,**kwargs)
    assert owner.solver_module is factory and owner.direction is function
    assert observed==info and certificate.report==reduction.report
    if expected is None:assert actual is None
    else:np.testing.assert_array_equal(actual,expected)
    assert len(calls)==len(records)==len(info['phase_checks'])
    for i,row in enumerate(records):
        assert row['solve_index']==i and row['status']=='Solved' and not row['quality_approved']
        if np.isfinite(points[i]).all():assert row['point']==points[i] and row['finite_point']
        else:assert row['point'] is None and not row['finite_point']


def test_rejected_native_surface_target_is_retained_only_as_unapproved_data(monkeypatch):
    solver(monkeypatch,[[.025,10.,10.],[.8,10.,10.]],'Solved');args,kwargs=fixture()
    actual,info,_,records=direction(*args,**kwargs)
    assert info['selected_phase']=='depth' and 'native_conditions' in info['phase_checks'][1]['rejections']
    assert records[1]['point']==[.8,10.,10.] and actual[0]==pytest.approx(.0005)
    records[1]['point'][0]=0.
    assert actual[0]==pytest.approx(.0005) and not records[1]['release_approved']


def test_fixed_conflict_does_not_fabricate_a_solver_point():
    from native_scene_norms import NormRows
    from scipy import sparse
    args,kwargs=fixture();args[0]=NormRows([[.03,0,0]],[.015],[1.]);args[1]=sparse.csc_matrix((3,1))
    delta,info,_,records=direction(*args,**kwargs)
    assert delta is None and info['status']=='FixedProtectedConflict' and records==[]


def test_real_conic_solver_keeps_original_direction_and_phase_checks():
    args,kwargs=fixture();expected,info,_=owner.direction(*args,**kwargs)
    actual,observed,_,records=direction(*args,**kwargs)
    np.testing.assert_array_equal(actual,expected)
    assert observed==info and len(records)==len(info['phase_checks'])
    assert all(r['finite_point'] and len(r['point'])==3 for r in records)
