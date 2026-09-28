import copy
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from scene_release_job import metadata,validate,prepare,run
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler

URL='/files/object-release-v2/seed-11-original/palm.json'


def payload():
    return dict(source_url=URL,revision=metadata(URL)['revision'],object='box',release_frame=121,
        mass_kg=3.,friction=.4,restitution=.1,label='Authored release test')


def test_versioned_sphere_release_fails_explicitly_before_simulation(work):
    source=read(ROOT/'reports/object-release-v2/seed-11-original/palm.json')
    folder=work/'sphere-collection';folder.mkdir()
    actor=source['scene']['actors']['A']
    shutil.copyfile(ROOT/'reports/object-release-v2'/actor['preview_glb'],folder/'actor.glb')
    actor['preview_glb']='actor.glb'
    obj=source['scene']['objects']['box'];obj.pop('shape');obj.pop('size_m')
    obj['geometry']=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.25)
    save(folder/'palm.json',source);save(folder/'manifest.json',dict(scenes=[dict(variants=dict(palm='palm.json'))]))
    url='/files/'+folder.relative_to(ROOT/'reports').as_posix()+'/palm.json'
    with pytest.raises(ValueError,match='versioned primitive release is not implemented'):metadata(url)


@pytest.fixture
def work():
    base=ROOT/'reports/scene-release-jobs';base.mkdir(exist_ok=True)
    path=Path(tempfile.mkdtemp(prefix='test-',dir=base)).resolve()
    yield path
    assert path.is_relative_to(base.resolve()) and path.name.startswith('test-')
    shutil.rmtree(path)


@pytest.mark.parametrize('key,value',[('revision','stale'),('source_url','/files/../../README.md'),
    ('release_frame',120),('release_frame',True),('object','missing'),('mass_kg',float('nan')),
    ('mass_kg',True),('friction',-1),('restitution',2)])
def test_invalid_requests_rejected_before_preparation(key,value,work):
    p=payload();p[key]=value
    with pytest.raises((ValueError,KeyError)):prepare(p,work/'job')
    assert not (work/'job').exists()


def test_changed_snapshot_is_rejected(work):
    folder=work/'job';prepare(payload(),folder)
    (folder/'source/events.json').write_text('{}')
    with pytest.raises(ValueError,match='input changed'):run(folder)
    assert read(folder/'pipeline.json')['status']=='failed' and not (folder/'simulation').exists()


@pytest.mark.parametrize('filename',['events.json','LICENSE.txt'])
def test_dependency_change_during_snapshot_is_rejected(work,monkeypatch,filename):
    import scene_release_job as job
    copyfile=job.shutil.copyfile
    def changed(source,target,*args,**kwargs):
        result=copyfile(source,target,*args,**kwargs)
        if Path(target).name==filename:Path(target).write_text('changed during copy',encoding='utf8')
        return result
    monkeypatch.setattr(job.shutil,'copyfile',changed)
    with pytest.raises(ValueError,match='changed during snapshot'):prepare(payload(),work/'job')
    assert not (work/'job/request.json').exists()


@pytest.mark.parametrize('mode',['static_scene','moving_scene'])
def test_real_worker_generic_objects_multiple_actors_portable_tracks_and_events(work,mode):
    source=read(ROOT/'reports/object-release-v2/seed-11-original/palm.json')
    folder=work/'collection';folder.mkdir();(folder/'actors').mkdir()
    glb=ROOT/'reports/object-release-v2'/source['scene']['actors']['A']['preview_glb']
    shutil.copyfile(glb,folder/'actors/actor.glb');source['scene']['actors']['A']['preview_glb']='actors/actor.glb'
    source['scene']['actors']['B']=copy.deepcopy(source['scene']['actors']['A'])
    source['scene']['actors']['B']['transform']['translation_m']=[3.,0.,0.]
    source['scene']['objects']['crate']=source['scene']['objects'].pop('box')
    for c in source['scene']['contacts']:c['target']['object']='crate'
    source['scene']['objects']['shelf']=dict(shape='box',size_m=[.3,.4,.5],keyframes=[dict(frame=0,translation_m=[5,1,0],rotation_xyzw=[0,0,0,1])])
    if mode=='moving_scene':
        source['scene']['objects']['shelf']['keyframes'].append(dict(frame=179,translation_m=[5.1,1.1,.1],rotation_xyzw=[0,0,0,1]))
    save(folder/'palm.json',source);save(folder/'manifest.json',dict(scenes=[dict(variants=dict(palm='palm.json'))]))
    url='/files/'+folder.relative_to(ROOT/'reports').as_posix()+'/palm.json'
    p=payload();p.update(source_url=url,revision=metadata(url)['revision'],object='crate',collision_mode=mode)
    job=work/'job';prepare(p,job);before=read(job/'source/bundle.json');run(job)
    assert read(job/'pipeline.json')['status']=='complete'
    after=read(job/'candidate.json');assert after['scene']['actors']==before['scene']['actors']
    audit=read(job/'release-audit.json');assert audit['collision_mode']==mode
    assert [c['id'] for c in audit['scene_collisions']['colliders']]==['object:shelf']
    assert after['scene']['objects']['shelf']==before['scene']['objects']['shelf']
    original=read(job/'source/object-track.json');candidate=read(job/'object-track.json')
    assert candidate['positions_m'][:122]==original['positions_m'][:122]
    assert candidate['positions_m'][-1]!=original['positions_m'][-1]
    assert after['scene']['contacts']==before['scene']['contacts']
    assert read(job/'events.json')['events'][:-1]==read(job/'source/events.json')['events']
    assert read(job/'events.json')['events'][-1]['type']=='dynamic_release_start'
    portable=read(job/'portable-scene.json')
    runtime=read(job/'scene-runtime.json')
    assert set(runtime['actors'])=={'A','B'} and set(runtime['objects'])=={'crate','shelf'}
    assert all(o['ownership']=='baked_track' for o in runtime['objects'].values())
    assert runtime['object_clip']['sha256']==sha256(job/'objects.glb')
    for actor in portable['actors'].values():assert (job/actor['motion']).is_file() and (job/actor['preview_glb']).is_file()
    doc,binary=read_glb(job/'objects.glb');sampler=AnimationSampler(doc,binary,0)
    assert {n['extras']['strep_object_id'] for n in doc['nodes']}=={'crate','shelf'}
    crate=next(i for i,n in enumerate(doc['nodes']) if n['extras']['strep_object_id']=='crate')
    for frame in [0,121,130,179]:
        np.testing.assert_allclose(sampler.sample(float(np.float32(frame/30)))[crate,:3,3],candidate['positions_m'][frame],atol=1e-6,rtol=0)
    with zipfile.ZipFile(job/'scene-animation.zip') as archive:
        assert archive.testzip() is None
        for name in ('scene-runtime.json','godot_scene_clock.gd','GODOT-SCENES.md'):
            assert archive.read(name)==(job/name).read_bytes()
        for name in archive.namelist():
            if name!='README.txt':assert hashlib.sha256(archive.read(name)).hexdigest()==sha256(job/name)


def test_real_http_metadata_origin_stale_busy_and_supervised_dispatch(work,monkeypatch):
    import threading,urllib.request,urllib.error,json,os
    from http.server import ThreadingHTTPServer
    import action_studio_server as api
    import scene_release_job as job
    class Child:
        pid=os.getpid()
        def poll(self):return None
    monkeypatch.setattr(job,'JOBS',work/'dispatched')
    monkeypatch.setattr(api.subprocess,'Popen',lambda *a,**k:Child())
    server=ThreadingHTTPServer(('127.0.0.1',0),api.Handler);port=server.server_port
    server.allowed_hosts={f'127.0.0.1:{port}'};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{port}'
    def post(body,origin=base):
        request=urllib.request.Request(base+'/api/scene-releases',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin})
        try:
            with urllib.request.urlopen(request) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as response:return response.code,json.load(response)
    try:
        p=payload()
        assert post(p,'https://example.com')[0]==403
        stale=dict(p,revision='stale');assert post(stale)[0]==400
        monkeypatch.setattr(api,'worker_busy',lambda:True);assert post(p)[0]==409
        assert not (work/'dispatched').exists()
        monkeypatch.setattr(api,'worker_busy',lambda:False);status,response=post(p)
        assert status==202
        folder=work/'dispatched'/response['id'];assert read(folder/'pipeline.json')['status']=='starting'
        assert read(folder/'request.json')['authored']==p
        with urllib.request.urlopen(base+'/api/scene-release-source?path='+urllib.parse.quote(URL,safe='')) as response:
            assert json.load(response)['earliest_release']['box']==121
    finally:server.shutdown();server.server_close();thread.join()
