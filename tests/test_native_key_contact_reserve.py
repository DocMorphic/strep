"""Solver contact margins retain authored decoded acceptance and source epochs."""
import copy,time
from pathlib import Path
import numpy as np
import pytest
from test_native_affine_key_pose import affine_setup
from native_key_contact_initializer import KeyPose,prepare,run,encode,contact_reserve
from audit_native_key_initializer import run as replay,bound
from native_scene_contacts import SceneContacts
from strep import read,save,sha256


@pytest.mark.parametrize('value',[True,False,-.001,float('inf'),float('nan'),'.001',.00001,.01])
def test_invalid_or_oversized_margin_rejects_before_solving(tmp_path,value):
    _,scene,contacts,policy,request=affine_setup(tmp_path);request['contact_reserve_m']=value
    with pytest.raises(ValueError,match='Contact reserve'):prepare(scene,request,sha256(contacts),policy)


def test_margin_checks_incoming_contacts_and_requires_affected_intent(tmp_path):
    _,_,contacts,_,_=affine_setup(tmp_path);spec=read(contacts)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['contacts'][0].update(actor='B',target=dict(space='actor',actor='A',vertices=[[6,0,0]],reduction='individual'))
    scene=SceneContacts(spec,tmp_path)
    with pytest.raises(ValueError,match='every affected'):contact_reserve(scene,'A',.00001)
    assert contact_reserve(scene,'A',.000001)==.000001
    spec['contacts']=[];scene=SceneContacts(spec,tmp_path)
    assert contact_reserve(scene,'A',0.)==0.
    with pytest.raises(ValueError,match='every affected'):contact_reserve(scene,'A',.000001)


def test_margin_tightens_only_contact_rows_and_keeps_complete_derivatives(tmp_path):
    _,_,contacts,policy,_=affine_setup(tmp_path);spec=read(contacts)
    spec['contacts'][0].update(interval_s=[1.,1.],limits=dict(position_m=.05))
    scene=SceneContacts(spec,tmp_path);args=(scene,'A',1.,[3],[30.],.22,policy['planes'],.005,.0005)
    plain=KeyPose(*args,pose_representation='native-trs-v1')
    reserved=KeyPose(*args,pose_representation='native-trs-v1',contact_reserve_m=.001)
    value=np.array([.08,-.05,.1]);a=plain.evaluate(value);b=reserved.evaluate(value)
    np.testing.assert_array_equal(a[0][:-1],b[0][:-1]);np.testing.assert_array_equal(a[1],b[1])
    np.testing.assert_allclose(b[0][-1]-a[0][-1],((.05-.001)**2-.05**2)/.05**2,atol=1e-13)
    fd=[]
    for i in range(3):
        delta=np.eye(3)[i]*1e-6;fd.append((reserved.evaluate(value+delta)[0]-reserved.evaluate(value-delta)[0])/2e-6)
    np.testing.assert_allclose(b[1],np.stack(fd,axis=1),atol=2e-5,rtol=2e-7)
    assert spec['contacts'][0]['limits']['position_m']==.05


def test_solved_contact_keeps_margin_after_actual_quaternion_export(tmp_path):
    source,scene,contacts,policy,_=affine_setup(tmp_path);actor=scene.actors['A']
    channel=next(c for c in actor['sampler'].channels if c[:2]==(3,'rotation'));index=len(channel[2])//2;stamp=float(channel[2][index])
    args=(scene,'A',stamp,[3],[30.],.22,policy['planes'],.005,.0005)
    guide=KeyPose(*args,pose_representation='native-trs-v1');before=guide.evaluate(np.zeros(3))[3]
    target=guide.evaluate(np.array([.45,0.,0.]))[3];vertex=int(np.linalg.norm(target-before,axis=1).argmax())
    assert np.linalg.norm(target[vertex]-before[vertex])>.01
    spec=read(contacts);spec['contacts'][0].update(vertices=[actor['skin'].vertex_references[vertex].tolist()],
        target=dict(space='world',points_m=[target[vertex].tolist()]),interval_s=[stamp,stamp],limits=dict(position_m=.005))
    scene=SceneContacts(spec,tmp_path)
    pose=KeyPose(scene,'A',stamp,[3],[30.],.22,policy['planes'],.005,.0005,pose_representation='native-trs-v1',contact_reserve_m=.0005)
    value,record=pose.solve(40,time.monotonic()+60);assert record['pose_conditions_pass']
    controls=np.zeros((len(channel[2]),1,3));controls[index,0]=value
    output=tmp_path/'edited.glb';new_index=encode(actor['rig'],0,[3],[channel],controls,[30.],output)
    spec['actors']['A'].update(glb=str(output),sha256=sha256(output),animation_index=new_index)
    report,_=SceneContacts(spec,tmp_path).evaluate()
    assert report['passed'] and report['contacts'][0]['maximum_position_error_m']<.00451
    assert spec['contacts'][0]['limits']['position_m']==.005


def test_public_request_result_and_fresh_audit_bind_the_explicit_margin(tmp_path):
    _,scene,contacts,policy,request=affine_setup(tmp_path);request['contact_reserve_m']=.000001
    geometry=tmp_path/'geometry.json';declaration=tmp_path/'request.json';save(geometry,policy);save(declaration,request)
    out=tmp_path/'proposal';result=run(contacts,geometry,declaration,out)
    assert result['contact_reserve_m']==.000001 and result['sampled_conditions_pass']
    checked=replay(out,tmp_path/'replay',sha256(out/'result.json'),sha256(out/'request.json'))
    assert checked['exact_glb_and_complete_arrays'] and not checked['optimizer_executed']
    result['contact_reserve_m']=0.;save(out/'result.json',result)
    with pytest.raises(ValueError,match='solver contact reserve changed'):
        bound(out,sha256(out/'result.json'),sha256(out/'request.json'))
