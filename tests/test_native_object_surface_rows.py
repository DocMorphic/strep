"""Whole triangles, enclosure, declared poses and conservative primitive guides."""
from pathlib import Path
import copy, sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_scene_geometry import closed_fixture, policy
from test_native_scene_contacts import setup
from native_scene_contacts import SceneContacts
from native_partner_surface_rows import build
from native_scene_geometry import evaluate
from native_surface_model import geometry_score, improved, model, include_times
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_object_surface_rows import support_extent
from object_geometry import Geometry
from strep import save, sha256

SHAPES = [dict(shape='sphere', radius_m=.1), dict(shape='box', size_m=[.2,.2,.2]),
    dict(shape='cylinder', radius_m=.1, height_m=.2)]


def fixture(tmp_path, shape, offset=(0,0,0)):
    _, path, spec = closed_fixture(tmp_path); scene = SceneContacts(spec, tmp_path)
    center = scene.actors['A']['rig'].vertices(scene.actors['A']['sampler'].sample(1.)).mean(0)
    spec['objects']['item'] = dict(geometry=dict(schema='strep-object-geometry-v1', **shape),
        keyframes=[dict(time_s=0., translation_m=(center + offset).tolist(), rotation_xyzw=[0,0,0,1])])
    save(path,spec); return path, spec, SceneContacts(spec,tmp_path), policy(path)


@pytest.mark.parametrize('shape', SHAPES)
def test_enclosed_object_has_escape_rows_even_when_all_surface_depths_zero(tmp_path, shape):
    path,spec,scene,p = fixture(tmp_path,shape)
    rows=build(scene,p,sha256(path)); report,_=evaluate(scene,p,sha256(path))
    assert rows.report['objects_included'] and len(rows.report['samples'])==3
    sample=report['samples'][1]['actor_objects'][0]
    assert sample['maximum_depth_upper_m']<1e-6 and sample['containment']['status']=='inside'
    assert any(r['kind']=='primitive-center-enclosure' and r['time_s']==1. for r in rows.rows)
    assert geometry_score(report)[0]>=shape.get('radius_m',.1)/.005
    assert not report['sampled_conditions_pass']
    assert (rows.gaps()<0).all()
    for row in rows.rows:
        assert abs(np.linalg.norm(row['normal_world'])-1)<1e-12
        assert sum(row['left']['weights'])==pytest.approx(1.)
    with pytest.raises(ValueError,match='resource budget'):build(scene,p,sha256(path),maximum_rows=1)


@pytest.mark.parametrize('shape', SHAPES)
def test_face_interior_witnesses_catch_object_when_all_vertices_miss(tmp_path,shape):
    path,spec,scene,p=fixture(tmp_path,shape,offset=(.2,0,0))
    a=scene.actors['A']; vertices=a['rig'].vertices(a['sampler'].sample(1.))
    spec['objects']['item']['keyframes'][0]['translation_m'][0]=float(vertices[:,0].max())
    save(path,spec);scene=SceneContacts(spec,tmp_path);p=policy(path)
    rows=build(scene,p,sha256(path)); indices=[i for i,r in enumerate(rows.rows) if r['kind']=='primitive-triangle' and r['time_s']==1.]
    assert indices and min(rows.gaps()[indices]) < -.09
    a=scene.actors['A']; vertices=a['rig'].vertices(a['sampler'].sample(1.))
    pos,rot=scene.object_poses('item',np.array([1.]))
    assert (scene.objects['item']['geometry'].distance_gradient(vertices,pos[0],rot[0])[0]>=0).all()
    assert all(rows.rows[i]['depth_upper_m']>=rows.rows[i]['depth_lower_m'] for i in indices)
    if shape['shape']=='sphere': assert any(not rows.rows[i]['normal_defined'] for i in indices)


@pytest.mark.parametrize('shape', SHAPES)
def test_support_planes_bound_rotated_primitive_surface(shape):
    g=Geometry.parse(dict(schema='strep-object-geometry-v1',**shape))
    r=Rotation.from_euler('xyz',[31,57,19],degrees=True).as_matrix()
    rng=np.random.default_rng(19)
    for normal in rng.normal(size=(30,3)):
        normal/=np.linalg.norm(normal); local=normal@r; extent=support_extent(g,normal,r)
        if g.shape=='sphere': point=g.dimensions[0]*local
        elif g.shape=='box': point=np.sign(local)*np.asarray(g.dimensions)/2
        else:
            radius,height=g.dimensions; point=np.zeros(3)
            point[[0,2]]=radius*local[[0,2]]/np.linalg.norm(local[[0,2]])
            point[1]=np.sign(local[1])*height/2
        assert (point@r.T)@normal==pytest.approx(extent,abs=1e-12)


def test_moving_rotated_objects_and_all_actor_object_pairs_are_queried(tmp_path):
    path,spec,scene,p=fixture(tmp_path,SHAPES[1],offset=(.2,0,0))
    spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m']=[4.,0,0]
    spec['objects']['other']=copy.deepcopy(spec['objects']['item'])
    key=copy.deepcopy(spec['objects']['item']['keyframes'][0]);key['time_s']=2.
    key['translation_m'][0]+=1.;key['rotation_xyzw']=Rotation.from_euler('y',60,degrees=True).as_quat().tolist()
    spec['objects']['item']['keyframes'].append(key);save(path,spec)
    scene=SceneContacts(spec,tmp_path);p=policy(path);rows=build(scene,p,sha256(path))
    assert all(len(s['actor_objects'])==4 for s in rows.report['samples'])
    for row in rows.rows:
        if row['kind'].startswith('primitive-'):
            pos,rot=scene.object_poses(row['object'],np.array([row['time_s']]))
            n=np.array(row['normal_world']);g=scene.objects[row['object']]['geometry']
            assert row['constant_m']==pytest.approx(n@pos[0]+support_extent(g,n,rot[0]),abs=1e-12)


def test_unavailable_containment_is_rejected_without_partial_model(tmp_path):
    _,rig,reader,spec=setup(tmp_path)
    spec['objects']['item']=dict(geometry=dict(schema='strep-object-geometry-v1',**SHAPES[0]),
        keyframes=[dict(time_s=0.,translation_m=rig.vertices(reader.sample(1.)).mean(0).tolist(),rotation_xyzw=[0,0,0,1])])
    path=tmp_path/'contacts.json';save(path,spec);scene=SceneContacts(spec,tmp_path);p=policy(path)
    with pytest.raises(ValueError,match='containment unavailable'):build(scene,p,sha256(path))
    report,_=evaluate(scene,p,sha256(path))
    with pytest.raises(ValueError,match='containment unavailable'):geometry_score(report)


def test_enclosure_severity_can_improve_while_surface_overlap_appears(tmp_path):
    path,_,scene,p=fixture(tmp_path,SHAPES[0]);before,_=evaluate(scene,p,sha256(path))
    actor=scene.actors['A']
    after,_=evaluate(scene,p,sha256(path),actor_vertices=lambda n,t:
        actor['rig'].vertices(actor['sampler'].sample(t))+np.array([.15,0,0]))
    assert before['samples'][1]['actor_objects'][0]['maximum_depth_upper_m']<1e-6
    assert after['samples'][1]['actor_objects'][0]['maximum_depth_lower_m']>.049
    assert improved(geometry_score(before),geometry_score(after))
    assert not after['sampled_conditions_pass']  # Escape severity is not a quality pass.


def test_primitive_rows_join_model_without_changing_original_caps(tmp_path):
    path,_,scene,p=fixture(tmp_path,SHAPES[0],offset=(.2,0,0));digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)))
    problem=SceneProblem(scene,SceneEdits(permissions,scene,digest));include_times(problem,[0.,1.,2.])
    original=problem.model(problem.initial); caps=[a.copy() for a in problem.caps['A'].caps]
    system,jac,rows,report=model(problem,problem.initial,scene,p,digest,.02)
    np.testing.assert_allclose(system.residual()[:len(original)],original,atol=1e-9)
    assert report['surface_rows']==len(rows.rows)>0 and jac.shape[1]==3
    for a,b in zip(caps,problem.caps['A'].caps):np.testing.assert_array_equal(a,b)


def test_separated_broadphase_witnesses_do_not_consume_row_budget(tmp_path):
    path,spec,scene,p=fixture(tmp_path,SHAPES[0])
    actor=scene.actors['A']
    spec['objects']['item']['keyframes']=[dict(time_s=t,translation_m=(
        actor['rig'].vertices(actor['sampler'].sample(t)).mean(0)+[.28,.28,0]).tolist(),
        rotation_xyzw=[0,0,0,1]) for t in (0.,2.)]
    save(path,spec);scene=SceneContacts(spec,tmp_path);p=policy(path)
    rows=build(scene,p,sha256(path),maximum_rows=1)
    assert not rows.rows
    assert any(s['actor_objects'][0]['separated_witnesses'] for s in rows.report['samples'])
    assert all(s['actor_objects'][0]['total_faces']==12 for s in rows.report['samples'])
