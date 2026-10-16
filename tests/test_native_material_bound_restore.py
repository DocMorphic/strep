from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_material_bound_restore as module
from native_scene_norms import NormRows
from native_partner_material_vectors import insert_guards


def example():
    base=NormRows([[0,0,0],[.3,0,0]],[1,0],[1,1]);j=sparse.csr_matrix([[1],[0],[0],[-1],[0],[0]])
    return base,j,np.array([[.010001,0,0]]),sparse.csr_matrix([[1],[0],[0]])


def test_infeasible_material_start_restores_with_inward_reserve_and_keeps_soft_rows():
    base,j,v,vj=example()
    with pytest.raises(ValueError):insert_guards(base,j,1,v,vj,[.01])
    model,jac,meta=module.assemble(base,j,1,v,vj,[.01]);step,info=module.direction(model,jac,[0],[-1],[1],.001,hard_rows=meta['hard_rows'])
    assert step is not None and -1.51e-6<step[0]<-1.49e-6 and info['affine_hard_rows_pass']
    assert np.linalg.norm(v+np.asarray(vj@step).reshape(1,3))<.01
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(model,key)[[0,2]],getattr(base,key))
    assert meta['initial_reference_material_failures']==1 and meta['material_search_reserve_m']==5e-7 and info['soft_rows_retained_not_optimized']==1


def test_full_vector_correction_handles_tangential_nonlinearity_with_margin():
    x=np.array([0.,.03]);v=np.array([[.01+x[0],x[1]**2,0]]);vj=sparse.csr_matrix([[1,0],[0,2*x[1]],[0,0]])
    base=NormRows([[0,0,0]],[1],[1]);model,j,meta=module.assemble(base,sparse.csr_matrix((3,2)),1,v,vj,[.01]);delta,info=module.direction(model,j,x,[-1,-1],[1,1],.001,hard_rows=meta['hard_rows'])
    assert delta is not None and info['affine_hard_rows_pass'];y=x+delta
    assert np.linalg.norm([.01+y[0],y[1]**2,0])<=.01


@pytest.mark.parametrize('fault',['base','shape','nan','caps','reserve','budget'])
def test_invalid_assembly_never_rebases_or_truncates(fault):
    base,j,v,vj=example();limits=[.01];kw={}
    if fault=='base':base.vectors[0,0]=2
    elif fault=='shape':vj=sparse.csr_matrix((2,1))
    elif fault=='nan':v[0,0]=np.nan
    elif fault=='caps':limits=[1e-9]
    elif fault=='reserve':kw['reserve_m']=-1
    else:kw['maximum_nonzeros']=1
    with pytest.raises(ValueError):module.assemble(base,j,1,v,vj,limits,**kw)


def test_fixed_failed_material_row_has_no_returned_direction():
    base,j,v,_=example();model,jac,meta=module.assemble(base,j,1,v,sparse.csr_matrix((3,1)),[.01]);step,info=module.direction(model,jac,[0],[-1],[1],.001,hard_rows=meta['hard_rows'])
    assert step is None and info['status']=='FixedProtectedConflict'


@pytest.mark.parametrize('status,point',[('NumericalError',-.002),('Solved',0.)])
def test_status_and_complete_postcheck_both_gate_selection(monkeypatch,status,point):
    actual=module.solver_module();solver=SimpleNamespace(**{key:getattr(actual,key) for key in ('__version__','DefaultSettings','NonnegativeConeT','SecondOrderConeT')},DefaultSolver=lambda *args:SimpleNamespace(solve=lambda:SimpleNamespace(status=status,iterations=1,x=[point])))
    monkeypatch.setattr(module,'solver_module',lambda:solver);base,j,v,vj=example();model,jac,meta=module.assemble(base,j,1,v,vj,[.01]);step,info=module.direction(model,jac,[0],[-1],[1],.001,hard_rows=meta['hard_rows'])
    assert step is None and info['status']==status


@pytest.mark.parametrize('fault',['trust','box','shape','budget'])
def test_invalid_restore_controls_and_sparse_population_reject(fault):
    base,j,v,vj=example();model,jac,meta=module.assemble(base,j,1,v,vj,[.01]);value=[0];trust=.001
    if fault=='trust':trust=True
    elif fault=='box':value=[2]
    elif fault=='shape':jac=jac[:2]
    else:jac=sparse.csr_matrix((np.ones(6000001),np.zeros(6000001,int),[0,6000001]+[6000001]*(model.vectors.size-1)),shape=(model.vectors.size,1))
    with pytest.raises(ValueError):module.direction(model,jac,value,[-1],[1],trust,hard_rows=meta['hard_rows'])


def test_nonfinite_norm_postcheck_never_becomes_a_serialized_pass(monkeypatch):
    actual=module.solver_module();solver=SimpleNamespace(**{key:getattr(actual,key) for key in ('__version__','DefaultSettings','NonnegativeConeT','SecondOrderConeT')},DefaultSolver=lambda *args:SimpleNamespace(solve=lambda:SimpleNamespace(status='Solved',iterations=1,x=[1.])))
    monkeypatch.setattr(module,'solver_module',lambda:solver);model=NormRows([[0,0,0]],[1],[1])
    with np.errstate(over='ignore',invalid='ignore'):
        step,info=module.direction(model,sparse.csr_matrix([[1e308],[0],[0]]),[0],[-1],[1],.001,hard_rows=1)
    assert step is None and info['nonfinite_affine_rows'] and not info['affine_hard_rows_pass']
