"""Tiny generated skins and explicit upstream engine doubles; no live HTTP."""
import copy
import io
import json
from pathlib import Path
import sys
import zipfile
from types import SimpleNamespace

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_native_scene_transfer as studio
import studio_native_rig_transfer as transfers
import studio_native_scene as scenes
import studio_characters as chars
import action_studio_server as server
import action_worker_lock
import audit_native_rig_transfer as engine
from strep import read,save,sha256
from test_native_transfer_surface_calibration import scene_fixture
from test_studio_native_rig_transfer import engine_double
from test_studio_native_scene import handler


def setup(root,patch,*,actual_engine=False):
    for module in (studio,transfers,scenes,server,action_worker_lock):patch.setattr(module,'ROOT',root)
    patch.setattr(chars,'ASSETS',root/'reports/c')
    if not actual_engine:patch.setattr(engine,'run',engine_double)
    recipe=scene_fixture(root/'fixture');request=dict(animation_index=0,rate=120)
    for side,file,profile in [('source','actor.glb','actor-profile.json'),('target','replacement.glb','replacement-profile.json')]:
        m=chars.import_bytes((recipe.parent/file).read_bytes(),file)
        saved=chars.save_profile(dict(asset_id=m['id'],profile=read(recipe.parent/profile)))
        request.update({side+'_asset_id':m['id'],side+'_profile_id':saved['profile_id']})
    upstream=transfers.folder_for('native1');transfers.prepare(request,upstream);transfers.run(upstream)
    source=read(recipe.parent/'scene.json');paths={}
    for name,entry in source['actors'].items():
        path=recipe.parent/entry['glb'];m=chars.import_bytes(path.read_bytes(),path.name)
        entry['glb']=m['glb_url'];paths[entry['glb']]=chars.asset_folder(m['id'])/'character.glb'
    gp=read(recipe.parent/'geometry-policy.json');gp.pop('schema');gp.pop('contacts_sha256')
    draft=dict(schema='strep-studio-native-scene-v1',scene=source,geometry=gp,object_edit=None)
    config=read(recipe);sp=read(recipe.parent/'surface-policy.json');sp.pop('schema');sp.pop('contacts_sha256')
    payload=dict(schema=studio.SCHEMA,draft=draft,transfers=dict(A=dict(job='native1',
        result_sha256=sha256(upstream/'result.json'),vertex_map=read(recipe.parent/'bridge.json')['transfers']['A']['vertex_map'])),
        calibration=dict(actors=config['actors'],surface=sp,search=config['search']))
    return payload,lambda url:paths.get(url)


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    patch=pytest.MonkeyPatch();root=tmp_path_factory.mktemp('stj');payload,resolver=setup(root,patch)
    folder=studio.folder_for('scene1');before=copy.deepcopy(payload);studio.prepare(payload,folder,resolver)
    result=studio.run(folder)
    assert payload==before
    yield root,payload,resolver,folder,result
    patch.undo()


def test_completed_job_keeps_originals_and_explicit_incoming_correspondence(study):
    root,payload,resolver,folder,result=study
    cat=studio.catalog(dict(draft=payload['draft'],transfers=dict(A={k:v for k,v in payload['transfers']['A'].items() if k!='vertex_map'})),resolver)
    refs=cat['actors']['A']['required_vertices']
    incoming=payload['draft']['scene']['contacts'][-1]['target']['vertices']
    assert all(r in refs for r in incoming) and len(refs)==12
    assert result['staging_conditions_pass'] is True and all(result['checks'].values())
    assert all(result[k] is False for k in studio.FALSE_FLAGS)
    assert read(folder/'source-scene.json')==payload['draft'] and studio.verify(folder)==result
    p=read(folder/'prepared.json');assert all(sha256(s['path'])==s['sha256'] for s in p['sources'].values())
    m=studio.manifest('scene1');draft=m['stage_draft'];actors=draft['scene']['actors']
    assert actors['A']['animation_index']==1 and actors['B']['animation_index']==0
    assert actors['B']['sha256']==payload['draft']['scene']['actors']['B']['sha256']
    assert actors['B']['glb']==payload['draft']['scene']['actors']['B']['glb']
    assert draft['geometry']==payload['draft']['geometry'] and draft['scene']['objects']==payload['draft']['scene']['objects']
    for old,new in zip(payload['draft']['scene']['contacts'],draft['scene']['contacts']):
        assert all(old[k]==new[k] for k in ('id','mode','interval_s','limits','reduction','actor'))
    def candidate_resolver(url):
        prefix='/files/'+studio.NAMESPACE+'/scene1/'
        return folder/url[len(prefix):] if url.startswith(prefix) else resolver(url)
    scenes.validate_request(draft,candidate_resolver,require_objects=False)
    with zipfile.ZipFile(folder/'candidate.zip') as z:
        assert 'actors/actor-0.glb' in z.namelist() and 'actors/actor-1.glb' in z.namelist()
        assert all(not n.startswith(('input/','implementation/','fit/')) for n in z.namelist())
    assert studio.served_file(studio.NAMESPACE+'/scene1/input/actor-0.glb') is None
    assert studio.served_file(studio.NAMESPACE+'/scene1/actors/actor-0.glb')==folder/'actors/actor-0.glb'
    assert studio.served_file(studio.NAMESPACE+'/scene1/../../prepared.json') is None


@pytest.mark.parametrize('fault',['result','job','source-clip','missing-incoming','duplicate-target','extra-source','invalid-target',
    'role','root-boolean','search-boolean','normal-missing','normal-nonunit','partner-normal','object-edit','schema'])
def test_invalid_requests_reject_before_new_folder(study,fault):
    _,payload,resolver,_,_=study;p=copy.deepcopy(payload);a=p['calibration']['actors']['A']
    if fault=='result':p['transfers']['A']['result_sha256']='f'*64
    elif fault=='job':p['transfers']['A']['job']='../native1'
    elif fault=='source-clip':p['draft']['scene']['actors']['A']['animation_index']=1
    elif fault=='missing-incoming':p['transfers']['A']['vertex_map'].pop()
    elif fault=='duplicate-target':p['transfers']['A']['vertex_map'][1]['target']=p['transfers']['A']['vertex_map'][0]['target']
    elif fault=='extra-source':p['transfers']['A']['vertex_map'].append(dict(source=[100,0,0],target=[100,0,0]))
    elif fault=='invalid-target':p['transfers']['A']['vertex_map'][0]['target']=[100,0,0]
    elif fault=='role':a['role_rotations_degrees']={'InventedPalm':10}
    elif fault=='root-boolean':a['maximum_root_offset_m']=True
    elif fault=='search-boolean':p['calibration']['search']['evaluations']=True
    elif fault=='normal-missing':p['calibration']['surface']['contacts'].pop('partner-initiated')
    elif fault=='normal-nonunit':p['calibration']['surface']['contacts']['box-grip']['target_normal']['normals']=[[0,0,2]]
    elif fault=='partner-normal':p['calibration']['surface']['contacts']['partner']['target_normal']={'space':'world','normals':[[0,0,1]]}
    elif fault=='object-edit':p['draft']['object_edit']={}
    elif fault=='schema':p['schema']='wrong'
    folder=studio.folder_for('reject-'+fault)
    with pytest.raises((ValueError,KeyError,IndexError)):studio.prepare(p,folder,resolver)
    assert not folder.exists()


@pytest.mark.parametrize('fault',['summary-approval','summary-pass','stage-placement','stage-old-clip','zip-extra','source-intent','permissions'])
def test_rehashed_published_tampering_still_rejects(study,fault):
    _,_,_,folder,_=study;paths=[folder/'result.json',folder/'completion.json'];mutated={}
    def change(name,edit):
        path=folder/name;mutated[path]=path.read_bytes();value=read(path);edit(value);save(path,value)
    backups={p:p.read_bytes() for p in paths}
    try:
        if fault=='summary-approval':change('result.json',lambda r:r.update(quality_approved=1))
        elif fault=='summary-pass':change('result.json',lambda r:r.update(staging_conditions_pass=1))
        elif fault=='stage-placement':change('stage-draft.json',lambda d:d['scene']['actors']['A']['placement'].update(translation_m=[99,0,0]))
        elif fault=='stage-old-clip':change('stage-draft.json',lambda d:d['scene']['actors']['A'].update(animation_index=0))
        elif fault=='source-intent':change('source-scene.json',lambda d:d['scene']['contacts'][0]['limits'].update(position_m=1))
        elif fault=='permissions':change('calibration-request.json',lambda d:d['actors']['A'].update(maximum_joint_displacement_m=.22))
        elif fault=='zip-extra':
            path=folder/'candidate.zip';mutated[path]=path.read_bytes()
            with zipfile.ZipFile(path,'a') as z:z.writestr('unrequested.json','{}')
        r=read(folder/'result.json');r['files_sha256']={n:sha256(folder/n) for n in r['files_sha256']};save(folder/'result.json',r)
        save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        with pytest.raises(ValueError):studio.manifest('scene1')
    finally:
        for path,data in {**backups,**mutated}.items():path.write_bytes(data)


@pytest.mark.parametrize('fault,code',[('valid',202),('host',403),('origin',403),('type',415),('size',400),('busy',409),('worker',409)])
def test_offline_http_worker_and_loopback_gates(study,monkeypatch,fault,code):
    _,payload,resolver,_,_=study;monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    calls=[];monkeypatch.setattr(server.subprocess,'Popen',lambda argv,**kw:(calls.append((argv,kw)) or SimpleNamespace(poll=lambda:None)))
    h=handler(payload,'/api/native-scene-transfer-assets')
    if fault=='host':h.headers['Host']='remote.test'
    if fault=='origin':h.headers['Origin']='https://remote.test'
    if fault=='type':h.headers['Content-Type']='text/plain'
    if fault=='size':h.headers['Content-Length']='1048577'
    if fault=='worker':h.server.worker=SimpleNamespace(poll=lambda:None)
    h.do_POST();assert h.responses[-1][0]==code and len(calls)==(fault=='valid')
    if calls:
        argv,kw=calls[0];assert Path(argv[1]).name=='studio_native_scene_transfer.py'
        assert kw['env']['HF_HUB_OFFLINE']=='1' and kw['env']['TRANSFORMERS_OFFLINE']=='1'


def test_worker_failure_retains_original_and_partial_output(study,monkeypatch):
    _,payload,resolver,_,_=study;folder=studio.folder_for('worker-failure');studio.prepare(payload,folder,resolver)
    def fail(recipe,output):output.mkdir();save(output/'partial.json',dict(retained=True));raise ValueError('explicit fixture failure')
    monkeypatch.setattr(studio.bridge,'run',fail)
    with pytest.raises(ValueError,match='fixture failure'):studio.run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and read(folder/'comparison/partial.json')['retained']
    assert studio.manifest(folder.name)['downloads']==[] and read(folder/'request.json')==payload


def test_negative_geometry_cannot_stage_but_preserves_candidate(study):
    _,payload,resolver,_,_=study;p=copy.deepcopy(payload);p['draft']['geometry']['planes']['floor']['offset_m']=.5
    folder=studio.folder_for('negative-geometry');studio.prepare(p,folder,resolver);result=studio.run(folder)
    assert result['checks']['candidate_contact_samples_pass'] is True and result['checks']['geometry_samples_pass'] is False
    assert result['staging_conditions_pass'] is False and studio.manifest(folder.name)['stage_draft'] is None
    assert (folder/'candidate.zip').exists() and result['quality_approved'] is False


def test_unchanged_verified_receipt_uses_only_exact_hash_cache_and_returns_copies(study,monkeypatch):
    _,_,_,folder,_=study;before=studio.manifest(folder.name)
    def reject_replay(*args,**kwargs):raise ValueError('full replay required')
    monkeypatch.setattr(studio,'verify',reject_replay)
    same=studio.manifest(folder.name);assert same==before
    same['checks'].clear();assert studio.manifest(folder.name)['checks']==before['checks']


@pytest.mark.parametrize('fault',['source','snapshot','archive','extra','upstream-result','upstream-state','saved-profile'])
def test_changed_dependencies_invalidate_verified_cache(study,monkeypatch,fault):
    _,_,_,folder,_=study;studio.manifest(folder.name);p=read(folder/'prepared.json');upstream=transfers.folder_for('native1')
    paths={'source':Path(p['sources']['B']['path']),'snapshot':folder/'input/actor-1.glb',
        'archive':folder/'implementation/studio_native_scene_transfer.py','extra':folder/'unrequested.json',
        'upstream-result':upstream/'result.json','upstream-state':upstream/'pipeline.json',
        'saved-profile':chars.profile_path(read(upstream/'request.json')['target_asset_id'],read(upstream/'request.json')['target_profile_id'])}
    path=paths[fault];original=path.read_bytes() if path.exists() else None
    def reject_replay(*args,**kwargs):raise ValueError('full replay required')
    monkeypatch.setattr(studio,'verify',reject_replay)
    try:
        path.write_bytes((original or b'')+b'changed')
        with pytest.raises((ValueError,json.JSONDecodeError)):studio.manifest(folder.name)
    finally:
        if original is None:path.unlink()
        else:path.write_bytes(original)


def test_reach_conflict_keeps_comparison_without_exporting_candidate(study):
    _,payload,resolver,_,_=study;p=copy.deepcopy(payload)
    p['draft']['scene']['contacts'][0]['target']['points_m'][0][1]+=1
    folder=studio.folder_for('reach-conflict');studio.prepare(p,folder,resolver);r=studio.run(folder)
    assert r['calibration_status']=='incompatible_with_joint_bound' and r['staging_conditions_pass'] is False
    assert not (folder/'candidate.zip').exists() and not (folder/'actors').exists()
    m=studio.manifest(folder.name);assert m['stage_draft'] is None
    assert all(not d['label'].endswith('.glb') for d in m['downloads'])


def test_two_selected_transfers_bind_both_incoming_vertex_populations(study):
    root,payload,resolver,_,_=study;p=copy.deepcopy(payload);base=read(transfers.folder_for('native1')/'request.json')
    asset=p['draft']['scene']['actors']['B']['sha256'];profile=read(root/'fixture/partner-profile.json')
    saved=chars.save_profile(dict(asset_id=asset,profile=profile));request={**base,'source_asset_id':asset,'source_profile_id':saved['profile_id']}
    second=transfers.folder_for('native2');transfers.prepare(request,second);transfers.run(second)
    from test_native_transfer_surface_calibration import face_patch
    from rig_asset import RigAsset
    source_refs=p['draft']['scene']['contacts'][2]['target']['vertices']
    target_refs=face_patch(RigAsset.load(second/'input/target.glb'),'RightHand',2,1)
    p['transfers']['B']=dict(job='native2',result_sha256=sha256(second/'result.json'),vertex_map=[dict(source=s,target=t) for s,t in zip(source_refs,target_refs)])
    p['calibration']['actors']['B']=dict(role_rotations_degrees=dict(RightHand=15),maximum_root_offset_m=0.,maximum_joint_displacement_m=.02)
    validated=studio.validate_request(p,resolver)
    assert set(validated[-1])=={'A','B'}


@pytest.mark.parametrize('query',['','?id=','?id=a&id=b','?id=a&extra=b'])
def test_offline_review_rejects_ambiguous_selection(study,query):
    h=handler({},'/api/native-scene-transfer-review'+query);h.do_GET();assert h.responses[-1][0]==400


def test_catalog_is_read_only_even_while_global_worker_is_busy(study,monkeypatch):
    _,payload,resolver,_,_=study
    p=dict(draft=payload['draft'],transfers={n:{k:v for k,v in row.items() if k!='vertex_map'} for n,row in payload['transfers'].items()})
    monkeypatch.setattr(server,'allowed_file',resolver);monkeypatch.setattr(server,'worker_busy',lambda:True)
    h=handler(p,'/api/native-scene-transfer-catalog');h.do_POST();assert h.responses[-1][0]==200
    assert h.responses[-1][1]['actors']['A']['source_sha256']==payload['draft']['scene']['actors']['A']['sha256']
