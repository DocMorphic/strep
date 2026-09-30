import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sampled_surface_guard import SampledSurfaceGuard, snapshot, compare, topology
from triangle_crossing import audit
from convex_partner_surface import penetration
from hand_norm_proposal import backtrack
import iterated_hand_norm


def observed(left, right, stamp=0.):
    return dict(time_s=stamp, surface=audit(left.vertices,left.faces,right.vertices,right.faces),
        depths=[penetration(a.vertices,b.vertices,b.faces) for a,b in [(left,right),(right,left)]])


def test_crossings_with_zero_vertex_depth_reject_a_solver_improvement():
    a=trimesh.creation.box(extents=[4,.5,.5]); b=trimesh.creation.box(extents=[.5,4,1])
    def vertices(x): return [[a.vertices,b.vertices+[0,0,3*(1-x[0])]]]
    guard=SampledSurfaceGuard([a.faces,b.faces],[8,8],[0.],vertices,[0.])
    result=guard([1.])
    assert not result['passed'] and result['samples'][0]['new_proper_pairs']
    assert result['samples'][0]['depth_increases_m']==[0.,0.]
    def exact(x): return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.array([.02-.01*x[0]]))
    candidate,records=backtrack(exact,[0.],[1.],exact([0.]),acceptance_guard=guard)
    assert records[0]['reason']=='geometry regression' and records[-1]['accepted']
    assert candidate[0]<1. and guard(candidate)['passed']
    assert not guard(candidate)['collision_free_certified']


def test_containment_without_triangle_crossings_also_rejects():
    a=trimesh.creation.box(extents=[.5,.5,.5]);b=trimesh.creation.box(extents=[2,2,2])
    guard=SampledSurfaceGuard([a.faces,b.faces],[8,8],[0.],lambda x:[[a.vertices+[3*(1-x[0]),0,0],b.vertices]],[0.])
    row=guard([1.])['samples'][0]
    assert row['proper_counts']==[0,0] and not row['passed'] and row['depth_increases_m'][0]>.5


def test_same_count_different_crossing_pairs_is_a_regression():
    a=trimesh.creation.box(extents=[4,.5,.5]);b=trimesh.creation.box(extents=[.5,4,1])
    meshes=topology([a.faces,b.faces],[8,8]); baseline=snapshot(meshes,[observed(a,b)])
    candidate=copy.deepcopy(baseline)
    pair=candidate['samples'][0]['proper'][0]
    candidates={(i,j) for i in range(len(a.faces)) for j in range(len(b.faces))}-set(map(tuple,candidate['samples'][0]['proper']))
    candidate['samples'][0]['proper'][0]=list(sorted(candidates)[0])
    result=compare(baseline,candidate)
    assert not result['passed'] and result['samples'][0]['new_proper_pairs']
    assert result['samples'][0]['proper_counts'][0]==result['samples'][0]['proper_counts'][1]


def test_new_uncertainty_and_degenerate_faces_cannot_masquerade_as_clearance():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([3,0,0])
    base=snapshot(topology([a.faces,b.faces],[8,8]),[observed(a,b)])
    candidate=copy.deepcopy(base);candidate['samples'][0]['uncertain']=[[0,0]]
    assert not compare(base,candidate)['passed']
    candidate=copy.deepcopy(base);candidate['samples'][0]['degenerate'][0]=[0]
    assert not compare(base,candidate)['passed']


def test_missing_clock_topology_or_vertex_observations_fail_closed():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([3,0,0])
    meshes=topology([a.faces,b.faces],[8,8]);row=observed(a,b);base=snapshot(meshes,[row])
    for edit in ['clock','topology','tolerance','missing']:
        other=copy.deepcopy(base)
        if edit=='clock':other['samples'][0]['time_s']=1.
        if edit=='topology':other['topology'][0]['sha256']='changed'
        if edit=='tolerance':other['samples'][0]['tolerance_m']=.1
        if edit=='missing':other['samples']=[]
        with pytest.raises(ValueError,match='Fixed'):compare(base,other)
    row['depths'][0]['vertices_checked']=7
    with pytest.raises(ValueError,match='complete'):snapshot(meshes,[row])


def test_no_baseline_rebase_and_decoded_meshes_bypass_cache():
    a=trimesh.creation.box(extents=[.5,.5,.5]);b=trimesh.creation.box(extents=[2,2,2])
    # Original containment can improve, but cannot get worse after an earlier call.
    provider=lambda x:[[a.vertices+[x[0],0,0],b.vertices]]
    guard=SampledSurfaceGuard([a.faces,b.faces],[8,8],[0.],provider,[.9])
    original=copy.deepcopy(guard.original)
    assert guard([1.])['passed']
    assert not guard([0.])['passed']
    assert guard.original==original
    assert not guard.fresh(provider([0.]))['passed']


def test_guard_does_not_override_numerical_failures_or_run_for_them():
    calls=[]
    def exact(x): return dict(vectors=np.array([[1.+x[0],0,0]]),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.array([.02-.01*x[0]]))
    candidate,records=backtrack(exact,[0.],[.1],exact([0.]),acceptance_guard=lambda p:calls.append(p))
    assert candidate is None and not calls and all(not r['accepted'] for r in records)


@pytest.mark.parametrize('result',[None,{},dict(passed=1),dict(passed='yes')])
def test_guard_must_explicitly_return_boolean(result):
    def exact(x): return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.array([.02-.01*x[0]]))
    with pytest.raises(ValueError,match='explicit boolean'):
        backtrack(exact,[0.],[.1],exact([0.]),acceptance_guard=lambda p:result)


def test_iterated_solver_keeps_rejected_geometry_out_of_next_iteration(monkeypatch):
    def exact(x): return dict(vectors=np.zeros((1,3)),caps=np.ones(1),scales=np.ones(1),margins=np.ones(1),depths=np.array([.02-.01*x[0]]))
    monkeypatch.setattr(iterated_hand_norm,'direction',lambda m,t,s:(np.array([.2]),dict(status='Solved')))
    calls=[]
    def guard(p):
        calls.append(p[0]);return dict(passed=bool(p[0]<=.1))
    point,report=iterated_hand_norm.solve(exact,exact,[0.],None,iterations=2,trusts=(.2,),acceptance_guard=guard)
    assert point[0]==.1 and report['geometry_guard']['passed']
    assert report['history'][0]['attempts'][0]['trials'][0]['reason']=='geometry regression'
    assert not report['history'][1]['accepted']
    assert calls[0]==0 and calls[-1]==.1
