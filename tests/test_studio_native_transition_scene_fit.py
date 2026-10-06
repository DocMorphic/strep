"""Contained bridge jobs, exact appended drafts and portable failed-epoch history."""
from pathlib import Path
import sys,copy,io,json,threading,zipfile
from types import SimpleNamespace
import pytest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import studio_native_transition_scene_fit as studio
import studio_native_scene_transition as transitions
import studio_native_scene as scenes
import studio_native_scene_game as games
import native_transition_scene_fit_lineage as lineage
import native_transition_scene_fit as correction
import action_studio_server as server
import action_worker_lock as locks
from test_native_transition_scene_fit import fixture
from strep import read,save,sha256


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('studio-bridge-fit');patch=pytest.MonkeyPatch()
    for module in (studio,transitions,scenes,games,server,locks):patch.setattr(module,'ROOT',root)
    path,recipe,_=fixture(root/'reports/authored');payload={k:copy.deepcopy(v) for k,v in recipe.items() if k not in ('schema','source')}
    payload.update(schema=studio.SCHEMA,source=dict(folder='authored/assembly',result_sha256=recipe['source']['result_sha256']),resume_from=None);payload['iterations']=1
    folder=studio.folder_for('fit1');studio.prepare(payload,folder);studio.run(folder);review=studio.manifest('fit1')
    yield root,payload,folder,review
    patch.undo()


def test_catalog_run_and_separate_draft_preserve_clip_roles_failures_and_exact_timing(study):
    root,payload,folder,m=study;catalog=studio.catalog(payload['source'])
    assert catalog['bridge_interval_s']==payload['actors']['A']['window_s'] and catalog['source_checks']['contacts'] is False
    assert all(a['original_clip_count']==4 and any(t['eligible'] and len(t['tangent_guards'])==2 for t in a['tracks']) for a in catalog['actors'].values())
    assert m['status']=='complete' and m['all_declared_samples_pass'] is False and m['checks']['native_contact_audit'] is False
    assert m['original_selected'] and not m['studio_selection_changed'] and m['native_roots_only'] and not m['engine_playback_verified']
    assert m['draft']['scene']['objects']==read(folder/'candidate/scene.json')['objects'] and m['draft']['object_edit'] is None
    assert m['draft']['scene']['contacts']==read(folder/'candidate/scene.json')['contacts']
    assert all(a['animation_index']==m['original_animation_counts'][n]==4 for n,a in m['draft']['scene']['actors'].items())
    assert all(not row['confirmed'] for row in m['game_tracks']['markers'])
    assert studio.listing()['jobs']==[dict(id='fit1',status='complete')]
    before={p:sha256(p) for p in folder.rglob('*') if p.is_file()};assert studio.run(folder)['candidate_result_sha256']==m['candidate_result_sha256']
    assert all(sha256(p)==h for p,h in before.items())


@pytest.mark.parametrize('fault',['escape','absolute','backslash','query','binding','extra','bool-iterations','bool-budget','phase-window','bad-track'])
def test_invalid_requests_reject_before_outputs(study,fault):
    _,payload,_,_=study;p=copy.deepcopy(payload)
    if fault=='escape':p['source']['folder']='../authored/assembly'
    elif fault=='absolute':p['source']['folder']='C:/bad'
    elif fault=='backslash':p['source']['folder']='authored\\assembly'
    elif fault=='query':p['source']['folder']+='?x=1'
    elif fault=='binding':p['source']['result_sha256']='0'*64
    elif fault=='extra':p['quality_approved']=True
    elif fault=='bool-iterations':p['iterations']=True
    elif fault=='bool-budget':p['maximum_pose_vertex_queries']=True
    elif fault=='phase-window':p['actors']['A']['window_s'][0]=0
    else:p['actors']['A']['tracks'][0]['node']=1000
    out=studio.folder_for('bad-'+fault)
    with pytest.raises(ValueError):studio.prepare(p,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['approve','integer-original','missing-file','marker-confirmation','wrong-index'])
def test_rehashed_job_completion_and_staged_payload_cannot_change_decisions(study,monkeypatch,fault):
    _,_,folder,_=study;verified=read(folder/'candidate/result.json');monkeypatch.setattr(correction,'verify',lambda _:copy.deepcopy(verified))
    files={n:(folder/n).read_bytes() for n in ('completion.json','stage-draft.json','stage-game-tracks.json')}
    try:
        c=read(folder/'completion.json')
        if fault=='approve':c['quality_approved']=True
        elif fault=='integer-original':c['original_selected']=1
        elif fault=='missing-file':c['files_sha256'].pop('candidate/fit/source-rate-caps.npz')
        else:
            file='stage-game-tracks.json' if fault=='marker-confirmation' else 'stage-draft.json';v=read(folder/file)
            if fault=='marker-confirmation':v['markers'][0]['confirmed']=True
            else:v['scene']['actors']['A']['animation_index']=3
            save(folder/file,v);c['files_sha256'][file]=sha256(folder/file)
        save(folder/'completion.json',c)
        with pytest.raises(ValueError):studio.manifest('fit1')
    finally:
        for n,b in files.items():(folder/n).write_bytes(b)


def test_portable_history_keeps_original_libraries_contacts_caps_and_parent_only_failures(study,tmp_path,monkeypatch):
    _,_,folder,m=study;monkeypatch.setattr(studio,'manifest',lambda _:copy.deepcopy(m))
    draft=m['draft'];out=tmp_path/'history';receipt=lineage.snapshot(draft,out);lineage.verify(draft,out,receipt)
    record=read(out/'record.json');job=record['jobs']['fit1'];assert not job['all_declared_samples_pass'] and not job['checks']['native_contact_audit']
    assert job['source_motion_caps_and_permissions_included'] and job['numerical_decisions_apply_to_parent_only'] and not job['complete_fit_trials_included']
    for n in ('original-scene.json','candidate-scene.json','transition/first-scene.json','transition/second-scene.json'):
        spec=read(out/'jobs/fit1'/n)
        for a in spec['actors'].values():assert sha256(out/'jobs/fit1'/Path(n).parent/a['glb'])==a['sha256']
    assert read(out/'jobs/fit1/result.json')['all_declared_samples_pass'] is False
    assert any(t['confirmed'] for t in read(out/'jobs/fit1/transition/first-game-tracks.json')['markers'])
    assert all(not t['confirmed'] for t in read(out/'jobs/fit1/game-tracks-request.json')['markers'])
    package=lineage.package_files(out,receipt);assert all(n.startswith('transition-corrections/') for n in package)
    with zipfile.ZipFile(tmp_path/'history.zip','w') as z:
        for n,p in package.items():z.write(p,n)
    with zipfile.ZipFile(tmp_path/'history.zip') as z:assert all(z.read(n)==p.read_bytes() for n,p in package.items())
    for n in ('native_transition_scene_fit_lineage.py','studio_native_transition_scene_fit.py'):assert n in scenes.method_names(draft) and n in games.method_names(SimpleNamespace(objects={'box':1}),transition_corrections=True)
    file=out/'record.json';v=read(file);v['quality_approved']=0;save(file,v);receipt['record_sha256']=sha256(file)
    with pytest.raises(ValueError):lineage.verify(draft,out,receipt)


def test_contained_serving_and_manifest_binding_reject_unpublished_or_traversal(study,monkeypatch):
    _,_,_,m=study;monkeypatch.setattr(studio,'manifest',lambda _:copy.deepcopy(m))
    for a in m['draft']['scene']['actors'].values():assert sha256(studio.served_file(a['glb'].removeprefix('/files/')))==a['sha256']
    for suffix in ['../prepared.json','prepared.json','implementation/strep.py','candidate/actors/../../prepared.json','candidate/actors/0.glb?x=1']:
        with pytest.raises(ValueError):studio.served_file(studio.NAMESPACE+'/fit1/'+suffix)


def test_scene_prepare_includes_complete_bridge_history_before_any_engine_runs(study,monkeypatch):
    root,_,_,m=study;monkeypatch.setattr(studio,'manifest',lambda _:copy.deepcopy(m))
    executable=root/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe';executable.parent.mkdir(parents=True);executable.write_bytes(b'Not executed by source test')
    out=scenes.folder_for('scene1');p=scenes.prepare(m['draft'],out,lambda url:studio.served_file(url.removeprefix('/files/')))
    assert p['transition_correction_lineage'] and scenes.frozen(out)==p
    assert 'transition-correction-lineage/record.json' in scenes.download_names(p)
    v=read(out/'prepared.json');v['transition_correction_lineage']=None;save(out/'prepared.json',v)
    with pytest.raises(ValueError):scenes.frozen(out)
    save(out/'prepared.json',p)


def handler(payload,path):
    h=server.Handler.__new__(server.Handler);h.path=path;body=json.dumps(payload).encode();h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(body))}
    h.rfile=io.BytesIO(body);h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},worker=None,job_lock=threading.Lock());h.responses=[];h.respond=lambda code,value:h.responses.append((code,value));return h


def test_offline_catalog_handler_retains_host_origin_content_gates(study):
    _,payload,_,_=study;h=handler(payload['source'],'/api/native-transition-fit-catalog');h.do_POST();assert h.responses[-1][0]==200
    for field,value,code in [('Host','bad.test',403),('Origin','http://bad.test',403),('Content-Type','text/plain',415)]:
        h=handler(payload['source'],'/api/native-transition-fit-catalog');h.headers[field]=value;h.do_POST();assert h.responses[-1][0]==code


def test_resume_retains_the_same_bound_epoch_and_rejects_permission_geometry_and_budget_changes(study,monkeypatch):
    _,payload,folder,m=study;r=copy.deepcopy(payload);r['resume_from']=m['candidate_binding'];r['label']='Continued';r['iterations']=2
    monkeypatch.setattr(correction,'verify',lambda _:read(folder/'candidate/result.json'))
    recipe,p,prior=studio.validate_request(r);assert prior==folder/'candidate' and recipe['actors']==payload['actors']
    for field in ['actors','geometry','maximum_pose_vertex_queries']:
        forged=copy.deepcopy(r)
        if field=='actors':forged[field]['A']['maximum_joint_displacement_m']*=.9
        elif field=='geometry':forged[field]['limits']['penetration_m']*=.9
        else:forged[field]-=1
        with pytest.raises(ValueError,match='Resume source'):studio.validate_request(forged)
    request=folder/'candidate/fit/request.json';old=request.read_bytes()
    try:
        v=read(request);v['resume']=dict(source_directory='C:/outside');save(request,v)
        with pytest.raises(ValueError,match='Contained'):studio.validate_request(r)
    finally:request.write_bytes(old)
