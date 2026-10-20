"""Index-query rejection preserves every old overlapping pair and record."""
from collections import Counter
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
import triangle_crossing as crossing


def reference(left,right,tolerance):
    counts=Counter();records=[];pairs=0
    # Exhaustive box pairs, independently of either the R-tree or envelope.
    for i,a in enumerate(left):
        low=a.min(0)-tolerance;high=a.max(0)+tolerance
        for j,b in enumerate(right):
            if np.all(high>=b.min(0)) and np.all(low<=b.max(0)):
                value=crossing.classify(a,b,tolerance);counts[value['kind']]+=1;pairs+=1
                if value['kind']!='disjoint':records.append(dict(left_triangle=i,right_triangle=j,**value))
    return pairs,dict(counts),records


@pytest.mark.parametrize('scale,translation',[(1.,0.),(.001,0.),(1000.,1e6),(1.,-1e8)])
def test_every_box_pair_record_and_order_matches_exhaustive_reference(scale,translation):
    rng=np.random.default_rng(411)
    left=rng.uniform(-2,2,(35,3,3))*scale+translation
    right=rng.uniform(-.2,.2,(7,3,3))*scale+translation
    left[0]=left[1]=right[0];left[2]=right[1,0];left[3]+=20*scale
    tolerance=1e-8*scale
    result=crossing.audit(left.reshape(-1,3),np.arange(left.size//3).reshape(-1,3),right.reshape(-1,3),np.arange(right.size//3).reshape(-1,3),tolerance)
    pairs,counts,records=reference(left,right,tolerance)
    assert (result['candidate_pairs'],result['counts'],result['records'])==(pairs,counts,records)
    assert 2 in result['degenerate_faces'][0] and not result['collision_free_certified']


def test_distant_faces_skip_queries_without_losing_progress_or_degeneracy(monkeypatch):
    a=np.array([[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]])
    left=np.repeat(a[None],4001,axis=0);left[1:2001]+=100;left[2001:]-=100;left[3000]=100
    right=np.array([[[0.,0.,-1.],[0.,0.,1.],[0.,.5,0.]]])
    real=crossing.index.Index;queries=[]
    class Spy:
        def __init__(self,*args,**kwargs):self.tree=real(*args,**kwargs)
        def intersection(self,bounds):queries.append(bounds);return self.tree.intersection(bounds)
        def close(self):self.tree.close()
    monkeypatch.setattr(crossing.index,'Index',Spy);progress=[]
    result=crossing.audit(left.reshape(-1,3),np.arange(len(left)*3).reshape(-1,3),right[0],[[0,1,2]],progress=progress.append)
    assert not result['whole_bounds_rejected'] and len(queries)==1 and result['candidate_pairs']==1
    assert result['records'][0]['left_triangle']==0 and result['degenerate_faces']==[[3000],[]]
    assert [p['left_faces_processed'] for p in progress]==[2000,4000]


def test_expanded_box_boundary_is_kept_including_one_ulp_neighbours():
    eps=1e-8;a=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    for z in (np.nextafter(eps,0),eps,np.nextafter(eps,np.inf)):
        # Far triangle keeps whole-mesh bounds overlapping even at >eps.
        left=np.stack([a,a+[10.,0.,1.]])
        right=(a+[0.,0.,z])[None]
        result=crossing.audit(left.reshape(-1,3),[[0,1,2],[3,4,5]],right[0],[[0,1,2]],eps)
        pairs,counts,records=reference(left,right,eps)
        assert (result['candidate_pairs'],result['counts'],result['records'])==(pairs,counts,records)
