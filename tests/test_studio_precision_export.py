"""Real tiny skin/geometry pipeline with explicitly mocked engine processes."""
import copy
from pathlib import Path
import sys
import zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_precision_export as studio
import studio_surface_export as sources
import native_scene_authoring_job
import action_worker_lock
from test_studio_surface_export import setup
from strep import read,save,sha256


@pytest.fixture
def context(tmp_path,monkeypatch):
    import test_native_imported_surface_contact as generated
    from test_native_scene_geometry import closed_fixture
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    def closed_source(path,*,mode='touch'):
        assert mode=='touch'
        source,contacts,spec=closed_fixture(path)
        rig=RigAsset.load(source);sampler=NativeSupportSampler(rig.document,rig.binary,0)
        spec['contacts'][0]['target']['points_m']=[rig.vertices(sampler.sample(1.))[0].tolist()]
        return source,rig,sampler,spec
    # The original transport helper's open triangle correctly fails full volume
    # availability. Use a complete closed fixture for the passing package tests;
    # do not weaken the production geometry condition.
    monkeypatch.setattr(generated,'setup',closed_source)
    original_geometry_policy=generated.geometry_policy
    monkeypatch.setattr(generated,'geometry_policy',lambda path:original_geometry_policy(path,
        planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-2.))))
    parent,game,surface=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    monkeypatch.setattr(native_scene_authoring_job,'worker_busy',lambda:False)
    spec=read(parent/'authoring/contacts.json')
    root_request=dict(schema='strep-native-scene-game-tracks-v1',actors={n:dict(root_node=0) for n in spec['actors']},markers=[])
    save(game/'request.json',dict(request=root_request))
    def fake_dispatch(events,out,engine):
        out.mkdir();result=dict(status='complete',gameplay_event_dispatch_verified=True)
        save(out/'result.json',result);return result
    monkeypatch.setattr(studio.games,'engine_audit',fake_dispatch)
    return parent,game,surface


@pytest.mark.parametrize('kind,job',[('scene','scene1'),('game','game1')])
def test_precision_reimports_complete_scene_and_references_original_skin(context,kind,job):
    parent,game,_=context;m=studio.metadata(kind,job)
    payload=dict(schema=studio.SCHEMA,source=m['source']);folder=studio.folder_for(kind+'-precision')
    original_package=sha256(parent/'assets.zip' if kind=='scene' else game/'game-assets.zip')
    studio.prepare(payload,folder);r=studio.run(folder);receipt=studio.manifest(folder.name)
    assert r['original_skin_samples_passed'] and r['scene_samples_passed'] and r['checked_package_available']
    assert all(r[k] is False for k in studio.FALSE_FLAGS)
    assert r['root_event_tracks_included'] is (kind=='game')
    assert sha256(folder/'original-assets.zip')==original_package
    assert read(folder/'fidelity.json')['actors'][0]['original_skin_reference_preserved']
    with zipfile.ZipFile(folder/'checked-assets.zip') as z:
        import json
        packed=json.loads(z.read('package.json'));assert set(z.namelist())==set(packed['files_sha256'])|{'package.json'}
        assert z.read('original-assets.zip')==(folder/'original-assets.zip').read_bytes()
        scene=json.loads(z.read('scene.json'));assert scene['contacts']==read(folder/'original-contacts.json')['contacts']
        assert scene['actors']['A']['glb']=='actors/0.glb'
        assert ('events.json' in z.namelist()) is (kind=='game')
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/checked-assets.zip')==folder/'checked-assets.zip'
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/original/0.glb') is None
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/../other/result.json') is None


def test_original_or_receipt_changes_reject_before_export(context):
    m=studio.metadata('scene','scene1');payload=dict(schema=studio.SCHEMA,source=m['source']);folder=studio.folder_for('changed')
    studio.prepare(payload,folder);(folder/'original/0.glb').write_bytes(b'changed')
    with pytest.raises(ValueError):studio.frozen(folder)
    bad=copy.deepcopy(payload);bad['source']['result_sha256']='0'*64
    with pytest.raises(ValueError):studio.validate_request(bad)


def test_inherited_normals_cannot_silently_disappear(context,monkeypatch):
    original=sources.source
    def changed(*args):
        v=list(original(*args));v[0]=copy.deepcopy(v[0]);v[0]['normal_origins']=[dict(job='prior')];v[0]['inherited_surface']=None;return tuple(v)
    monkeypatch.setattr(sources,'source',changed)
    with pytest.raises(ValueError,match='normal intent'):studio.metadata('scene','scene1')


def test_failed_original_fidelity_retains_diagnostics_without_checked_zip(context,monkeypatch):
    m=studio.metadata('scene','scene1');folder=studio.folder_for('precision-failure')
    studio.prepare(dict(schema=studio.SCHEMA,source=m['source']),folder)
    original=studio.measure_original
    def failed(*args):
        row,errors,witnesses=original(*args)
        # Keep the injected failure numerically consistent; a boolean alone is
        # correctly rejected by the receipt reader.
        errors=errors.copy();errors[0]=.0002
        row.update(position_samples_passed=False,maximum_position_error_m=.0002,
                   samples_over_tolerance=1,worst_time_s=0.,worst_source_vertex=int(witnesses[0]))
        return row,errors,witnesses
    monkeypatch.setattr(studio,'measure_original',failed)
    r=studio.run(folder);assert not r['checked_package_available'] and not (folder/'checked-assets.zip').exists()
    assert studio.manifest(folder.name)['original_skin_samples_passed'] is False
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/checked-assets.zip') is None


def test_studio_template_contains_unique_precision_panel():
    from build_desktop import render
    page=render()
    for n in ('Panel','Build','Bind','Kind','Source','Status','Review','Results'):
        assert page.count('id="precisionExport'+n+'"')==1
    assert "import('/precision-export-editor.mjs')" in page


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409),('valid',202)])
def test_precision_loopback_dispatch(tmp_path,monkeypatch,fault,expected):
    from types import SimpleNamespace
    from test_studio_native_scene import handler
    import action_studio_server as server
    monkeypatch.setattr(studio,'ROOT',tmp_path)
    monkeypatch.setattr(studio,'validate_request',lambda payload:None)
    def prepare(payload,folder):folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='starting'))
    monkeypatch.setattr(studio,'prepare',prepare)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy')
    monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None))
    h=handler({},'/api/precision-export-assets')
    if fault=='host':h.headers['Host']='remote.test'
    elif fault=='origin':h.headers['Origin']='https://remote.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    elif fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:
        argv,kw=calls[0];assert Path(argv[1]).name=='studio_precision_export.py'
        assert kw['env']['HF_HUB_OFFLINE']=='1' and kw['env']['TRANSFORMERS_OFFLINE']=='1'


@pytest.mark.parametrize('query',['kind=scene&id=one&id=two','kind=scene&id=one&extra=1','id=one','kind=scene&id=','kind=scene&kind=game&id=one'])
def test_precision_read_routes_reject_ambiguous_selection(query,monkeypatch):
    from test_studio_native_scene import handler
    monkeypatch.setattr(studio,'metadata',lambda *a:pytest.fail('invalid query reached source'))
    h=handler({},'/api/precision-export-source?'+query);h.do_GET();assert h.responses[-1][0]==400


def test_corrupt_source_zip_returns_client_error_without_worker(monkeypatch):
    from test_studio_native_scene import handler
    def reject(payload):raise zipfile.BadZipFile('retained malformed source fixture')
    monkeypatch.setattr(studio,'validate_request',reject)
    h=handler({},'/api/precision-export-assets');h.do_POST()
    assert h.responses[-1][0]==400 and h.server.worker is None


def test_rehashed_results_and_zip_cannot_bypass_measurements(context):
    import numpy as np
    m=studio.metadata('scene','scene1');folder=studio.folder_for('tamper-test')
    studio.prepare(dict(schema=studio.SCHEMA,source=m['source']),folder);studio.run(folder)
    originals={p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    for fault in ('typed-pass','typed-approval','numeric-fidelity','drop-stage','zip-payload','extra-file'):
        try:
            r=read(folder/'result.json');c=read(folder/'completion.json')
            if fault=='typed-pass':r['scene_samples_passed']=1
            elif fault=='typed-approval':r['quality_approved']=0
            elif fault=='drop-stage':r['inherited_surface_checked']=True
            elif fault=='numeric-fidelity':
                with np.load(folder/'fidelity.npz',allow_pickle=False) as z:arrays={n:z[n].copy() for n in z.files}
                arrays['actor_0_errors_m'][0]=.1;np.savez_compressed(folder/'fidelity.npz',**arrays)
            elif fault=='zip-payload':
                with zipfile.ZipFile(folder/'checked-assets.zip') as z:files={n:z.read(n) for n in z.namelist()}
                files['actors/0.glb']=b'changed'
                with zipfile.ZipFile(folder/'checked-assets.zip','w') as z:
                    for n,data in files.items():z.writestr(n,data)
            else:(folder/'unrequested.json').write_text('{}')
            save(folder/'result.json',r);c['result_sha256']=sha256(folder/'result.json')
            c['downloads']={n:sha256(folder/n) for n in c['downloads']}
            c['produced_files_sha256']={n:sha256(folder/n) for n in c['produced_files_sha256']}
            save(folder/'completion.json',c)
            with pytest.raises((ValueError,OSError)):studio.manifest(folder.name)
        finally:
            for path,data in originals.items():path.write_bytes(data)
            (folder/'unrequested.json').unlink(missing_ok=True)


def test_inherited_surface_intent_is_freshly_checked_and_preserved(context,monkeypatch):
    import numpy as np
    from native_surface_contact import normals
    from native_scene_geometry import faces_for
    parent,_,surface=context
    spec=read(parent/'authoring/contacts.json');scene=sources.SceneContacts(spec,parent/'authoring')
    rig=scene.actors['A']['rig'];vertices=rig.vertices(scene.actors['A']['sampler'].sample(1.))
    faces,_=faces_for(rig)
    normal=normals(vertices,faces,[[0]],minimum_area=1e-14,minimum_coherence=.1)[0]['normal_world']
    surface=copy.deepcopy(surface)
    surface['contacts'][spec['contacts'][0]['id']]['target_normal']['normals']=[(-np.asarray(normal)).tolist()]
    monkeypatch.setattr(sources,'origins',lambda *a:([dict(job='explicit-lineage-fixture')],copy.deepcopy(surface)))
    m=studio.metadata('scene','scene1');folder=studio.folder_for('precision-with-normals')
    studio.prepare(dict(schema=studio.SCHEMA,source=m['source']),folder);r=studio.run(folder)
    assert r['inherited_surface_checked'] and r['inherited_surface_samples_passed'] and r['checked_package_available']
    checked=read(folder/'portable-surface-policy.json');assert checked['contacts']==surface['contacts']
    assert studio.manifest(folder.name)['inherited_surface_checked'] is True
