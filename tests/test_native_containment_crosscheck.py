from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_containment_crosscheck import crosscheck
from native_containment_crosscheck import penetration, METHOD
from native_containment_crosscheck import _ray_consensus, RAY_DIRECTIONS


@pytest.mark.parametrize('counts,inside,resolved',[
    ([[1,1],[3,1],[1,3]],True,True),([[0,0],[2,2],[4,2]],False,True),
    ([[1,1],[0,0],[1,1]],False,False),([[0,1],[0,0],[0,0]],False,False),
    ([[1,2],[1,1],[1,1]],False,False)])
def test_fixed_ray_parities_require_every_forward_and_backward_vote(counts,inside,resolved):
    class Rays:
        calls=0
        def intersects_location(self,origins,directions,*,multiple_hits):
            assert multiple_hits and origins.shape==directions.shape==(2,3)
            np.testing.assert_array_equal(directions[0],-directions[1])
            np.testing.assert_allclose(np.linalg.norm(directions,axis=1),1)
            counts_here=counts[self.calls];self.calls+=1
            indices=np.repeat([0,1],counts_here)
            return np.empty((len(indices),3)),indices,np.zeros(len(indices),int)
    rays=Rays();actual,complete,observed=_ray_consensus(rays,np.zeros((1,3)))
    assert rays.calls==len(RAY_DIRECTIONS)==3
    assert actual.tolist()==[inside] and complete.tolist()==[resolved] and observed.tolist()==[counts]


def test_random_ray_entry_points_are_never_used_and_query_partition_is_invariant(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Random/default ray containment used')
    monkeypatch.setattr(trimesh.util,'random_generator',forbidden)
    monkeypatch.setattr(trimesh.ray.ray_triangle.RayMeshIntersector,'contains_points',forbidden)
    a=trimesh.creation.box(extents=[2,2,2]);b=trimesh.creation.box();b.apply_translation([3,0,0])
    mesh=trimesh.util.concatenate([a,b])
    points=np.array([[0,.2,.3],[1.2,1.3,0],[1,1,1],[3,.1,.2],[2,.1,.1]])
    whole=crosscheck(mesh.vertices,mesh.faces,points)
    for i,point in enumerate(points):
        single=crosscheck(mesh.vertices,mesh.faces,point[None])
        assert single['states']==[whole['states'][i]]
        for name in ('ray_inside','ray_resolved','ray_hit_counts','signed_distance_m','unsigned_distance_m','winding'):
            np.testing.assert_array_equal(single[name][0],whole[name][i])


def test_unresolved_ray_cannot_be_turned_into_outside_by_signed_distance_or_winding(monkeypatch):
    import native_containment_crosscheck as module
    mesh=trimesh.creation.box()
    def ambiguous(intersector,points):
        return np.zeros(len(points),bool),np.zeros(len(points),bool),np.tile([[0,1],[0,0],[0,0]],(len(points),1,1))
    monkeypatch.setattr(module,'_ray_consensus',ambiguous)
    result=crosscheck(mesh.vertices,mesh.faces,[[1,0,0]])
    assert result['signed_distance_m'][0]<0 and abs(result['winding'][0])<1e-5
    assert result['states']==['unresolved'] and not result['all_resolved']


def test_retained_transition_ray_disagreement_is_reproducible_without_random_retry(monkeypatch):
    import json
    fixture=json.loads((Path(__file__).parent/'fixtures/containment-ray-ambiguity.json').read_text())
    def forbidden(*args,**kwargs):raise AssertionError('Retained ambiguity attempted random retry')
    monkeypatch.setattr(trimesh.util,'random_generator',forbidden)
    before=None
    for _ in range(3):
        result=crosscheck(fixture['vertices'],fixture['faces'],[fixture['point']],surface_tolerance_m=1e-8)
        assert result['states']==['unresolved'] and not result['ray_resolved'][0]
        assert result['unsigned_distance_m'][0]==pytest.approx(4.1768168875048427e-7,rel=1e-10)
        evidence={name:result[name].tobytes() for name in ('signed_distance_m','unsigned_distance_m','ray_inside','ray_resolved','ray_hit_counts','winding')}
        if before is not None:assert evidence==before
        before=evidence


@pytest.mark.parametrize('transformed',[False,True])
def test_inside_outside_and_surface_have_independent_geometric_expectations(transformed):
    mesh=trimesh.creation.box(extents=[2,2,2]);points=np.array([[0,0,0],[1.5,0,0],[1,0,0.]])
    if transformed:
        rotation=Rotation.from_euler('xyz',[22,31,17],degrees=True).as_matrix();shift=np.array([4,-2,3])
        mesh.vertices=mesh.vertices@rotation.T+shift;points=points@rotation.T+shift
    r=crosscheck(mesh.vertices,mesh.faces,points)
    assert r['states']==['inside','outside','near-surface'] and not r['all_resolved']
    np.testing.assert_allclose(r['unsigned_distance_m'],[1,.5,0],atol=1e-14)
    np.testing.assert_allclose(r['winding'][:2],[1,0],atol=1e-14)
    assert not r['self_intersection_checked'] and not r['quality_approved']


def test_disconnected_closed_components_do_not_fill_the_gap():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([2,0,0]);mesh=trimesh.util.concatenate([a,b])
    r=crosscheck(mesh.vertices,mesh.faces,[[0,0,0],[1,0,0],[2,0,0]])
    assert r['states']==['inside','outside','inside'] and r['all_resolved']


def test_overlapping_positive_shells_are_unresolved_not_assumed_single_volume():
    a=trimesh.creation.box(extents=[2,2,2]);b=a.copy();b.apply_translation([.5,0,0]);mesh=trimesh.util.concatenate([a,b])
    assert mesh.is_volume
    r=crosscheck(mesh.vertices,mesh.faces,[[.2,.1,.1]])
    assert r['winding'][0]==pytest.approx(2.) and r['states']==['unresolved']


def test_positive_total_volume_with_crossing_inward_shell_exposes_signed_disagreement():
    a=trimesh.creation.box(extents=[2,2,2]);b=trimesh.creation.box(extents=[1.5]*3);b.invert();b.apply_translation([.8,0,0])
    mesh=trimesh.util.concatenate([a,b]);assert mesh.is_volume
    r=crosscheck(mesh.vertices,mesh.faces,[[.9,.1,.1]])
    assert r['signed_distance_m'][0]==pytest.approx(.1) and not r['ray_inside'][0]
    assert r['winding'][0]==pytest.approx(0.,abs=1e-14) and r['states']==['unresolved']


@pytest.mark.parametrize('fault',['nan-point','too-many-points','empty-points','bad-face','open-mesh','bad-tolerance','bool-tolerance','bad-winding-tolerance'])
def test_invalid_or_unbounded_requests_reject(fault):
    m=trimesh.creation.box();points=np.zeros((1,3));faces=m.faces;kwargs={}
    if fault=='nan-point':points[0,0]=np.nan
    elif fault=='too-many-points':points=np.zeros((33,3))
    elif fault=='empty-points':points=np.zeros((0,3))
    elif fault=='bad-face':faces=faces.copy();faces[0,0]=len(m.vertices)
    elif fault=='open-mesh':faces=faces[:-1]
    elif fault=='bad-tolerance':kwargs['surface_tolerance_m']=.01
    elif fault=='bool-tolerance':kwargs['surface_tolerance_m']=True
    else:kwargs['winding_tolerance']=float('nan')
    with pytest.raises(ValueError):crosscheck(m.vertices,faces,points,**kwargs)


@pytest.mark.parametrize('batch',[1,7,32])
@pytest.mark.parametrize('shift',[[0.,0.,0.],[100.,-50.,30.]])
def test_measured_false_outside_cannot_be_counted_as_zero_penetration(batch,shift):
    a=trimesh.creation.box(extents=[2,2,2]);b=a.copy();b.apply_translation([.75,.25,.2])
    mesh=trimesh.util.concatenate([a,b]);mesh.apply_translation(shift)
    point=np.array([[-.26,.1,.2]])+shift
    # Analytically inside A and outside B, but the nearest face belongs to B.
    assert mesh.is_volume
    assert trimesh.proximity.signed_distance(mesh,point)[0]==pytest.approx(-.01)
    assert mesh.contains(point)[0]
    result=penetration(np.vstack([point,point+[10,0,0]]),mesh.vertices,mesh.faces,query_batch_size=batch)
    assert result['containment_method']==METHOD and not result['available']
    assert result['vertices_checked']==2 and result['queried_vertices']==1
    assert 'max_depth_m' not in result and 'vertices_over_tolerance' not in result
    assert result['unresolved_vertices'][0]['vertex']==0
    assert result['unresolved_vertices'][0]['state']=='unresolved'
    assert result['unresolved_vertices'][0]['winding']==pytest.approx(1.)


def test_isolated_boxes_keep_analytic_depths_and_nested_shells_are_unresolved():
    a=trimesh.creation.box(extents=[2,2,2]);b=a.copy();b.apply_translation([.75,.25,.2])
    point=[[-.26,.1,.2]]
    inside=penetration(point,a.vertices,a.faces);outside=penetration(point,b.vertices,b.faces)
    assert inside['available'] and inside['max_depth_m']==pytest.approx(.74)
    assert outside['available'] and outside['max_depth_m']==0.
    nested=trimesh.util.concatenate([a,trimesh.creation.box()])
    result=penetration([[.1,.1,.1]],nested.vertices,nested.faces)
    assert not result['available'] and result['unresolved_vertices'][0]['winding']==pytest.approx(2.)


def test_surface_contact_is_unavailable_and_no_query_point_is_silently_removed():
    m=trimesh.creation.box(extents=[2,2,2])
    result=penetration([[0,0,0],[1,0,0],[1,1,1],[20,20,20]],m.vertices,m.faces,query_batch_size=1)
    assert result['vertices_checked']==4 and result['queried_vertices']==3
    assert not result['available'] and 'max_depth_m' not in result
    assert [(r['vertex'],r['state']) for r in result['unresolved_vertices']]==[(1,'near-surface'),(2,'near-surface')]


def test_broadphase_retains_the_whole_declared_near_surface_band():
    m=trimesh.creation.box(extents=[2,2,2])
    result=penetration([[1+5e-5,0,0]],m.vertices,m.faces,surface_tolerance_m=1e-4)
    assert result['queried_vertices']==1 and not result['available']
    assert result['unresolved_vertices'][0]['state']=='near-surface'


@pytest.mark.parametrize('fault',['reversed','open','degenerate','invalid-batch'])
def test_invalid_mesh_or_query_cannot_pass_even_when_all_points_are_far(fault):
    m=trimesh.creation.box();kwargs={}
    if fault=='reversed':m.invert()
    elif fault=='open':m.update_faces(np.arange(len(m.faces)-1))
    elif fault=='degenerate':m.vertices[0]=m.vertices[1]
    else:kwargs['query_batch_size']=True
    with pytest.raises(ValueError):penetration([[50,50,50]],m.vertices,m.faces,**kwargs)
