"""Independent relation expansion and original projected-gap equivalence."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pair_gap_groups import MAXIMUM_PAIR_REFERENCES,MAXIMUM_VERTEX_ID,triangle_gap_groups
from native_region_support_gap import region_support_gap
from native_support_gap import triangle_support_gaps

def relation(a,b):return {(int(u),int(v)) for av,bv in zip(a,b) for u in av for v in bv}
def covered(result):return {(u,v) for g in result['groups'] for u in g['left_vertices'] for v in g['right_vertices']}
def verify(a,b,result):
    assert result['pair_references']==len(a)
    assert covered(result)==relation(a,b)
    assert result['vertex_relations']==len(relation(a,b))==sum(len(g['left_vertices'])*len(g['right_vertices']) for g in result['groups'])

def test_disconnected_triangles_keep_two_groups_without_false_cross_pairs():
    a=np.array([[0,1,2],[3,4,5]]);b=a.copy();r=triangle_gap_groups(a,b);verify(a,b,r)
    assert len(r['groups'])==2 and r['grouped_by']=='left'
    av=np.array([[0.,0,0],[.1,1,0],[0.,0,1],[1.,3,0],[1.1,4,0],[1.,3,1]]);bv=av+[.2,0,0];n=np.array([1.,0,0])
    assert region_support_gap(av,bv,n)['projected_gap_m']<0
    assert all(region_support_gap(av[list(g['left_vertices'])],bv[list(g['right_vertices'])],n)['projected_gap_m']>0 for g in r['groups'])

def test_complete_biclique_collapses_references_without_losing_edges():
    a=np.array([[0,1,2],[3,4,5],[0,1,2],[3,4,5]]);b=np.array([[10,11,12],[10,11,12],[13,14,15],[13,14,15]])
    r=triangle_gap_groups(a,b);verify(a,b,r);assert len(r['groups'])==1 and r['vertex_relations']==36

def test_shared_vertex_does_not_add_neighbor_comparisons():
    a=np.array([[0,1,2],[2,3,4]]);b=np.array([[0,1,2],[3,4,5]])
    r=triangle_gap_groups(a,b);verify(a,b,r);assert (0,3) not in covered(r) and (3,0) not in covered(r)

@pytest.mark.parametrize('seed',range(8))
def test_random_shared_references_preserve_all_projected_conditions(seed):
    rng=np.random.default_rng(seed);a=rng.integers(0,17,size=(41,3));b=rng.integers(0,23,size=(41,3));r=triangle_gap_groups(a,b);verify(a,b,r)
    av=rng.normal(size=(17,3));bv=rng.normal(size=(23,3));n=rng.normal(size=3);n/=np.linalg.norm(n)
    pairs=triangle_support_gaps(av[a],bv[b],np.tile(n,(len(a),1)))['projected_gap_m']
    groups=[region_support_gap(av[list(g['left_vertices'])],bv[list(g['right_vertices'])],n)['projected_gap_m'] for g in r['groups']]
    assert min(groups)==pytest.approx(float(pairs.min()),abs=3e-15,rel=0)
    for threshold in [-3.,0.,.00002,3.]:assert bool(np.all(pairs>=threshold))==bool(np.all(np.array(groups)>=threshold))

def test_duplicate_and_degenerate_index_triples_preserve_input_identity():
    a=np.array([[1,1,1],[1,1,1]]);b=np.array([[2,2,2],[2,2,2]])
    r=triangle_gap_groups(a,b);verify(a,b,r);assert r['vertex_relations']==1 and len(r['groups'])==1
    single=triangle_gap_groups(a[:1],b[:1]);assert single['groups']==r['groups'] and single['pair_references_sha256']!=r['pair_references_sha256']

def test_canonical_groups_are_order_and_winding_independent_but_digest_binds_input():
    a=np.array([[0,1,2],[2,3,4]]);b=np.array([[4,5,6],[1,2,3]])
    r=triangle_gap_groups(a,b);changed=triangle_gap_groups(a[::-1,::-1],b[::-1,::-1]);assert r['groups']==changed['groups'] and r['pair_references_sha256']!=changed['pair_references_sha256']
    swapped=triangle_gap_groups(b,a);assert covered(swapped)=={(v,u) for u,v in relation(a,b)}

def test_integer_dtypes_and_sparse_largest_id_are_lossless():
    a=np.array([[0,1,MAXIMUM_VERTEX_ID]],dtype=np.uint32);b=np.array([[4,5,6]],dtype=np.int64);r=triangle_gap_groups(a,b);verify(a,b,r)
    assert MAXIMUM_VERTEX_ID in r['groups'][0]['left_vertices']

def test_complete_maximum_reference_budget_is_not_truncated():
    a=np.arange(MAXIMUM_PAIR_REFERENCES*3,dtype=np.int64).reshape(-1,3);b=a.copy();r=triangle_gap_groups(a,b);verify(a,b,r)
    assert len(r['groups'])==MAXIMUM_PAIR_REFERENCES and r['vertex_relations']==9*MAXIMUM_PAIR_REFERENCES
    with pytest.raises(ValueError):triangle_gap_groups(np.r_[a,a[:1]],np.r_[b,b[:1]])

@pytest.mark.parametrize('kind',['empty','shape','mismatch','negative','large','float','complex','bool','string','nan','uint-overflow'])
def test_invalid_references_reject(kind):
    a=np.array([[0,1,2],[3,4,5]]);b=a.copy()
    if kind=='empty':a=a[:0];b=b[:0]
    elif kind=='shape':a=a.ravel()
    elif kind=='mismatch':b=b[:1]
    elif kind=='negative':a[0,0]=-1
    elif kind=='large':a[0,0]=MAXIMUM_VERTEX_ID+1
    elif kind=='float':a=a.astype(float)
    elif kind=='complex':a=a.astype(complex)
    elif kind=='bool':a=a.astype(bool)
    elif kind=='string':a=a.astype(str)
    elif kind=='nan':a=a.astype(float);a[0,0]=np.nan
    else:a=a.astype(np.uint64);a[0,0]=2**64-1
    with pytest.raises(ValueError):triangle_gap_groups(a,b)
