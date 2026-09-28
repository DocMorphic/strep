import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save, sha256
from portable_integrity import contained, verify_vendor, verify_files


def fixture(tmp_path):
    root=tmp_path/'Installation with spaces'
    source=root/'vendor/kimodo/package.py';source.parent.mkdir(parents=True)
    source.write_text('x=1\n',encoding='utf-8')
    save(root/'benchmarks/sources.lock.json',{'kimodo_git_commit':'abc'})
    save(root/'benchmarks/vendor-export.json',{'schema':1,'commit':'abc','files_sha256':{'package.py':sha256(source)}})
    return root,source


def test_source_export_accepts_relocation_without_git(tmp_path):
    root,source=fixture(tmp_path)
    assert verify_vendor(root)=='abc'
    cache=source.parent/'__pycache__/package.pyc';cache.parent.mkdir();cache.write_bytes(b'cache')
    assert verify_vendor(root)=='abc'


@pytest.mark.parametrize('change',['missing','changed','extra','revision'])
def test_source_export_rejects_drift(tmp_path,change):
    root,source=fixture(tmp_path)
    if change=='missing':source.unlink()
    if change=='changed':source.write_text('x=2',encoding='utf-8')
    if change=='extra':source.with_name('injected.py').write_text('x=1',encoding='utf-8')
    if change=='revision':save(root/'benchmarks/sources.lock.json',{'kimodo_git_commit':'different'})
    with pytest.raises(RuntimeError):verify_vendor(root)


@pytest.mark.parametrize('path',['../outside','C:/outside','/outside','x/../../outside','x\\outside',''])
def test_inventory_paths_are_contained(tmp_path,path):
    with pytest.raises(ValueError):contained(tmp_path,path)


def test_package_hash_detects_changed_runtime(tmp_path):
    p=tmp_path/'python.exe';p.write_bytes(b'python')
    inventory={'python.exe':sha256(p)}
    verify_files(tmp_path,inventory)
    p.write_bytes(b'different')
    with pytest.raises(RuntimeError):verify_files(tmp_path,inventory)


def test_scene_discovery_accepts_empty_install_and_only_ready_collections(tmp_path,monkeypatch):
    import threading
    import json
    from urllib.request import urlopen
    from http.server import ThreadingHTTPServer
    import action_studio_server as api
    monkeypatch.setattr(api,'ROOT',tmp_path)
    server=ThreadingHTTPServer(('127.0.0.1',0),api.Handler)
    host=f'127.0.0.1:{server.server_port}';server.allowed_hosts={host}
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get():
        with urlopen('http://'+host+'/api/scene-collections') as result:
            return json.load(result)['collections']
    try:
        assert get()==[]
        for name,status in [('action-jobs/new-scene','complete'),('scene-release-jobs/pending','processing')]:
            save(tmp_path/'reports'/name/'manifest.json',{'scenes':[]})
            save(tmp_path/'reports'/name/'pipeline.json',{'status':status})
        assert get()==['action-jobs/new-scene']
        save(tmp_path/'reports/action-jobs/engine-audit/manifest.json',{'cases':[]})
        save(tmp_path/'reports/action-jobs/engine-audit/pipeline.json',{'status':'complete'})
        assert get()==['action-jobs/new-scene']
    finally:
        server.shutdown();thread.join();server.server_close()
