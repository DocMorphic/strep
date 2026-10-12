"""Studio clearance jobs preserve original epochs and complete failed evidence."""
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_fit as studio
import studio_native_scene as scenes
from studio_native_storage import SCHEMA
from strep import read,save,sha256
from test_native_fit_storage import fixture


def setup(tmp_path,monkeypatch,*,speed=False):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(scenes,'ROOT',tmp_path)
    inputs=tmp_path/'reports/rig-jobs/source/transfer';inputs.mkdir(parents=True)
    base,_,_,contacts,_,_,_=fixture(inputs);source=Path(next(iter(base.scene.inputs)))
    spec=read(contacts);url='/files/rig-jobs/source/transfer/'+source.name;spec['actors']['A']['glb']=url
    geometry=dict(clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.)))
    payload=dict(schema=SCHEMA,draft=dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=geometry,object_edit=None),
        actors=copy.deepcopy(base.request['permissions']['actors']),options=dict(iterations=1),resume_from=None,
        rotation_speed_limits=[dict(actor='A',node=3,maximum_degrees_per_second=0.)] if speed else [],
        export_repair=dict(stages=2,probes=8))
    return payload,source,lambda candidate:source if candidate==url else None


@pytest.mark.parametrize('speed',[False,True])
def test_complete_studio_clearance_job_and_original_bound_continuation(tmp_path,monkeypatch,speed):
    payload,source,resolver=setup(tmp_path,monkeypatch,speed=speed);before=copy.deepcopy(payload);checksum=sha256(source)
    first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    manifest=studio.manifest('first');assert manifest['native_conditions_pass'] and manifest['geometry_conditions_pass']
    assert manifest['authoring_request']==before and manifest['original_selected'] and not manifest['quality_approved']
    assert payload==before and sha256(source)==checksum
    assert any(d['label']=='fit/final-storage-continuation.json' for d in manifest['downloads'])
    if speed:assert manifest['rotation_speed_conditions_pass']
    payload['resume_from']='first';second=studio.folder_for('second');studio.prepare(payload,second,resolver)
    assert read(second/'storage-continuation.json')==read(first/'fit/final-storage-continuation.json')
    studio.run(second);continued=studio.manifest('second');assert continued['native_conditions_pass']
    assert read(second/'fit/contacts.json')==read(first/'fit/contacts.json')
    assert sha256(second/'fit/source-rate-caps.npz')==sha256(first/'fit/source-rate-caps.npz')
    assert read(second/'fit/request.json')['resume'] is None
    assert read(second/'fit/request.json')['storage_continuation_sha256']==sha256(second/'storage-continuation.json')
    assert studio.served_file('native-scene-fit-jobs/second/fit/final-storage-continuation.json') is not None


@pytest.mark.parametrize('fault',['stages-bool','stages-zero','stages-large','probes-bool','probes-zero','probes-large','extra','speeds-type'])
def test_invalid_clearance_contract_creates_no_job(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch)
    if fault=='stages-bool':payload['export_repair']['stages']=True
    elif fault=='stages-zero':payload['export_repair']['stages']=0
    elif fault=='stages-large':payload['export_repair']['stages']=9
    elif fault=='probes-bool':payload['export_repair']['probes']=True
    elif fault=='probes-zero':payload['export_repair']['probes']=0
    elif fault=='probes-large':payload['export_repair']['probes']=65
    elif fault=='extra':payload['export_repair']['approve']=True
    else:payload['rotation_speed_limits']={}
    folder=studio.folder_for('bad')
    with pytest.raises(ValueError):studio.prepare(payload,folder,resolver)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['boundary','policy','method'])
def test_frozen_clearance_bindings_cannot_be_dropped(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('frozen');studio.prepare(payload,folder,resolver)
    name={'boundary':'boundary-edit.json','policy':'storage-repair-policy.json','method':'implementation/studio_native_storage.py'}[fault]
    (folder/name).write_bytes(b'changed')
    with pytest.raises(ValueError):studio.frozen(folder)


@pytest.mark.parametrize('fault',['state','policy','probe','raw-array','raw-asset','unrounded','search-label'])
def test_review_rejects_changed_stored_fit_evidence(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('job');studio.prepare(payload,folder,resolver);studio.run(folder)
    if fault=='state':(folder/'fit/final-storage-continuation.json').write_bytes(b'changed')
    elif fault=='policy':(folder/'fit/storage-repair-policy.json').write_bytes(b'changed')
    elif fault=='unrounded':(folder/'fit/probes/start/unrounded-observations.npz').write_bytes(b'changed')
    elif fault=='search-label':
        report=read(folder/'fit/probes/start/storage-repair.json');report['native_probe_receipts_sha256']={'../../outside':'0'*64};save(folder/'fit/probes/start/storage-repair.json',report)
    else:
        file={'probe':'probe.json','raw-array':'observations.npz','raw-asset':'actor-0.glb'}[fault]
        (folder/'fit/probes/start/storage-search/start'/file).write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):studio.manifest('job')


@pytest.mark.parametrize('fault',['scene','geometry','speed','mode','permissions'])
def test_clearance_continuation_cannot_rebase_or_drop_original_limits(tmp_path,monkeypatch,fault):
    payload,_,resolver=setup(tmp_path,monkeypatch);first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    payload['resume_from']='first'
    if fault=='scene':payload['draft']['scene']['contacts'][0]['target']['points_m'][0][0]+=.001
    elif fault=='geometry':payload['draft']['geometry']['limits']['penetration_m']=.006
    elif fault=='speed':payload['rotation_speed_limits']=[dict(actor='A',node=3,maximum_degrees_per_second=1.)]
    elif fault=='mode':payload.pop('export_repair');payload.pop('rotation_speed_limits');payload['schema']='strep-studio-native-scene-fit-v1'
    else:payload['actors']['A']['tracks'][0]['maximum_change']=6.
    second=studio.folder_for('second')
    with pytest.raises(ValueError):studio.prepare(payload,second,resolver)
    assert not second.exists()


def test_existing_scene_speed_policy_cannot_disappear_in_clearance_request(tmp_path,monkeypatch):
    payload,_,resolver=setup(tmp_path,monkeypatch);payload['draft']['schema']='strep-studio-native-scene-v2'
    payload['draft']['rotation_speed_limits']=[dict(actor='A',node=3,maximum_degrees_per_second=1.)]
    with pytest.raises(ValueError,match='retain every current'):studio.validate_request(payload,resolver)


def test_failed_floor_remains_visible_and_native_state_can_continue(tmp_path,monkeypatch):
    payload,_,resolver=setup(tmp_path,monkeypatch);payload['draft']['geometry']['planes']['floor']['offset_m']=.5
    first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    manifest=studio.manifest('first');assert manifest['native_conditions_pass'] and not manifest['geometry_conditions_pass']
    assert manifest['original_selected'] and not manifest['quality_approved']
    payload['resume_from']='first';second=studio.folder_for('second');studio.prepare(payload,second,resolver)
    assert studio.frozen(second)['resume_from']=='first'


def test_clearance_does_not_treat_failed_contacts_as_a_valid_start(tmp_path,monkeypatch):
    payload,_,resolver=setup(tmp_path,monkeypatch);payload['draft']['scene']['contacts'][0]['target']['points_m'][0][0]+=.001
    folder=studio.folder_for('failed');studio.prepare(payload,folder,resolver)
    with pytest.raises(ValueError,match='feasible native/contact start'):studio.run(folder)
    assert studio.manifest('failed')['status']=='failed' and studio.manifest('failed')['downloads']==[]
    assert (folder/'fit/probes/start/storage-search/start/probe.json').exists()


def test_partner_scene_can_edit_only_the_second_actor_and_continue(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch)
    # Complete partner containment requires closed surfaces, unlike the
    # single-triangle contact fixture used by the ordinary Studio cases.
    from test_native_scene_geometry import closed_fixture
    _,_,closed=closed_fixture(source.parent)
    closed['actors']['A']['glb']=payload['draft']['scene']['actors']['A']['glb']
    closed['contacts']=[];payload['draft']['scene']=closed
    payload['draft']['scene']['actors']['B']=copy.deepcopy(payload['draft']['scene']['actors']['A'])
    payload['draft']['scene']['actors']['B']['placement']['translation_m']=[5.,0.,0.]
    payload['actors']={'B':payload['actors']['A']}
    first=studio.folder_for('partner-first');studio.prepare(payload,first,resolver);studio.run(first)
    manifest=studio.manifest('partner-first');assert manifest['native_conditions_pass']
    assert set(manifest['actors'])=={'A','B'}
    assert not manifest['actors']['A']['correction_requested'] and manifest['actors']['B']['correction_requested']
    state=read(first/'fit/final-storage-continuation.json')
    assert set(state['actors'])=={'B'} and Path(state['actors']['B']['path']).name=='actor-1.glb'
    native=read(first/'fit/probes/start/storage-search/start/probe.json')
    assert set(native['files'])=={'B'} and native['files']['B']['path']=='actor-0.glb'
    assert sha256(first/'input/actor-0.glb')==sha256(source)
    payload['resume_from']='partner-first';second=studio.folder_for('partner-second')
    studio.prepare(payload,second,resolver);studio.run(second)
    assert studio.manifest('partner-second')['native_conditions_pass']
    assert sha256(first/'fit/source-rate-caps.npz')==sha256(second/'fit/source-rate-caps.npz')
