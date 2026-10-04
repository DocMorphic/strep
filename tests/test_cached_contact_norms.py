"""Shared caches must reproduce complete authored surface rows and clocks."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cached_contact_norms import CachedContactNorms
from native_contact_norms import ContactNorms
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from test_native_contact_norms import prepared
from test_native_surface_contact import scene_fixture,policy
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from strep import sha256,save


def make(spec,path,policy_value):
    scene=SceneContacts(spec,path.parent);digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=3,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.02)))
    problem=SceneProblem(scene,SceneEdits(permissions,scene,digest))
    return problem,policy_value,digest


def compare(problem,p,digest,worlds):
    reference=ContactNorms(problem,p,digest,maximum_rows=50000);cached=CachedContactNorms(problem,p,digest,maximum_rows=50000)
    before,bg,bi=reference.sample(worlds);after,ag,ai=cached.sample(worlds)
    np.testing.assert_allclose(before.vectors,after.vectors,atol=1e-12,rtol=0)
    np.testing.assert_allclose(bg,ag,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(before.caps,after.caps);np.testing.assert_array_equal(before.scales,after.scales)
    assert ai['identity']==bi['identity'] and ai['actor_pose_queries']==bi['actor_pose_queries']
    assert not ai['whole_body_geometry_checked'] and not ai['quality_approved'] and not ai['release_approved']
    return cached,ai


@pytest.mark.parametrize('partner',[False,True])
@pytest.mark.parametrize('hold',[False,True])
@pytest.mark.parametrize('edited',[False,True])
def test_world_and_partner_rows_reproduce_all_reference_populations(tmp_path,partner,hold,edited):
    problem,p,digest=prepared(tmp_path,partner=partner,hold=hold);value=problem.initial.copy()
    if edited:value[:]=[.02,-.01,.03]
    compare(problem,p,digest,problem.worlds(value))


@pytest.mark.parametrize('centroid',[False,True])
def test_object_transforms_and_centroid_union_faces_match_reference(tmp_path,centroid):
    _,rig,reader,spec,path,_=scene_fixture(tmp_path);row=spec['contacts'][0]
    q=Rotation.from_euler('z',60,degrees=True);v=rig.vertices(reader.sample(1.))[0]
    local=np.array([0.,.2,0.]);position=v-q.apply(local)
    spec['objects']['prop']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),keyframes=[
        dict(time_s=t,translation_m=position.tolist(),rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()) for t,angle in [(0.,0),(2.,120)]])
    row['target']=dict(space='object',object='prop',points_m=[local.tolist()])
    if centroid:row.update(vertices=[[6,0,0],[6,0,1]],reduction='centroid')
    row.update(mode='hold',interval_s=[.8,1.2],limits=dict(position_m=.5,relative_speed_m_s=.5))
    save(path,spec);problem,p,digest=make(spec,path,policy(path,spec));compare(problem,p,digest,problem.worlds(problem.initial))


def test_shared_pose_cache_preserves_logical_query_budget_and_every_contact(tmp_path):
    _,_,_,spec,path,_=scene_fixture(tmp_path);row=spec['contacts'][0]
    row.update(mode='hold',interval_s=[.8,1.2],limits=dict(position_m=.5,relative_speed_m_s=.5))
    second=copy.deepcopy(row);second['id']='another-group';spec['contacts'].append(second)
    save(path,spec);problem,p,digest=make(spec,path,policy(path,spec));cached,identity=compare(problem,p,digest,problem.worlds(problem.initial))
    assert identity['actor_pose_queries']==2*identity['computed_actor_poses']
    assert {v['contact'] for v in identity['identity']}=={row['id'],second['id']}
    p['maximum_actor_pose_queries']=identity['computed_actor_poses']
    with pytest.raises(ValueError,match='pose budget'):CachedContactNorms(problem,p,digest)


def test_complete_incident_cache_uses_all_skin_influences_and_primitives(tmp_path):
    source,rig,_,spec,path,_=scene_fixture(tmp_path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    original=doc['meshes'][0]['primitives'][0]
    original['attributes']['WEIGHTS_0']=append_accessor(doc,binary,np.tile([.7,.3,0.,0.],(3,1)),'VEC4')
    # Slot 1 is root in the original fixture's joint accessor, and contributes.
    second=copy.deepcopy(original);second['attributes']['POSITION']=append_accessor(doc,binary,rig.primitives[0]['positions']+[2.,0.,0.],'VEC3')
    doc['meshes'][0]['primitives'].append(second);write_glb(source,doc,binary)
    spec['actors']['A']['sha256']=sha256(source);save(path,spec)
    problem,p,digest=make(spec,path,policy(path,spec));value=problem.initial.copy();value[:]=[.02,-.01,.03]
    cached,identity=compare(problem,p,digest,problem.worlds(value))
    population=identity['complete_incident_populations']['A']
    assert population==dict(source_vertices=6,required_vertices=3,source_faces=2,required_incident_faces=1)
    assert cached.patches['A']['vertices'].tolist()==[0,1,2]


def test_unavailable_normal_at_an_unqueried_group_time_does_not_reject(tmp_path):
    source,rig,_,spec,path,_=scene_fixture(tmp_path);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    second=copy.deepcopy(doc['meshes'][0]['primitives'][0])
    # Copy the original accessor payload and bind the second primitive to joint 5.
    array=np.tile([5,0,0,0],(3,1)).astype('<u2')
    while len(binary)%4:binary.append(0)
    doc['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=array.nbytes));binary.extend(array.tobytes())
    doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1,componentType=5123,count=3,type='VEC4'))
    second['attributes']['JOINTS_0']=len(doc['accessors'])-1;doc['meshes'][0]['primitives'].append(second)
    write_glb(source,doc,binary);spec['actors']['A']['sha256']=sha256(source)
    row=spec['contacts'][0];row['interval_s']=[.8,.8]
    later=copy.deepcopy(row);later.update(id='later-other-surface',vertices=[[6,1,0]],interval_s=[1.2,1.2]);spec['contacts'].append(later)
    save(path,spec);problem,p,digest=make(spec,path,policy(path,spec));worlds=problem.worlds(problem.initial)
    stamp=np.searchsorted(problem.times,1.2);worlds['A'][stamp,3,:3,:3]=0
    _,identity=compare(problem,p,digest,worlds)
    assert len(identity['identity'])==2


def test_unavailable_active_normal_and_missing_pose_data_reject(tmp_path):
    problem,p,digest=prepared(tmp_path);cached=CachedContactNorms(problem,p,digest);worlds=problem.worlds(problem.initial)
    with pytest.raises(ValueError,match='dictionary'):cached.sample({})
    with pytest.raises(ValueError,match='population'):cached.sample({'A':np.zeros((1,1,4,4))})
    worlds['A'][np.searchsorted(problem.times,1.),3,:3,:3]=0
    with pytest.raises(ValueError,match='Unavailable'):cached.sample(worlds)


def test_clock_mutation_rejects_before_cache_is_used(tmp_path):
    problem,p,digest=prepared(tmp_path);cached=CachedContactNorms(problem,p,digest);worlds=problem.worlds(problem.initial)
    problem.times=problem.times.copy();problem.times[1]+=1e-8
    with pytest.raises(ValueError,match='clock'):cached.sample(worlds)


def test_inherited_full_orientation_and_side_derivatives_match_reference(tmp_path):
    problem,p,digest=prepared(tmp_path,hold=True);value=problem.initial.copy();worlds=problem.worlds(value)
    reference=ContactNorms(problem,p,digest);cached=CachedContactNorms(problem,p,digest)
    before,bj,bi=reference.linearize(value,worlds,.02,step=1e-4);after,aj,ai=cached.linearize(value,worlds,.02,step=1e-4)
    np.testing.assert_allclose(before.vectors,after.vectors,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(before.caps,after.caps);np.testing.assert_array_equal(before.scales,after.scales)
    np.testing.assert_allclose(bj.toarray(),aj.toarray(),atol=1e-8,rtol=0)
    assert bi['identity']==ai['identity'] and ai['orientation_rows']==len(problem.rows[0]['times'])


@pytest.mark.parametrize('option,value',[('maximum_rows',2),('maximum_rows',True),('maximum_cache_bytes',True),('maximum_cache_bytes',1),('maximum_cache_bytes',1024),('maximum_cache_bytes',1024**3+1)])
def test_resource_overflow_never_returns_a_subset(tmp_path,option,value):
    problem,p,digest=prepared(tmp_path,hold=True)
    with pytest.raises(ValueError):CachedContactNorms(problem,p,digest,**{option:value})


def test_source_asset_mutation_rejects_even_with_prepared_topology(tmp_path):
    problem,p,digest=prepared(tmp_path);cached=CachedContactNorms(problem,p,digest);worlds=problem.worlds(problem.initial)
    path=Path(next(iter(problem.scene.inputs)));path.write_bytes(path.read_bytes()+b'mutation')
    with pytest.raises(ValueError):cached.sample(worlds)
