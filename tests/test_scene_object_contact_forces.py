"""Actual closed skinned fixture, explicit COM/inertia and failed contact/geometry."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_object_contact_forces as subject
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256


def fixture(tmp_path,*,intersecting=False,shape='box',mass=1.):
    cubes=[]
    for x in (-.25,.25):
        cube=trimesh.creation.box(extents=[.1,.1,.1]);cube.apply_translation([x,.1,0]);cubes.append(cube)
    if intersecting:cubes.append(trimesh.creation.box(extents=[.05,.05,.05]))
    mesh=trimesh.util.concatenate(cubes)
    doc=dict(asset=dict(version='2.0'),buffers=[dict(byteLength=0)],bufferViews=[],accessors=[],
        nodes=[dict(name='fixture-root',children=[1]),dict(name='mesh',mesh=0,skin=0)],
        scenes=[dict(nodes=[0])],scene=0,skins=[dict(joints=[0])],meshes=[dict(primitives=[])],animations=[])
    binary=bytearray()
    def unsigned(values,kind):
        values=np.asarray(values,dtype='<u2')
        while len(binary)%4:binary.append(0)
        doc['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=values.nbytes));binary.extend(values.tobytes())
        doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1,componentType=5123,count=len(values),type=kind))
        return len(doc['accessors'])-1
    count=len(mesh.vertices)
    doc['meshes'][0]['primitives']=[dict(attributes=dict(POSITION=append_accessor(doc,binary,mesh.vertices,'VEC3'),
        JOINTS_0=unsigned(np.zeros((count,4)),'VEC4'),WEIGHTS_0=append_accessor(doc,binary,np.tile([1.,0,0,0],(count,1)),'VEC4')),
        indices=unsigned(mesh.faces.reshape(-1),'SCALAR'))]
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,binary,np.eye(4).reshape(1,16),'MAT4')
    clock=append_accessor(doc,binary,[0.,1.],'SCALAR');translation=append_accessor(doc,binary,[[0.,0,0],[0.,0,0]],'VEC3')
    doc['animations']=[dict(name='synthetic closed grip fixture',channels=[dict(sampler=0,target=dict(node=0,path='translation'))],
        samplers=[dict(input=clock,output=translation,interpolation='LINEAR')])]
    source=tmp_path/'fixture.glb';write_glb(source,doc,binary)
    geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.4,.4,.4]) if shape=='box' else dict(schema='strep-object-geometry-v1',shape='cylinder',radius_m=.2,height_m=.4)
    spec=dict(schema='strep-native-scene-contacts-v1',duration_s=1.,actors=dict(A=dict(glb=source.name,sha256=sha256(source),animation_index=0,
        placement=dict(translation_m=[0.,0,0],rotation_xyzw=[0.,0,0,1]))),
        objects=dict(prop=dict(geometry=geometry,keyframes=[dict(time_s=0.,translation_m=[0.,0,0],rotation_xyzw=[0.,0,0,1])])),contacts=[])
    for i,(name,x) in enumerate((('left',-.2),('right',.2))):
        ids=np.flatnonzero(abs(mesh.vertices[:,0]-x)<1e-12)
        spec['contacts'].append(dict(id=name,actor='A',vertices=[[1,0,int(v)] for v in ids],reduction='centroid',
            target=dict(space='object',object='prop',points_m=[[x,.1,0.]]),mode='hold',interval_s=[0.,1.],limits=dict(position_m=1e-6,relative_speed_m_s=1e-6)))
    contacts=tmp_path/'contacts.json';save(contacts,spec)
    surface=dict(schema='strep-native-surface-contact-v1',contacts_sha256=sha256(contacts),maximum_actor_pose_queries=20000,
        limits=dict(maximum_opposition_error_degrees=10.,backface_allowance_m=.0005,minimum_normal_area_m2=1e-14,minimum_normal_coherence=.1),
        contacts={name:dict(target_normal=dict(space='object',normals=[[sign,0.,0.]])) for name,sign in [('left',-1),('right',1)]})
    sp=tmp_path/'surface.json';save(sp,surface)
    gp=tmp_path/'geometry.json';save(gp,dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(contacts),
        clock=dict(mode='explicit',times_s=[0.,1.]),limits=dict(penetration_m=.0001,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={}))
    def binding(path):return dict(path=path.name,sha256=sha256(path))
    request=dict(schema=subject.SCHEMA,scene=binding(contacts),surface_policy=binding(sp),geometry_policy=binding(gp),object='prop',sample_count=5,
        body=dict(mass_kg=mass,inertia_body_about_com_kg_m2=(np.eye(3)*.01*mass).tolist(),com_from_object_origin_local_m=[0.,0,0.],gravity_world_m_s2=[0.,-9.81,0.]),
        contact_forces={name:dict(friction_coefficient=.5,maximum_point_forces_N=[100.]) for name in ('left','right')},
        phases=[dict(id='held',start_frame=0,end_frame_exclusive=5,support_assumption='supported')],
        force_tolerance_N=1e-6,torque_tolerance_Nm=1e-6,seconds_per_sample=.25,
        assumption_notes={k:'Explicit synthetic test assumption, not measured human data.' for k in ('com','mass','inertia','friction','capacity','contacts')})
    path=tmp_path/'request.json';save(path,request)
    return path,request,contacts,sp,gp


def prepared(paths):
    path,r,contacts,sp,gp=paths
    scene=subject.SceneContacts(read(contacts),path.parent)
    return scene,subject.prepare(scene,read(sp),read(gp),r,sha256(contacts))


@pytest.mark.parametrize('shape',['box','cylinder'])
def test_actual_skin_geometry_and_conditional_force_are_coupled_on_complete_clocks(tmp_path,monkeypatch,shape):
    paths=fixture(tmp_path,shape=shape);monkeypatch.setattr(subject,'ROOT',tmp_path)
    result=subject.run(paths[0],tmp_path/'reports/force');report=read(tmp_path/'reports/force/assessment.json')
    assert result['conditional_force_feasible']==result['coupled_sampled_scene_force_consistent']==3
    assert report['uniform_times_s']==[0.,.25,.5,.75,1.]
    assert [s['frame'] for s in report['assessed_samples']]==[1,2,3] and report['unestimated_endpoint_frames']==[0,4]
    assert all(s['actual_sticking_contact_samples_passed'] and s['sampled_geometry_passed'] for s in report['assessed_samples'])
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']
    geometry=read(tmp_path/'reports/force/geometry-result.json')
    assert set(report['uniform_times_s']).issubset(geometry['times_s']) and len(geometry['times_s'])>5
    for name,h in result['files_sha256'].items():assert sha256(tmp_path/'reports/force'/name)==h
    with pytest.raises(FileExistsError):subject.run(paths[0],tmp_path/'reports/force')


def test_force_only_success_cannot_approve_an_unrelated_body_object_intersection(tmp_path,monkeypatch):
    paths=fixture(tmp_path,intersecting=True);monkeypatch.setattr(subject,'ROOT',tmp_path)
    result=subject.run(paths[0],tmp_path/'reports/force')
    assert result['conditional_force_feasible']==3 and result['coupled_sampled_scene_force_consistent']==0
    surface=read(tmp_path/'reports/force/surface-result.json');assert surface['point_contacts_pass'] and surface['surface_contacts_pass']
    assert not read(tmp_path/'reports/force/geometry-result.json')['sampled_conditions_pass']


def test_mass_force_limit_failure_keeps_unchanged_actual_source_geometry(tmp_path,monkeypatch):
    paths=fixture(tmp_path,mass=20.);monkeypatch.setattr(subject,'ROOT',tmp_path)
    before=sha256(tmp_path/'fixture.glb');result=subject.run(paths[0],tmp_path/'reports/force')
    assert result['conditional_force_feasible']==result['coupled_sampled_scene_force_consistent']==0
    assert read(tmp_path/'reports/force/geometry-result.json')['sampled_conditions_pass']
    assert sha256(tmp_path/'fixture.glb')==before


def test_nonzero_com_uses_object_orientation_and_preserves_original_origin(tmp_path):
    paths=fixture(tmp_path);path,r,contacts,sp,gp=paths;spec=read(contacts)
    rotation=Rotation.from_euler('z',.7);spec['objects']['prop']['keyframes'][0].update(translation_m=[3.,4.,5.],rotation_xyzw=rotation.as_quat().tolist())
    save(contacts,spec);s=read(sp);g=read(gp);s['contacts_sha256']=g['contacts_sha256']=sha256(contacts);save(sp,s);save(gp,g)
    r['body']['com_from_object_origin_local_m']=[.03,.02,-.01]
    scene,p=prepared(paths)
    expected=np.array([3,4,5])+rotation.apply([.03,.02,-.01])
    np.testing.assert_allclose(p['centers'],np.tile(expected,(5,1)),atol=1e-12,rtol=0)
    np.testing.assert_array_equal(p['object_positions'],np.tile([3.,4.,5.],(5,1)))


@pytest.mark.parametrize('change',['missing_contact','extra_contact','wrong_normal','unphysical_inertia','free_flight_endpoint','too_many_samples','touch'])
def test_incomplete_or_inconsistent_physics_is_rejected_before_output(tmp_path,monkeypatch,change):
    path,r,c,sp,gp=fixture(tmp_path);monkeypatch.setattr(subject,'ROOT',tmp_path)
    if change=='missing_contact':r['contact_forces'].pop('left')
    if change=='extra_contact':r['contact_forces']['unknown']=copy.deepcopy(r['contact_forces']['left'])
    if change=='wrong_normal':s=read(sp);s['contacts']['left']['target_normal']['normals']=[[1.,0,0]];save(sp,s);r['surface_policy']['sha256']=sha256(sp)
    if change=='unphysical_inertia':r['body']['inertia_body_about_com_kg_m2']=[[1.,0,0],[0,1.,0],[0,0,3.]]
    if change=='free_flight_endpoint':r['phases']=[dict(id='flight',start_frame=0,end_frame_exclusive=1,support_assumption='free_flight'),dict(id='held',start_frame=1,end_frame_exclusive=5,support_assumption='supported')]
    if change=='too_many_samples':r['sample_count']=901
    if change=='touch':spec=read(c);spec['contacts'][0].update(mode='touch',interval_s=[0.,0.],limits=dict(position_m=1e-6));save(c,spec);r['scene']['sha256']=sha256(c);s=read(sp);g=read(gp);s['contacts_sha256']=g['contacts_sha256']=sha256(c);save(sp,s);save(gp,g);r['surface_policy']['sha256']=sha256(sp);r['geometry_policy']['sha256']=sha256(gp)
    save(path,r)
    with pytest.raises(ValueError):subject.run(path,tmp_path/'reports/force')
    assert not (tmp_path/'reports/force').exists()


def test_source_mutation_after_actual_force_measurement_preserves_failed_outputs(tmp_path,monkeypatch):
    paths=fixture(tmp_path);monkeypatch.setattr(subject,'ROOT',tmp_path);original=subject.assess
    def changed(*args,**kwargs):
        result=original(*args,**kwargs);paths[2].write_bytes(paths[2].read_bytes()+b' ');return result
    monkeypatch.setattr(subject,'assess',changed);output=tmp_path/'reports/force'
    with pytest.raises(ValueError,match='source changed'):subject.run(paths[0],output)
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()
    assert (output/'assessment.json').exists()
