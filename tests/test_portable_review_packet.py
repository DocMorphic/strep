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
    for name in ['soma-preview-skin.js','serve_review_packet.py']:(scripts/name).write_text('synthetic fixture',encoding='utf-8')
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
