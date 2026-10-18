from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_triangle_relation_rows as module
from native_support_gap import triangle_support_gaps


def sample():
    rng=np.random.default_rng(328);a=rng.normal(size=(6,3))*.1;b=rng.normal(size=(7,3))*.1+[1,0,0]
    ta=np.array([[0,1,2],[1,2,3],[0,1,2]]);tb=np.array([[0,1,2],[2,3,4],[0,1,2]]);n=np.array([1.,0,0])
    ja=rng.normal(size=a.shape+(5,));jb=rng.normal(size=b.shape+(5,));return a,b,ta,tb,n,ja,jb


def test_every_occurrence_is_mapped_to_exact_relation_and_original_margin():
    a,b,ta,tb,n,ja,jb=sample();r=module.triangle_relation_rows(a,b,ta,tb,n,left_jacobian=ja,right_jacobian=jb)
    expected={(int(u),int(v)) for l,rr in zip(ta,tb) for u in l for v in rr}
    assert set(map(tuple,r['edges']))==expected and r['occurrence_to_relation'].shape==(3,3,3)
    for p in range(len(ta)):
        for i in range(3):
            for j in range(3):assert tuple(r['edges'][r['occurrence_to_relation'][p,i,j]])==(ta[p,i],tb[p,j])
    old=(triangle_support_gaps(a[ta],b[tb],np.tile(n,(3,1)))['projected_gap_m']-2e-5)/.01
    assert r['canonical_pair_margins'].tobytes()==old.tobytes() and np.all(r['margins'][r['occurrence_to_relation']].min(axis=(1,2))<=old)
    assert r['report']['comparison_occurrences']==27 and r['report']['repeated_occurrences_coalesced']>0


def test_shared_columns_match_nonlinear_position_differences():
    a,b,ta,tb,n,ja,jb=sample();r=module.triangle_relation_rows(a,b,ta,tb,n,left_jacobian=ja,right_jacobian=jb)
    for c in range(5):
        h=1e-6;plus=module.triangle_relation_rows(a+h*ja[...,c],b+h*jb[...,c],ta,tb,n);minus=module.triangle_relation_rows(a-h*ja[...,c],b-h*jb[...,c],ta,tb,n)
        np.testing.assert_allclose(r['jacobian'][:,c],(plus['margins']-minus['margins'])/(2*h),atol=5e-8,rtol=1e-7)


def test_shared_self_translation_chains_cancel():
    a,b,ta,tb,n,ja,jb=sample();ja[:]=0;jb[:]=0;ja[...,0]=[1,0,0];jb[...,0]=[1,0,0]
    r=module.triangle_relation_rows(a,b,ta,tb,n,left_jacobian=ja,right_jacobian=jb);assert not np.any(r['jacobian'])


def test_last_vertex_and_last_column_are_present():
    a,b,ta,tb,n,ja,jb=sample();jb=np.zeros(b.shape+(768,));jb[4,0,-1]=1
    r=module.triangle_relation_rows(a,b,ta,tb,n,right_jacobian=jb);assert r['jacobian'].shape==(len(r['edges']),768)
    np.testing.assert_array_equal(r['jacobian'][:,-1],np.where(r['edges'][:,1]==4,100.,0.))


def test_no_cross_relations_are_added_between_disjoint_triangles():
    a,b,ta,tb,n,ja,jb=sample();ta=np.array([[0,1,2],[3,4,5]]);tb=np.array([[0,1,2],[3,4,5]])
    r=module.triangle_relation_rows(a,b,ta,tb,n);assert len(r['edges'])==18 and (0,5) not in set(map(tuple,r['edges']))


def test_complete_budget_rejection_precedes_kernel(monkeypatch):
    a,b,ta,tb,n,ja,jb=sample();monkeypatch.setattr(module,'triangle_support_gaps',lambda *a,**k:pytest.fail('kernel before budget'))
    with pytest.raises(ValueError,match='budget'):module.triangle_relation_rows(a,b,ta,tb,n,left_jacobian=ja,right_jacobian=jb,maximum_array_bytes=1)


def test_inputs_are_immutable():
    args=sample();before=[a.copy() for a in args];module.triangle_relation_rows(*args[:5],left_jacobian=args[5],right_jacobian=args[6])
    for a,b in zip(args,before):np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('kind',['bad_triangle','negative','too_large','column_mismatch','zero_columns','nan','bool_points','nonunit','bool_gap','zero_scale','bad_budget'])
def test_invalid_complete_inputs_reject(kind):
    a,b,ta,tb,n,ja,jb=sample();kw={}
    if kind=='bad_triangle':ta=ta[:,:2]
    elif kind=='negative':ta[0,0]=-1
    elif kind=='too_large':tb[0,0]=len(b)
    elif kind=='column_mismatch':jb=jb[...,:2]
    elif kind=='zero_columns':ja=ja[...,:0]
    elif kind=='nan':ja[0,0,0]=np.nan
    elif kind=='bool_points':a=a.astype(bool)
    elif kind=='nonunit':n*=2
    elif kind=='bool_gap':kw['minimum_gap_m']=True
    elif kind=='zero_scale':kw['length_scale_m']=0
    elif kind=='bad_budget':kw['maximum_array_bytes']=True
    with pytest.raises(ValueError):module.triangle_relation_rows(a,b,ta,tb,n,left_jacobian=ja,right_jacobian=jb,**kw)
