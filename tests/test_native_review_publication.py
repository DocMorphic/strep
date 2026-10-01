"""Synthetic byte packages test serving boundaries; no motion/quality evidence."""
import copy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_review_publication as publication
import publish_native_contact_review as publisher
from strep import read, save, sha256


@pytest.fixture
def package(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, 'ROOT', tmp_path)
    folder = tmp_path/'reports'/publication.NAMESPACE/'synthetic'
    folder.mkdir(parents=True)
    for name in publication.SUPPORT-{'viewer-manifest.json'}:
        (folder/name).write_text('Synthetic bytes, no actual animation.', encoding='utf8')
    versions = []
    for index in range(2):
        actors = []
        for actor in range(2):
            url = f'assets/{index}-{actor}.glb'; path = folder/url
            path.parent.mkdir(exist_ok=True); path.write_bytes(f'{index}/{actor}'.encode())
            actors.append(dict(url=url, sha256=sha256(path), placement=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])))
        for kind in ('result', 'decoded'):
            path = folder/f'audits/{index}-{kind}.json'; save(path, dict(synthetic=True,index=index))
        audit = f'audits/{index}-result.json'
        versions.append(dict(id=str(index), label='Synthetic', quality_approved=False,
                             actors=actors,duration_s=3.6666667461395264,event_time_s=2.0917225950783,
                             audit=audit,source_result_sha256=sha256(folder/audit)))
    save(folder/'viewer-manifest.json', dict(versions=versions))
    build = dict(schema_version=1,kind='native_contact_review',status='complete',quality_approved=False,
                 human_review_submitted=False,studio_selection_changed=False,browser_render_verified=False,
                 outputs={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()})
    save(folder/'build.json', build)
    return folder


def rebind(folder):
    build=read(folder/'build.json')
    build['outputs']={name:sha256(folder/name) for name in build['outputs']}
    save(folder/'build.json',build)


def test_discovery_serves_only_bound_publication(package):
    manifest,build=publication.validate(package)
    assert manifest['versions'][0]['event_time_s']==2.0917225950783
    result=publication.listing()
    assert not result['rejected'] and len(result['reviews'])==1
    assert result['reviews'][0]['quality_approved'] is False
    for name in (*build['outputs'],'build.json'):
        assert publication.served_file(f'{publication.NAMESPACE}/synthetic/{name}')==package/name
    (package/'secret.html').write_text('Unbound')
    assert publication.served_file(f'{publication.NAMESPACE}/synthetic/secret.html') is None


@pytest.mark.parametrize('relative',['../outside','/outside','assets/../../outside','assets\\0-0.glb','./viewer.html','assets//0-0.glb'])
def test_noncanonical_paths_rejected(package,relative):
    with pytest.raises(ValueError):publication.bound_path(package,relative)


def test_changed_actor_invalidates_entire_package(package):
    (package/'assets/0-0.glb').write_bytes(b'Changed')
    assert publication.listing()['reviews']==[]
    assert publication.listing()['rejected'][0]['id']=='synthetic'
    assert publication.served_file(f'{publication.NAMESPACE}/synthetic/viewer.html') is None


@pytest.mark.parametrize('flag',['quality_approved','studio_selection_changed','human_review_submitted','browser_render_verified'])
def test_no_scope_promotion_by_completion_marker(package,flag):
    build=read(package/'build.json');build[flag]=True;save(package/'build.json',build)
    with pytest.raises(ValueError):publication.validate(package)


@pytest.mark.parametrize('fault',['actor_hash','actor_url','placement','rotation','audit','duration','event','version_id','approved','extra_output','missing_decoded'])
def test_manifest_contracts_are_checked_after_rehash(package,fault):
    manifest=read(package/'viewer-manifest.json');version=manifest['versions'][0]
    if fault=='actor_hash':version['actors'][0]['sha256']='a'*64
    elif fault=='actor_url':version['actors'][0]['url']='../assets/0-0.glb'
    elif fault=='placement':version['actors'][0]['placement']['translation_m']=[True,0,0]
    elif fault=='rotation':version['actors'][0]['placement']['rotation_xyzw']=[0,0,0,0]
    elif fault=='audit':version['source_result_sha256']='a'*64
    elif fault=='duration':version['duration_s']=False
    elif fault=='event':version['event_time_s']=4
    elif fault=='version_id':version['id']='1'
    elif fault=='approved':version['quality_approved']=True
    save(package/'viewer-manifest.json',manifest);rebind(package)
    if fault in ('extra_output','missing_decoded'):
        build=read(package/'build.json')
        if fault=='extra_output':
            (package/'extra.html').write_text('Synthetic');build['outputs']['extra.html']=sha256(package/'extra.html')
        else:del build['outputs']['audits/0-decoded.json']
        save(package/'build.json',build)
    with pytest.raises(ValueError):publication.validate(package)


def test_publisher_preserves_source_and_native_clock(package,monkeypatch):
    root=publication.ROOT;source=root/'reports/source';source.mkdir()
    build=read(package/'build.json')
    import shutil
    for name in build['outputs']:
        target=source/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(package/name,target)
    # Only viewer/feedback are refreshed from source-controlled code.
    scripts=root/'scripts';scripts.mkdir()
    for name in ('native-contact-review.html','native-contact-feedback.mjs','native_review_publication.py'):
        (scripts/name).write_text('../../assets/viewer/node_modules/three/build/three.module.js',encoding='utf8')
    build['inputs']={};save(source/'build.json',build)
    monkeypatch.setattr(publisher,'ROOT',root)
    original=sha256(source/'viewer-manifest.json')
    target=publisher.run(source,'published')
    assert sha256(source/'viewer-manifest.json')==original==sha256(target/'viewer-manifest.json')
    assert '/assets/build/three.module.js' in (target/'viewer.html').read_text()
    assert publication.validate(target)[0]['versions'][0]['event_time_s']==2.0917225950783
    built=read(target/'build.json')
    assert len(built['implementation'])==4
    assert all(str(root/'scripts') not in p for p in built['inputs'])
    assert publication.served_file(f'{publication.NAMESPACE}/published/implementation/native_review_publication.py') is None
    with pytest.raises(ValueError):publisher.run(source,'published')
    for name in ('../escape','bad/name',''):
        with pytest.raises(ValueError):publisher.run(source,name)


def test_server_api_and_module_mime(package,monkeypatch):
    import action_studio_server as studio
    monkeypatch.setattr(studio,'ROOT',publication.ROOT)
    server=ThreadingHTTPServer(('127.0.0.1',0),studio.Handler)
    port=server.server_port;server.allowed_hosts={f'127.0.0.1:{port}'}
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get(path,host=None):
        conn=HTTPConnection('127.0.0.1',port)
        conn.request('GET',path,headers={'Host':host or f'127.0.0.1:{port}'})
        response=conn.getresponse();data=response.read();result=(response.status,response.getheader('Content-Type'),data);conn.close();return result
    try:
        import json
        status,_,body=get('/api/native-contact-reviews')
        assert status==200 and len(json.loads(body)['reviews'])==1
        status,mime,_=get(f'/files/{publication.NAMESPACE}/synthetic/native-contact-clock.mjs')
        assert status==200 and mime=='text/javascript'
        assert get('/api/native-contact-reviews','foreign.example')[0]==403
        assert get(f'/files/{publication.NAMESPACE}/synthetic/%2e%2e/secret.html')[0]==404
        (package/'assets/1-1.glb').write_bytes(b'Changed')
        assert get(f'/files/{publication.NAMESPACE}/synthetic/viewer.html')[0]==404
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
