"""Synthetic review-package fixtures; never animator evidence."""
from pathlib import Path
import sys
import zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import portable_review_packet as portable
from strep import save,read,sha256


def fixture(tmp_path,monkeypatch):
    root=tmp_path/'project';three=root/'assets/viewer/node_modules/three'
    for name in ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','LICENSE']:
        p=three/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic fixture',encoding='utf-8')
    scripts=root/'scripts';scripts.mkdir(parents=True)
    for name in ['soma-preview-skin.js','serve_review_packet.py','start_review.cmd']:(scripts/name).write_text('synthetic fixture',encoding='utf-8')
    monkeypatch.setattr(portable,'ROOT',root)
    packet=tmp_path/'packet';(packet/'clips').mkdir(parents=True);clip=packet/'clips/clip-001.glb';clip.write_bytes(b'synthetic')
    save(packet/'manifest.json',{'packet_id':'synthetic','cases':[{'path':'clips/clip-001.glb','sha256':sha256(clip)}]})
    (packet/'viewer.html').write_text('../../assets/viewer/node_modules/three/build/three.module.js ../../scripts/soma-preview-skin.js',encoding='utf-8')
    (packet/'LICENSE.txt').write_text('synthetic fixture',encoding='utf-8')
    return packet


def test_portable_inventory_and_zip_preserve_only_packet(tmp_path,monkeypatch):
    packet=fixture(tmp_path,monkeypatch);archive=tmp_path/'packet.zip';before=sha256(packet/'manifest.json')
    portable.package(packet,archive)
    assert sha256(packet/'manifest.json')==before and '../../' not in (packet/'viewer.html').read_text()
    html=(packet/'viewer.html').read_text()
    assert './runtime/three/build/three.module.js' in html and './runtime/soma-preview-skin.js' in html
    inventory=read(packet/'package-integrity.json')['files']
    assert all(sha256(packet/name)==digest for name,digest in inventory.items())
    assert 'Start Review.cmd' in inventory
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(inventory)|{'package-integrity.json'}
        assert z.testzip() is None
    with pytest.raises(ValueError):portable.package(packet,tmp_path/'other.zip')


def test_organizer_file_is_never_accidentally_packed(tmp_path,monkeypatch):
    packet=fixture(tmp_path,monkeypatch);(packet/'key.json').write_text('private',encoding='utf-8')
    with pytest.raises(ValueError,match='organizer'):portable.package(packet,tmp_path/'packet.zip')
    assert not (tmp_path/'packet.zip').exists()


def test_changed_clip_blocks_packaging(tmp_path,monkeypatch):
    packet=fixture(tmp_path,monkeypatch);(packet/'clips/clip-001.glb').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Changed'):portable.package(packet,tmp_path/'packet.zip')


def test_cleanup_timer_dependency_is_inside_portable_packet(tmp_path,monkeypatch):
    packet=fixture(tmp_path,monkeypatch)
    timer=Path(__file__).resolve().parents[1]/'scripts/cleanup-timer.mjs'
    target=portable.ROOT/'scripts/cleanup-timer.mjs';target.write_bytes(timer.read_bytes())
    with (packet/'viewer.html').open('a',encoding='utf-8') as stream:stream.write(" import '../../scripts/cleanup-timer.mjs';")
    portable.package(packet,tmp_path/'packet.zip')
    assert (packet/'runtime/cleanup-timer.mjs').read_bytes()==timer.read_bytes()
    assert './runtime/cleanup-timer.mjs' in (packet/'viewer.html').read_text()
    assert read(packet/'package-integrity.json')['files']['runtime/cleanup-timer.mjs']==sha256(timer)


def server_fixture(tmp_path,monkeypatch):
    import serve_review_packet as server
    (tmp_path/'manifest.json').write_text('{}')
    monkeypatch.setattr(server,'__file__',str(tmp_path/'serve.py'))
    calls=[]
    class StubServer:
        def __init__(self,address,handler):
            calls.append(('bind',address,handler.keywords['directory']))
        def serve_forever(self):
            calls.append(('serve',));raise KeyboardInterrupt
        def server_close(self):calls.append(('close',))
    monkeypatch.setattr(server.http.server,'ThreadingHTTPServer',StubServer)
    monkeypatch.setattr(server.webbrowser,'open',lambda url:calls.append(('browser',url)) or True)
    return server,calls


def test_review_browser_opens_only_after_loopback_bind_and_server_closes(tmp_path,monkeypatch):
    server,calls=server_fixture(tmp_path,monkeypatch)
    server.main(['--port','8772','--open'])
    assert calls==[('bind',('127.0.0.1',8772),str(tmp_path)),
        ('browser','http://127.0.0.1:8772/viewer.html'),('serve',),('close',)]


@pytest.mark.parametrize('browser_result',['false','exception'])
def test_browser_failure_leaves_manual_url_and_serving_available(tmp_path,monkeypatch,capsys,browser_result):
    server,calls=server_fixture(tmp_path,monkeypatch)
    def browser(url):
        if browser_result=='exception':raise OSError('No browser')
        return False
    monkeypatch.setattr(server.webbrowser,'open',browser)
    server.main(['--open'])
    assert ('serve',) in calls and calls[-1]==('close',)
    assert 'http://127.0.0.1:8771/viewer.html' in capsys.readouterr().out


def test_occupied_port_does_not_open_unrelated_browser_service(tmp_path,monkeypatch,capsys):
    server,calls=server_fixture(tmp_path,monkeypatch)
    def busy(*args,**kwargs):raise OSError('Address already in use')
    monkeypatch.setattr(server.http.server,'ThreadingHTTPServer',busy)
    with pytest.raises(SystemExit) as error:server.main(['--open'])
    assert error.value.code==1 and calls==[]
    message=capsys.readouterr().err
    assert '--port 8772 --open' in message and 'same port' in message


@pytest.mark.parametrize('port',['0','65536'])
def test_invalid_port_rejected_without_binding(tmp_path,monkeypatch,port):
    server,calls=server_fixture(tmp_path,monkeypatch)
    with pytest.raises(SystemExit):server.main(['--port',port])
    assert calls==[]


def test_manual_start_does_not_open_browser(tmp_path,monkeypatch):
    server,calls=server_fixture(tmp_path,monkeypatch)
    server.main([])
    assert not any(c[0]=='browser' for c in calls) and calls[-1]==('close',)


def test_start_outside_packet_never_binds_or_opens_browser(tmp_path,monkeypatch):
    server,calls=server_fixture(tmp_path,monkeypatch)
    (tmp_path/'manifest.json').unlink()
    with pytest.raises(SystemExit):server.main(['--open'])
    assert calls==[]


def test_windows_launcher_executes_packet_from_path_with_spaces(tmp_path):
    import os,shutil,subprocess,json
    if os.name!='nt':pytest.skip('Actual Windows command launcher')
    if not shutil.which('py'):pytest.skip('Python launcher is not installed')
    packet=tmp_path/'review packet & spaces';packet.mkdir()
    launcher=packet/'Start Review.cmd'
    launcher.write_bytes((Path(__file__).resolve().parents[1]/'scripts/start_review.cmd').read_bytes())
    # A real Python child records arguments, but never starts a server/browser.
    (packet/'serve.py').write_text('import sys,json\nfrom pathlib import Path\n'
        "Path('called.json').write_text(json.dumps(dict(args=sys.argv[1:],cwd=str(Path.cwd()))))\n")
    result=subprocess.run('cmd /d /s /c ""'+str(launcher)+'""',input='\n',text=True,
        capture_output=True,cwd=tmp_path,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads((packet/'called.json').read_text())=={'args':['--open'],'cwd':str(packet)}
