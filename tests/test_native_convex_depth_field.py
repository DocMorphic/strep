from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_convex_depth_field import ConvexDepthField


def cube():
    m=trimesh.creation.box(extents=[2.,2.,2.]);return m.vertices.copy(),m.faces.copy()


def test_all_values_match_independent_box_depth_and_keep_every_duplicate():
    v,f=cube();field=ConvexDepthField(v,f);p=np.vstack([np.random.default_rng(17).uniform(-2,2,(100,3)),np.zeros((3,3))]);r=field.evaluate(p,temperature_m=1e-5)
    np.testing.assert_allclose(r['exact_depth_m'],np.maximum(0,1-np.abs(p).max(axis=1)),atol=2e-15);assert len(r['exact_depth_m'])==103 and r['report']['all_points_facets_columns_retained'] and not r['report']['collision_certified']


def test_upper_bound_and_error_bound_include_inside_outside_edges_corners_and_ties():
    v,f=cube();p=np.array([[0.,0,0],[.7,.2,0],[1.,0,0],[1.,1.,0],[1.,1.,1.],[1.00001,0,0],[2.,2.,2.]])
    for tau in [1e-7,1e-5,1e-3]:
        r=ConvexDepthField(v,f).evaluate(p,temperature_m=tau);gap=r['upper_depth_m']-r['exact_depth_m'];assert np.all(gap>=-2e-15) and np.all(gap<=r['report']['real_arithmetic_upper_error_bound_m']+2e-15)


def test_every_supplied_column_matches_independent_point_perturbations():
    v,f=cube();p=np.array([[.7,.1,.2],[1.00002,0,0],[.4,.3,.2]]);j=np.random.default_rng(43).normal(size=(3,3,9));field=ConvexDepthField(v,f);r=field.evaluate(p,point_jacobian=j,temperature_m=1e-4);h=1e-8
    for c in range(9):
        finite=(field.evaluate(p+h*j[...,c],temperature_m=1e-4)['upper_depth_m']-field.evaluate(p-h*j[...,c],temperature_m=1e-4)['upper_depth_m'])/(2*h)
        np.testing.assert_allclose(finite,r['upper_jacobian'][:,c],atol=5e-8,rtol=3e-6)


def test_final_of_768_columns_is_retained():
    v,f=cube();p=np.array([[.7,0,0]]);j=np.zeros((1,3,768));j[0,0,-1]=2.;r=ConvexDepthField(v,f).evaluate(p,point_jacobian=j)
    assert r['upper_jacobian'].shape==(1,768) and np.count_nonzero(r['upper_jacobian'][0,:-1])==0;np.testing.assert_allclose(r['upper_jacobian'][0,-1],-2.)


def test_rigid_reexpression_preserves_depth_and_full_jacobian():
    v,f=cube();p=np.array([[.8,.2,.1],[1.1,0,0]]);j=np.random.default_rng(17).normal(size=(2,3,7));R=Rotation.from_rotvec([.2,-.4,.1]).as_matrix();t=np.array([2.,3.,4.]);a=ConvexDepthField(v,f).evaluate(p,point_jacobian=j);b=ConvexDepthField(v@R.T+t,f).evaluate(p@R.T+t,point_jacobian=np.einsum('ij,vjc->vic',R,j))
    for name in ['exact_depth_m','upper_depth_m','upper_jacobian']:np.testing.assert_allclose(a[name],b[name],atol=2e-14)


def test_mesh_point_and_derivative_arrays_are_not_modified():
    v,f=cube();p=np.array([[.7,0,0]]);j=np.ones((1,3,2));original=[a.copy() for a in [v,f,p,j]];ConvexDepthField(v,f).evaluate(p,point_jacobian=j)
    for a,b in zip(original,[v,f,p,j]):np.testing.assert_array_equal(a,b)


def test_complete_chunk_partition_preserves_each_point_result():
    v,f=cube();field=ConvexDepthField(v,f);p=np.random.default_rng(17).uniform(-2,2,(57,3));j=np.random.default_rng(43).normal(size=(57,3,5));full=field.evaluate(p,point_jacobian=j)
    parts=[field.evaluate(p[i:i+7],point_jacobian=j[i:i+7]) for i in range(0,57,7)]
    for name in ['exact_depth_m','upper_depth_m','upper_jacobian']:np.testing.assert_allclose(full[name],np.concatenate([r[name] for r in parts]),atol=1e-14)


@pytest.mark.parametrize('kind',['open','inward','degenerate','concave','disconnected'])
def test_invalid_targets_are_rejected_without_repair_or_hull_substitution(kind):
    v,f=cube()
    if kind=='open':f=f[:-1]
    elif kind=='inward':f=f[:,::-1]
    elif kind=='degenerate':f[0,1]=f[0,0]
    elif kind=='concave':v[0]=[0.,0.,0.]
    else:v=np.vstack([v,v+[4.,0,0]]);f=np.vstack([f,f+8])
    with pytest.raises(ValueError):ConvexDepthField(v,f)


@pytest.mark.parametrize('bad',[np.nan,np.inf,-np.inf])
def test_nonfinite_points_or_derivatives_are_rejected(bad):
    v,f=cube();field=ConvexDepthField(v,f);p=np.array([[.5,0,0]]);j=np.zeros((1,3,2));j[0,2,-1]=bad
    with pytest.raises(ValueError,match='finite'):field.evaluate(p,point_jacobian=j)
    p[0,0]=bad
    with pytest.raises(ValueError,match='finite'):field.evaluate(p)


@pytest.mark.parametrize('bad',['shape','empty','boolean','complex','columns','matching_rows','point_bound'])
def test_incomplete_or_nonreal_point_inputs_are_rejected(bad):
    v,f=cube();field=ConvexDepthField(v,f);p=np.array([[.5,0,0]]);j=np.zeros((1,3,2))
    if bad=='shape':p=p[:,:2]
    elif bad=='empty':p=p[:0]
    elif bad=='boolean':p=p.astype(bool)
    elif bad=='complex':j=j.astype(complex)
    elif bad=='columns':j=np.zeros((1,3,769))
    elif bad=='matching_rows':j=np.zeros((2,3,2))
    else:p[0,0]=1e7
    with pytest.raises(ValueError):field.evaluate(p,point_jacobian=j)


@pytest.mark.parametrize('option',[dict(maximum_working_bytes=1),dict(maximum_jacobian_bytes=1),dict(maximum_working_bytes=True),dict(temperature_m=0.),dict(temperature_m=np.nan)])
def test_complete_evaluation_budget_and_temperature_rejections(option):
    v,f=cube()
    with pytest.raises(ValueError):ConvexDepthField(v,f).evaluate(np.array([[.5,0,0]]),point_jacobian=np.zeros((1,3,2)),**option)


def test_constructor_budget_and_invalid_final_face_are_rejected():
    v,f=cube()
    with pytest.raises(ValueError):ConvexDepthField(v,f,maximum_working_bytes=1)
    f[-1,-1]=len(v)
    with pytest.raises(ValueError):ConvexDepthField(v,f)


def test_nonbox_convex_mesh_matches_independent_triangle_signed_distance():
    cloud=np.array([[0.,0,0],[2.,0,0],[0.,1.5,0],[0.,0,1.],[-.3,.2,.4],[.5,.3,1.2]])
    mesh=trimesh.convex.convex_hull(cloud);field=ConvexDepthField(mesh.vertices,mesh.faces);p=np.random.default_rng(43).uniform([-.4,-.2,-.2],[2.1,1.6,1.4],(73,3));r=field.evaluate(p)
    expected=np.maximum(0,trimesh.proximity.signed_distance(mesh,p));np.testing.assert_allclose(r['exact_depth_m'],expected,atol=2e-14)
    assert r['report']['facets']==len(mesh.faces) and field.report['all_vertex_facet_checks']==len(mesh.vertices)*len(mesh.faces)


def test_all_reordered_facets_remain_and_produce_equivalent_depths():
    v,f=cube();p=np.array([[.8,.1,.2],[1.,1.,0.],[-.2,-.6,-.4]]);a=ConvexDepthField(v,f).evaluate(p,temperature_m=1e-4);b=ConvexDepthField(v,f[::-1]).evaluate(p,temperature_m=1e-4)
    for name in ['exact_depth_m','upper_depth_m','upper_point_gradient']:np.testing.assert_allclose(a[name],b[name],atol=1e-14)
    assert a['report']['facets']==b['report']['facets']==12
