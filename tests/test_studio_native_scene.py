"""Offline handler stubs and source-bound drafts; no live Studio HTTP calls."""
import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene as studio
import action_studio_server as server
from strep import read,save,sha256
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for
from test_native_object_hold_fit import fixture
from test_native_scene_geometry import policy


def setup(tmp_path,monkeypatch,edit=True):
    monkeypatch.setattr(studio,'ROOT',tmp_path);monkeypatch.setattr(server,'ROOT',tmp_path)
    inputs=tmp_path/'reports/rig-jobs/parent/transfer';inputs.mkdir(parents=True)
    source,path,spec,scene,request=fixture(inputs)
    url='/files/rig-jobs/parent/transfer/'+source.name
    for actor in spec['actors'].values():actor['glb']=url
    geometry=policy(path,mode='native-and-frame-populations')
    geometry.pop('schema');geometry.pop('contacts_sha256');request.pop('contacts_sha256')
    draft=dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=geometry,object_edit=request if edit else None)
    engine=tmp_path/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    engine.parent.mkdir(parents=True);engine.write_bytes(b'mocked engine; not executed')
    resolver=lambda candidate:source if candidate==url else None
    return draft,source,resolver


def test_prepare_preserves_exact_inputs_and_explicit_planes(tmp_path,monkeypatch):
    draft,source,resolver=setup(tmp_path,monkeypatch);before=copy.deepcopy(draft);digest=sha256(source)
    folder=studio.folder_for('draft1');p=studio.prepare(draft,folder,resolver)
    assert draft==before and sha256(source)==digest and read(folder/'draft.json')==before
    assert read(folder/'geometry-policy.json')['planes']=={}
    assert studio.frozen(folder)==p and not p['quality_approved'] and p['original_selected']
    saved=read(folder/'contacts.json')
    assert saved['contacts']==draft['scene']['contacts'] and saved['objects']==draft['scene']['objects']
    assert all(sha256(a['glb'])==digest for a in saved['actors'].values())
    assert studio.listing()['jobs'][0]['status']=='starting'
    assert studio.manifest('draft1')['downloads']==[]
    assert studio.served_file('native-scene-jobs/draft1/input/actor-0.glb') is None
    with pytest.raises(ValueError,match='Fresh'):studio.prepare(draft,folder,resolver)


@pytest.mark.parametrize('fault',['extra','schema','remote','query','fragment','absolute','unserved','sha','duration','no-object','plane','edit','boolean-key'])
def test_invalid_requests_reject_before_outputs(tmp_path,monkeypatch,fault):
    draft,source,resolver=setup(tmp_path,monkeypatch);a=draft['scene']['actors']['A']
    if fault=='extra':draft['automatic_quality_approval']=True
    elif fault=='schema':draft['schema']='other'
    elif fault=='remote':a['glb']='https://example.test/a.glb'
    elif fault=='query':a['glb']+='?x=1'
    elif fault=='fragment':a['glb']+='#x'
    elif fault=='absolute':a['glb']=str(source)
    elif fault=='unserved':a['glb']='/files/rig-jobs/missing.glb'
    elif fault=='sha':a['sha256']='0'*64
    elif fault=='duration':draft['scene']['duration_s']=1
    elif fault=='no-object':draft['scene']['objects']={}
    elif fault=='plane':draft['geometry']['planes']['floor']={'normal_world':[0,0,0],'offset_m':0}
    elif fault=='edit':draft['object_edit']['contact_ids']=['left-grip']*2
    else:draft['object_edit']['maximum_keys']=True
    folder=studio.folder_for('bad')
    with pytest.raises((ValueError,KeyError)):studio.prepare(draft,folder,resolver)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['source','snapshot','draft','policy','archive','engine','missing-method','snapshot-escape'])
def test_frozen_rejects_changes(tmp_path,monkeypatch,fault):
    draft,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('frozen');studio.prepare(draft,folder,resolver)
    if fault=='source':source.write_bytes(source.read_bytes()+b'changed')
    elif fault=='snapshot':(folder/'input/actor-0.glb').write_bytes(b'changed')
    elif fault=='draft':v=read(folder/'draft.json');v['geometry']['limits']['penetration_m']=.02;save(folder/'draft.json',v)
    elif fault=='policy':v=read(folder/'geometry-policy.json');v['limits']['penetration_m']=.02;save(folder/'geometry-policy.json',v)
    elif fault=='archive':(folder/'implementation/studio_native_scene.py').write_bytes(b'changed')
    elif fault=='engine':Path(read(folder/'prepared.json')['engine_path']).write_bytes(b'changed')
    else:
        v=read(folder/'prepared.json')
        if fault=='missing-method':v['implementation_sha256'].pop('studio_native_scene.py')
        else:v['sources']['A']['snapshot']='../outside.glb'
        save(folder/'prepared.json',v)
    with pytest.raises((ValueError,OSError)):studio.frozen(folder)


def handler(payload,path='/api/native-scene-assets'):
    h=server.Handler.__new__(server.Handler);h.path=path;data=json.dumps(payload).encode()
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(data))}
    h.rfile=io.BytesIO(data);h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},worker=None,job_lock=threading.Lock())
    h.responses=[];h.respond=lambda code,value:h.responses.append((code,value));return h


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_offline_post_gates_and_single_worker_dispatch(tmp_path,monkeypatch,fault,expected):
    draft,source,resolver=setup(tmp_path,monkeypatch);monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    def launch(argv,**kwargs):calls.append((argv,kwargs));return SimpleNamespace(poll=lambda:None)
    monkeypatch.setattr(server.subprocess,'Popen',launch);h=handler(draft)
    if fault=='host':h.headers['Host']='example.test'
    elif fault=='origin':h.headers['Origin']='https://example.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:
        argv,kw=calls[0];assert Path(argv[1]).name=='studio_native_scene.py'
        assert kw['env']['HF_HUB_OFFLINE']=='1' and kw['env']['TRANSFORMERS_OFFLINE']=='1'
        assert read(Path(argv[2])/'pipeline.json')['status']=='starting'


@pytest.mark.parametrize('query',['','?id=a&id=b','?id=a&extra=b','?id='])
def test_offline_get_rejects_ambiguous_selection(tmp_path,monkeypatch,query):
    setup(tmp_path,monkeypatch);h=handler({},'/api/native-scene-review'+query);h.do_GET();assert h.responses[-1][0]==400


def test_worker_failure_keeps_partial_evidence(tmp_path,monkeypatch):
    draft,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('failure');studio.prepare(draft,folder,resolver)
    def fail(recipe,out):out.mkdir();save(out/'partial.json',{'retained':True});raise ValueError('fixture failure')
    monkeypatch.setattr(studio,'author',fail)
    with pytest.raises(ValueError,match='fixture failure'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and (folder/'authoring/partial.json').is_file()
    assert studio.manifest('failure')['downloads']==[] and sha256(source)==draft['scene']['actors']['A']['sha256']
    before=sha256(folder/'pipeline.json')
    with pytest.raises(ValueError,match='Fresh prepared'):studio.run(folder)
    assert sha256(folder/'pipeline.json')==before


def test_portable_package_has_exact_population_and_contact_clock(tmp_path,monkeypatch):
    draft,source,resolver=setup(tmp_path,monkeypatch,False);folder=studio.folder_for('package');p=studio.prepare(draft,folder,resolver)
    authoring=folder/'authoring';(authoring/'objects-common').mkdir(parents=True)
    (authoring/'objects-engine').mkdir();(authoring/'actors-engine').mkdir()
    (authoring/'objects-common/objects.glb').write_bytes(b'mocked object file')
    (authoring/'objects-engine/native-animation.res').write_bytes(b'mocked object resource')
    for name in p['sources']:(authoring/f'actors-engine/{name}-animation.res').write_bytes(b'mocked character resource')
    save(authoring/'objects-common/common-policy.json',read(folder/'geometry-policy.json'))
    result=dict(artifacts=dict(active_contacts=str(folder/'contacts.json')),sampled_conditions_pass=False)
    save(authoring/'result.json',result);digest=studio.package(folder,p,result)
    assert digest==sha256(folder/'assets.zip')
    with zipfile.ZipFile(folder/'assets.zip') as z:
        assert set(z.namelist())=={'scene.json','geometry-policy.json','package.json','objects.glb','animations/objects.res','actors/0.glb','actors/1.glb','animations/A.res','animations/B.res'}
        extracted=tmp_path/'portable';z.extractall(extracted)
    portable=SceneContacts(read(extracted/'scene.json'),extracted)
    pp=read(extracted/'geometry-policy.json');policy_for(pp,portable,sha256(extracted/'scene.json'))
    assert pp['clock']==draft['geometry']['clock'] and pp['limits']==draft['geometry']['limits']
    assert read(extracted/'scene.json')['contacts']==draft['scene']['contacts']
    receipt=read(extracted/'package.json');assert not receipt['sampled_conditions_pass'] and not receipt['root_event_tracks_included']
    assert all(sha256(extracted/name)==h for name,h in receipt['files_sha256'].items())
    assert sha256(extracted/'actors/0.glb')==sha256(source)


def test_generated_studio_exposes_scene_workflow():
    from build_desktop import render
    page=render()
    for name in ('nativeScenePanel','nativeSceneBuild','nativeScenePartnerPatch','nativeSceneFit'):
        assert page.count('id="'+name+'"')==1
    assert "getPatch:()=>contactEditor.nativePatch()" in page


def mock_author(folder,*,passed=True):
    """Receipt/serving test doubles only, never actual animation or engine evidence."""
    import shutil
    def author(recipe,out):
        out.mkdir();prepared=read(folder/'prepared.json');impl=out/'implementation';impl.mkdir()
        methods={n:h for n,h in prepared['implementation_sha256'].items() if n!='studio_native_scene.py'}
        for name in methods:shutil.copyfile(folder/'implementation'/name,impl/name)
        stages=[]
        names=['source-contacts','object-edit','objects-source','objects-common','objects-engine','actors-engine','combined-engine','replay']
        for name in names:
            d=out/name;d.mkdir();record={'status':'complete'}
            if name=='source-contacts':record['passed']=False
            if name=='object-edit':record['sampled_constraints_pass']=True
            if name=='objects-common':
                save(d/'common-policy.json',read(folder/'geometry-policy.json'));(d/'objects.glb').write_bytes(b'mocked object GLB')
                (d/'implementation').mkdir();shutil.copyfile(impl/'native_engine_clock.gd',d/'implementation/native_engine_clock.gd')
            if name=='objects-engine':
                (d/'native-animation.res').write_bytes(b'mocked object resource')
                record['implementation_sha256']={'native_engine_clock.gd':methods['native_engine_clock.gd']}
            if name=='actors-engine':
                for actor in prepared['sources']:(d/f'{actor}-animation.res').write_bytes(b'mocked actor resource')
                for fn,key in [('engine-output.json','engine_output_sha256'),('raw-engine-receipt.json','raw_engine_receipt_sha256'),('native-observations.npz','native_observations_sha256'),('imported-contact-observations.npz','imported_contact_observations_sha256')]:
                    (d/fn).write_bytes(b'mocked receipt/array bytes');record[key]=sha256(d/fn)
                for fn in ['geometry-observations.npz','geometry-observations.npz.receipt.json']:(d/fn).write_bytes(b'mocked geometry bytes')
                save(d/'geometry.json',dict(observations_sha256=sha256(d/'geometry-observations.npz'),observation_receipt_sha256=sha256(d/'geometry-observations.npz.receipt.json')))
                record['geometry_sha256']=sha256(d/'geometry.json')
            if name=='combined-engine':
                record.update(samples=3,all_sampled_conditions_pass=passed,implementation_sha256={})
                save(d/'geometry.json',{'fixture':'not actual geometry'});record['files_sha256']={'geometry.json':sha256(d/'geometry.json')}
            if name=='replay':
                shutil.copyfile(impl/'verify_native_object_scene_engine.py',d/'verifier.py')
                record.update(samples=3,all_replayed_observations_exact=True,recorded_sampled_conditions_pass=passed,
                    producer_implementation_sha256={},combined_files_sha256={str(out/'combined-engine/result.json'):sha256(out/'combined-engine/result.json')})
            save(d/'result.json',record);stages.append(dict(id=name,result_sha256=sha256(d/'result.json')))
        result=dict(status='complete',original_selected=True,samples=3,sampled_conditions_pass=passed,source_contact_conditions_pass=False,
            object_edit_requested=True,object_edit_conditions_pass=True,implementation_sha256=methods,recipe_sha256=sha256(recipe),
            inputs_sha256={str(folder/'contacts.json'):sha256(folder/'contacts.json')},derived_inputs_sha256={},stages=stages,
            artifacts=dict(active_contacts=str(folder/'contacts.json')),scope='Mocked receipt transport only')
        for k in ('studio_selection_changed','quality_approved','training_admitted','release_approved','gpu_render_checked','physics_verified','real_time_playback_verified','human_review_submitted'):result[k]=False
        save(out/'result.json',result);return result
    return author


@pytest.mark.parametrize('passed',[True,False])
def test_completed_worker_manifest_keeps_failed_decisions_and_downloads(tmp_path,monkeypatch,passed):
    draft,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('complete');studio.prepare(draft,folder,resolver)
    monkeypatch.setattr(studio,'author',mock_author(folder,passed=passed));completion=studio.run(folder)
    m=studio.manifest(folder.name);assert m['status']=='complete' and m['sampled_conditions_pass'] is passed
    assert m['source_contacts_pass'] is False and not m['quality_approved'] and m['original_selected']
    assert len(m['downloads'])==len(studio.download_names(read(folder/'prepared.json')))
    for entry in m['downloads']:assert studio.served_file(entry['url'].removeprefix('/files/')).is_file()
    assert studio.served_file('native-scene-jobs/complete/implementation/studio_native_scene.py') is None
    assert studio.served_file('native-scene-jobs/complete/../outside/assets.zip') is None
    assert read(folder/'completion.json')==completion
    before={n:sha256(folder/n) for n in ('completion.json','pipeline.json','worker.json','assets.zip')}
    with pytest.raises(ValueError,match='Fresh prepared'):studio.run(folder)
    assert before=={n:sha256(folder/n) for n in before}


@pytest.mark.parametrize('fault',['zip','raw','geometry-array','resource','core-archive','producer-method','replay-method','source','decision'])
def test_manifest_rejects_changed_saved_evidence_and_blocks_downloads(tmp_path,monkeypatch,fault):
    draft,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('tampered');studio.prepare(draft,folder,resolver)
    monkeypatch.setattr(studio,'author',mock_author(folder));studio.run(folder)
    paths={'zip':'assets.zip','raw':'authoring/actors-engine/engine-output.json',
        'geometry-array':'authoring/actors-engine/geometry-observations.npz','resource':'authoring/actors-engine/A-animation.res',
        'core-archive':'authoring/implementation/native_scene_authoring_job.py','producer-method':'authoring/objects-common/implementation/native_engine_clock.gd',
        'replay-method':'authoring/replay/verifier.py'}
    if fault=='source':source.write_bytes(b'changed')
    elif fault=='decision':c=read(folder/'completion.json');c['quality_approved']=True;save(folder/'completion.json',c)
    else:(folder/paths[fault]).write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):studio.manifest(folder.name)
    assert studio.served_file('native-scene-jobs/tampered/assets.zip') is None
