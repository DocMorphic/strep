"""Studio mixed repair and explicit boundary authoring without source rebasing."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_fit as studio
import studio_native_scene as scenes
from studio_native_storage import COMPONENT_SCHEMA
from test_native_component_storage import fixture
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256


def setup(tmp_path,monkeypatch,*,edges=False,speed=False):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(scenes,'ROOT',tmp_path)
    inputs=tmp_path/'reports/rig-jobs/source/input';inputs.mkdir(parents=True)
    base,_,_,contacts,_,_=fixture(inputs,boundaries=edges)
    source=Path(next(iter(base.scene.inputs)));spec=read(contacts);url='/files/rig-jobs/source/input/'+source.name
    spec['actors']['A']['glb']=url
    payload=dict(schema=COMPONENT_SCHEMA,draft=dict(schema='strep-studio-native-scene-v1',scene=spec,
        geometry=dict(clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),
            limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
            planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.))),object_edit=None),
        actors=copy.deepcopy(base.request['permissions']['actors']),options=dict(iterations=1),resume_from=None,
        rotation_speed_limits=[dict(actor='A',node=3,maximum_degrees_per_second=0.)] if speed else [],
        export_repair=dict(stages=2,probes=8),boundary_keys=copy.deepcopy(base.boundary_keys),
        acknowledge_changed_boundary_compatibility=edges)
    return payload,source,lambda candidate:source if candidate==url else None


@pytest.mark.parametrize('edges',[False,True])
@pytest.mark.parametrize('speed',[False,True])
def test_complete_mixed_studio_job_and_exact_continuation(tmp_path,monkeypatch,edges,speed):
    payload,source,resolver=setup(tmp_path,monkeypatch,edges=edges,speed=speed);before=copy.deepcopy(payload);digest=sha256(source)
    first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    review=studio.manifest('first');assert review['native_conditions_pass'] and review['geometry_conditions_pass']
    assert review['controls']==(30 if edges else 18) and review['authoring_request']==before and review['original_selected']
    assert not review['quality_approved'] and sha256(source)==digest and payload==before
    policy=read(first/'storage-repair-policy.json');assert policy['schema']=='strep-native-component-storage-repair-v1'
    assert policy['allowed_paths']==['rotation','translation'] and read(first/'boundary-edit.json')['boundary_keys']==payload['boundary_keys']
    state=read(first/'fit/final-storage-continuation.json');assert state['schema']=='strep-native-component-storage-continuation-v1'
    assert 'native_fit_component_storage.py' in read(first/'fit/request.json')['implementation_sha256']
    payload['resume_from']='first';second=studio.folder_for('second');studio.prepare(payload,second,resolver);studio.run(second)
    continued=studio.manifest('second');assert continued['native_conditions_pass']
    assert read(second/'storage-continuation.json')==state and sha256(first/'fit/source-rate-caps.npz')==sha256(second/'fit/source-rate-caps.npz')
    if speed:assert review['rotation_speed_conditions_pass'] and continued['rotation_speed_conditions_pass']


@pytest.mark.parametrize('fault',['missing','extra-actor','bad-mode','extra-edge','ack-false','ack-string','ack-unneeded','protected','internal-window','capacity'])
def test_bad_boundary_contract_creates_no_job(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch,edges=True)
    if fault=='missing':payload.pop('boundary_keys')
    elif fault=='extra-actor':payload['boundary_keys']['B']=dict(start='preserve',end='preserve')
    elif fault=='bad-mode':payload['boundary_keys']['A']['start']='whatever'
    elif fault=='extra-edge':payload['boundary_keys']['A']['middle']='edit'
    elif fault=='ack-false':payload['acknowledge_changed_boundary_compatibility']=False
    elif fault=='ack-string':payload['acknowledge_changed_boundary_compatibility']='true'
    elif fault=='ack-unneeded':payload['boundary_keys']['A']=dict(start='preserve',end='preserve')
    elif fault=='protected':payload['actors']['A']['protected_s']=[[0.,.1]]
    elif fault=='internal-window':payload['actors']['A']['window_s'][0]=.1;payload['actors']['A']['knots_s'][0]=.1
    else:
        payload['actors']['A']['knots_s']=np.linspace(0,2,12).tolist()
        payload['actors']['A']['tracks']+=[dict(node=n,path='rotation',maximum_change=30.) for n in (1,2)]
    job=studio.folder_for('invalid')
    with pytest.raises(ValueError):studio.prepare(payload,job,resolver)
    assert not job.exists()


@pytest.mark.parametrize('fault',['edges','ack','mode','policy','state'])
def test_continuation_or_review_cannot_change_mixed_epoch(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch);first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    if fault in ('policy','state'):
        target=first/('fit/storage-repair-policy.json' if fault=='policy' else 'fit/final-storage-continuation.json');target.write_bytes(b'changed')
        with pytest.raises((ValueError,OSError)):studio.manifest('first')
        return
    payload['resume_from']='first'
    if fault=='edges':payload['boundary_keys']['A']['start']='edit';payload['acknowledge_changed_boundary_compatibility']=True
    elif fault=='ack':payload['acknowledge_changed_boundary_compatibility']=True
    else:payload['schema']='strep-studio-native-scene-fit-v3';payload.pop('boundary_keys');payload.pop('acknowledge_changed_boundary_compatibility')
    second=studio.folder_for('second')
    with pytest.raises(ValueError):studio.prepare(payload,second,resolver)
    assert not second.exists()


def test_two_native_keys_can_be_edited_at_explicit_edges(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch,edges=True);rig=RigAsset.load(source)
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=doc['animations'][0]
    channel=next(c for c in animation['channels'] if c['target']==dict(node=0,path='translation'))
    sampler=animation['samplers'][channel['sampler']]
    sampler['input']=append_accessor(doc,binary,[0.,2.],'SCALAR');sampler['output']=append_accessor(doc,binary,[[0.,1.2,0.],[0.,1.2,0.]],'VEC3')
    write_glb(source,doc,binary);payload['draft']['scene']['actors']['A']['sha256']=sha256(source)
    payload['actors']['A']['tracks']=[dict(node=0,path='translation',maximum_change=.02)]
    payload['actors']['A']['knots_s']=[0.,1.,2.]
    channel=next(c for c in studio.catalog(payload['draft'],resolver)['actors']['A']['channels'] if (c['node'],c['path'])==(0,'translation'))
    assert channel['keys']==2 and channel['clip_edge_eligible'] and not channel['eligible']
    job=studio.folder_for('two-keys');studio.prepare(payload,job,resolver);studio.run(job)
    assert studio.manifest('two-keys')['native_conditions_pass'] and studio.frozen(job)['controls']==9


def test_mixed_floor_failure_is_visible_but_native_state_can_continue(tmp_path,monkeypatch):
    payload,_,resolver=setup(tmp_path,monkeypatch);payload['draft']['geometry']['planes']['floor']['offset_m']=.5
    job=studio.folder_for('failed-floor');studio.prepare(payload,job,resolver);studio.run(job)
    review=studio.manifest(job.name);assert review['native_conditions_pass'] and not review['geometry_conditions_pass'] and review['original_selected']
    payload['resume_from']=job.name;second=studio.folder_for('second');studio.prepare(payload,second,resolver)
    assert studio.frozen(second)['resume_from']==job.name
