"""Analytic and triangle-query checks for complete separating-plane guidance."""
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_separation_planes import planes,face_planes
from triangle_crossing import audit


def test_complete_surface_bounds_witnesses_and_authored_halfspaces():
    a=np.array([[-2.,0.,0.],[-1.,2.,1.],[-1.,-2.,-1.]]);b=np.array([[2.,0.,0.],[3.,2.,1.],[2.,-2.,-1.]])
    row=planes(a,b,[1.,0.,0.],.1)
    assert row['signed_projection_gap_m']==3. and row['left_witness_vertex']==1 and row['right_witness_vertex']==0
    assert row['left_vertices']==row['right_vertices']==3 and row['clearance_condition_pass']
    assert row['strict_projection_separation'] and row['all_supplied_vertices_considered']
    for vertices,key in ((a,'left_guide_plane'),(b,'right_guide_plane')):
        guide=row[key];assert np.all(vertices@np.array(guide['normal_world'])>=guide['offset_m'])
    assert not row['axis_inferred'] and not row['quality_approved'] and not row['release_approved']


def test_one_unselected_looking_outlier_cannot_disappear_from_bounds():
    a=np.array([[-1.,0.,0.],[-1.,1.,0.],[4.,2.,0.]]);b=np.array([[1.,0.,0.],[2.,1.,0.]])
    row=planes(a,b,[1.,0.,0.],.01)
    assert row['signed_projection_gap_m']==-3. and row['left_witness_vertex']==2
    assert not row['clearance_condition_pass'] and row['left_vertices']==3


def test_rigid_coordinate_change_preserves_gap_and_original_witness_order():
    rng=np.random.default_rng(77);a=rng.normal(size=(131,3));b=rng.normal(size=(89,3))+[7.,0.,0.]
    axis=np.array([1.,0.,0.]);baseline=planes(a,b,axis,.001)
    rotation=Rotation.from_euler('xyz',[23.,-48.,17.],degrees=True).as_matrix();shift=np.array([4.,-20.,11.])
    changed=planes(a@rotation.T+shift,b@rotation.T+shift,axis@rotation.T,.001)
    assert changed['signed_projection_gap_m']==pytest.approx(baseline['signed_projection_gap_m'],abs=1e-13)
    assert changed['left_witness_vertex']==baseline['left_witness_vertex'] and changed['right_witness_vertex']==baseline['right_witness_vertex']


def test_positive_gap_agrees_with_complete_triangle_disjointness():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([1.01,0.,0.])
    row=planes(a.vertices,b.vertices,[1.,0.,0.],.001)
    measured=audit(a.vertices,a.faces,b.vertices,b.faces)
    assert row['clearance_condition_pass'] and measured['candidate_pairs']==0 and not measured['records']


def test_failed_projection_is_not_a_collision_and_zero_gap_is_not_strict_separation():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([0.,4.,0.])
    row=planes(a.vertices,b.vertices,[1.,0.,0.],.001)
    assert not row['clearance_condition_pass'] and not audit(a.vertices,a.faces,b.vertices,b.faces)['records']
    b=a.copy();b.apply_translation([1.,0.,0.]);touch=planes(a.vertices,b.vertices,[1.,0.,0.],0.)
    assert touch['clearance_condition_pass'] and not touch['strict_projection_separation']
    assert audit(a.vertices,a.faces,b.vertices,b.faces)['records']


@pytest.mark.parametrize('fault',['empty-left','empty-right','shape','nan','infinite','axis-zero','axis-scale','axis-shape','axis-nan','negative-clearance','boolean-clearance','infinite-clearance','overflow'])
def test_invalid_or_nonfinite_projection_inputs_reject(fault):
    a=np.array([[0.,0.,0.],[1.,0.,0.]]);b=a+[2.,0.,0.];axis=[1.,0.,0.];clearance=.001
    if fault=='empty-left':a=np.empty((0,3))
    if fault=='empty-right':b=np.empty((0,3))
    if fault=='shape':a=np.zeros((2,2))
    if fault=='nan':a[0,0]=np.nan
    if fault=='infinite':b[0,0]=np.inf
    if fault=='axis-zero':axis=[0.,0.,0.]
    if fault=='axis-scale':axis=[2.,0.,0.]
    if fault=='axis-shape':axis=[1.,0.]
    if fault=='axis-nan':axis=[np.nan,0.,0.]
    if fault=='negative-clearance':clearance=-.001
    if fault=='boolean-clearance':clearance=True
    if fault=='infinite-clearance':clearance=np.inf
    if fault=='overflow':a[:]=[-1e308,0.,0.];b[:]=[1e308,0.,0.]
    with pytest.raises(ValueError):planes(a,b,axis,clearance)


def thin_boxes(offset=.025):
    a=trimesh.creation.box(extents=[.4,.02,.04]);b=a.copy();b.apply_translation([0.,offset,0.])
    rotation=Rotation.from_euler('z',37.,degrees=True).as_matrix()
    a.vertices=np.asarray(a.vertices)@rotation.T;b.vertices=np.asarray(b.vertices)@rotation.T
    return a,b


def test_facet_axis_finds_oblique_separation_hidden_from_all_world_axes():
    a,b=thin_boxes();row=face_planes(a.vertices,b.vertices,.001)
    assert max(row['signed_projection_gaps_m'][:3])<0
    assert row['selected']['signed_projection_gap_m']==pytest.approx(.005,abs=1e-14)
    assert row['candidate_count']==3+sum(row['hull_facet_counts']) and row['candidate_count']==27
    assert row['selected']['clearance_condition_pass'] and row['selected']['axis_inferred']
    assert not row['anatomical_axis_inferred'] and not row['edge_cross_axes_included'] and not row['minimum_translation_certified']
    assert not audit(a.vertices,a.faces,b.vertices,b.faces)['records']
    populations=[a.vertices,b.vertices]
    for index,key in ((row['left_population'],'left_guide_plane'),(row['right_population'],'right_guide_plane')):
        guide=row['selected'][key];assert np.all(populations[index]@np.array(guide['normal_world'])>=guide['offset_m']-1e-14)


def test_overlapping_facet_guidance_is_not_a_collision_or_quality_approval():
    a,b=thin_boxes(.015);row=face_planes(a.vertices,b.vertices,.001)
    assert row['selected']['signed_projection_gap_m']==pytest.approx(-.005,abs=1e-14)
    assert not row['selected']['clearance_condition_pass'] and not row['collision_certified'] and not row['quality_approved']


def test_one_column_workspace_keeps_every_point_and_axis():
    a,b=thin_boxes();full=face_planes(a.vertices,b.vertices,.001)
    tiled=face_planes(a.vertices,b.vertices,.001,workspace_bytes=(len(a.vertices)+len(b.vertices))*8)
    assert tiled['projection_columns_per_batch']==1 and tiled['axes_world']==full['axes_world']
    np.testing.assert_allclose(tiled['signed_projection_gaps_m'],full['signed_projection_gaps_m'],atol=1e-15,rtol=0)
    assert tiled['selected']['signed_projection_gap_m']==pytest.approx(full['selected']['signed_projection_gap_m'],abs=1e-15)


def test_rigid_transform_preserves_oblique_facet_separation():
    a,b=thin_boxes();rotation=Rotation.from_euler('xyz',[17.,-31.,54.],degrees=True).as_matrix();shift=[5.,-7.,2.]
    changed=face_planes(a.vertices@rotation.T+shift,b.vertices@rotation.T+shift,.001)
    assert changed['selected']['signed_projection_gap_m']==pytest.approx(.005,abs=1e-12)


def test_outlier_inside_opponent_cannot_be_omitted_from_facet_projections():
    a=trimesh.creation.box();b=a.copy();a.apply_translation([-1.,0.,0.]);b.apply_translation([1.,0.,0.])
    clear=face_planes(a.vertices,b.vertices,.001);assert clear['selected']['strict_projection_separation']
    changed=face_planes(np.r_[a.vertices,[[1.,0.,0.]]],b.vertices,.001)
    assert changed['population_vertices']==[9,8] and not changed['selected']['strict_projection_separation']


@pytest.mark.parametrize('fault',['too-few','too-many','flat','axes-budget','axes-bool','axes-zero','workspace','workspace-bool'])
def test_invalid_or_incomplete_facet_populations_and_budgets_reject(fault):
    a,b=thin_boxes();first=np.array(a.vertices);options={}
    if fault=='too-few':first=first[:3]
    if fault=='too-many':first=np.tile(first,(4097,1))
    if fault=='flat':first[:,2]=0.
    if fault=='axes-budget':options['maximum_axes']=26
    if fault=='axes-bool':options['maximum_axes']=True
    if fault=='axes-zero':options['maximum_axes']=0
    if fault=='workspace':options['workspace_bytes']=127
    if fault=='workspace-bool':options['workspace_bytes']=True
    with pytest.raises(ValueError):face_planes(first,b.vertices,.001,**options)
