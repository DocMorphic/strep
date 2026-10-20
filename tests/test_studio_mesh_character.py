"""Real saved-scene corrections, receipt validation and local route boundaries."""
import copy
import json
import threading
import numpy as np
import pytest
from test_studio_mesh_scene import authored
from test_studio_prop_routes import handler
from strep import read, save, sha256
from native_scene_contacts import SceneContacts
from static_prop_asset import StaticPropAsset
import studio_props as props
import studio_mesh_scene_job as scenes
import studio_mesh_scene_preview as source_preview
import studio_mesh_character_job as jobs
import studio_mesh_character_preview as preview
import action_studio_server as server


@pytest.fixture
def saved(authored, monkeypatch):
    root, mesh, source, resolver = authored
    for module in (source_preview, jobs, preview): monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(source_preview, 'SAMPLING_METHODS', ('method.py',))
    monkeypatch.setattr(preview, 'SAMPLING_METHODS', ('method.py',))
    # A generated closed rig and a real imported mesh grip, just outside its
    # surface. The worker still uses the full declared source/frame clock.
    spec=copy.deepcopy(mesh['draft']['scene']);spec['actors']['A']['glb']=str(source)
    scene=SceneContacts(spec,root);point=scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
    asset_id=mesh['props']['box']['asset_id'];asset=StaticPropAsset.load(props.bounded_path(asset_id,'prop.glb'))
    face=next(i for i in range(len(asset.faces)) if asset.surface_point(i,[.2,.3,.5])['winding_normal'][0]>.99)
    grip=props.save_grip(dict(asset_id=asset_id,geometry_sha256=asset.geometry_sha256,face=face,barycentric=[.2,.3,.5],label='Reach'))
    mesh['props']['box']['keyframes'][0]['translation_m']=(point+[-.003,0,0]-np.array(grip['selection']['position_m'])).tolist()
    mesh['contacts'][0].update(vertices=[[6,0,2]],grip_id=grip['grip_id'],limits=dict(position_m=.002))
    mesh['draft']['geometry']['planes']={'floor':dict(normal_world=[0.,1.,0.],offset_m=0.)}
    folder=scenes.prepare(mesh);scenes.execute(folder,resolver);save(folder/'guard/pipeline.json',dict(status='complete'))
    actor=dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)
    correction=dict(schema='strep-studio-native-scene-fit-v1',draft=copy.deepcopy(mesh['draft']),actors={'A':actor},options={'iterations':16},resume_from=None)
    request=dict(schema='strep-studio-mesh-character-v1',scene_job=folder.name,scene_result_sha256=sha256(folder/'package/result.json'),mesh_request=copy.deepcopy(mesh),correction=correction,editable_clip_boundaries={'A':['start','end']},acknowledge_changed_boundary_compatibility=True)
    return folder,request


def complete(request):
    folder=jobs.prepare(request);result=jobs.execute(folder);save(folder/'guard/pipeline.json',dict(status='complete'))
    return folder,result


def test_real_saved_scene_correction_and_portable_comparison(saved):
    source,request=saved;before={p:sha256(p) for p in source.rglob('*') if p.is_file()}
    folder,result=complete(request)
    assert result['candidate'] and result['sampled_candidate_pass'],result
    response=jobs.review(folder.name);data=preview.descriptor(folder.name,response['result_sha256'])
    assert data['original_selected'] and data['candidate']['motion_fitted'] and not data['original']['motion_fitted']
    assert data['original']['contacts'][0]['maximum_position_error_m'] > .002
    assert data['candidate']['contacts'][0]['maximum_position_error_m'] <= .002
    from native_mesh_prop_scene import MeshPropScene
    for role in ('original','candidate'):
        package=folder/'preview'/role
        actual,observations=MeshPropScene(package/'mesh-scene.json').contact_audit()
        assert actual==read(package/'contact-report.json')
        with np.load(package/'contact-observations.npz') as stored:
            for name,array in observations.items():np.testing.assert_array_equal(stored[name],array)
        for group in ('actors','props'):
            for asset in data[role][group].values():assert sha256(server.allowed_file(asset['url']))==asset['sha256']
    q=handler(f'/api/mesh-character-jobs/{folder.name}/preview/{response["result_sha256"]}');q.do_GET();assert q.responses==[(200,data)]
    assert jobs.served_file(response['download_url']).is_file()
    assert all(sha256(p)==digest for p,digest in before.items())
    # The original saved scene and preview remain usable after correction.
    assert source_preview.descriptor(source.name,request['scene_result_sha256'])['motion_fitted'] is False


def test_already_passing_scene_does_not_invent_a_candidate(saved):
    source,request=saved
    # Use a deliberately broad authored limit in a fresh measurement, never
    # mutate a completed package. Both correction and original bind that intent.
    import studio_mesh_scene
    package=source/'package';mesh=request['mesh_request'];mesh['contacts'][0]['limits']['position_m']=.1
    actor_path=package/'actors/A.glb'
    fresh=scenes.prepare(mesh);scenes.execute(fresh,lambda _:actor_path);save(fresh/'guard/pipeline.json',dict(status='complete'))
    request.update(scene_job=fresh.name,scene_result_sha256=sha256(fresh/'package/result.json'))
    folder,result=complete(request);assert result['candidate'] is None and not result['sampled_candidate_pass']
    data=preview.descriptor(folder.name,sha256(folder/'result.json'));assert data['candidate'] is None and data['original']['all_declared_point_contacts_pass']


@pytest.mark.parametrize('fault',['resume','speed','clearance','extra','draft','ack','edges','iterations','null-draft'])
def test_unsupported_settings_never_silently_disappear(saved,fault):
    _,request=saved
    if fault=='resume':request['correction']['resume_from']='old'
    elif fault=='speed':request['correction']['rotation_speed_limits']=[]
    elif fault=='clearance':request['correction']['schema']='strep-studio-native-scene-fit-v3'
    elif fault=='extra':request['ignored']=True
    elif fault=='draft':request['correction']['draft']['scene']['duration_s']=3
    elif fault=='ack':request['acknowledge_changed_boundary_compatibility']=False
    elif fault=='edges':request['editable_clip_boundaries']['A']=['start','start']
    elif fault=='iterations':request['correction']['options']['iterations']=17
    else:request['correction']['draft']=None;request['mesh_request']['draft']=None
    with pytest.raises(ValueError):jobs.prepare(request)


@pytest.mark.parametrize('fault',['source','result','draft','method'])
def test_changed_saved_scene_or_implementation_rejected_before_fit(saved,fault):
    source,request=saved;folder=jobs.prepare(request)
    if fault=='source':(source/'package/actors/A.glb').write_bytes(b'changed')
    elif fault=='method':(jobs.ROOT/'scripts/method.py').write_text('# changed')
    else:
        if fault=='result':request['scene_result_sha256']='0'*64
        else:request['mesh_request']['contacts'][0]['limits']['position_m']=.1
        # Re-prepare explicitly different user intent to exercise saved-source comparison.
        folder=jobs.prepare(request)
    with pytest.raises(ValueError):jobs.execute(folder)
    assert not (folder/'fit').exists()


def test_routes_queue_without_loading_model_or_geometry(saved,monkeypatch):
    _,request=saved;launched=[]
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(jobs,'launch',lambda folder:launched.append(folder))
    h=handler('/api/mesh-character-jobs',json.dumps(request).encode());h.server.job_lock=threading.Lock();h.server.worker=None;h.do_POST()
    assert h.responses[0][0]==202 and len(launched)==1 and not (launched[0]/'source').exists()
    q=handler('/api/mesh-character-jobs/'+h.responses[0][1]['id']);q.do_GET();assert q.responses[0][1]['status']=='starting'
    q.headers['Host']='remote.test';q.do_GET();assert q.responses[-1][0]==403
    h.headers['Origin']='https://remote.test';h.do_POST();assert h.responses[-1][0]==403


def test_receipt_and_asset_tampering_fail_closed(saved):
    _,request=saved;request['correction']['options']['iterations']=1
    folder,result=complete(request);digest=sha256(folder/'result.json')
    for url in (f'/files/mesh-character-previews/{folder.name}/{digest}/original/actors/../result.json',f'/files/mesh-character-jobs/{folder.name}/request.json'):
        assert server.allowed_file(url) is None
    (folder/'preview/original/actors/A.glb').write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact changed'):preview.descriptor(folder.name,digest)


@pytest.mark.parametrize('fault',['host','type','duplicate','nonfinite','large','busy'])
def test_queue_rejects_untrusted_and_busy_transport(saved,monkeypatch,fault):
    _,request=saved;h=handler('/api/mesh-character-jobs',json.dumps(request).encode());h.server.job_lock=threading.Lock();h.server.worker=None
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(jobs,'prepare',lambda _:pytest.fail('Invalid transport reached preparation'))
    if fault=='host':h.headers['Host']='remote.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='large':h.headers['Content-Length']=str(1024**2+1)
    elif fault in ('duplicate','nonfinite'):
        import io
        raw=b'{"x":1,"x":2}' if fault=='duplicate' else b'{"x":NaN}'
        h.rfile=io.BytesIO(raw);h.headers['Content-Length']=str(len(raw))
    h.do_POST();assert h.responses[0][0] in (400,403,409,415)


def test_launch_failure_visible(saved,monkeypatch):
    _,request=saved;folder=jobs.prepare(request)
    def fail(*a,**k):raise OSError('Launch failed')
    monkeypatch.setattr(jobs.subprocess,'Popen',fail)
    with pytest.raises(OSError):jobs.launch(folder)
    assert jobs.review(folder.name)['status']=='failed'


def test_built_ui_connects_existing_bounds_and_scene():
    from build_desktop import render
    page=render()
    assert page.count('id="meshCharacterPanel"')==1
    assert 'getScene:()=>meshSceneEditor.selection(),getBounds:()=>nativeSceneFitEditor.request()' in page
    assert server.allowed_file('/mesh-character-viewer.mjs').is_file()
