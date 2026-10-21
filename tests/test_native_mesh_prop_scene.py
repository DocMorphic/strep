"""Real prop-store/rig integration with generated assets and retained failures."""
import copy
import json
from pathlib import Path
import sys
import uuid

import numpy as np
import pytest
from scipy.spatial.transform import Rotation
import trimesh

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import native_mesh_prop_scene as module
from native_mesh_prop_scene import MeshPropScene,run
from static_prop_asset import StaticPropAsset
import studio_props
from gltf_tools import append_accessor,write_glb
from native_scene_contacts import SceneContacts
from native_observation_archive import ObservationArchive,verify
from strep import read,save,sha256
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from test_native_scene_geometry import closed_fixture
from test_native_scene_contacts import setup
from test_static_prop_asset import fixture as triangle_fixture


def cube(path,extents=(.2,.2,.2),offset=(0,0,0),*,mesh=None):
    mesh=trimesh.creation.box(extents=extents) if mesh is None else mesh
    document=dict(asset=dict(version='2.0'),nodes=[dict(mesh=0)],scene=0,scenes=[dict(nodes=[0])],buffers=[{}],bufferViews=[],accessors=[])
    binary=bytearray();position=append_accessor(document,binary,mesh.vertices+offset,'VEC3');indices=np.asarray(mesh.faces.reshape(-1),dtype='<u2')
    while len(binary)%4:binary.append(0)
    document['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=indices.nbytes));binary.extend(indices.tobytes())
    document['accessors'].append(dict(bufferView=len(document['bufferViews'])-1,componentType=5123,count=len(indices),type='SCALAR'))
    document['meshes']=[dict(primitives=[dict(attributes=dict(POSITION=position),indices=len(document['accessors'])-1)])]
    write_glb(path,document,binary);return StaticPropAsset.load(path)


def fixture(tmp_path,*,closed=True):
    if closed:source,actor_path,actors=closed_fixture(tmp_path)
    else:
        source,_,_,actors=setup(tmp_path);actor_path=tmp_path/'contacts.json';save(actor_path,actors)
    # closed_fixture replaces the old triangle mesh; author its fixture point
    # explicitly on the replacement cube, rather than keep the old landmark.
    rig=RigAsset.load(source);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    actors['contacts'][0]['target']['points_m']=[rig.vertices(sampler.sample(1.))[0].tolist()]
    save(actor_path,actors)
    prop_path=tmp_path/'prop.glb';prop=cube(prop_path)
    grip=dict(schema='strep-prop-grip-selection-v1',label='Grip',**prop.surface_point(0,[.2,.3,.5]));grip_path=tmp_path/'grip.json';save(grip_path,grip)
    spec=dict(schema='strep-native-mesh-prop-scene-v1',actor_scene=actor_path.name,actor_scene_sha256=sha256(actor_path),props=dict(crate=dict(glb=prop_path.name,sha256=sha256(prop_path),geometry_sha256=prop.geometry_sha256,keyframes=[dict(time_s=0.,translation_m=[3.,1.,0],rotation_xyzw=[0,0,0,1])])),mesh_contacts=[])
    path=tmp_path/'mesh-scene.json';save(path,spec)
    policy=dict(schema='strep-native-mesh-prop-geometry-v1',mesh_scene_sha256=sha256(path),clock=dict(mode='explicit',times_s=[0.,1.,2.]),limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes=dict(floor=dict(normal_world=[0.,1.,0],offset_m=0.)))
    return path,spec,policy,prop,grip_path


def rewrite(path,spec,policy):
    save(path,spec);policy['mesh_scene_sha256']=sha256(path)
    return MeshPropScene(path)


def contact(grip_path):
    return dict(id='mesh-touch',actor='A',vertices=[[6,0,0]],reduction='individual',prop='crate',grip=grip_path.name,grip_sha256=sha256(grip_path),mode='touch',interval_s=[1.,1.],limits=dict(position_m=1e-6))


def test_self_intersecting_prop_fails_even_when_other_entities_are_far(tmp_path):
    path,spec,policy,_,_=fixture(tmp_path)
    a=trimesh.creation.box();b=a.copy();b.apply_translation([.3,.2,.1])
    combined=trimesh.util.concatenate([a,b]);assert combined.is_volume
    prop=cube(tmp_path/'crossing.glb',mesh=combined)
    spec['props']['crate'].update(glb='crossing.glb',sha256=prop.source_sha256,geometry_sha256=prop.geometry_sha256)
    scene=rewrite(path,spec,policy);report,_=scene.geometry(policy)
    assert not report['sampled_conditions_pass']
    for sample in report['samples']:
        own=next(row['audit'] for row in sample['self_surfaces'] if row['kind']=='prop')
        assert own['complete_triangle_population'] and own['counts']['proper_crossing']>0
        pair=sample['mesh_pairs'][0]
        assert not pair['vertex_containment'][0]['available'] and not pair['passed']
        state=next(row for row in sample['volumes'] if row['kind']=='prop')
        assert state['containment_blocked_by_self_geometry'] and state['self_intersection_checked']


def test_import_store_grip_to_moving_contact_uses_original_triangle_and_clock(tmp_path,monkeypatch):
    path,spec,policy,_,_=fixture(tmp_path)
    monkeypatch.setattr(studio_props,'ASSETS',tmp_path/'store')
    document,binary=triangle_fixture();source=tmp_path/'triangle.glb';write_glb(source,document,binary);original=source.read_bytes()
    imported=studio_props.import_bytes(original,'Triangle.glb','Self-created fixture')
    saved=studio_props.save_grip(dict(asset_id=imported['id'],geometry_sha256=imported['geometry_sha256'],face=0,barycentric=[1.,0,0],label='Exact original vertex'))
    prop_path=studio_props.bounded_path(imported['id'],'prop.glb');grip_path=studio_props.bounded_path(imported['id'],f'grips/{saved["grip_id"]}.json')
    scene=SceneContacts(read(tmp_path/'contacts.json'),tmp_path);actor=scene.actors['A'];clock=actor['sampler'].channels[0][2].astype(float)
    positions=scene.actor_points('A',np.array([0]),clock)[:,0]
    spec['props']['crate']=dict(glb=str(prop_path),sha256=imported['id'],geometry_sha256=imported['geometry_sha256'],keyframes=[dict(time_s=float(t),translation_m=p.tolist(),rotation_xyzw=[0,0,0,1]) for t,p in zip(clock,positions)])
    row=contact(grip_path);row.update(grip=str(grip_path),mode='hold',interval_s=[.3,1.7],limits=dict(position_m=1e-6,relative_speed_m_s=1e-5));spec['mesh_contacts']=[row]
    mesh_scene=rewrite(path,spec,policy);result,arrays=mesh_scene.contact_audit();audit=result['mesh_contacts'][0]
    assert result['all_declared_point_contacts_pass'] and audit['passed'] and audit['maximum_position_error_m']<1e-12
    assert audit['relative_speed_populations'] and all(p['passed'] for p in audit['relative_speed_populations'])
    for t in clock[(clock>=.3)&(clock<=1.7)]:assert t in arrays['mesh_contact_0_times_s']
    assert prop_path.read_bytes()==original and not result['collision_verified'] and not result['motion_fitted']
    # Point coincidence does not approve an open prop's collision volume.
    geometry,_=mesh_scene.geometry(policy,sample_indices=[1])
    assert not geometry['sampled_conditions_pass'] and not geometry['samples'][0]['mesh_pairs'][0]['vertex_containment'][0]['available']


def test_rigid_rotations_hierarchy_scale_and_world_grip_transport_are_preserved(tmp_path):
    path,spec,policy,_,grip_path=fixture(tmp_path)
    prop_path=tmp_path/'scaled.glb';prop=cube(prop_path,extents=(.4,.6,.8),offset=(.5,1.,-.3))
    grip=dict(schema='strep-prop-grip-selection-v1',label='Surface',**prop.surface_point(3,[.1,.2,.7]));save(grip_path,grip)
    spec['props']['crate'].update(glb=prop_path.name,sha256=sha256(prop_path),geometry_sha256=prop.geometry_sha256,keyframes=[dict(time_s=0.,translation_m=[3,4,5],rotation_xyzw=[0,0,0,1]),dict(time_s=2.,translation_m=[5,6,7],rotation_xyzw=Rotation.from_euler('y',90,degrees=True).as_quat().tolist())])
    spec['mesh_contacts']=[contact(grip_path)];scene=rewrite(path,spec,policy);result,arrays=scene.contact_audit()
    expected=Rotation.from_euler('y',45,degrees=True).apply(grip['position_m'])+[4,5,6]
    np.testing.assert_allclose(arrays['mesh_contact_0_target_world_m'][0,0],expected,atol=2e-15,rtol=0)
    expected_normal=Rotation.from_euler('y',45,degrees=True).apply(grip['winding_normal'])
    np.testing.assert_allclose(arrays['mesh_contact_0_target_winding_normal_world'][0,0],expected_normal,atol=2e-15,rtol=0)
    assert not result['mesh_contacts'][0]['orientation_evaluated'] and not result['mesh_contacts'][0]['outward_normal_verified']
    assert not result['mesh_contacts'][0]['passed'] and not result['all_declared_point_contacts_pass']


def test_all_actors_props_primitives_and_planes_are_checked_without_proxies(tmp_path):
    path,spec,policy,_,_=fixture(tmp_path);actors=read(tmp_path/'contacts.json')
    actors['actors']['B']=copy.deepcopy(actors['actors']['A']);actors['actors']['B']['placement']['translation_m']=[5.,0,0]
    actors['objects']['ball']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),keyframes=[dict(time_s=0.,translation_m=[10.,1.,0],rotation_xyzw=[0,0,0,1])])
    save(tmp_path/'contacts.json',actors);spec['actor_scene_sha256']=sha256(tmp_path/'contacts.json')
    spec['props']['other']=copy.deepcopy(spec['props']['crate']);spec['props']['other']['keyframes'][0]['translation_m']=[7.,1.,0]
    scene=rewrite(path,spec,policy);result,arrays=scene.geometry(policy)
    assert result['sampled_conditions_pass'] and result['all_policy_samples_evaluated']
    assert result['actor_faces']=={'A':12,'B':12} and result['prop_faces']=={'crate':12,'other':12}
    for row in result['samples']:
        assert len(row['mesh_pairs'])==5 and len(row['mesh_primitive_pairs'])==2 and len(row['mesh_world_planes'])==2
        assert len(row['base_scene']['actor_pairs'])==1 and len(row['base_scene']['actor_objects'])==2
    assert arrays['mesh_frame_1_prop_crate_world_m'].shape==(8,3) and not result['topology_modified']


@pytest.mark.parametrize('kind',['prop_inside_actor','actor_inside_prop','surface_crossing'])
def test_full_triangle_and_bidirectional_containment_failures_are_retained(tmp_path,kind):
    path,spec,policy,_,_=fixture(tmp_path);prop_path=tmp_path/'replacement.glb'
    extents={'prop_inside_actor':(.05,.05,.05),'actor_inside_prop':(2.,2.,2.),'surface_crossing':(2.,.05,.05)}[kind]
    prop=cube(prop_path,extents=extents);spec['props']['crate'].update(glb=prop_path.name,sha256=sha256(prop_path),geometry_sha256=prop.geometry_sha256)
    spec['props']['crate']['keyframes'][0]['translation_m']=[0.,.2,0]
    scene=rewrite(path,spec,policy);result,_=scene.geometry(policy,sample_indices=[1]);pair=result['samples'][0]['mesh_pairs'][0]
    assert not pair['passed'] and not result['sampled_conditions_pass']
    if kind=='surface_crossing':
        assert pair['surface']['records'] and all(d['max_depth_m']==0 for d in pair['vertex_containment'])
    else:assert not pair['surface']['records'] and max(d['max_depth_m'] for d in pair['vertex_containment'])>.1


def test_mesh_prop_plane_penetration_is_separate_from_actor_floor(tmp_path):
    path,spec,policy,_,_=fixture(tmp_path);spec['props']['crate']['keyframes'][0]['translation_m']=[3.,0,0]
    scene=rewrite(path,spec,policy);result,_=scene.geometry(policy,sample_indices=[1]);row=result['samples'][0]
    assert all(p['passed'] for p in row['base_scene']['world_planes']) and all(p['passed'] for p in row['mesh_pairs'])
    assert row['mesh_world_planes'][0]['maximum_depth_m']>.099 and not result['sampled_conditions_pass']


def test_open_actor_volume_is_explicitly_unavailable_even_when_far_away(tmp_path):
    path,spec,policy,_,_=fixture(tmp_path,closed=False);result,_=MeshPropScene(path).geometry(policy,sample_indices=[1])
    pair=result['samples'][0]['mesh_pairs'][0]
    assert pair['surface']['records']==[] and not pair['vertex_containment'][1]['available'] and not result['sampled_conditions_pass']


def test_complete_clock_includes_exact_prop_keys_and_mesh_contact_boundaries(tmp_path):
    path,spec,policy,_,grip_path=fixture(tmp_path);stamp=float(np.float32(.33333334))
    spec['props']['crate']['keyframes']=[dict(time_s=t,translation_m=[3.,1.,0],rotation_xyzw=[0,0,0,1]) for t in [0.,stamp,2.]]
    spec['mesh_contacts']=[contact(grip_path)];spec['mesh_contacts'][0]['interval_s']=[.777777777,.777777777]
    scene=rewrite(path,spec,policy);policy['clock']['mode']='native-and-frame-populations';times,_,populations=scene._clock(policy)
    assert stamp in times and .777777777 in times and populations
    result,_=scene.geometry(policy,sample_indices=[0,len(times)-1])
    assert result['times_s']==[0.,2.] and not result['all_policy_samples_evaluated'] and result['complete_clock_s']==times.tolist()


@pytest.mark.parametrize('fault',['scene_digest','prop_digest','geometry_digest','prop_name','first_key','last_key','repeated_key','quaternion','unknown_actor','unknown_prop','duplicate_contact','individual_many','interval','hold_limit','grip_digest','forged_grip','grip_flag'])
def test_malformed_or_unbound_authoring_is_rejected(tmp_path,fault):
    path,spec,policy,_,grip_path=fixture(tmp_path);row=contact(grip_path);spec['mesh_contacts']=[row]
    if fault=='scene_digest':spec['actor_scene_sha256']='0'*64
    elif fault=='prop_digest':spec['props']['crate']['sha256']='0'*64
    elif fault=='geometry_digest':spec['props']['crate']['geometry_sha256']='0'*64
    elif fault=='prop_name':spec['props']['A']=spec['props'].pop('crate')
    elif fault=='first_key':spec['props']['crate']['keyframes'][0]['time_s']=.1
    elif fault=='last_key':spec['props']['crate']['keyframes'].append(dict(time_s=1.,translation_m=[3,1,0],rotation_xyzw=[0,0,0,1]))
    elif fault=='repeated_key':spec['props']['crate']['keyframes']*=2
    elif fault=='quaternion':spec['props']['crate']['keyframes'][0]['rotation_xyzw']=[0,0,0,2]
    elif fault=='unknown_actor':row['actor']='unknown'
    elif fault=='unknown_prop':row['prop']='unknown'
    elif fault=='duplicate_contact':row['id']='arbitrary-body-patch'
    elif fault=='individual_many':row['vertices']=[[6,0,0],[6,0,1]]
    elif fault=='interval':row['interval_s']=[-1.,-1.]
    elif fault=='hold_limit':row.update(mode='hold',interval_s=[.5,1.5])
    elif fault=='grip_digest':row['grip_sha256']='0'*64
    else:
        grip=read(grip_path)
        if fault=='forged_grip':grip['position_m'][0]+=.01
        else:grip['contact_verified']=0
        save(grip_path,grip);row['grip_sha256']=sha256(grip_path)
    save(path,spec)
    with pytest.raises(ValueError):MeshPropScene(path)


@pytest.mark.parametrize('member',['prop.glb','grip.json','source.glb','contacts.json','mesh-scene.json'])
def test_changed_original_files_reject_subsequent_measurements(tmp_path,member):
    path,spec,policy,_,grip_path=fixture(tmp_path);spec['mesh_contacts']=[contact(grip_path)];scene=rewrite(path,spec,policy)
    changed=tmp_path/member;changed.write_bytes(changed.read_bytes()+b' ')
    with pytest.raises(ValueError,match='changed'):scene.contact_audit()
    with pytest.raises(ValueError,match='changed'):scene.geometry(policy)


@pytest.mark.parametrize('indices',[[],[1,1],[2,1],[-1],[3],[True],[0,True]])
def test_geometry_slice_cannot_hide_malformed_or_reordered_samples(tmp_path,indices):
    path,_,policy,_,_=fixture(tmp_path)
    with pytest.raises(ValueError):MeshPropScene(path).geometry(policy,sample_indices=indices)


@pytest.mark.parametrize('times',[[False,1.],[0.,True]])
def test_query_clocks_reject_boolean_values_before_numeric_coercion(tmp_path,times):
    path,_,_,_,_=fixture(tmp_path)
    with pytest.raises(ValueError,match='boolean'):MeshPropScene(path).prop_poses('crate',times)


def test_underscore_entity_names_cannot_collide_in_observation_archives(tmp_path):
    path,spec,policy,_,_=fixture(tmp_path);actors=read(tmp_path/'contacts.json')
    for name,x in [('z',10.),('y_z',12.)]:
        actors['objects'][name]=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),keyframes=[dict(time_s=0.,translation_m=[x,1.,0],rotation_xyzw=[0,0,0,1])])
    save(tmp_path/'contacts.json',actors);spec['actor_scene_sha256']=sha256(tmp_path/'contacts.json')
    item=spec['props'].pop('crate');spec['props']['x_y']=item;spec['props']['x']=copy.deepcopy(item);spec['props']['x']['keyframes'][0]['translation_m']=[6.,1.,0]
    scene=rewrite(path,spec,policy)
    with ObservationArchive(tmp_path/'names.npz') as sink:result,_=scene.geometry(policy,sample_indices=[1],observation_sink=sink)
    verify(tmp_path/'names.npz');assert result['sampled_conditions_pass']
    with np.load(tmp_path/'names.npz',allow_pickle=False) as z:
        names=[name for name in z.files if name.startswith('mesh_frame_') and name.endswith('_depth_lower_m')]
        assert len(names)==4 and len(set(names))==4


def test_bound_policy_array_admission_and_streaming_archive(tmp_path,monkeypatch):
    path,_,policy,_,_=fixture(tmp_path);scene=MeshPropScene(path);bad=copy.deepcopy(policy);bad['mesh_scene_sha256']='0'*64
    with pytest.raises(ValueError,match='bind'):scene.geometry(bad)
    monkeypatch.setattr(module,'MAX_ARRAY_BYTES',1)
    with pytest.raises(ValueError,match='streaming'):scene.geometry(policy)
    monkeypatch.setattr(module,'MAX_ARRAY_BYTES',64*1024**2)
    with ObservationArchive(tmp_path/'observations.npz') as sink:result,_=scene.geometry(policy,observation_sink=sink)
    verify(tmp_path/'observations.npz');assert result['sampled_conditions_pass']


def test_json_and_full_prop_budgets_reject_without_truncation(tmp_path,monkeypatch):
    path,_,_,_,_=fixture(tmp_path);raw=path.read_bytes()
    path.write_bytes(b'{"schema":"a","schema":"b"}')
    with pytest.raises(ValueError,match='Duplicate'):MeshPropScene(path)
    path.write_bytes(b'{"value":NaN}')
    with pytest.raises(ValueError,match='Finite'):MeshPropScene(path)
    path.write_bytes(b' '*(module.MAX_JSON_BYTES+1))
    with pytest.raises(ValueError,match='Bounded'):MeshPropScene(path)
    path.write_bytes(raw);monkeypatch.setattr(module,'MAX_PROP_BYTES',1)
    with pytest.raises(ValueError,match='no triangles dropped'):MeshPropScene(path)


def test_guarded_cli_output_is_confined_before_starting_a_worker(tmp_path):
    for output in [tmp_path/'outside',ROOT/'reports',ROOT/'scripts']:
        with pytest.raises(ValueError,match='inside reports'):module.guarded_output(output)
    fresh=ROOT/'reports'/('mesh-output-admission-test-'+uuid.uuid4().hex)
    assert module.guarded_output(fresh)==fresh.resolve() and not fresh.exists()


def test_complete_source_bound_run_preserves_originals_and_failed_decisions(tmp_path):
    path,spec,policy,_,grip_path=fixture(tmp_path);spec['mesh_contacts']=[contact(grip_path)];rewrite(path,spec,policy)
    policy_path=tmp_path/'policy.json';save(policy_path,policy);before={p:p.read_bytes() for p in tmp_path.glob('*') if p.is_file()}
    output=tmp_path/'evaluation';result=run(path,policy_path,output)
    assert result['status']=='complete' and result['all_geometry_samples_evaluated'] and result['sampled_geometry_pass'] and not result['point_contacts_pass']
    assert not result['motion_fitted'] and not result['quality_approved'] and not result['release_approved']
    assert all(p.read_bytes()==raw for p,raw in before.items()) and (output/'implementation/native_mesh_prop_scene.py').is_file()
    verify(output/'geometry-observations.npz')
    with pytest.raises(ValueError,match='Fresh'):run(path,policy_path,output)
