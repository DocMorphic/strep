"""Generated skins and explicitly mocked parent manifests/engine subprocesses."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile
import json

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_surface_export as studio
import studio_native_scene as scenes
import studio_native_scene_game as games
import action_studio_server as server
import native_scene_engine as actor_engine
import test_native_imported_surface_contact as generated
from native_scene_contacts import SceneContacts
from strep import save,read,sha256
from test_studio_native_scene import handler


def setup(root,patch):
    for module in (studio,scenes,games,server):patch.setattr(module,'ROOT',root)
    parent=scenes.folder_for('scene1');(parent/'authoring').mkdir(parents=True)
    patch.setattr(generated,'actor_run',lambda path,out,**kw:actor_engine.run(path,out.with_name('actors-engine'),**kw))
    contacts,sp,gp,_=generated.actor_producer(parent/'authoring',patch)
    spec=read(contacts);source=contacts.parent/spec['actors']['A']['glb']
    result=dict(status='complete',sampled_conditions_pass=True,artifacts=dict(active_contacts=str(contacts)))
    save(parent/'authoring/result.json',result);save(parent/'pipeline.json',dict(status='complete'))
    save(parent/'draft.json',dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=read(gp),object_edit=None))
    save(parent/'prepared.json',dict(sources=dict(A=dict(path=str(source),url='/files/character-assets/fixture/character.glb',sha256=sha256(source))),
        engine_path=str(parent/'authoring/mock-engine')))
    # The complete imported actor producer is real CPU reconstruction; the
    # parent scene/package manifest below is an explicit transport test double.
    policy=read(gp);save(parent/'geometry-policy.json',policy)
    # Producer binds its own original policy, so the wrapper selects that exact
    # path by placing the original authored policy at the standard location.
    # Recreate the producer with that location rather than rebinding receipts.
    import shutil
    shutil.rmtree(parent/'authoring/actors-engine')
    actor_engine.run(contacts,parent/'authoring/actors-engine',geometry_policy=parent/'geometry-policy.json',
        engine=parent/'authoring/mock-engine',playback_mode='native-authoring')
    portable=copy.deepcopy(spec);portable['actors']['A']['glb']='actors/0.glb'
    with zipfile.ZipFile(parent/'assets.zip','w') as z:
        z.writestr('scene.json',json.dumps(portable).encode());z.writestr('actors/0.glb',source.read_bytes())
        z.writestr('animations/A.res',(parent/'authoring/actors-engine/A-animation.res').read_bytes())
        z.writestr('package.json',json.dumps(dict(root_event_tracks_included=False,quality_approved=False)))
    def parent_manifest(job):
        assert job=='scene1'
        return dict(id=job,status='complete',sampled_conditions_pass=read(parent/'authoring/result.json')['sampled_conditions_pass'],
            result_sha256=sha256(parent/'authoring/result.json'),downloads=[],quality_approved=False)
    patch.setattr(scenes,'manifest',parent_manifest)
    game=games.folder_for('game1');game.mkdir(parents=True)
    save(game/'result.json',dict(source_scene_job='scene1',root_samples_pass=True,event_helper_dispatch_verified=True))
    save(game/'pipeline.json',dict(status='complete'))
    with zipfile.ZipFile(parent/'assets.zip') as src,zipfile.ZipFile(game/'game-assets.zip','w') as z:
        for info in src.infolist():z.writestr(info,src.read(info.filename))
        z.writestr('root-motion.json',b'{"fixture_root_reference":true}')
        z.writestr('events.json',b'{"fixture_events":["touch"]}')
        z.writestr('runtime/events.gd',b'# explicit fixture helper, not engine evidence')
    patch.setattr(games,'manifest',lambda job:dict(id=job,status='complete'))
    surface=read(sp);surface.pop('schema');surface.pop('contacts_sha256')
    return parent,game,surface


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    patch=pytest.MonkeyPatch();root=tmp_path_factory.mktemp('sfe');parent,game,surface=setup(root,patch)
    payloads={};folders={}
    for kind,job in [('scene','scene1'),('game','game1')]:
        m=studio.metadata(kind,job);p=dict(schema=studio.SCHEMA,source=m['source'],surface=surface,
            normal_origins_sha256=m['normal_origins_sha256'],normal_revision=None)
        folder=studio.folder_for(kind+'-checked');studio.prepare(p,folder);studio.run(folder);payloads[kind]=p;folders[kind]=folder
    yield root,parent,game,surface,payloads,folders
    patch.undo()


@pytest.mark.parametrize('kind',['scene','game'])
def test_checked_export_preserves_all_source_payloads_and_rebinds_only_portable_digest(study,kind):
    _,parent,game,_,payloads,folders=study;folder=folders[kind];m=studio.manifest(folder.name)
    assert m['checked_package_available'] is True and m['new_engine_executed'] is False and m['engine_queries_reused'] is True
    assert all(m[k] is False for k in studio.FALSE_FLAGS) and m['root_event_tracks_included'] is (kind=='game')
    src=parent/'assets.zip' if kind=='scene' else game/'game-assets.zip'
    with zipfile.ZipFile(src) as original,zipfile.ZipFile(folder/'checked-assets.zip') as checked:
        assert set(checked.namelist())==set(original.namelist())|set(studio.ADDED)
        assert all(checked.read(n)==original.read(n) for n in original.namelist())
        policy=json.loads(checked.read('surface-policy.json'));portable_hash=__import__('hashlib').sha256(checked.read('scene.json')).hexdigest()
        assert policy['contacts_sha256']==portable_hash and policy['contacts']==payloads[kind]['surface']['contacts']
        if kind=='game':assert checked.read('events.json')==original.read('events.json') and checked.read('root-motion.json')==original.read('root-motion.json')
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/source-assets.zip') is None
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/audit/observations.npz') is None
    assert studio.served_file(studio.NAMESPACE+'/'+folder.name+'/checked-assets.zip')==folder/'checked-assets.zip'


def test_facing_failure_blocks_checked_zip_while_point_contacts_pass(study):
    _,_,_,_,payloads,_=study;p=copy.deepcopy(payloads['scene'])
    first=next(iter(p['surface']['contacts'].values()));first['target_normal']['normals']=[[0,-1,0]]
    folder=studio.folder_for('facing-failure');studio.prepare(p,folder);r=studio.run(folder)
    assert r['point_conditions_pass'] is True and r['surface_conditions_pass'] is False
    assert r['checked_package_available'] is False and not (folder/'checked-assets.zip').exists()
    m=studio.manifest(folder.name);assert all(d['label']!='checked-assets.zip' for d in m['downloads'])


@pytest.mark.parametrize('fault',['source-result','origin-result','missing-contact','nonunit-normal','extra-field','schema','revision-without-origin','budget-boolean'])
def test_bad_authoring_requests_reject_before_output(study,fault):
    _,_,_,_,payloads,_=study;p=copy.deepcopy(payloads['scene'])
    if fault=='source-result':p['source']['result_sha256']='f'*64
    elif fault=='origin-result':p['normal_origins_sha256']='f'*64
    elif fault=='missing-contact':p['surface']['contacts'].clear()
    elif fault=='nonunit-normal':next(iter(p['surface']['contacts'].values()))['target_normal']['normals']=[[0,2,0]]
    elif fault=='extra-field':p['automatically_approve']=True
    elif fault=='schema':p['schema']='wrong'
    elif fault=='revision-without-origin':p['normal_revision']=dict(notes='fake change')
    elif fault=='budget-boolean':p['surface']['maximum_actor_pose_queries']=True
    folder=studio.folder_for('reject-'+fault)
    with pytest.raises(ValueError):studio.prepare(p,folder)
    assert not folder.exists()


def test_inherited_normals_cannot_silently_relax_or_drop_when_scene_scope_changes(study,monkeypatch):
    _,_,_,surface,payloads,_=study;original=studio.origins
    # Explicit lineage transport double; no animator/anatomical review implied.
    rows=[dict(job='transfer-origin',result_sha256='a'*64,actor_assignments={'A':'A'},original_scene={},original_surface=surface)]
    monkeypatch.setattr(studio,'origins',lambda *a:(copy.deepcopy(rows),copy.deepcopy(surface)))
    m=studio.metadata('scene','scene1');p=copy.deepcopy(payloads['scene']);p['normal_origins_sha256']=m['normal_origins_sha256']
    studio.validate_request(p)
    p['surface']['limits']['maximum_opposition_error_degrees']=30
    with pytest.raises(ValueError,match='Explicit'):studio.validate_request(p)
    p['normal_revision']=dict(notes='Explicit fixture experiment with a different facing limit; original intent retained.')
    studio.validate_request(p)
    monkeypatch.setattr(studio,'origins',lambda *a:(copy.deepcopy(rows),None))
    p['surface']=copy.deepcopy(surface);p['normal_revision']=None
    with pytest.raises(ValueError):studio.validate_request(p)


@pytest.mark.parametrize('fault',['typed-pass','typed-approval','portable-normals','zip-events','zip-extra','gate-approval','audit-count'])
def test_rehashed_publication_changes_do_not_manufacture_a_checked_package(study,fault):
    _,_,_,_,_,folders=study;folder=folders['game'];mutated={}
    for name in ('result.json','completion.json'):mutated[folder/name]=(folder/name).read_bytes()
    def change(name,edit):
        path=folder/name;mutated.setdefault(path,path.read_bytes());value=read(path);edit(value);save(path,value)
    try:
        if fault=='typed-pass':change('result.json',lambda r:r.update(checked_package_available=1))
        elif fault=='typed-approval':change('result.json',lambda r:r.update(quality_approved=0))
        elif fault=='portable-normals':change('portable-surface-policy.json',lambda p:p['limits'].update(maximum_opposition_error_degrees=90))
        elif fault=='gate-approval':change('surface-gate.json',lambda p:p.update(release_approved=True))
        elif fault=='audit-count':change('audit/result.json',lambda r:r['counts']['native-authoring'].update(points=999))
        elif fault in ('zip-events','zip-extra'):
            path=folder/'checked-assets.zip';mutated[path]=path.read_bytes()
            with zipfile.ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
            files['events.json' if fault=='zip-events' else 'unrequested.json']=b'changed'
            with zipfile.ZipFile(path,'w') as z:
                for n,data in files.items():z.writestr(n,data)
        r=read(folder/'result.json');r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']}
        if fault=='audit-count':r['imported_surface_result_sha256']=sha256(folder/'audit/result.json')
        save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        with pytest.raises(ValueError):studio.manifest(folder.name)
    finally:
        for path,data in mutated.items():path.write_bytes(data)


def test_unchanged_receipt_cache_returns_copies_and_changed_resource_forces_full_replay(study,monkeypatch):
    _,parent,_,_,_,folders=study;folder=folders['scene'];before=studio.manifest(folder.name)
    def fail(*a):raise ValueError('full replay required')
    monkeypatch.setattr(studio,'verify',fail);value=studio.manifest(folder.name);value['source']['job']='changed'
    assert studio.manifest(folder.name)==before
    path=parent/'authoring/actors-engine/A-animation.res';data=path.read_bytes()
    try:
        path.write_bytes(data+b'changed')
        with pytest.raises(ValueError,match='full replay'):studio.manifest(folder.name)
    finally:path.write_bytes(data)


@pytest.mark.parametrize('fault,expected',[('host',403),('origin',403),('type',415),('size',400),('busy',409),('valid',202)])
def test_offline_loopback_and_worker_dispatch(study,monkeypatch,fault,expected):
    _,_,_,_,payloads,_=study;calls=[]
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:(calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None)))
    h=handler(payloads['scene'],'/api/surface-export-assets')
    if fault=='host':h.headers['Host']='remote.test'
    elif fault=='origin':h.headers['Origin']='https://remote.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST();assert h.responses[-1][0]==expected and len(calls)==(fault=='valid')
    if calls:assert Path(calls[0][0][1]).name=='studio_surface_export.py' and calls[0][1]['env']['HF_HUB_OFFLINE']=='1'


def test_failure_keeps_partial_audit_and_never_exposes_checked_files(study,monkeypatch):
    _,_,_,_,payloads,_=study;folder=studio.folder_for('failed-worker');studio.prepare(payloads['scene'],folder)
    def fail(*args,**kw):out=args[4];out.mkdir();save(out/'partial.json',dict(retained=True));raise ValueError('fixture failure')
    monkeypatch.setattr(studio.imported,'run',fail)
    with pytest.raises(ValueError,match='fixture failure'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and (folder/'audit/partial.json').exists()
    assert studio.manifest(folder.name)['downloads']==[]


@pytest.mark.parametrize('field',['scene_conditions_pass','root_conditions_pass','event_dispatch_verified'])
@pytest.mark.parametrize('failed_value',[False,1])
def test_scene_root_or_event_gate_is_independent_of_passing_surface_samples(study,field,failed_value):
    _,_,_,_,_,folders=study;folder=folders['game']
    metadata=read(folder/'source.json');metadata[field]=failed_value
    r=studio.outcome(folder,metadata,read(folder/'audit/result.json'),read(folder/'replay.json'))
    assert r['point_conditions_pass'] is True and r['surface_conditions_pass'] is True
    assert r['checked_package_available'] is False and r['all_declared_scene_and_surface_samples_pass'] is False


@pytest.mark.parametrize('fault',['changed-scene','multiple-origins','clip','sha','not-passing','malformed-url'])
def test_real_lineage_reader_retains_origins_and_only_inherits_exact_scene_intent(study,monkeypatch,fault):
    _,parent,_,surface,_,_=study;prepared=read(parent/'prepared.json');spec=read(Path(read(parent/'authoring/result.json')['artifacts']['active_contacts']))
    original=copy.deepcopy(spec);current=copy.deepcopy(spec)
    url='/files/'+studio.transfers.NAMESPACE+'/origin/actors/actor-0.glb'
    prepared['sources']['A']['url']=url
    origin=dict(status='complete',staging_conditions_pass=True,result_sha256='c'*64,
        authoring_request=dict(draft=dict(scene=original),calibration=dict(surface=surface)),
        stage_draft=dict(scene=original),actors=dict(A=dict(candidate_url=url,candidate_sha256=spec['actors']['A']['sha256'],animation_index=spec['actors']['A']['animation_index'])))
    if fault=='changed-scene':current['duration_s']+=.01
    elif fault=='multiple-origins':
        current['actors']['B']=copy.deepcopy(current['actors']['A']);prepared['sources']['B']=copy.deepcopy(prepared['sources']['A'])
        prepared['sources']['B']['url']=url.replace('/origin/','/other/')
    elif fault=='clip':origin['actors']['A']['animation_index']+=1
    elif fault=='sha':origin['actors']['A']['candidate_sha256']='d'*64
    elif fault=='not-passing':origin['staging_conditions_pass']=False
    elif fault=='malformed-url':prepared['sources']['A']['url']=url.replace('actor-0','actor-8')
    def manifest(job):
        value=copy.deepcopy(origin)
        if job=='other':value['actors']['A']['candidate_url']=url.replace('/origin/','/other/')
        return value
    monkeypatch.setattr(studio.transfers,'manifest',manifest)
    before=(parent/'prepared.json').read_bytes()
    try:
        save(parent/'prepared.json',prepared)
        if fault in ('clip','sha','not-passing','malformed-url'):
            with pytest.raises(ValueError):studio.origins(parent,current)
        else:
            rows,inherited=studio.origins(parent,current)
            assert inherited is None and rows[0]['original_surface']==surface
            assert len(rows)==(2 if fault=='multiple-origins' else 1)
            rows,inherited=studio.origins(parent,original) if fault=='changed-scene' else (rows,None)
            if fault=='changed-scene':assert inherited==surface
    finally:(parent/'prepared.json').write_bytes(before)


@pytest.mark.parametrize('name',['../secret','/absolute','a\\b','a:stream','a/./b','surface-policy.json'])
def test_unsafe_or_surface_overwriting_source_zip_is_rejected(tmp_path,name):
    path=tmp_path/'source.zip'
    # ZipInfo normally rewrites Windows separators before writing. Preserve
    # the literal hostile header so this is a malformed ZIP on either OS.
    info=zipfile.ZipInfo('fixture');info.filename=name
    with zipfile.ZipFile(path,'w') as z:z.writestr(info,b'fixture')
    with pytest.raises(ValueError):studio.zip_members(path)


@pytest.mark.parametrize('query',['kind=scene&id=scene1&id=other','kind=scene&id=scene1&extra=1','kind=other&id=scene1','id=scene1','kind=scene&id=../scene1'])
def test_source_read_route_rejects_ambiguous_or_uncontained_selection(study,query):
    h=handler({},'/api/surface-export-source?'+query);h.do_GET()
    assert h.responses[-1][0]==400
