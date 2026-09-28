from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conic_root_descent import affine_constraints,cone_rows,direction
from test_root_release_block import make_problem


def test_cone_signs_and_trust_scaling_match_affine_vector():
    vector=np.array([.02,-.01]);jac=np.array([[1.,2.],[3.,4.]]);z=np.array([.4,-.7]);trust=.001
    a,b=cone_rows(vector,jac,.04,.01,trust)
    np.testing.assert_allclose(b-a@z,np.r_[.04,vector+jac@(z*trust)]/.01)


def test_all_conic_margins_reproduce_original_exact_constraints():
    p=make_problem();x=p.initial[np.ix_(p.frames,p.free)].ravel();c,j,cones=affine_constraints(p,x)
    margins=np.r_[c,[(t['cap']**2-t['vector']@t['vector'])/t['scale']**2 for t in cones]]
    np.testing.assert_allclose(margins,p.evaluate(x)[2],atol=1e-12,rtol=0)
    d=np.random.default_rng(63).normal(size=len(x));d/=np.linalg.norm(d)
    minus=affine_constraints(p,x-1e-6*d,False);plus=affine_constraints(p,x+1e-6*d,False);base=affine_constraints(p,x,False)
    np.testing.assert_allclose((plus[0]-minus[0])/2e-6,base[1]@d,atol=1e-7)
    for old,m,a in zip(base[2],minus[2],plus[2]):np.testing.assert_allclose((a['vector']-m['vector'])/2e-6,old['jacobian']@d,atol=1e-7)


def test_known_root_problem_has_norm_feasible_descent_proposal():
    p=make_problem();x=p.initial[np.ix_(p.frames,p.free)].ravel();delta,record=direction(p,x,.01)
    assert delta is not None and record['predicted_objective_change']<0
    assert record['predicted_norm_max_excess']<1e-7 and record['predicted_linear_minimum']>=-1e-7
