"""Repeated correction cannot trade a new scene failure for fewer rate failures."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_key_interval_restoration import validate,geometry_conditions,geometry_face_state,retain,run,SCHEMA
from native_key_contact_initializer import run as initialize
from strep import save,read,sha256
from test_native_key_contact_initializer import setup


def geometry(depths=(.007,.002),state='outside'):
    return dict(limits=dict(penetration_m=.005),samples=[dict(time_s=0.,conditions_available=True,degenerate_faces=dict(A=[]),
        world_planes=[dict(actor='A',plane=str(i),maximum_depth_m=d,passed=d<=.005) for i,d in enumerate(depths)],
        actor_objects=[dict(actor='A',object='box',maximum_depth_upper_m=0.,containment=dict(status=state,signed_center_distance_m=-.1),passed=state=='outside')],actor_pairs=[])])


def observed(report,rate=2.,prefix=True):
    identity,values=geometry_conditions(report);full=np.r_[rate,values];positive=np.maximum(full,0)
    return dict(full=full,geometry_identity=identity,geometry_face_state=geometry_face_state(report),record=dict(decoded_prefix_pass=prefix,score=[float(positive.max()),float(positive@positive),int((full>0).sum())]))


def test_new_plane_failure_rejects_even_when_global_worst_depth_and_rates_improve():
    before=observed(geometry());after=observed(geometry((.006,.0051)),rate=1.)
    assert not retain(before,after)
    assert retain(before,observed(geometry((.005,.002)),rate=1.))


def test_new_object_enclosure_or_prefix_failure_cannot_be_traded_for_rate_repair():
    before=observed(geometry())
    assert not retain(before,observed(geometry(state='inside'),rate=.1))
    assert not retain(before,observed(geometry((.004,.002)),rate=.1,prefix=False))


def test_partner_crossing_and_containment_have_separate_guard_rows():
    report=geometry();report['samples'][0]['actor_pairs']=[dict(actors=['A','B'],passed=True,
        surface=dict(records=[],degenerate_faces=[[],[]]),vertex_containment=[dict(source='A',target='B',available=True,max_depth_m=0.,vertices_over_tolerance=0),
        dict(source='B',target='A',available=True,max_depth_m=0.,vertices_over_tolerance=0)])]
    before=observed(report);after=copy.deepcopy(report)
    after['samples'][0]['actor_pairs'][0]['surface']['records']=[dict(crossing=True)];after['samples'][0]['actor_pairs'][0]['passed']=False
    assert not retain(before,observed(after,rate=.1))


def test_same_count_cannot_hide_a_new_degenerate_face():
    before=geometry();before['samples'][0]['degenerate_faces']['A']=[1]
    after=copy.deepcopy(before);after['samples'][0]['degenerate_faces']['A']=[2]
    assert not retain(observed(before),observed(after,rate=.1))


def test_missing_condition_or_clock_cannot_become_a_shorter_passing_audit():
    before=observed(geometry());report=geometry();report['samples'][0]['world_planes'].pop()
    with pytest.raises(ValueError,match='condition population'):retain(before,observed(report))


def recipe(producer):
    return dict(schema=SCHEMA,producer=dict(path=str(producer),result_sha256='a'*64,request_sha256='b'*64),active_keys=[3,4,5],iterations=2,trust=.02,difference_step=.001,backoffs=8,maximum_seconds=600.)


@pytest.mark.parametrize('field,value',[('iterations',True),('iterations',5),('trust',.020001),('trust',float('nan')),('difference_step',0.),('backoffs',0),('maximum_seconds',751),('active_keys',[True,2])])
def test_invalid_effort_rejects_before_source_loading(field,value):
    value_recipe=recipe('unused');value_recipe[field]=value
    with pytest.raises(ValueError):validate(value_recipe)


def test_public_workflow_preserves_passing_clip_and_does_not_invent_release_approval(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'lock')
    _,_,contacts,policy,request=setup(tmp_path);gp=tmp_path/'geometry.json';rp=tmp_path/'initializer.json';save(gp,policy);save(rp,request)
    producer=tmp_path/'producer';initialize(contacts,gp,rp,producer)
    payload=recipe(producer);payload['producer'].update(result_sha256=sha256(producer/'result.json'),request_sha256=sha256(producer/'request.json'))
    config=tmp_path/'recipe.json';save(config,payload);output=tmp_path/'restoration';result=run(config,output)
    assert result['sampled_conditions_pass'] and result['stop_reason']=='sampled_conditions_pass' and result['history']==[]
    assert result['original_selected'] and not result['quality_approved'] and not result['training_admitted'] and not result['release_approved']
    assert result['source_request_sha256']==sha256(output/'request.json')
    assert sha256(producer/'character.glb')==sha256(output/'probes/start/character.glb')==sha256(output/'probes/final/character.glb')
    with np.load(output/'probes/start/observations.npz') as before,np.load(output/'probes/final/observations.npz') as after:
        assert before.files==after.files
        for name in before.files:np.testing.assert_array_equal(before[name],after[name])
