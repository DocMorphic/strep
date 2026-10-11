"""Raw engine skin reaches solver/geometry paths without changing the asset."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_engine_skin_view import EngineSkinView, EngineSkinScene
from native_scene_engine import EngineObservations
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from native_scene_edit import SceneEdits
from native_scene_geometry import evaluate as geometry_audit
from strep import save, sha256
from test_native_scene_engine import mock_actor
from test_native_scene_fit import prepare
from test_native_scene_geometry import closed_fixture, policy


def observed(scene, times):
    cases = [dict(id=n, path=n+'.glb', animation_index=a['animation_index']) for n,a in scene.actors.items()]
    actors = [dict(mock_actor(a['rig'],a['sampler'],times), id=n, path=n+'.glb') for n,a in scene.actors.items()]
    assert not scene.objects
    return EngineObservations(scene, dict(cases=actors,objects=[]), cases, times)


def bindings(tmp_path):
    path = tmp_path/'raw-engine-fixture.json'
    save(path,dict(mocked=True))
    return {str(path):sha256(path)}


def test_solver_and_export_decode_use_engine_skin_without_rewriting_source(tmp_path):
    source,spec,contacts,permissions,path,scene,_ = prepare(tmp_path)
    # A real quantization deficit, with both influences on the same bone,
    # changes skinning under translation without changing the skeleton.
    from gltf_tools import read_glb, append_accessor, write_glb
    doc,binary = read_glb(source); data=bytearray(binary)
    primitive=doc['meshes'][0]['primitives'][0]
    count=len(scene.actors['A']['skin'].nodes)
    primitive['attributes']['WEIGHTS_0']=append_accessor(doc,data,np.tile([.5,.5,0,0],(count,1)),'VEC4')
    joint_values=np.tile([3,3,0,0],(count,1)).astype('<u2')
    while len(data)%4: data.append(0)
    view=len(doc['bufferViews']); doc['bufferViews'].append(dict(buffer=0,byteOffset=len(data),byteLength=joint_values.nbytes))
    data.extend(joint_values.tobytes()); acc=len(doc['accessors'])
    doc['accessors'].append(dict(bufferView=view,componentType=5123,count=count,type='VEC4'))
    primitive['attributes']['JOINTS_0']=acc
    write_glb(source,doc,data); spec['actors']['A']['sha256']=sha256(source); save(contacts,spec)
    permissions['contacts_sha256']=sha256(contacts)
    scene=SceneContacts(spec,tmp_path); original=source.read_bytes()
    provider=observed(scene,[0.,1.,2.]); view=EngineSkinScene(scene,provider,bindings(tmp_path))
    assert np.any(view.actors['A']['skin'].weights.sum(axis=1)<1)
    edits=SceneEdits(permissions,view,sha256(contacts)); problem=SceneProblem(view,edits)
    times=np.array([0.,1.,2.]); worlds=dict(A=np.array([scene.actors['A']['sampler'].sample(t) for t in times]))
    expected=np.array([provider.skins['A'].vertices(w[scene.actors['A']['rig'].joints]) for w in worlds['A']])
    actual=problem.skin_points('A',np.arange(count),worlds,np.arange(3),'individual')
    np.testing.assert_allclose(actual,expected,atol=1e-15,rtol=0)
    assert np.max(abs(actual-np.array([scene.actors['A']['rig'].vertices(w) for w in worlds['A']])))>1e-6
    report,_=view.evaluate(); assert not report['loaded_skin_weights_normalized'] and not report['future_engine_pose_verified']
    candidate=tmp_path/'candidate.glb'; x=edits.initial.copy(); x.reshape(-1,3)[:,1]=.1
    edits.export('A',x,candidate); residual,decoded=problem.decoded(dict(A=candidate),x)
    row=problem.rows[0]; entry=row['entry']; declaration=entry['authored']
    assert declaration['mode']=='hold' and declaration['target']['space']=='world'
    goal=entry['target_ids']
    oracle=np.array([provider.skins['A'].vertices(w[scene.actors['A']['rig'].joints])[entry['ids']]
                     for w in decoded['A'][row['ids']]])
    limit=declaration['limits']['position_m']
    expected_residual=((np.linalg.norm(oracle-goal,axis=2)-limit)/max(limit,.0001)).ravel()
    speed_rows=sum(max(1,len(pop['times_s'])-1) for pop in row['populations'])
    stop=len(residual)-speed_rows
    np.testing.assert_allclose(residual[stop-len(expected_residual):stop],expected_residual,atol=1e-12,rtol=0)
    assert source.read_bytes()==original
    assert scene.actors['A']['rig'] is view.actors['A']['rig'].source
    assert scene.actors['A']['skin'] is not view.actors['A']['skin']


def test_all_materials_and_eight_nonzero_influences_survive(tmp_path):
    from test_native_support_skin_geometry import multiprimitive
    from native_support_skin import NativeSupportSkin
    from gltf_tools import append_accessor
    _,_,_,_,_,scene,_=prepare(tmp_path)
    rig,reader=multiprimitive(tmp_path)
    rig.primitives[1]['joints']=np.tile([0,1,2,3,4,5,0,1],(3,1))
    rig.primitives[1]['weights']=np.tile([.1,.2,.1,.15,.12,.08,.13,.12],(3,1))
    data=bytearray(rig.binary)
    for primitive in rig.primitives[1:]:
        attributes={}
        for slot in range(primitive['weights'].shape[1]//4):
            attributes['WEIGHTS_'+str(slot)]=append_accessor(rig.document,data,primitive['weights'][:,slot*4:slot*4+4],'VEC4')
        rig.document['meshes'][0]['primitives'].append(dict(attributes=attributes))
    rig.binary=bytes(data)
    scene.actors['A'].update(rig=rig,sampler=reader,skin=NativeSupportSkin(rig))
    provider=observed(scene,[0.,1.,2.]); model=EngineSkinView(provider,'A')
    assert model.primitive_offsets==[0,3,6,9] and np.all(model.weights[3:6]>0)
    world=reader.sample(.853725)
    expected=[]
    raw=provider.skins['A']
    for vertex in range(9):
        point=np.zeros(3)
        for slot in range(8):
            matrix=world[rig.joints[raw.nodes[vertex,slot]]]
            point+=raw.weights[vertex,slot]*np.array([sum(matrix[row,col]*raw.points[vertex,slot,col] for col in range(4)) for row in range(3)])
        expected.append(point)
    np.testing.assert_allclose(model.vertices(world),expected,atol=1e-15,rtol=0)
    np.testing.assert_array_equal(model.vertex_references,scene.actors['A']['skin'].vertex_references)


def test_complete_geometry_and_derivatives_use_same_view(tmp_path):
    _,path,spec=closed_fixture(tmp_path); scene=SceneContacts(spec,tmp_path)
    provider=observed(scene,[0.,1.,2.]); view=EngineSkinScene(scene,provider,bindings(tmp_path)); skin=view.actors['A']['skin']
    worlds=np.array([scene.actors['A']['sampler'].sample(t) for t in (0.,1.,2.)])
    rows=np.array([2,0,1,2]); vertices=np.array([3,1,2,0])
    jac=np.zeros(worlds.shape+(1,)); jac[:,:,0,3,0]=.3
    expected=[]
    for frame,vertex in zip(rows,vertices):
        expected.append(sum(float(weight)*(.3 if node>=0 else 0) for node,weight in zip(skin.nodes[vertex],skin.weights[vertex])))
    actual=skin.derivative(jac,rows,vertices)
    np.testing.assert_allclose(actual[:,0,0],expected,atol=1e-15,rtol=0)
    np.testing.assert_array_equal(actual[:,1:,0],0.)
    full,_=geometry_audit(view,policy(path),policy(path)['contacts_sha256'])
    reference,_=geometry_audit(scene,policy(path),policy(path)['contacts_sha256'],actor_vertices=provider.actor_vertices)
    assert full['samples']==reference['samples'] and full['topology']==reference['topology']
    assert not skin.weights.flags.writeable and not skin.points.flags.writeable


@pytest.mark.parametrize('fault',['unbound','digest','other-scene','missing-actor','source-binding'])
def test_invalid_context_or_changed_evidence_rejects(tmp_path,fault):
    _,_,_,_,_,scene,_=prepare(tmp_path); provider=observed(scene,[0.,1.,2.]); pins=bindings(tmp_path)
    if fault=='unbound':pins={}
    elif fault=='digest': pins={next(iter(pins)):'0'*64}
    elif fault=='other-scene': provider.scene=copy.copy(scene)
    elif fault=='missing-actor':provider.skins={}
    else:pins={next(iter(scene.inputs)):'0'*64}
    with pytest.raises(ValueError): EngineSkinScene(scene,provider,pins)


def test_changed_raw_evidence_is_detected_after_construction(tmp_path):
    _,_,_,_,_,scene,_=prepare(tmp_path); pins=bindings(tmp_path)
    view=EngineSkinScene(scene,observed(scene,[0.,1.,2.]),pins)
    Path(next(iter(pins))).write_text('changed')
    with pytest.raises(ValueError):view.evaluate()
