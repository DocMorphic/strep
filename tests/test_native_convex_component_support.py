"""Whole vertex populations, topology rejection and geometric guide meaning."""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_convex_component_support import support_pair


def box(center=(0.,0.,0.)):
    points=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float)/2
    faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
        [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]])
    return points+center,faces


@pytest.mark.parametrize('x,expected',[(1.5,.5),(1.,0.),(.75,-.25),(0.,-1.)])
def test_full_component_support_gap_for_separation_touching_and_volume_overlap(x,expected):
    a,af=box();b,bf=box((x,0,0))
    axis,gaps,r=support_pair(a,af,b,bf)
    assert r['maximum_signed_support_gap_m']==expected
    assert r['minimum_complete_pair_gap_m']==expected and gaps.shape==(8,8)
    np.testing.assert_array_equal(gaps,(a[:,None]-b[None,:])@axis)
    assert r['complete_vertex_pair_rows']==64 and r['complete_signed_axis_budget']==696
    assert r['tested_signed_axis_count']+2*len(r['skipped_raw_axis_indices'])==696
    assert not r['certified_collision_predicate'] and not r['original_mesh_gate_replaced']


def test_world_axis_aabb_overlap_does_not_hide_diagonal_separation():
    a,af=box();b,bf=box();rot=Rotation.from_euler('z',45,degrees=True).as_matrix()
    # Both oriented boxes share a diagonal orientation. Their axis-aligned
    # bounds overlap, while their complete projected shapes are separated.
    a=a@rot.T;b=b@rot.T+np.array([.8,.8,0])
    assert np.all(np.minimum(a.max(0),b.max(0))-np.maximum(a.min(0),b.min(0))>0)
    axis,gaps,r=support_pair(a,af,b,bf)
    assert r['maximum_signed_support_gap_m']>.13 and np.min(gaps)>.13


def test_consistent_reversed_winding_is_supported_without_anatomical_normal_inference():
    a,af=box();b,bf=box((1.5,0,0))
    _,_,original=support_pair(a,af,b,bf)
    _,_,reversed_result=support_pair(a,af[:,::-1],b,bf[:,::-1])
    assert original['maximum_signed_support_gap_m']==reversed_result['maximum_signed_support_gap_m']==.5
    assert reversed_result['left_component']['winding']=='negative'


def test_edge_cross_axis_can_separate_boxes_when_all_face_normal_axes_overlap():
    p,f=box()
    angles=[[159.01061112179457,16.576464449961804,12.844360968539235],
            [-61.62790956147272,178.9139973220568,112.79511368880753]]
    a=(p*np.array([1.6,.7,.4]))@Rotation.from_euler('xyz',angles[0],degrees=True).as_matrix().T
    b=(p*np.array([1.4,.6,.3]))@Rotation.from_euler('xyz',angles[1],degrees=True).as_matrix().T
    b+=np.array([-.029252266638654767,-.4780529087715064,.7653139555982253])
    face_axes=[]
    for points in (a,b):
        triangles=points[f];normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        normal/=np.linalg.norm(normal,axis=1)[:,None];face_axes.extend(normal);face_axes.extend(-normal)
    axes=np.array(face_axes)
    assert ((a@axes.T).min(0)-(b@axes.T).max(0)).max()<-.23
    _,gaps,r=support_pair(a,f,b,f)
    assert r['selected_axis_identity']['kind']=='edge-cross'
    assert r['maximum_signed_support_gap_m']>.058 and gaps.min()>.058


def test_reindexing_and_rigid_rotation_keep_complete_support_gap():
    a,af=box();b,bf=box((1.5,0,0));rot=Rotation.from_euler('xyz',[16,27,-9],degrees=True).as_matrix()
    order=np.array([7,2,5,0,1,6,3,4]);inverse=np.argsort(order)
    _,gaps,r=support_pair((a@rot.T)[order],inverse[af],(b@rot.T)[order],inverse[bf])
    assert abs(r['maximum_signed_support_gap_m']-.5)<1e-14 and gaps.shape==(8,8)


@pytest.mark.parametrize('fault',['missing-face','reverse-one-face','duplicate-face','missing-vertex','unreferenced-vertex',
    'nonconvex','flat','nan','bool-faces','disconnected','axis-budget','pair-budget','bool-budget'])
def test_incomplete_invalid_or_unbudgeted_components_never_become_guides(fault):
    a,af=box();b,bf=box((1.5,0,0));kw={}
    if fault=='missing-face':af=af[:-1]
    elif fault=='reverse-one-face':af[0]=af[0,::-1]
    elif fault=='duplicate-face':af=np.vstack([af,af[0]])
    elif fault=='missing-vertex':a=a[:-1]
    elif fault=='unreferenced-vertex':a=np.vstack([a,[0,0,0]])
    elif fault=='nonconvex':a[6]=[0,0,0]
    elif fault=='flat':a[:,2]=0
    elif fault=='nan':a[0,0]=np.nan
    elif fault=='bool-faces':af=af.astype(bool)
    elif fault=='disconnected':a=np.vstack([a,a+3]);af=np.vstack([af,af+8])
    elif fault=='axis-budget':kw['maximum_candidate_axes']=695
    elif fault=='pair-budget':kw['maximum_vertex_pairs']=63
    else:kw['maximum_vertex_pairs']=True
    with pytest.raises(ValueError):support_pair(a,af,b,bf,**kw)


def test_diagnostics_do_not_modify_input_geometry():
    a,af=box();b,bf=box((1.5,0,0));copies=[x.copy() for x in (a,af,b,bf)]
    axis,gaps,r=support_pair(a,af,b,bf);axis.fill(5);gaps.fill(5);r['left_vertex_order'].clear()
    for actual,expected in zip((a,af,b,bf),copies):np.testing.assert_array_equal(actual,expected)
