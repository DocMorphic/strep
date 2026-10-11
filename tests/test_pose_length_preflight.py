"""Numerical exclusions, editable-pivot invariants and non-exclusion scope."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pose_length_preflight import preflight
import bounded_pose_ik as ik


def target(n,p,tolerance=.03):
    m=np.eye(4);m[:3,3]=p
    return dict(node=n,world_matrix=m,position_tolerance_m=tolerance,rotation_tolerance_degrees=5)


def chain():
    local=np.tile(np.eye(4),(4,1,1));local[1,0,3]=1;local[2,0,3]=1;local[3,0,3]=1
    return local,np.array([-1,0,1,2])


def test_endpoint_rotations_cannot_change_direct_edge_length():
    local,parents=chain();r=preflight(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],[1,2])
    assert r['position_targets_excluded'] and r['pairs'][0]['invariant_distance_m']==1
    assert r['pairs'][0]['minimum_max_endpoint_error_m']==pytest.approx(.4)
    assert not r['non_exclusion_proves_feasibility'] and not r['quality_approved']


def test_common_ancestor_and_both_endpoint_edits_preserve_sibling_distance():
    local,parents=chain();parents[2]=0
    r=preflight(local,parents,[target(1,[0,0,0]),target(2,[2,0,0])],[0,1,2])
    assert r['position_targets_excluded'] and r['pairs'][0]['invariant_distance_m']==0


def test_editable_third_pivot_prevents_false_fixed_distance_exclusion():
    local,parents=chain()
    r=preflight(local,parents,[target(0,[0,0,0]),target(3,[1,0,0])],[1])
    assert not r['pairs'] and r['skipped_variable_distance_pairs']==1
    assert not r['position_targets_excluded']


def test_actual_rotation_keeps_every_assessed_pair_distance():
    local,parents=chain();goals=[target(n,[n,0,0]) for n in range(4)]
    edited=[0,2,3];r=preflight(local,parents,goals,edited);changed=local.copy()
    for n in edited:changed[n,:3,:3]=Rotation.from_euler('xyz',[39,-22,17],degrees=True).as_matrix()
    world=ik.world_matrices(changed,parents,ik.hierarchy_order(parents))
    for p in r['pairs']:
        a,b=p['nodes'];assert np.linalg.norm(world[a,:3,3]-world[b,:3,3])==pytest.approx(p['invariant_distance_m'])


def test_duplicate_node_targets_can_be_mutually_incompatible():
    local,parents=chain();r=preflight(local,parents,[target(2,[0,0,0]),target(2,[1,0,0])],[0,1,2])
    assert r['position_targets_excluded'] and r['pairs'][0]['invariant_distance_m']==0


def test_tolerance_sum_and_roundoff_guard_do_not_create_false_exclusion():
    local,parents=chain()
    for distance in (1.,1.059,1.06,1.06000000001):
        r=preflight(local,parents,[target(0,[0,0,0]),target(1,[distance,0,0])],[0,1])
        assert not r['position_targets_excluded']
    assert preflight(local,parents,[target(0,[0,0,0]),target(1,[1.061,0,0])],[0,1])['position_targets_excluded']


def test_nonrigid_drift_is_unassessed_rather_than_certified():
    local,parents=chain();local[0,0,0]+=1e-7
    r=preflight(local,parents,[target(0,[0,0,0]),target(1,[2,0,0])],[0])
    assert r['status']=='not_assessed_nonrigid_drift' and not r['pairs'] and not r['position_targets_excluded']


def test_fitter_skips_proven_impossibility_and_keeps_source_exactly(monkeypatch):
    local,parents=chain();old=local.copy()
    def forbidden(*a,**kw):raise AssertionError('Nonlinear solver should not run')
    monkeypatch.setattr(ik,'least_squares',forbidden)
    fitted,r=ik.solve(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],{0:25,1:25,2:25})
    np.testing.assert_array_equal(fitted,old);np.testing.assert_array_equal(local,old)
    assert r['evaluations']==0 and not r['solver_success'] and not r['targets_matched']
    assert r['preflight']['position_targets_excluded'] and all(v==0 for v in r['max_edit_degrees'])


def test_rejected_source_copy_preserves_signed_zero_storage():
    local,parents=chain();local[:,0,1]=-0.;before=local.tobytes()
    fitted,r=ik.solve(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],{1:25,2:25})
    assert r['preflight']['position_targets_excluded'] and fitted.tobytes()==before and local.tobytes()==before


def test_non_excluded_targets_still_invoke_and_reach_the_real_solver():
    local,parents=chain();goals=[target(0,[0,0,0]),target(1,[np.cos(.1),np.sin(.1),0],.0005)]
    for goal in goals:goal['world_matrix'][:3,:3]=Rotation.from_euler('z',.1).as_matrix()
    fitted,r=ik.solve(local,parents,goals,{0:30})
    assert r['evaluations']>0 and r['targets_matched'] and not r['preflight']['position_targets_excluded']
    np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3])


def test_norm_refinement_does_not_retry_proven_impossibility(monkeypatch):
    import bounded_pose_ball_ik as ball
    def forbidden(*a,**kw):raise AssertionError('Refinement must skip excluded targets')
    monkeypatch.setattr(ik,'least_squares',forbidden);monkeypatch.setattr(ball,'minimize',forbidden)
    local,parents=chain();fitted,r=ball.solve(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],{1:25,2:25})
    np.testing.assert_array_equal(fitted,local)
    assert r['norm_refinement']['skipped_by_position_preflight'] and not r['norm_refinement']['accepted']
    assert r['norm_refinement']['evaluations']==0 and r['box_initializer']['evaluations']==0


def test_continuation_keeps_projected_previous_fallback_when_targets_excluded(monkeypatch):
    import bounded_pose_continuation as continuation
    def forbidden(*a,**kw):raise AssertionError('Continuation solve must skip excluded targets')
    monkeypatch.setattr(continuation,'minimize',forbidden)
    local,parents=chain();previous=local.copy();previous[1,:3,:3]=Rotation.from_euler('z',70,degrees=True).as_matrix()
    fitted,r=continuation.solve(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],{1:25,2:25},previous)
    assert r['evaluations']==0 and not r['optimized_candidate_accepted'] and r['preflight']['position_targets_excluded']
    np.testing.assert_array_equal(r['rotation_vectors_rad'],r['initial_rotation_vectors_rad'])
    np.testing.assert_array_equal(fitted[:,:3,3],local[:,:3,3]);assert max(r['max_edit_degrees'])<=25


def test_assessed_distances_are_invariant_for_every_edit_subset_in_a_fork():
    local,parents=chain();parents=np.array([-1,0,0,1]);local[2,:3,3]=[0,1,0]
    world=ik.world_matrices(local,parents,ik.hierarchy_order(parents));goals=[target(i,w[:3,3]) for i,w in enumerate(world)]
    for mask in range(16):
        edits=[i for i in range(4) if mask&(1<<i)];r=preflight(local,parents,goals,edits);changed=local.copy()
        for i in edits:changed[i,:3,:3]=Rotation.from_euler('xyz',[17+i*11,-9+i*3,35-i*7],degrees=True).as_matrix()
        world=ik.world_matrices(changed,parents,ik.hierarchy_order(parents))
        for pair in r['pairs']:
            a,b=pair['nodes'];assert np.linalg.norm(world[a,:3,3]-world[b,:3,3])==pytest.approx(pair['invariant_distance_m'])


@pytest.mark.parametrize('budget',[0,True,1001])
def test_exclusion_does_not_bypass_solver_budget_validation(budget):
    local,parents=chain()
    with pytest.raises(ValueError,match='evaluations'):ik.solve(local,parents,[target(1,[1,0,0]),target(2,[1.2,0,0])],{1:25},budget)


@pytest.mark.parametrize('fault',['cycle','bad-parent','nonfinite','affine','bool-node','missing-field','bad-target','negative-tolerance','duplicate-edits'])
def test_bad_or_ambiguous_inputs_reject(fault):
    local,parents=chain();goals=[target(0,[0,0,0]),target(1,[2,0,0])];edited=[0]
    if fault=='cycle':parents[0]=3
    if fault=='bad-parent':parents[0]=9
    if fault=='nonfinite':local[0,0,3]=np.nan
    if fault=='affine':local[0,3,0]=1
    if fault=='bool-node':goals[0]['node']=True
    if fault=='missing-field':del goals[0]['rotation_tolerance_degrees']
    if fault=='bad-target':goals[0]['world_matrix']=np.eye(3)
    if fault=='negative-tolerance':goals[0]['position_tolerance_m']=-1
    if fault=='duplicate-edits':edited=[0,0]
    with pytest.raises(ValueError):preflight(local,parents,goals,edited)
