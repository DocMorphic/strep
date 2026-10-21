"""Exact scalar-norm compilation, preserving both signs and all vector axes."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_scene_conic as conic
from native_scene_norms import NormRows


@pytest.mark.parametrize('dense',[False,True])
def test_compiled_membership_equals_original_norms_on_all_axes(monkeypatch,dense):
    captured={}
    def solver(q,c,a,b,cones,settings):
        captured.update(matrix=a,bound=b,cones=cones)
        return SimpleNamespace(solve=lambda:SimpleNamespace(status='MaxIterations',iterations=0))
    backend=SimpleNamespace(__version__=conic.VERSION,DefaultSettings=SimpleNamespace,DefaultSolver=solver,
        NonnegativeConeT=lambda n:SimpleNamespace(kind='linear',dim=n),SecondOrderConeT=lambda n:SimpleNamespace(kind='norm',dim=n))
    monkeypatch.setattr(conic,'solver_module',lambda:backend)
    model=NormRows([[2,0,0],[0,-2,0],[0,0,0],[.1,.2,.3],[.7,1e-30,0]],[2.1,2.2,.2,.25,.6],[.005,.2,1,2,.7])
    j=np.array([[[1,.5],[0,0],[0,0]],[[0,0],[.4,1],[0,0]],[[0,0],[0,0],[1,-.3]],
        [[.2,.1],[.1,.5],[-.5,.2]],[[1,.2],[0,0],[0,0]]])
    derivative=j if dense else sparse.csc_matrix(j.reshape(-1,2))
    _,info=conic.direction(model,derivative,np.zeros(2),-np.ones(2),np.ones(2),.5,hard_rows=2,linear_axis_rows=True)
    description=info['axis_linear_representation']
    assert description['scalar_norm_rows']==3 and description['linear_inequalities']==4
    assert description['trust_box_sign_certified_rows']==2 and description['two_sided_rows']==1
    assert info['active_cones']==2 # Tiny nonzero perpendicular component is retained.
    generator=np.random.default_rng(431);passing=0
    for _ in range(500):
        delta=generator.uniform(-.5,.5,2);t=generator.uniform(0,1)
        raw=model.vectors+np.einsum('rcn,n->rc',j,delta)
        expected=bool(np.all(np.linalg.norm(raw,axis=1)<=model.caps+(np.arange(5)>=2)*model.scales*t))
        slack=captured['bound']-captured['matrix']@np.r_[delta/.5,t]
        offset=0;actual=True
        for cone in captured['cones']:
            block=slack[offset:offset+cone.dim];offset+=cone.dim
            actual &= bool(np.all(block>=0)) if cone.kind=='linear' else bool(block[0]>=np.linalg.norm(block[1:]))
        assert offset==len(slack) and actual==expected
        passing+=expected
    assert 0<passing<500


@pytest.mark.parametrize('sign',[-1.,1.])
def test_actual_solver_keeps_two_sided_hard_bound_and_soft_optimum(sign):
    model=NormRows([[0,0,0],[0,0,-sign*.4]],[.2,0],[1,1])
    j=sparse.csc_matrix([[0],[1],[0],[0],[0],[1]],dtype=float)
    delta,info=conic.direction(model,j,[0.],[-1.],[1.],.5,hard_rows=1,linear_axis_rows=True)
    assert delta is not None and sign*delta[0]==pytest.approx(.2,abs=1e-7)
    assert abs(delta[0])<=.2+1e-8
    assert info['axis_linear_representation']['two_sided_rows']==2
    assert info['active_cones']==0


@pytest.mark.parametrize('choice',[None,1,'true'])
def test_representation_choice_requires_boolean(choice):
    with pytest.raises(ValueError,match='axis-linear representation'):
        conic.direction(None,None,None,None,None,None,linear_axis_rows=choice)


@pytest.mark.parametrize('choice',[None,1,'true',True])
def test_character_choice_rejects_invalid_or_missing_guidance_before_loading(tmp_path,choice):
    from native_mesh_character_fit import fit
    with pytest.raises(ValueError,match='axis-linear|Axis-linear'):
        fit(tmp_path/'missing',tmp_path/'missing-policy',tmp_path/'out',linear_axis_rows=choice)
