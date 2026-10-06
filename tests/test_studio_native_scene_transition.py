"""Offline staging, contained serving and portable transition export history."""
from pathlib import Path
import sys,copy,io,json,threading,zipfile
from types import SimpleNamespace
import pytest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import studio_native_scene_transition as studio
import native_transition_lineage as lineage
import native_scene_transition as assembly
import studio_native_scene as scenes
import studio_native_scene_game as games
import action_studio_server as server
import action_worker_lock as locks
from test_native_scene_transition import fixture
from test_native_scene_geometry import policy
from strep import read,save,sha256


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('studio-transition');patch=pytest.MonkeyPatch()
    for module in (studio,scenes,games,server,locks):patch.setattr(module,'ROOT',root)
    source=root/'reports/original';path,_=fixture(source);out=root/'reports/assembled';assembly.run(path,out)
    geometry=policy(out/'scene.json');geometry.pop('schema');geometry.pop('contacts_sha256');geometry['clock']['times_s']=read(out/'roots.json')['times_s']
    payload=dict(schema='strep-studio-native-scene-transition-v1',source=dict(folder='assembled',result_sha256=sha256(out/'result.json')),geometry=geometry)
    folder=studio.folder_for('stage1');studio.prepare(payload,folder)
    yield root,out,payload,folder
    patch.undo()


def test_separate_stage_keeps_all_source_bytes_negative_checks_and_unconfirmed_timing(study):
    root,source,payload,folder=study;m=studio.manifest('stage1');assert studio.verify(folder)['staging_conditions_pass']
    assert m['source_conditions_pass'] is False and m['source_checks']['contacts'] is False and not m['quality_approved']
    assert all(not t['confirmed'] for t in m['game_tracks']['markers']) and m['draft']['geometry']==payload['geometry'] and m['draft']['object_edit'] is None
    assert {p.relative_to(source).as_posix():sha256(p) for p in source.rglob('*') if p.is_file()}==read(folder/'prepared.json')['source_files_sha256']
    for n,a in m['draft']['scene']['actors'].items():
        resolved=studio.served_file(a['glb'].removeprefix('/files/'));assert sha256(resolved)==a['sha256'] and a['animation_index']==3
    spec,_,_,_=scenes.validate_request(m['draft'],lambda u:studio.served_file(u.removeprefix('/files/')))
    assert spec['contacts']==read(source/'scene.json')['contacts'] and studio.listing()['jobs'][0]['status']=='complete'
    for path in ('native-scene-transition-jobs/stage1/../prepared.json','native-scene-transition-jobs/stage1/prepared.json','native-scene-transition-jobs/stage1/implementation/strep.py'):
        with pytest.raises(ValueError):studio.served_file(path)


@pytest.mark.parametrize('fault',['escape','absolute','backslash','query','binding','extra','bad-plane'])
def test_bad_stage_requests_reject_before_output(study,tmp_path,fault):
    _,_,payload,_=study;p=copy.deepcopy(payload)
    if fault=='escape':p['source']['folder']='../assembled'
    elif fault=='absolute':p['source']['folder']='C:/assembled'
    elif fault=='backslash':p['source']['folder']='x\\assembled'
    elif fault=='query':p['source']['folder']='assembled?x=1'
    elif fault=='binding':p['source']['result_sha256']='0'*64
    elif fault=='extra':p['approve_animation']=True
    else:p['geometry']['planes']['floor']=dict(normal_world=[0,0,0],offset_m=0)
    out=studio.folder_for('bad-'+fault)
    with pytest.raises(ValueError):studio.prepare(p,out)
    assert not out.exists()


def test_portable_lineage_carries_original_libraries_scenes_confirmations_and_failed_measurements(study):
    root,_,_,folder=study;draft=read(folder/'stage-draft.json');out=root/'lineage';receipt=lineage.snapshot(draft,out)
    assert lineage.verify(draft,out,receipt)==receipt
    record=read(out/'record.json');assert record['jobs']['stage1']['source_conditions_pass'] is False
    base=out/'jobs/stage1';a=read(base/'first-scene.json');b=read(base/'second-scene.json')
    for spec in (a,b):
        for actor in spec['actors'].values():assert actor['glb'].startswith('libraries/') and sha256(base/actor['glb'])==actor['sha256']
    assert any(m['confirmed'] for m in read(base/'first-game-tracks.json')['markers'])
    assert all(not m['confirmed'] for m in read(base/'game-tracks-request.json')['markers'])
    assert read(base/'result.json')['checks']['contacts'] is False and len(read(base/'result.json')['timeline_mapping'])==16
    package=lineage.package_files(out,receipt);assert len(package)==len(receipt['files_sha256'])+1 and 'transition-lineage/record.json' in package
    with zipfile.ZipFile(root/'lineage.zip','w') as z:
        for n,p in package.items():z.write(p,n)
    with zipfile.ZipFile(root/'lineage.zip') as z:assert all(z.read(n)==p.read_bytes() for n,p in package.items())
    assert 'native_transition_lineage.py' in scenes.method_names(draft)
    for name in ('studio_native_scene_transition.py','native_transition_lineage.py'):assert name in games.method_names(SimpleNamespace(objects={'box':1}),transitions=True)
    p=base/'result.json';old=p.read_bytes()
    try:
        v=read(p);v['checks']['contacts']=True;save(p,v)
        with pytest.raises(ValueError):lineage.verify(draft,out,receipt)
    finally:p.write_bytes(old)


def test_scene_prepare_freezes_transition_history_without_executing_an_engine(study):
    root,_,_,folder=study;draft=read(folder/'stage-draft.json');engine=root/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';engine.parent.mkdir(parents=True);engine.write_bytes(b'CPU test engine stub; never executed')
    out=scenes.folder_for('export1');p=scenes.prepare(draft,out,lambda url:studio.served_file(url.removeprefix('/files/')))
    assert p['transition_lineage'] and scenes.frozen(out)==p and 'transition-lineage/record.json' in scenes.download_names(p)
    old=read(out/'transition-lineage/record.json');v=copy.deepcopy(old);v['quality_approved']=True;save(out/'transition-lineage/record.json',v)
    with pytest.raises(ValueError):scenes.frozen(out)
    save(out/'transition-lineage/record.json',old)


def handler(payload,path):
    h=server.Handler.__new__(server.Handler);h.path=path;body=json.dumps(payload).encode();h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(body))}
    h.rfile=io.BytesIO(body);h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},worker=None,job_lock=threading.Lock());h.responses=[];h.respond=lambda code,value:h.responses.append((code,value));return h


def test_offline_inspection_handler_obeys_origin_and_content_gates(study):
    _,_,payload,_=study;h=handler(payload['source'],'/api/native-scene-transition-inspect');h.do_POST();assert h.responses[-1][0]==200 and h.responses[-1][1]['checks']['contacts'] is False
    for field,value,expected in [('Host','bad.test',403),('Origin','http://bad.test',403),('Content-Type','text/plain',415)]:
        h=handler(payload['source'],'/api/native-scene-transition-inspect');h.headers[field]=value;h.do_POST();assert h.responses[-1][0]==expected


@pytest.mark.parametrize('fault',['quality-integer','original-integer','marker-integer','extra-file'])
def test_lineage_rejects_rehashed_typed_aliases_and_incomplete_population(tmp_path,monkeypatch,fault):
    original=tmp_path/'original.glb';original.write_bytes(b'original unchanged payload')
    record=dict(schema='strep-native-transition-lineage-v1',quality_approved=False,jobs={'stage':dict(original_sources_and_annotations_included=True)})
    payload=dict(markers=[dict(confirmed=False)])
    files={'original.glb':('file',original,sha256(original)),'markers.json':('json',payload,None)}
    monkeypatch.setattr(lineage,'plan',lambda _: (copy.deepcopy(record),copy.deepcopy(files),{str(original):sha256(original)}))
    out=tmp_path/'snapshot';receipt=lineage.snapshot({},out);assert lineage.verify({},out,receipt)==receipt
    v=read(out/'record.json')
    if fault=='quality-integer':v['quality_approved']=0
    elif fault=='original-integer':v['jobs']['stage']['original_sources_and_annotations_included']=1
    elif fault=='marker-integer':
        save(out/'markers.json',dict(markers=[dict(confirmed=0)]));v['files_sha256']['markers.json']=sha256(out/'markers.json');receipt['files_sha256']=copy.deepcopy(v['files_sha256'])
    else:(out/'extra.json').write_text('{}')
    save(out/'record.json',v);receipt['record_sha256']=sha256(out/'record.json')
    with pytest.raises(ValueError):lineage.verify({},out,receipt)
