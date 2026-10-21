from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_self_surface import audit
from triangle_crossing import classify
from native_mesh_self_regression import compare_self_surfaces
from native_self_surface import METHOD
import copy

A=np.array([[-2.,-1.,0.],[2.,-1.,0.],[0.,2.,0.]])
B=np.array([[0.,0.,-1.],[0.,0.,1.],[0.,1.,0.]])


def test_closed_box_valid_adjacencies_are_not_reported_as_crossings():
    m=trimesh.creation.box();r=audit(m.vertices,m.faces)
    assert not r['records'] and not r['degenerate_faces']
    assert r['complete_triangle_population'] and not r['self_collision_free_certified']
    assert sum(r['shared_vertex_counts'].values())==r['candidate_pairs']


@pytest.mark.parametrize('transformed',[False,True])
def test_transverse_crossing_is_visited_once_and_has_analytic_length(transformed):
    v=np.vstack([A,B])
    if transformed:v=v@Rotation.from_euler('xyz',[17,31,22],degrees=True).as_matrix().T+[5,2,-3]
    r=audit(v,[[0,1,2],[3,4,5]])
    assert r['candidate_pairs']==1 and r['has_observed_transverse_crossings']
    assert r['records'][0]['overlap_length_m']==pytest.approx(1.)


def test_shared_vertex_does_not_hide_a_crossing_away_from_the_vertex():
    v=np.vstack([A,[[0,0,-1.],[0,0,1.]]]);r=audit(v,[[0,1,2],[0,3,4]])
    assert r['records'][0]['kind']=='proper_crossing' and r['records'][0]['shared_vertices']==1


def test_folded_coplanar_neighbors_are_kept_as_ambiguous_area_overlap():
    v=np.array([[0,0,0],[2,0,0],[0,2,0],[.2,1.,0.]])
    r=audit(v,[[0,1,2],[1,0,3]])
    assert r['records'][0]['kind']=='coplanar_or_near_parallel_overlap'
    assert r['records'][0]['shared_vertices']==2 and r['has_ambiguous_surface_records']


def test_nesting_and_degeneracy_do_not_become_collision_certificates():
    a=trimesh.creation.box(extents=[2]*3);b=trimesh.creation.box(extents=[.5]*3);m=trimesh.util.concatenate([a,b])
    r=audit(m.vertices,m.faces);assert not r['records'] and not r['self_collision_free_certified']
    r=audit(np.vstack([A,[[7,7,7]]]),[[0,1,2],[3,3,3]])
    assert r['degenerate_faces']==[1] and r['complete_triangle_population']


def test_spatial_index_matches_complete_bruteforce_flagged_pairs():
    v=np.random.default_rng(572).normal(size=(36,3));f=np.arange(36).reshape(-1,3);tri=v[f]
    expected={(i,j) for i in range(12) for j in range(i+1,12) if classify(tri[i],tri[j],1e-7)['kind'] in ('proper_crossing','coplanar_or_near_parallel_overlap','boundary_or_near_contact')}
    r=audit(v,f);assert {(x['left_triangle'],x['right_triangle']) for x in r['records']}==expected


@pytest.mark.parametrize('budget',['pairs','records'])
def test_budget_exhaustion_never_returns_a_complete_truncated_report(budget):
    v=np.vstack([A,A*.5,A*.25]);f=np.arange(9).reshape(-1,3)
    kwargs={'maximum_pairs':1} if budget=='pairs' else {'maximum_records':1}
    with pytest.raises(ValueError,match='budget exhausted'):audit(v,f,**kwargs)


@pytest.mark.parametrize('fault',['nan','float-faces','bad-index','empty','bool-tolerance','large-tolerance','bad-pairs','bad-records'])
def test_invalid_inputs_reject(fault):
    v=A.copy();f=np.array([[0,1,2]]);kwargs={}
    if fault=='nan':v[0,0]=np.nan
    elif fault=='float-faces':f=f.astype(float)
    elif fault=='bad-index':f[0,0]=3
    elif fault=='empty':f=np.zeros((0,3),int)
    elif fault=='bool-tolerance':kwargs['tolerance_m']=True
    elif fault=='large-tolerance':kwargs['tolerance_m']=.01
    elif fault=='bad-pairs':kwargs['maximum_pairs']=0
    else:kwargs['maximum_records']=True
    with pytest.raises(ValueError):audit(v,f,**kwargs)


def comparison_report(vertices,faces):
    own=audit(vertices,faces)
    return dict(schema='strep-native-mesh-prop-geometry-result-v1',all_policy_samples_evaluated=True,
        self_surface_method=METHOD,complete_clock_s=[0.],times_s=[0.],sample_indices=[0],
        actor_faces={'A':len(faces)},prop_faces={},samples=[dict(index=0,time_s=0.,
            self_surfaces=[dict(kind='actor',name='A',audit=own)])])


def test_same_crossing_count_cannot_hide_a_new_intersecting_triangle_pair():
    faces=np.arange(9).reshape(-1,3)
    original=comparison_report(np.vstack([A,B,B+[5,0,0]]),faces)
    changed=comparison_report(np.vstack([A,B+[5,0,0],B]),faces)
    result=compare_self_surfaces(original,changed)
    assert not result['passed'] and len(result['regressions'])==1
    assert result['regressions'][0]['triangles']==[0,2]
    assert result['regressions'][0]['reason']=='new-crossing'


def test_retained_crossing_interval_cannot_grow_and_removal_is_not_release_approval():
    faces=np.arange(6).reshape(-1,3);original=comparison_report(np.vstack([A,B]),faces)
    bigger=B.copy();bigger[2,1]=1.5
    result=compare_self_surfaces(original,comparison_report(np.vstack([A,bigger]),faces))
    assert not result['passed'] and result['regressions'][0]['reason']=='crossing-interval-increased'
    cleared=compare_self_surfaces(original,comparison_report(np.vstack([A,B+[5,0,0]]),faces))
    assert cleared['passed'] and not cleared['self_collision_free_certified'] and not cleared['release_approved']
    assert compare_self_surfaces(original,original)['passed']


@pytest.mark.parametrize('fault',['coplanar','degenerate'])
def test_unresolved_self_geometry_never_passes_even_when_unchanged(fault):
    vertices=np.vstack([A,A*.5 if fault=='coplanar' else np.zeros((3,3))])
    original=comparison_report(vertices,np.arange(6).reshape(-1,3))
    result=compare_self_surfaces(original,original)
    assert not result['passed'] and result['unavailable']


@pytest.mark.parametrize('fault',['missing-method','partial','missing-entity','topology','tolerance','missing-crossing','duplicate-crossing','clock'])
def test_incomplete_changed_or_unversioned_self_evidence_rejects(fault):
    original=comparison_report(np.vstack([A,B]),np.arange(6).reshape(-1,3));changed=copy.deepcopy(original)
    own=changed['samples'][0]['self_surfaces'][0]['audit']
    if fault=='missing-method':changed.pop('self_surface_method')
    elif fault=='partial':changed['all_policy_samples_evaluated']=False
    elif fault=='missing-entity':changed['samples'][0]['self_surfaces']=[]
    elif fault=='topology':own['faces_sha256']='0'*64
    elif fault=='tolerance':own['tolerance_m']=1e-8
    elif fault=='missing-crossing':own['records']=[]
    elif fault=='duplicate-crossing':own['records']*=2
    else:changed['sample_indices']=[1]
    with pytest.raises(ValueError):compare_self_surfaces(original,changed)
