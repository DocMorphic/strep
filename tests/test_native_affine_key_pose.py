"""Actual affine TRS derivatives, authored contacts and complete native replay."""
from pathlib import Path
import copy,sys,json
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_key_contact_initializer import setup
from native_key_contact_initializer import KeyPose,run,encode,prepare
from native_affine_key_pose import AffineKeyPose,rotation_fractions
from audit_native_key_initializer import run as replay
from native_scene_contacts import SceneContacts
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from gltf_tools import write_glb,append_accessor
from strep import read,save,sha256
from native_key_boundaries import boundary_policy,key_frozen


def affine_setup(tmp_path):
    base,_,contacts,policy,request=setup(tmp_path);spec=read(contacts)
    source=Path(next(iter(base.scene.inputs)));rig=RigAsset.load(source);document=copy.deepcopy(rig.document)
    document['nodes'][0]['scale']=[1.000002,.999999,1.]
    document['nodes'][3]['scale']=[.999998,1.000003,1.]
    write_glb(source,document,rig.binary)
    for actor in spec['actors'].values():actor['sha256']=sha256(source)
    scene=SceneContacts(spec,tmp_path);point=scene.actor_points('A',scene.rows[0]['ids'],np.array([1.]))[0]
    spec['contacts'][0]['target']['points_m']=point.tolist();save(contacts,spec)
    request.update(contacts_sha256=sha256(contacts),pose_representation='native-trs-v1',orientation_mode='right-polar-v1')
    policy['contacts_sha256']=sha256(contacts)
    return source,SceneContacts(spec,tmp_path),contacts,policy,request


@pytest.mark.parametrize('incoming',[False,True])
@pytest.mark.parametrize('homogeneous',[False,True])
def test_affine_pose_rows_and_all_skin_derivatives_match_finite_differences(tmp_path,incoming,homogeneous):
    _,_,contacts,policy,request=affine_setup(tmp_path);spec=read(contacts)
    spec['contacts'][0].update(interval_s=[1.,1.],limits=dict(position_m=.05))
    if incoming:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['contacts'][0].update(actor='B',target=dict(space='actor',actor='A',vertices=[[6,0,0]],reduction='individual'))
    spec['actors']['A']['placement']['rotation_xyzw']=Rotation.from_euler('xyz',[12.,34.,-9.],degrees=True).as_quat().tolist()
    scene=SceneContacts(spec,tmp_path)
    if homogeneous:scene.actors['A']['skin'].points[:,:,3]*=np.linspace(.95,1.05,scene.actors['A']['skin'].points.shape[1])
    pose=KeyPose(scene,'A',1.,[3],[30.],.22,policy['planes'],.005,.0005,pose_representation='native-trs-v1')
    value=np.array([.05,-.12,.08]);rows,jac,world,vertices=pose.evaluate(value)
    fd=[];skin_fd=[];joint_fd=[]
    graph=pose.affine;_,_,skin_jac,joint_jac=graph.evaluate(value)
    for i in range(3):
        delta=np.eye(3)[i]*1e-6
        fd.append((pose.evaluate(value+delta)[0]-pose.evaluate(value-delta)[0])/2e-6)
        high=graph.evaluate(value+delta);low=graph.evaluate(value-delta)
        skin_fd.append((high[1]-low[1])/2e-6)
        joint_fd.append((high[0][graph.rig.joints,:3,3]-low[0][graph.rig.joints,:3,3])/2e-6)
    np.testing.assert_allclose(jac,np.stack(fd,axis=1),atol=2e-5,rtol=2e-7)
    np.testing.assert_allclose(skin_jac,np.stack(skin_fd,axis=-1),atol=3e-9,rtol=2e-7)
    np.testing.assert_allclose(joint_jac,np.stack(joint_fd,axis=-1),atol=3e-9,rtol=2e-7)
    assert len(vertices)==len(scene.actors['A']['skin'].nodes)
    assert np.array_equal(graph.evaluate(np.zeros(3))[0],graph.source)


def test_actual_quaternion_export_matches_affine_pose_without_changing_rig_scale(tmp_path):
    source,scene,contacts,policy,request=affine_setup(tmp_path);actor=scene.actors['A']
    node=3;channel=next(c for c in actor['sampler'].channels if c[:2]==(node,'rotation'));index=5;stamp=float(channel[2][index]);value=np.array([.1,.2,-.08])
    graph=AffineKeyPose(actor,stamp,[node],[30.]);world,vertices,*_=graph.evaluate(value)
    controls=np.zeros((len(channel[2]),1,3));controls[index,0]=value
    path=tmp_path/'edited.glb';output_index=encode(actor['rig'],0,[node],[channel],controls,[30.],path)
    decoded=RigAsset.load(path);reader=NativeSupportSampler(decoded.document,decoded.binary,output_index)
    actual=reader.sample(stamp)
    np.testing.assert_allclose(actual,world,atol=2e-7,rtol=0)
    np.testing.assert_allclose(decoded.vertices(actual),vertices,atol=2e-7,rtol=0)
    assert decoded.document['nodes']==actor['rig'].document['nodes']
    assert decoded.binary[:len(actor['rig'].binary)]==actor['rig'].binary
    fraction=rotation_fractions(actor,dict(sampler=reader),[stamp],[node],[30.])[0]
    assert abs(fraction-np.linalg.norm(value))<2e-7


@pytest.mark.parametrize('boundary_edit',[False,True])
def test_affine_initializer_and_fresh_audit_keep_original_epoch_and_endpoints(tmp_path,boundary_edit):
    source,scene,contacts,policy,request=affine_setup(tmp_path)
    if boundary_edit:
        request.update(boundary_keys=dict(start='edit',end='preserve'),acknowledge_changed_boundary_compatibility=True,frozen_times_s=[scene.duration])
    geometry=tmp_path/'geometry.json';declaration=tmp_path/'request.json';save(geometry,policy);save(declaration,request)
    original=source.read_bytes();out=tmp_path/'proposal';result=run(contacts,geometry,declaration,out)
    assert result['sampled_conditions_pass'] and result['pose_representation']=='native-trs-v1'
    assert result['orientation_mode']=='right-polar-v1' and result['failed_original_rate_rows']==0
    assert result.get('boundary_contract_changed',False) is boundary_edit
    assert result['root_world_element_error']==0 and source.read_bytes()==original
    journal=[json.loads(line) for line in (out/'key-results.jsonl').read_text().splitlines()]
    assert journal==read(out/'key-results.json') and len(journal)==result['keys']
    checked=replay(out,tmp_path/'replay',sha256(out/'result.json'),sha256(out/'request.json'))
    assert checked['exact_glb_and_complete_arrays'] and not checked['optimizer_executed']
    assert checked['sampled_conditions_pass'] and not checked['quality_approved']
    with np.load(out/'motion-observations.npz') as observed:
        assert np.array_equal(observed['source_world'],observed['candidate_world'])
        assert np.array_equal(observed['source_right_stretch'],observed['candidate_right_stretch'])


@pytest.mark.parametrize('key,value',[('pose_representation','automatic'),('orientation_mode','automatic')])
def test_unknown_affine_modes_do_not_silently_relax_request(tmp_path,key,value):
    _,scene,contacts,policy,request=affine_setup(tmp_path);request[key]=value
    with pytest.raises(ValueError,match='modes'):prepare(scene,request,sha256(contacts),policy)


def test_legacy_rigid_pose_still_rejects_nonrigid_local_bases(tmp_path):
    _,scene,_,policy,_=affine_setup(tmp_path)
    with pytest.raises(ValueError,match='Proper rigid'):
        KeyPose(scene,'A',1.,[3],[30.],.22,policy['planes'],.005,.0005)


def test_endpoint_edits_require_exact_intent_and_do_not_freeze_the_requested_start():
    clock=[0.,.5,1.];request=dict(window_s=[0.,1.],frozen_times_s=[0.,1.])
    assert boundary_policy(request,clock)==dict(start='preserve',end='preserve')
    assert key_frozen(request,clock,0.) and key_frozen(request,clock,1.)
    request.update(boundary_keys=dict(start='edit',end='preserve'),acknowledge_changed_boundary_compatibility=True,frozen_times_s=[1.])
    assert not key_frozen(request,clock,0.) and not key_frozen(request,clock,.5)
    assert key_frozen(request,clock,1.) and key_frozen(request,clock,1.1)


@pytest.mark.parametrize('fault',['missing-ack','false-ack','frozen-edit','missing-preserved','unknown'])
def test_invalid_boundary_contract_rejects(fault):
    request=dict(window_s=[0.,1.],frozen_times_s=[1.],boundary_keys=dict(start='edit',end='preserve'),acknowledge_changed_boundary_compatibility=True)
    if fault=='missing-ack':request.pop('acknowledge_changed_boundary_compatibility')
    elif fault=='false-ack':request['acknowledge_changed_boundary_compatibility']=False
    elif fault=='frozen-edit':request['frozen_times_s']=[0.,1.]
    elif fault=='missing-preserved':request['frozen_times_s']=[]
    else:request['boundary_keys']['start']='automatic'
    with pytest.raises(ValueError):boundary_policy(request,[0.,.5,1.])


@pytest.mark.parametrize('edited',['start','end'])
def test_interior_channel_endpoint_cannot_authorize_edits_to_held_clip_boundary(tmp_path,edited):
    source,scene,contacts,policy,request=affine_setup(tmp_path);actor=scene.actors['A'];rig=actor['rig']
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=document['animations'][0]
    channel=next(c for c in actor['sampler'].channels if c[:2]==(3,'rotation'))
    clock=channel[2][1:-1];values=channel[3][1:-1]
    target=next(c for c in animation['channels'] if c['target']==dict(node=3,path='rotation'))
    target['sampler']=len(animation['samplers'])
    animation['samplers'].append(dict(input=append_accessor(document,binary,clock,'SCALAR'),
        output=append_accessor(document,binary,values,'VEC4'),interpolation='LINEAR'))
    write_glb(source,document,binary);spec=read(contacts);spec['actors']['A']['sha256']=sha256(source);save(contacts,spec)
    scene=SceneContacts(spec,tmp_path);assert 0<float(clock[0])<float(clock[-1])<scene.duration
    request.update(contacts_sha256=sha256(contacts),window_s=[float(clock[0]),float(clock[-1])],
        frozen_times_s=[float(clock[-1] if edited=='start' else clock[0])],
        boundary_keys={edge:('edit' if edge==edited else 'preserve') for edge in ('start','end')},
        acknowledge_changed_boundary_compatibility=True)
    policy['contacts_sha256']=sha256(contacts)
    with pytest.raises(ValueError,match='actual clip boundary'):prepare(scene,request,sha256(contacts),policy)
    preserved=copy.deepcopy(request);preserved.pop('boundary_keys');preserved.pop('acknowledge_changed_boundary_compatibility')
    preserved['frozen_times_s']=[float(clock[0]),float(clock[-1])]
    assert np.array_equal(prepare(scene,preserved,sha256(contacts),policy)[3],clock)


def test_timeout_retains_completed_key_journal_and_last_evaluated_pose(tmp_path,monkeypatch):
    source,_,contacts,policy,request=affine_setup(tmp_path)
    geometry=tmp_path/'geometry.json';declaration=tmp_path/'request.json';save(geometry,policy);save(declaration,request)
    def stop(self,*args):
        self.evaluate(np.zeros(3*len(self.nodes)))
        raise TimeoutError('forced owned-job budget stop')
    monkeypatch.setattr(KeyPose,'solve',stop)
    output=tmp_path/'interrupted'
    with pytest.raises(TimeoutError):run(contacts,geometry,declaration,output)
    with np.load(output/'key-checkpoint.npz') as data:assert int(data['completed_keys'])==1
    assert len((output/'key-results.jsonl').read_text().splitlines())==1
    assert read(output/'failed-key.json')['completed_keys']==1
    assert (output/'failed-key-observations.npz').is_file()
    assert not (output/'result.json').exists() and not (output/'character.glb').exists()


def test_nested_affine_rotations_preserve_moving_object_centroid_derivatives(tmp_path):
    source,scene,contacts,policy,request=affine_setup(tmp_path);rig=scene.actors['A']['rig']
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=document['animations'][0]
    if not any(c['target']==dict(node=2,path='rotation') for c in animation['channels']):
        existing=next(c for c in animation['channels'] if c['target']==dict(node=3,path='rotation'))
        clock=animation['samplers'][existing['sampler']]['input'];count=document['accessors'][clock]['count']
        values=np.tile(document['nodes'][2].get('rotation',[0.,0.,0.,1.]),(count,1))
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=2,path='rotation')))
        animation['samplers'].append(dict(input=clock,output=append_accessor(document,binary,values,'VEC4'),interpolation='LINEAR'))
    write_glb(source,document,binary);spec=read(contacts);spec['actors']['A']['sha256']=sha256(source)
    spec['objects']['prop']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[1.,1.,1.]),keyframes=[
        dict(time_s=0.,translation_m=[0.,0.,0.],rotation_xyzw=[0.,0.,0.,1.]),
        dict(time_s=spec['duration_s'],translation_m=[.3,0.,.2],rotation_xyzw=Rotation.from_euler('yz',[40.,10.],degrees=True).as_quat().tolist())])
    spec['contacts'][0].update(vertices=[[6,0,0],[6,0,1]],reduction='centroid',target=dict(space='object',object='prop',points_m=[[0.,.5,0.]]),interval_s=[1.,1.],limits=dict(position_m=.05))
    scene=SceneContacts(spec,tmp_path)
    pose=KeyPose(scene,'A',1.,[2,3],[30.,30.],.22,policy['planes'],.005,.0005,pose_representation='native-trs-v1')
    value=np.array([.04,.09,-.03,-.05,.07,.1]);_,jac,*_=pose.evaluate(value);fd=[]
    for i in range(6):
        delta=np.eye(6)[i]*1e-6
        fd.append((pose.evaluate(value+delta)[0]-pose.evaluate(value-delta)[0])/2e-6)
    np.testing.assert_allclose(jac,np.stack(fd,axis=1),atol=2e-5,rtol=2e-7)
