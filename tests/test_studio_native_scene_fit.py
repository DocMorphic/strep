"""Source-bound character jobs; handler tests never contact live Studio."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_fit as studio
import studio_native_scene as scenes
from strep import read,save,sha256
from test_native_scene_fit import prepare as fixture


def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(scenes,'ROOT',tmp_path)
    inputs=tmp_path/'reports/rig-jobs/source/transfer';inputs.mkdir(parents=True)
    source,spec,c,permissions,p,scene,edits=fixture(inputs,rotation=True)
    url='/files/rig-jobs/source/transfer/'+source.name;spec['actors']['A']['glb']=url
    geometry=dict(clock=dict(mode='explicit',times_s=[0,spec['duration_s']]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={})
    draft=dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=geometry,object_edit=None)
    payload=dict(schema='strep-studio-native-scene-fit-v1',draft=draft,actors=permissions['actors'],options=dict(iterations=1),resume_from=None)
    resolver=lambda candidate:source if candidate==url else None
    return payload,source,resolver


def test_catalog_retains_all_joint_paths_without_automatic_selection(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch);before=copy.deepcopy(payload)
    value=studio.catalog(payload['draft'],resolver)
    from rig_asset import RigAsset
    rig=RigAsset.load(source)
    assert len(value['actors']['A']['channels'])==2*len(rig.joints)
    assert value['actors']['A']['sha256']==sha256(source) and value['maximum_controls']==96
    assert any(not row['eligible'] for row in value['actors']['A']['channels'])
    assert payload==before and not value['quality_approved']


def test_prepare_and_completed_real_native_worker_preserve_source(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch);before=copy.deepcopy(payload);digest=sha256(source)
    folder=studio.folder_for('native1');p=studio.prepare(payload,folder,resolver)
    assert payload==before and sha256(source)==digest
    assert studio.frozen(folder)==p and studio.manifest('native1')['downloads']==[]
    with pytest.raises(ValueError,match='Fresh'):studio.prepare(payload,folder,resolver)
    c=studio.run(folder);m=studio.manifest('native1')
    assert m['status']=='complete' and m['original_selected'] and not m['quality_approved']
    assert not c['studio_selection_changed'] and all(d['sha256']==sha256(studio.served_file(d['url'].removeprefix('/files/'))) for d in m['downloads'])
    assert studio.run(folder)==c and sha256(source)==digest
    assert studio.served_file('native-scene-fit-jobs/native1/draft.json') is None
    assert studio.served_file('native-scene-fit-jobs/native1/../../outside.glb') is None
    assert studio.listing()['jobs'][0]['id']=='native1'


@pytest.mark.parametrize('fault',['extra','schema','bounds','controls','iteration-bool','iteration-zero','object-edit','wrong-source','resume-missing'])
def test_invalid_requests_leave_no_job(tmp_path,monkeypatch,fault):
    payload,source,resolver=setup(tmp_path,monkeypatch)
    if fault=='extra':payload['quality_approved']=True
    if fault=='schema':payload['schema']='other'
    if fault=='bounds':payload['actors']['A']['tracks'][0]['maximum_change']=46
    if fault=='controls':payload['actors']['A']['knots_s']=list(__import__('numpy').linspace(0,2,12));payload['actors']['A']['tracks']*=2
    if fault=='iteration-bool':payload['options']['iterations']=True
    if fault=='iteration-zero':payload['options']['iterations']=0
    if fault=='object-edit':payload['draft']['object_edit']={}
    if fault=='wrong-source':payload['draft']['scene']['actors']['A']['sha256']='0'*64
    if fault=='resume-missing':payload['resume_from']='missing'
    folder=studio.folder_for('bad')
    with pytest.raises((ValueError,OSError)):studio.prepare(payload,folder,resolver)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['source','snapshot','draft','permissions','geometry','archive','options','missing-method'])
def test_frozen_rejects_changed_inputs(tmp_path,monkeypatch,fault):
    payload,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('frozen');studio.prepare(payload,folder,resolver)
    if fault=='source':source.write_bytes(source.read_bytes()+b'changed')
    if fault=='snapshot':(folder/'input/actor-0.glb').write_bytes(b'changed')
    if fault=='draft':save(folder/'draft.json',{})
    if fault=='permissions':save(folder/'permissions.json',{})
    if fault=='geometry':save(folder/'geometry-policy.json',{})
    if fault=='archive':(folder/'implementation/studio_native_scene_fit.py').write_bytes(b'changed')
    if fault in ('options','missing-method'):
        p=read(folder/'prepared.json')
        if fault=='options':p['options']['iterations']=2
        else:p['implementation_sha256'].pop('native_scene_fit.py')
        save(folder/'prepared.json',p)
    with pytest.raises((ValueError,OSError)):studio.frozen(folder)


def test_failed_worker_and_duplicate_guard_keep_evidence(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('fail');studio.prepare(payload,folder,resolver)
    with studio.job_lock(folder):
        with pytest.raises(RuntimeError,match='already running'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='starting'
    def failed(*args,**kwargs):
        partial=folder/'fit';partial.mkdir();save(partial/'partial.json',{'retained':True});raise ValueError('fixture worker failure')
    monkeypatch.setattr(studio,'fit',failed)
    with pytest.raises(ValueError,match='fixture worker failure'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and (folder/'fit/partial.json').is_file()
    digest=sha256(folder/'pipeline.json')
    with pytest.raises(ValueError,match='prepared'):studio.run(folder)
    assert sha256(folder/'pipeline.json')==digest and studio.manifest('fail')['downloads']==[]


def test_real_resume_keeps_first_epoch_caps_and_prior_bytes(tmp_path,monkeypatch):
    import numpy as np
    payload,source,resolver=setup(tmp_path,monkeypatch);first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    payload['resume_from']='first';second=studio.folder_for('second');studio.prepare(payload,second,resolver);studio.run(second)
    assert studio.manifest('second')['resume_from']=='first'
    assert sha256(first/'fit/probes/final/A.glb')==sha256(second/'fit/probes/start/A.glb')
    for name in ('contacts.json','permissions.json','geometry-policy.json'):assert sha256(first/'fit'/name)==sha256(second/name)
    with np.load(first/'fit/source-rate-caps.npz') as a,np.load(second/'fit/source-rate-caps.npz') as b:
        assert a.files==b.files
        for n in a.files:assert a[n].dtype==b[n].dtype and np.array_equal(a[n],b[n])


@pytest.mark.parametrize('fault',['bounds','geometry','target','timing'])
def test_resume_cannot_change_nonpatch_intent_or_bounds(tmp_path,monkeypatch,fault):
    payload,source,resolver=setup(tmp_path,monkeypatch);first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    payload['resume_from']='first'
    if fault=='bounds':payload['actors']['A']['maximum_joint_displacement_m']*=2
    if fault=='geometry':payload['draft']['geometry']['limits']['penetration_m']*=2
    if fault=='target':payload['draft']['scene']['contacts'][0]['target']['points_m'][0][0]+=.001
    if fault=='timing':payload['draft']['scene']['contacts'][0]['interval_s']=[1,1]
    folder=studio.folder_for('invalid-resume')
    with pytest.raises((ValueError,KeyError)):studio.prepare(payload,folder,resolver)
    assert not folder.exists()


def revised(payload):
    from native_contact_revision import apply
    baseline=copy.deepcopy(payload['draft'])
    patch=dict(glb_sha256=baseline['scene']['actors']['A']['sha256'],
        vertices=baseline['scene']['contacts'][0]['vertices'],reduction='centroid')
    changes=[dict(id=baseline['scene']['contacts'][0]['id'],source=patch,partner=None)]
    draft=apply(baseline,changes)
    draft['contact_revision']=dict(schema='strep-native-contact-revision-v1',baseline=baseline,edits=changes)
    payload['draft']=draft;return payload


def test_actual_fresh_revision_retains_original_intent_audit(tmp_path,monkeypatch):
    payload,source,resolver=setup(tmp_path,monkeypatch);revised(payload)
    folder=studio.folder_for('revised');studio.prepare(payload,folder,resolver);studio.run(folder)
    m=studio.manifest('revised')
    assert m['original_intent_pass'] is read(folder/'original-intent-audit/result.json')['passed']
    assert read(folder/'original-contact-intent.json')['contacts']==payload['draft']['contact_revision']['baseline']['scene']['contacts']
    assert read(folder/'original-intent-proposal.json')['actors']==read(folder/'fit/proposal/contacts.json')['actors']
    assert m['authoring_request']==payload and sha256(source)==payload['draft']['scene']['actors']['A']['sha256']


def test_actual_patch_resume_retains_original_caps_and_both_audits(tmp_path,monkeypatch):
    import numpy as np
    payload,source,resolver=setup(tmp_path,monkeypatch);first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first)
    revised(payload);payload['resume_from']='first';second=studio.folder_for('second');studio.prepare(payload,second,resolver);studio.run(second)
    m=studio.manifest('second');r=read(second/'fit/result.json')
    assert r['original_contact_intent_result_sha256']==sha256(second/'fit/original-contact-audit/result.json')
    assert m['resume_from']=='first' and read(second/'contact-revision.json')['original_contacts_sha256']==sha256(first/'fit/contacts.json')
    assert sha256(first/'fit/probes/final/A.glb')==sha256(second/'fit/probes/start/A.glb')
    with np.load(first/'fit/source-rate-caps.npz') as a,np.load(second/'fit/source-rate-caps.npz') as b:
        assert a.files==b.files
        for n in a.files:assert np.array_equal(a[n],b[n])


@pytest.mark.parametrize('fault',['omit-intent','omit-revision'])
def test_frozen_cannot_omit_revision_provenance(tmp_path,monkeypatch,fault):
    payload,source,resolver=setup(tmp_path,monkeypatch)
    if fault=='omit-revision':
        first=studio.folder_for('first');studio.prepare(payload,first,resolver);studio.run(first);payload['resume_from']='first'
    revised(payload);folder=studio.folder_for('revision');studio.prepare(payload,folder,resolver)
    p=read(folder/'prepared.json');p['files_sha256'].pop('original-contact-intent.json' if fault=='omit-intent' else 'contact-revision.json');save(folder/'prepared.json',p)
    with pytest.raises(ValueError,match='input population'):studio.frozen(folder)


@pytest.mark.parametrize('edited',['A','both'])
def test_actual_partner_job_keeps_full_actor_population(tmp_path,monkeypatch,edited):
    payload,source,resolver=setup(tmp_path,monkeypatch);draft=payload['draft'];draft['scene']['actors']['B']=copy.deepcopy(draft['scene']['actors']['A'])
    draft['scene']['actors']['B']['placement']['translation_m']=[3,0,0]
    contact=draft['scene']['contacts'][0];contact['mode']='touch';contact['interval_s']=[1,1];contact['limits']={'position_m':.001}
    contact['target']=dict(space='actor',actor='B',vertices=contact['vertices'],reduction=contact['reduction'])
    if edited=='both':payload['actors']['B']=copy.deepcopy(payload['actors']['A'])
    folder=studio.folder_for('partner');studio.prepare(payload,folder,resolver);studio.run(folder);m=studio.manifest('partner')
    assert set(m['actors'])=={'A','B'} and m['actors']['A']['correction_requested']
    assert m['actors']['B']['correction_requested'] is (edited=='both')
    assert m['actors']['B']['candidate_url'].endswith('B.glb' if edited=='both' else 'input/actor-1.glb')
    assert not m['quality_approved'] and m['original_selected']


@pytest.mark.parametrize('fault',['geometry-array','geometry-receipt','contact-array','contact-snapshot','contact-method','core-snapshot','probe','proposal','source-caps','downloads','decision','rebound-decision','approval'])
def test_manifest_rejects_changed_complete_evidence_and_blocks_serving(tmp_path,monkeypatch,fault):
    payload,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('changed');studio.prepare(payload,folder,resolver);studio.run(folder)
    paths={'geometry-array':'fit/geometry-audit/observations.npz','geometry-receipt':'fit/geometry-audit/observations.npz.receipt.json',
        'contact-array':'fit/contact-audit/observations.npz','contact-snapshot':'fit/contact-audit/input/actor-0.glb',
        'contact-method':'fit/contact-audit/implementation/native_scene_contacts.py','probe':'fit/probes/final/probe.json',
        'proposal':'fit/proposal/contacts.json','source-caps':'fit/source-rate-caps.npz'}
    if fault=='core-snapshot':
        r=read(folder/'fit/request.json');(folder/'fit'/r['actor_snapshots']['A']['path']).write_bytes(b'changed')
    elif fault in ('downloads','decision','rebound-decision','approval'):
        c=read(folder/'completion.json')
        if fault=='downloads':c['downloads'].pop('fit/contact-audit/result.json')
        elif fault=='decision':c['native_conditions_pass']=not c['native_conditions_pass']
        elif fault=='rebound-decision':
            r=read(folder/'fit/result.json');r['native_constraints_pass']=not r['native_constraints_pass'];save(folder/'fit/result.json',r)
            c['native_conditions_pass']=r['native_constraints_pass'];c['fit_result_sha256']=sha256(folder/'fit/result.json')
        else:c['quality_approved']=True
        save(folder/'completion.json',c)
    else:(folder/paths[fault]).write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):studio.manifest('changed')
    assert studio.served_file('native-scene-fit-jobs/changed/fit/probes/final/A.glb') is None


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_dispatch_gates(tmp_path,monkeypatch,fault,expected):
    import action_studio_server as server
    from types import SimpleNamespace
    from test_studio_native_scene import handler
    payload,source,resolver=setup(tmp_path,monkeypatch);monkeypatch.setattr(server,'ROOT',tmp_path);monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    def launch(argv,**kwargs):calls.append((argv,kwargs));return SimpleNamespace(poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch);h=handler(payload,'/api/native-scene-fits')
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:
        argv,kw=calls[0];assert Path(argv[1]).name=='studio_native_scene_fit.py'
        assert kw['env']['HF_HUB_OFFLINE']=='1' and kw['env']['TRANSFORMERS_OFFLINE']=='1'
        assert read(Path(argv[2])/'pipeline.json')['status']=='starting'


def test_offline_catalog_has_no_worker_or_job_side_effect(tmp_path,monkeypatch):
    import action_studio_server as server
    from test_studio_native_scene import handler
    payload,source,resolver=setup(tmp_path,monkeypatch);monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server.subprocess,'Popen',lambda *a,**kw:pytest.fail('Catalog cannot launch a worker'))
    h=handler(payload['draft'],'/api/native-scene-fit-catalog');h.do_POST()
    assert h.responses[-1][0]==200 and not (tmp_path/'reports/native-scene-fit-jobs').exists()


@pytest.mark.parametrize('query',['','?id=a&id=b','?id=a&extra=b','?id='])
def test_offline_review_rejects_ambiguous_selection(tmp_path,monkeypatch,query):
    from test_studio_native_scene import handler
    setup(tmp_path,monkeypatch);h=handler({},'/api/native-scene-fit-review'+query);h.do_GET();assert h.responses[-1][0]==400


def test_build_exposes_character_correction_once():
    from build_desktop import render
    page=render()
    for name in ('nativeSceneFitPanel','nativeSceneFitTracks','nativeSceneFitBuild','nativeSceneFitStage'):
        assert page.count('id="'+name+'"')==1
    assert 'getDraft:()=>nativeSceneEditor.snapshot()' in page


def test_actual_declared_moving_object_job(tmp_path,monkeypatch):
    from test_native_scene_contacts import object_target
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    payload,source,resolver=setup(tmp_path,monkeypatch);rig=RigAsset.load(source)
    object_target(payload['draft']['scene'],NativeSupportSampler(rig.document,rig.binary,0),rig,gap=.001)
    folder=studio.folder_for('object');studio.prepare(payload,folder,resolver);studio.run(folder);m=studio.manifest('object')
    assert m['authoring_request']==payload
    assert read(folder/'fit/contact-audit/result.json')['contacts'][0]['target_space']=='object'
    assert read(folder/'contacts.json')['objects']==payload['draft']['scene']['objects']
    assert m['original_selected'] and not m['quality_approved']


@pytest.mark.parametrize('namespace',['native-scene-jobs','native-scene-fit-jobs'])
def test_saved_scene_and_correction_clips_can_enter_a_fresh_explicit_request(tmp_path,monkeypatch,namespace):
    import shutil
    payload,source,resolver=setup(tmp_path,monkeypatch)
    destination=tmp_path/'reports'/namespace/'saved/input/actor-0.glb';destination.parent.mkdir(parents=True);shutil.copyfile(source,destination)
    url=f'/files/{namespace}/saved/input/actor-0.glb';payload['draft']['scene']['actors']['A']['glb']=url
    resolver=lambda candidate:destination if candidate==url else None
    assert studio.catalog(payload['draft'],resolver)['actors']['A']['sha256']==sha256(source)
    p=studio.prepare(payload,studio.folder_for('fresh'),resolver)
    assert p['sources']['A']['path']==str(destination) and p['resume_from'] is None
