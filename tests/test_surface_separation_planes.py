"""Analytic and triangle-query checks for complete separating-plane guidance."""
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_separation_planes import planes
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
