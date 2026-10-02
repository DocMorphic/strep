"""Explicit planting requirements, real offline jobs and bound serving."""
from pathlib import Path
from types import SimpleNamespace
import sys
import copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_native_support import setup
from test_native_foot_plant import setup as plant_fixture
import studio_native_support as studio
import rig_contact_authoring
from native_studio_plant import settings
from strep import read,save,sha256


@pytest.mark.parametrize('choice',[None,True,{},[],{'maximum_patch_anchor_error_m':.001},
    {'maximum_patch_anchor_error_m':True,'maximum_patch_speed_m_s':.005},
    {'maximum_patch_anchor_error_m':.031,'maximum_patch_speed_m_s':.005},
    {'maximum_patch_anchor_error_m':.001,'maximum_patch_speed_m_s':float('nan')},
    {'maximum_patch_anchor_error_m':.001,'maximum_patch_speed_m_s':-.005},
    {'maximum_patch_anchor_error_m':.001,'maximum_patch_speed_m_s':.005,'iterations':100}])
def test_explicit_bounded_precision_required(setup,choice):
    with pytest.raises(ValueError):studio.validate_request(dict(setup.body,planting=choice))


@pytest.mark.parametrize('mode',['prepare_rigid_input','sampled_support_repair','joint_source_rate_search'])
def test_planting_requires_a_single_method_and_already_rigid_source(setup,mode):
    body=dict(setup.body,planting=dict(maximum_patch_anchor_error_m=.001,maximum_patch_speed_m_s=.005),**{mode:True})
    with pytest.raises(ValueError):studio.validate_request(body)


def complete(tmp_path,monkeypatch,*,moving=False):
    source,rig,reader,spec,draft,policy,rows,limits=plant_fixture(tmp_path,moving=moving)
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    def bound(job,variant):
        if job!='parent' or variant!='transfer':raise ValueError('Wrong source')
        return tmp_path,dict(label='Toy planted motion'),None,dict(root_node=0,mapping=dict(LeftLeg=1,LeftShin=2,LeftFoot=3)),source
    monkeypatch.setattr(rig_contact_authoring,'source',bound)
    choice={k:v for k,v in policy['supports'][0].items() if k!='id'}
    body=dict(source_job='parent',variant='transfer',spec=spec,planting=choice)
    folder=studio.folder_for('plant-toy');studio.prepare(body,folder);studio.run(folder)
    return SimpleNamespace(source=source,spec=spec,choice=choice,folder=folder,output=tmp_path/'reports/native-support-fit-plant-toy')


def test_satisfactory_toy_retains_exact_source_and_exposes_bound_contact_audit(tmp_path,monkeypatch):
    data=complete(tmp_path,monkeypatch);manifest=studio.manifest('plant-toy')
    assert manifest['retained_input'] and manifest['output_planting_samples_pass']
    assert manifest['planting']['limits']==data.choice
    assert len(manifest['trials'])==1
    assert read(data.output/'joint/result.json')['optimization']['iterations']==0
    assert not (data.output/'coordinates').exists()
    assert sha256(data.output/'candidate.glb')==sha256(data.source)
    assert manifest['planting']['selected_audit']['contacts'][0]['maximum_patch_anchor_error_m']==0
    assert manifest['planting']['selected_audit']['authored_clearance_pass']
    assert not manifest['quality_approved']
    for name in ('plant-policy.json','trial-0-planting.json','trial-0.controls.json','plant-seed.glb','candidate.glb'):
        assert studio.served_file('native-support-jobs/plant-toy/'+name)==data.output/name
    markers=read(studio.served_file(manifest['events_url'].removeprefix('/files/')))
    assert markers['target_clip_sha256']==sha256(data.source) and markers['constraint_status']=='satisfied_at_samples'
    assert read(data.folder/'draft.json')==data.spec


def test_real_failed_joint_and_coordinate_searches_retain_source_and_markers(tmp_path,monkeypatch):
    data=complete(tmp_path,monkeypatch,moving=True);manifest=studio.manifest('plant-toy')
    assert manifest['retained_input'] and not manifest['output_planting_samples_pass']
    assert len(manifest['trials'])==2
    assert sha256(data.output/'candidate.glb')==sha256(data.source)
    assert read(data.output/'joint/result.json')['optimization']['maximum_iterations']==8
    assert read(data.output/'coordinates/result.json')['optimization']['method']=='quantized_coordinate_search'
    assert manifest['planting']['selected_audit']['contacts'][0]['maximum_patch_anchor_error_m']>.001
    assert read(data.output/'support-events.json')['constraint_status']=='unverified_on_retained_input'
    assert not read(data.output/'result.json')['release_approved']


def test_policy_and_method_changes_cannot_be_served_even_after_shallow_rebinding(tmp_path,monkeypatch):
    data=complete(tmp_path,monkeypatch)
    policy=data.folder/'plant-policy.json';original=policy.read_bytes()
    changed=read(policy);changed['supports'][0]['maximum_patch_speed_m_s']*=2;save(policy,changed)
    request=read(data.folder/'request.json');request['plant_policy_sha256']=sha256(policy);save(data.folder/'request.json',request)
    prepared=read(data.folder/'prepared.json');prepared['request_sha256']=sha256(data.folder/'request.json');save(data.folder/'prepared.json',prepared)
    with pytest.raises(ValueError,match='policy'):studio.frozen(data.folder)
    assert studio.served_file('native-support-jobs/plant-toy/candidate.glb') is None
    policy.write_bytes(original);request['plant_policy_sha256']=sha256(policy);save(data.folder/'request.json',request)
    prepared['request_sha256']=sha256(data.folder/'request.json');save(data.folder/'prepared.json',prepared)
    (data.folder/'implementation/native_studio_plant.py').write_bytes(b'changed')
    with pytest.raises(ValueError,match='archive'):studio.frozen(data.folder)
