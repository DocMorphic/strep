"""Offline game-package transport and handler stubs, explicitly mocked Godot."""
import copy
from pathlib import Path
from types import SimpleNamespace
import sys
import zipfile
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_game as game
import studio_native_scene as scenes
import action_studio_server as server
import action_worker_lock
from native_scene_contacts import SceneContacts
from native_scene_game_tracks import crossed
from native_engine_clock import clock_wire
from strep import read,save,sha256
from test_studio_native_scene import setup as source_setup,mock_author,handler


def test_only_archived_ordinary_game_jobs_accept_pre_revision_method_population(tmp_path,monkeypatch):
    payload,*_=setup(tmp_path,monkeypatch)
    folder=game.folder_for('archived');game.prepare(payload,folder)
    prepared=read(folder/'prepared.json');prepared['implementation_sha256'].pop('native_contact_revision.py')
    save(folder/'prepared.json',prepared)
    assert game.frozen(folder,current_methods=False)[0]==prepared
    with pytest.raises(ValueError,match='method population'):game.frozen(folder)
    prepared['implementation_sha256'].pop('native_scene_authoring_job.py');save(folder/'prepared.json',prepared)
    with pytest.raises(ValueError,match='method population'):game.frozen(folder,current_methods=False)


def setup(tmp_path,monkeypatch,*,scene_pass=True,root_pass=True):
    draft,source,resolver=source_setup(tmp_path,monkeypatch)
    monkeypatch.setattr(game,'ROOT',tmp_path);monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    folder=scenes.folder_for('source');scenes.prepare(draft,folder,resolver)
    times=np.array([0.,1/480,.8,1.,2.],dtype='<f8')
    base_author=mock_author(folder,passed=scene_pass)
    def source_author(recipe,out):
        r=base_author(recipe,out)
        request=dict(sample_times_s=times.tolist(),sample_clock=clock_wire(times))
        actor=out/'actors-engine';save(actor/'request.json',request)
        save(actor/'raw-engine-receipt.json',dict(request_sha256=sha256(actor/'request.json')))
        a=read(actor/'result.json');a['raw_engine_receipt_sha256']=sha256(actor/'raw-engine-receipt.json');save(actor/'result.json',a)
        scene=SceneContacts(read(folder/'contacts.json'),folder);report,_=scene.evaluate()
        combined=out/'combined-engine';save(combined/'native-authoring-contacts.json',report)
        c=read(combined/'result.json');c['samples']=len(times);c['files_sha256']['native-authoring-contacts.json']=sha256(combined/'native-authoring-contacts.json');save(combined/'result.json',c)
        replay=out/'replay/result.json';p=read(replay);p['samples']=len(times);p['combined_files_sha256'][str(combined/'result.json')]=sha256(combined/'result.json');save(replay,p)
        r['samples']=len(times)
        for stage in r['stages']:stage['result_sha256']=sha256(out/stage['id']/'result.json')
        save(out/'result.json',r);return r
    monkeypatch.setattr(scenes,'author',source_author);scenes.run(folder)
    def imported(contacts,policy,actors,objects):
        scene=SceneContacts(read(contacts),contacts.parent)
        worlds={name:np.array([a['sampler'].sample(t)[a['rig'].joints] for t in times]) for name,a in scene.actors.items()}
        if not root_pass:worlds['A'][1,:,0,3]+=.02
        return scene,read(policy),SimpleNamespace(worlds=worlds),{},times,{}
    monkeypatch.setattr(game,'load',imported)
    def execute(command,**kwargs):
        request=read(command[-2]);events=read(request['events_path']);clock=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8');traces={}
        for scenario in request['scenarios']:
            fired=[];previous=None
            for index in scenario['indices']:
                current=float(clock[index]);fired.extend(crossed(events,previous,current));previous=current
            traces[scenario['id']]=fired
        save(command[-1],dict(engine=dict(string='mocked Godot; not actual execution'),traces=traces,invalid_rejected=True,
            malformed_configs_rejected=True,malformed_config_cases=6))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(game.subprocess,'run',execute)
    meta=game.metadata(folder.name)
    payload=dict(scene_job=folder.name,source_result_sha256=meta['source_result_sha256'],request=dict(
        schema='strep-native-scene-game-tracks-v1',actors={name:dict(root_node=a['joints'][0]['node']) for name,a in meta['actors'].items()},
        markers=[dict(id='grasp',name='grasp',actor='A',time_s=float(times[1]),confirmed=True),dict(id='review',name='review',actor='B',time_s=.8,confirmed=False)]))
    return payload,folder


@pytest.mark.parametrize('scene_pass,root_pass',[(True,True),(False,True),(True,False)])
def test_complete_packages_keep_original_assets_failed_conditions_and_root_mode(tmp_path,monkeypatch,scene_pass,root_pass):
    payload,source=setup(tmp_path,monkeypatch,scene_pass=scene_pass,root_pass=root_pass)
    before={n:sha256(source/n) for n in ('assets.zip','completion.json','pipeline.json','authoring/result.json')}
    folder=game.folder_for('complete');game.prepare(payload,folder);result=game.run(folder);manifest=game.manifest(folder.name)
    assert result['scene_sampled_conditions_pass'] is scene_pass and result['root_samples_pass'] is root_pass
    assert manifest['event_helper_dispatch_verified'] and not manifest['quality_approved']
    assert result['original_selected'] and not result['studio_selection_changed'] and not result['animation_runtime_playback_verified']
    assert before=={n:sha256(source/n) for n in before}
    assert len(manifest['downloads'])==len(game.DOWNLOADS)
    for entry in manifest['downloads']:assert game.served_file(entry['url'].removeprefix('/files/')).is_file()
    assert game.served_file('native-scene-game-jobs/complete/implementation/studio_native_scene_game.py') is None
    with zipfile.ZipFile(source/'assets.zip') as original,zipfile.ZipFile(folder/'game-assets.zip') as package:
        for name in original.namelist():assert package.read('source-package.json' if name=='package.json' else name)==original.read(name)
        assert package.read('runtime/godot_scene_game_events.gd')==(folder/'runtime-events/project/godot_scene_game_events.gd').read_bytes()
        receipt=read(folder/'package.json');assert set(package.namelist())==set(receipt['files_sha256'])|{'package.json'}
    before={n:sha256(folder/n) for n in ('pipeline.json','result.json','game-assets.zip')}
    with pytest.raises(ValueError,match='Fresh prepared'):game.run(folder)
    assert before=={n:sha256(folder/n) for n in before}


@pytest.mark.parametrize('fault',['source-id','result-sha','root','rounded-time','confirmation','extra'])
def test_invalid_track_request_rejects_before_job_creation(tmp_path,monkeypatch,fault):
    payload,source=setup(tmp_path,monkeypatch)
    if fault=='source-id':payload['scene_job']='../source'
    elif fault=='result-sha':payload['source_result_sha256']='0'*64
    elif fault=='root':payload['request']['actors']['A']['root_node']=True
    elif fault=='rounded-time':payload['request']['markers'][0]['time_s']=float('0.00208333333333333')
    elif fault=='confirmation':payload['request']['markers'][0]['confirmed']='yes'
    else:payload['approve_everything']=True
    folder=game.folder_for('invalid')
    with pytest.raises((ValueError,OSError)):game.prepare(payload,folder)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['request','archive','source-zip','copied-zip','engine'])
def test_frozen_rejects_changed_preparation(tmp_path,monkeypatch,fault):
    payload,source=setup(tmp_path,monkeypatch);folder=game.folder_for('frozen');p=game.prepare(payload,folder)
    if fault=='request':v=read(folder/'request.json');v['request']['markers'][0]['confirmed']=False;save(folder/'request.json',v)
    elif fault=='archive':(folder/'implementation/native_scene_game_tracks.py').write_bytes(b'changed')
    elif fault=='source-zip':(source/'assets.zip').write_bytes(b'changed')
    elif fault=='copied-zip':(folder/'source-assets.zip').write_bytes(b'changed')
    else:Path(p['engine_path']).write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):game.frozen(folder)


def test_failed_engine_audit_retains_complete_tracks_without_publishing(tmp_path,monkeypatch):
    payload,source=setup(tmp_path,monkeypatch);folder=game.folder_for('failed');game.prepare(payload,folder)
    monkeypatch.setattr(game.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=3))
    with pytest.raises(ValueError,match='engine audit failed'):game.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and (folder/'tracks/result.json').is_file()
    assert (folder/'runtime-events/engine.log').is_file() and game.manifest(folder.name)['downloads']==[]
    before=sha256(folder/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh prepared'):game.run(folder)
    assert sha256(folder/'pipeline.json')==before


@pytest.mark.parametrize('fault',['zip','root','array','events','executed-helper','archive','runtime-receipt','forged-contact','forged-confirmation'])
def test_modified_game_artifacts_and_forged_intent_block_serving(tmp_path,monkeypatch,fault):
    payload,source=setup(tmp_path,monkeypatch);folder=game.folder_for('tampered');game.prepare(payload,folder);game.run(folder)
    if fault in ('forged-contact','forged-confirmation'):
        events=read(folder/'tracks/events.json')
        entry=next(e for e in events['events'] if e['kind']==('contact_intent' if fault=='forged-contact' else 'gameplay_intent'))
        entry['timing_confirmed']=not entry['timing_confirmed'];entry['runtime_dispatch_allowed']=True
        save(folder/'tracks/events.json',events)
        stage=read(folder/'tracks/result.json');stage['files_sha256']['events.json']=sha256(folder/'tracks/events.json');save(folder/'tracks/result.json',stage)
        runtime=read(folder/'runtime-events/result.json');runtime['events_sha256']=sha256(folder/'tracks/events.json');save(folder/'runtime-events/result.json',runtime)
        result=read(folder/'result.json')
        for n in ('tracks/events.json','tracks/result.json','runtime-events/result.json'):result['files_sha256'][n]=sha256(folder/n)
        save(folder/'result.json',result);completion=read(folder/'completion.json');completion['result_sha256']=sha256(folder/'result.json');save(folder/'completion.json',completion)
    else:
        relative={'zip':'game-assets.zip','root':'tracks/root-motion.json','array':'tracks/root-observations.npz','events':'tracks/events.json',
            'executed-helper':'runtime-events/project/godot_scene_game_events.gd','archive':'implementation/native_scene_game_tracks.py','runtime-receipt':'runtime-events/engine-output.json'}[fault]
        (folder/relative).write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):game.manifest(folder.name)
    assert game.served_file('native-scene-game-jobs/tampered/game-assets.zip') is None


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('valid',202)])
def test_offline_game_endpoint_gates(tmp_path,monkeypatch,fault,expected):
    payload,source=setup(tmp_path,monkeypatch);h=handler(payload,'/api/native-scene-game-assets')
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    def launch(argv,**kw):calls.append((argv,kw));return SimpleNamespace(poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch)
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_native_scene_game.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


def test_offline_source_get_and_build_preserve_exact_controls(tmp_path,monkeypatch):
    payload,source=setup(tmp_path,monkeypatch);h=handler({},'/api/native-scene-game-source?id=source');h.do_GET()
    assert h.responses[-1][0]==200 and h.responses[-1][1]['times_s'][1]==1/480
    h=handler({},'/api/native-scene-game-source?id=source&id=other');h.do_GET();assert h.responses[-1][0]==400
    from build_desktop import render
    page=render();assert page.count('id="nativeSceneGamePanel"')==1 and 'createNativeSceneGameEditor({api,post})' in page
