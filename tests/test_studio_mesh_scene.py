"""Authoring through actual prop store, rig reader, mesh clock and package."""
import copy
import json
import threading
import zipfile
from pathlib import Path
import numpy as np
import pytest
from test_native_mesh_prop_scene import cube
from test_native_scene_geometry import closed_fixture
from test_studio_prop_routes import handler
from native_scene_contacts import SceneContacts
from native_mesh_prop_scene import MeshPropScene
from strep import save,read,sha256
import studio_props as props
import studio_native_scene as native
import studio_mesh_scene as assembler
import studio_mesh_scene_job as jobs
import action_studio_server as server


@pytest.fixture
def authored(tmp_path,monkeypatch):
    monkeypatch.setattr(native,'ROOT',tmp_path);monkeypatch.setattr(assembler,'ROOT',tmp_path);monkeypatch.setattr(jobs,'ROOT',tmp_path)
    (tmp_path/'scripts').mkdir();(tmp_path/'scripts/method.py').write_text('# Pinned test source\n')
    assets=tmp_path/'reports/fixtures';assets.mkdir(parents=True)
    source,_,spec=closed_fixture(assets);spec['contacts']=[]
    scene=SceneContacts(spec,assets);point=scene.actor_points('A',np.array([0]),np.array([1.]))[0,0]
    monkeypatch.setattr(props,'ASSETS',tmp_path/'reports/props')
    p=assets/'prop.glb';cube(p);asset=props.import_bytes(p.read_bytes(),'Box.glb','Generated fixture')
    grip=props.save_grip(dict(asset_id=asset['id'],geometry_sha256=asset['geometry_sha256'],face=0,barycentric=[.2,.3,.5],label='Hand'))
    url='/files/character-assets/fixture/actor.glb';spec['actors']['A']['glb']=url
    draft=dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=dict(clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={}),object_edit=None)
    request=dict(schema='strep-studio-mesh-scene-v1',draft=draft,props=dict(box=dict(asset_id=asset['id'],geometry_sha256=asset['geometry_sha256'],keyframes=[dict(time_s=0.,translation_m=(point-np.array(grip['selection']['position_m'])).tolist(),rotation_xyzw=[0,0,0,1])])),contacts=[dict(id='hand',actor='A',vertices=[[6,0,0]],reduction='centroid',prop='box',grip_id=grip['grip_id'],mode='touch',interval_s=[1.,1.],limits=dict(position_m=1e-6))])
    return tmp_path,request,source,lambda value:source if value==url else None


def test_scene_package_reopens_and_replays_exact_points(authored):
    root,request,source,resolver=authored;before=source.read_bytes();folder=jobs.prepare(request)
    result=jobs.execute(folder,resolver)
    assert result['all_declared_point_contacts_pass'] and not result['geometry_evaluated'] and not result['motion_fitted']
    assert source.read_bytes()==before and read(folder/'package/studio-draft.json')==request
    assert read(folder/'package/prop-metadata/box.json')['license_note']=='Generated fixture'
    assert read(folder/'package/implementation.json')['request_sha256']==sha256(folder/'request.json')
    assert read(folder/'package/implementation.json')['methods_sha256']==read(folder/'prepared.json')['methods_sha256']
    scene=MeshPropScene(folder/'package/mesh-scene.json');report,arrays=scene.contact_audit()
    assert report==read(folder/'package/contact-report.json')
    with np.load(folder/'package/contact-observations.npz') as saved:
        assert set(saved.files)==set(arrays)
        for key,value in arrays.items():np.testing.assert_array_equal(saved[key],value)
    with zipfile.ZipFile(folder/'scene-package.zip') as package:
        assert set(package.namelist())==set(result['files_sha256'])|{'result.json'}
        for name in package.namelist():assert package.read(name)==(folder/'package'/name).read_bytes()
    # The synthetic guard record only exercises serving; the separate real
    # guarded integration study proves worker admission and completion.
    save(folder/'guard/pipeline.json',dict(status='complete'))
    reviewed=jobs.review(folder.name);assert reviewed['all_declared_point_contacts_pass'] and reviewed['original_selected']
    for link in reviewed['downloads']:assert jobs.served_file(link['url']).is_file()
    assert jobs.served_file(f'/files/mesh-scene-jobs/{folder.name}/request.json') is None


def test_missed_hold_is_retained_as_failure(authored):
    root,request,_,resolver=authored;request['props']['box']['keyframes'][0]['translation_m']=[10.,10.,10.]
    request['contacts'][0].update(mode='hold',interval_s=[.3,1.7],limits=dict(position_m=.005,relative_speed_m_s=.02))
    folder=jobs.prepare(request);result=jobs.execute(folder,resolver);row=result['contacts'][0]
    assert not result['all_declared_point_contacts_pass'] and row['samples']>2 and row['relative_speed_populations']
    assert row['maximum_position_error_m']>1 and not result['quality_approved']
    npz=np.load(folder/'package/contact-observations.npz');clock=npz['mesh_contact_0_times_s'];assert clock[0]==.3 and clock[-1]==1.7


@pytest.mark.parametrize('change',['geometry','grip','actor','interval','duplicate','bounds','edit','extra'])
def test_invalid_bindings_and_intent_rejected(authored,change):
    root,r,_,resolver=authored
    if change=='geometry':r['props']['box']['geometry_sha256']='0'*64
    elif change=='grip':r['contacts'][0]['grip_id']='0'*64
    elif change=='actor':r['draft']['scene']['actors']['A']['sha256']='0'*64
    elif change=='interval':r['contacts'][0]['interval_s']=[1.,3.]
    elif change=='duplicate':r['contacts'].append(copy.deepcopy(r['contacts'][0]))
    elif change=='bounds':r['props']['box']['keyframes'][0]['rotation_xyzw']=[0,0,0,2]
    elif change=='edit':r['draft']['object_edit']={}
    else:r['ignored_constraint']=True
    with pytest.raises((ValueError,FileNotFoundError)):assembler.assemble(r,root/'reports/rejected/package',resolver)
    assert not (root/'reports/rejected/scene-package.zip').exists()


@pytest.mark.parametrize('change',['request','method','missing-method'])
def test_queued_job_rejects_changed_inputs(authored,change):
    root,request,_,resolver=authored;folder=jobs.prepare(request)
    if change=='request':save(folder/'request.json',{})
    elif change=='method':(root/'scripts/method.py').write_text('# Changed\n')
    else:
        value=read(folder/'prepared.json');value['methods_sha256']={};save(folder/'prepared.json',value)
    with pytest.raises(ValueError):jobs.execute(folder,resolver)
    assert not (folder/'package').exists()


def test_completed_package_tampering_rejected(authored):
    _,r,_,resolver=authored;folder=jobs.prepare(r);jobs.execute(folder,resolver);save(folder/'guard/pipeline.json',dict(status='complete'))
    save(folder/'package/contact-report.json',dict(passed=True))
    with pytest.raises(ValueError,match='package changed'):jobs.review(folder.name)


def test_api_queues_without_running_scene_math(authored,monkeypatch):
    _,r,_,_=authored;launched=[]
    monkeypatch.setattr(server,'worker_busy',lambda:False);monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(jobs,'launch',lambda folder:launched.append(folder))
    h=handler('/api/mesh-scene-jobs',json.dumps(r).encode());h.server.job_lock=threading.Lock();h.server.worker=None;h.do_POST()
    assert h.responses[0][0]==202 and len(launched)==1 and not (launched[0]/'package').exists()
    q=handler('/api/mesh-scene-jobs/'+h.responses[0][1]['id']);q.do_GET();assert q.responses[0][1]['status']=='starting'


@pytest.mark.parametrize('fault',['host','origin','type','duplicate','nonfinite','large','busy'])
def test_route_rejects_untrusted_or_busy_requests(authored,monkeypatch,fault):
    _,r,_,_=authored;h=handler('/api/mesh-scene-jobs',json.dumps(r).encode());h.server.job_lock=threading.Lock();h.server.worker=None
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy');monkeypatch.setattr(server,'external_pair_fit_busy',lambda:False)
    monkeypatch.setattr(jobs,'prepare',lambda _:pytest.fail('Invalid request reached preparation'))
    if fault=='host':h.headers['Host']='external.test'
    elif fault=='origin':h.headers['Origin']='https://external.test'
    elif fault=='type':h.headers['Content-Type']='text/plain'
    elif fault=='large':h.headers['Content-Length']=str(1024**2+1)
    elif fault in ('duplicate','nonfinite'):
        import io
        raw=b'{"x":1,"x":2}' if fault=='duplicate' else b'{"x":NaN}'
        h.rfile=io.BytesIO(raw);h.headers['Content-Length']=str(len(raw))
    h.do_POST();assert h.responses[0][0] in (400,403,409,415)


def test_launch_failure_is_visible(authored,monkeypatch):
    _,r,_,_=authored;folder=jobs.prepare(r)
    def fail(*a,**k):raise OSError('Launch failed')
    monkeypatch.setattr(jobs.subprocess,'Popen',fail)
    with pytest.raises(OSError):jobs.launch(folder)
    assert jobs.review(folder.name)['status']=='failed'


def test_studio_build_exposes_connected_editor():
    from build_desktop import render,ROOT
    page=render()
    assert page.count('id="meshScenePanel"')==1
    assert page.count("await import('/mesh-scene-editor.mjs')")==1
    assert 'getDraft:()=>nativeSceneEditor.snapshot(),getPatch:()=>contactEditor.nativePatch(),getGrip:' in page
    assert server.allowed_file('/mesh-scene-editor.mjs')==ROOT/'scripts/mesh-scene-editor.mjs'
