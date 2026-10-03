"""Worst-geometry proposal protection without authored-limit changes."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_scene_conic import direction
from native_geometry_norms import protect_worst,regression
import native_surface_model as surface
from test_native_surface_model import report


def test_existing_prefix_and_complete_geometry_block_are_preserved():
    original=NormRows([[0.,0,0],[3.,0,0],[2.,0,0],[5.,0,0]],np.ones(4),np.ones(4))
    jac=sparse.csc_matrix(np.arange(24).reshape(12,2));caps=original.caps.copy()
    guarded,derivative,identity=protect_worst(original,jac,1,2)
    assert identity['hard_rows']==3 and identity['baseline_worst_positive_residual']==2.
    np.testing.assert_array_equal(guarded.caps,[1.,3.,3.,1.,1.,1.])
    np.testing.assert_array_equal(guarded.vectors[3:],original.vectors[1:])
    np.testing.assert_array_equal(guarded.caps[3:],original.caps[1:])
    np.testing.assert_array_equal(original.caps,caps)
    np.testing.assert_array_equal(derivative.toarray(),jac.toarray()[[0,1,2,3,4,5,6,7,8,3,4,5,6,7,8,9,10,11]])
    np.testing.assert_array_equal(guarded.residual()[1:3],[0.,-1.])


def test_bound_changes_the_direction_that_trades_geometry_for_dominant_contact():
    # x improves contact but hurts geometry; y repairs geometry independently.
    original=NormRows([[0.,0,0],[3.,0,0],[5.,0,0]],np.ones(3),np.ones(3))
    jac=sparse.csc_matrix([[0,0],[0,0],[0,0],[1,-1],[0,0],[0,0],[-1,0],[0,0],[0,0]])
    plain,_=direction(original,jac,np.zeros(2),-np.ones(2),np.ones(2),.02,hard_rows=1)
    assert plain[0]>.019 and abs(plain[1])<1e-7
    guarded,j,identity=protect_worst(original,jac,1,1)
    delta,info=direction(guarded,j,np.zeros(2),-np.ones(2),np.ones(2),.02,hard_rows=identity['hard_rows'])
    assert delta[0]>.019 and delta[1]>=delta[0]-1e-8
    assert original.residual(jac,delta)[1]<=2.+1e-8
    assert original.residual(jac,delta)[2]<4.-.019
    assert info['protected_norm_rows']==2


def test_passing_geometry_keeps_its_original_cap():
    original=NormRows([[0.,0,0],[.5,0,0]],np.ones(2),np.ones(2))
    guarded,_,identity=protect_worst(original,sparse.csc_matrix((6,1)),1,1)
    assert identity['baseline_worst_positive_residual']==0.
    np.testing.assert_array_equal(guarded.caps,[1.,1.,1.])


@pytest.mark.parametrize('hard,count',[(True,1),(0,1),(1,0),(1,2)])
def test_missing_or_invalid_geometry_blocks_are_rejected(hard,count):
    original=NormRows([[0.,0,0],[1.,0,0]],np.ones(2),np.ones(2))
    with pytest.raises(ValueError):protect_worst(original,sparse.csc_matrix((6,1)),hard,count)


@pytest.mark.parametrize('values,bound',[([],0.),([float('nan')],1.),([1.],-.1),([[1.]],0.)])
def test_decoded_restoration_requires_a_complete_finite_population(values,bound):
    with pytest.raises(ValueError):regression(values,bound)


def test_decoded_proxy_can_expose_a_defect_that_affine_bounds_missed():
    np.testing.assert_allclose(regression([4.382351362980052,3.],4.198894921923313),[.183456441056739,-1.198894921923313])


def guided_fixture(monkeypatch,*,restore=False,hidden_geometry_failure=False):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1))
    rows=NormRows([[0.,0,0],[1.01,0,0],[5.,0,0]],[1.,.9995,1.],[1.,.005,1.])
    jac=sparse.csc_matrix((9,1))
    gaps={0:-.01,1:-.009 if hidden_geometry_failure else -.011,2:-.009}
    witnesses=SimpleNamespace(rows=[{}],gaps=lambda worlds:np.array([gaps[worlds]]))
    monkeypatch.setattr(surface,'model',lambda *a,**kw:(rows,jac,witnesses,dict(conversion=dict(offset_m=[1.]))))
    monkeypatch.setattr(surface,'surface_points',lambda problem,worlds:worlds)
    monkeypatch.setattr(surface,'direction',lambda *a,**kw:(np.array([.01]),dict(status='Solved')))
    guide=SimpleNamespace(residual=lambda worlds:np.array([4. if worlds==0 else 3.]))
    captured=[];original=surface.tighten
    def tighten(system,jac,delta,actual,hard,reserve):
        captured.append((actual.copy(),hard));return original(system,jac,delta,actual,hard,reserve)
    monkeypatch.setattr(surface,'tighten',tighten)
    def evaluate(x,label):
        state=0 if label=='start' else (2 if 'restore' in label else 1)
        return dict(native=np.array([-1.]),geometry=report(depth={0:2.,1:2.2,2:1.8}[state]),worlds=state,
            scene=None,policy=None,digest=None,surface_contact=dict(surface_contacts_pass=False))
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=1 if restore else 0,contact_model=guide)
    return value,result,captured


def test_geometry_proxy_defects_restore_even_if_original_native_and_contacts_pass(monkeypatch):
    value,result,captured=guided_fixture(monkeypatch,restore=True)
    assert np.any(value) and captured[0][1]==3
    np.testing.assert_allclose(captured[0][0],[-1.,-1.,.2,2.3,3.],atol=1e-10)
    assert result['worst_geometry_proxy_bounded_in_proposal']
    assert result['history'][0]['probes'][1]['accepted']


def test_complete_mesh_regression_overrules_a_passing_proxy_guard(monkeypatch):
    value,result,_=guided_fixture(monkeypatch,hidden_geometry_failure=True)
    np.testing.assert_array_equal(value,[0.])
    assert all(not p['accepted'] for p in result['history'][0]['probes'])
