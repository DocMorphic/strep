"""Complete native-key initialization, analytic skin and retained clip failures."""
from pathlib import Path
import copy,sys,time
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_key_contact_initializer import KeyPose,prepare,run,SCHEMA
from native_scene_contacts import SceneContacts
from rig_asset import RigAsset
from strep import save,sha256,read
from test_native_component_storage import fixture
from test_native_scene_geometry import policy as geometry_policy


def setup(tmp_path):
    base,_,_,contacts,*_=fixture(tmp_path);scene=SceneContacts(read(contacts),tmp_path)
    policy=geometry_policy(contacts,mode='native-and-frame-populations',planes=dict(ground=dict(normal_world=[0.,1.,0.],offset_m=-1.)))
    request=dict(schema=SCHEMA,contacts_sha256=sha256(contacts),actor='A',root_node=0,
        rotations=[dict(node=3,maximum_degrees=30.)],window_s=[0.,scene.duration],frozen_times_s=[0.,scene.duration],
        maximum_joint_displacement_m=.22,maximum_keys=100,iterations_per_key=40,maximum_seconds=60.,floor_reserve_m=.0005)
    return base,scene,contacts,policy,request


@pytest.mark.parametrize('incoming',[False,True])
@pytest.mark.parametrize('homogeneous',[False,True])
def test_complete_analytic_derivative_matches_central_pose_difference(tmp_path,incoming,homogeneous):
    _,_,contacts,policy,request=setup(tmp_path);spec=read(contacts)
    spec['contacts'][0].update(interval_s=[1.,1.],limits=dict(position_m=.05))
    if incoming:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['contacts'][0].update(actor='B',target=dict(space='actor',actor='A',vertices=[[6,0,0]],reduction='individual'))
    spec['actors']['A']['placement']['rotation_xyzw']=Rotation.from_euler('xyz',[12.,34.,-9.],degrees=True).as_quat().tolist()
    scene=SceneContacts(spec,tmp_path)
    if homogeneous:scene.actors['A']['skin'].points[:,:,3]*=np.linspace(.95,1.05,scene.actors['A']['skin'].points.shape[1])
    pose=KeyPose(scene,'A',1.,[3],[30.],.22,policy['planes'],.005,.0005);value=np.array([.05,-.12,.08])
    rows,jac,_,vertices=pose.evaluate(value);fd=[]
    for i in range(3):
        delta=np.eye(3)[i]*1e-6
        fd.append((pose.evaluate(value+delta)[0]-pose.evaluate(value-delta)[0])/2e-6)
    np.testing.assert_allclose(jac,np.stack(fd,axis=1),atol=2e-5,rtol=2e-7)
    assert len(vertices)==len(scene.actors['A']['skin'].nodes)
    assert len(rows)==1+len(scene.actors['A']['rig'].joints)+len(pose.used)+1


@pytest.mark.parametrize('fault',['hash','root-edit','cap','displacement','keys','endpoint','budget','window-between-keys','window-type','frozen-type','row-budget'])
def test_invalid_or_incomplete_key_contract_rejects(tmp_path,fault):
    _,scene,contacts,policy,request=setup(tmp_path)
    if fault=='hash':request['contacts_sha256']='0'*64
    elif fault=='root-edit':request['rotations'][0]['node']=0
    elif fault=='cap':request['rotations'][0]['maximum_degrees']=30.01
    elif fault=='displacement':request['maximum_joint_displacement_m']=.22001
    elif fault=='keys':request['maximum_keys']=2
    elif fault=='endpoint':request['frozen_times_s']=[0.]
    elif fault=='budget':request['maximum_seconds']=601
    elif fault=='window-between-keys':request['window_s'][0]=.031234
    elif fault=='window-type':request['window_s'][0]=False
    elif fault=='frozen-type':request['frozen_times_s'][0]='0'
    elif fault=='row-budget':policy['planes']={str(i):dict(normal_world=[0.,1.,0.],offset_m=-1.) for i in range(50000)}
    with pytest.raises(ValueError):prepare(scene,request,sha256(contacts),policy)


def test_actual_feasible_sequence_preserves_native_clock_payload_and_original_caps(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    base,scene,contacts,policy,request=setup(tmp_path);gp=tmp_path/'geometry.json';rp=tmp_path/'request.json';save(gp,policy);save(rp,request)
    source=Path(next(iter(scene.inputs)));original=RigAsset.load(source);output=tmp_path/'output';result=run(contacts,gp,rp,output)
    proposed=RigAsset.load(output/'character.glb')
    assert proposed.binary[:len(original.binary)]==original.binary and proposed.document['animations'][:-1]==original.document['animations']
    assert result['sampled_conditions_pass'] and result['root_world_element_error']==0
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert all(sha256(path)==digest for path,digest in base.scene.inputs.items())
    with np.load(output/'key-controls.npz') as keys:
        np.testing.assert_array_equal(keys['times_s'],next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation')))
        assert not np.any(keys['controls'])
    with np.load(output/'motion-observations.npz') as data:
        np.testing.assert_array_equal(data['source_world'],data['candidate_world'])
        assert np.all(data['rate_residual']<=0)


def test_frozen_conflict_is_recorded_and_cannot_approve_sequence(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    _,_,contacts,policy,request=setup(tmp_path);spec=read(contacts)
    spec['contacts'][0]['target']['points_m'][0][0]+=.03;save(contacts,spec)
    request['contacts_sha256']=policy['contacts_sha256']=sha256(contacts)
    gp=tmp_path/'geometry.json';rp=tmp_path/'request.json';save(gp,policy);save(rp,request)
    result=run(contacts,gp,rp,tmp_path/'rejected')
    assert not result['contact_samples_pass'] and not result['sampled_conditions_pass']
    assert result['pose_failures']>0 and result['original_selected']


def test_failed_single_pose_keeps_zero_and_no_solver_flag_promotes_it(tmp_path):
    _,scene,_,policy,_=setup(tmp_path)
    pose=KeyPose(scene,'A',1.,[3],[30.],.22,dict(ceiling=dict(normal_world=[0.,1.,0.],offset_m=100.)),.005,.0005)
    value,result=pose.solve(1,time.monotonic()+60)
    assert result['solved'] and not result['pose_conditions_pass'] and result['failed_pose_retains_original']
    assert not np.any(value)
