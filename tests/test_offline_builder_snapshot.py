"""Exercise the builder with tiny synthetic runtime/vendor inputs, not a release."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_offline_install as builder
from strep import read,save,sha256


@pytest.fixture
def environment(tmp_path,monkeypatch):
    root=tmp_path/'source';runtime=tmp_path/'runtime';destination=tmp_path/'installation'
    for directory in ['scripts','assets','benchmarks','integrations','models','vendor/kimodo','.cache/godot/4.7.2-stable']:
        (root/directory).mkdir(parents=True)
    (root/'scripts/portable_site.py').write_text('# synthetic runtime guard fixture\n')
    (root/'scripts/scene-feedback.js').write_text('// synthetic UI fixture\n')
    (root/'vendor/kimodo/package.py').write_text('# synthetic vendor fixture\n')
    (root/'.cache/godot/4.7.2-stable/engine.txt').write_text('synthetic engine fixture')
    save(root/'models/manifest.json',dict(models={}))
    (runtime/'Lib/site-packages').mkdir(parents=True)
    (runtime/'Lib/site-packages/package.py').write_text('# synthetic dependency fixture\n')
    (runtime/'Lib/site.py').write_text('ENABLE_USER_SITE = None\n')
    monkeypatch.setattr(builder,'ROOT',root)
    monkeypatch.setattr(builder,'sys',SimpleNamespace(base_prefix=str(runtime),prefix=str(runtime)))
    monkeypatch.setattr(builder,'source_check',lambda:'synthetic-commit')
    monkeypatch.setattr(builder.subprocess,'check_output',lambda *a,**k:'package.py\0')
    monkeypatch.setattr(builder.shutil,'disk_usage',lambda *a:SimpleNamespace(free=50*1024**3))
    monkeypatch.setattr(builder.importlib.metadata,'distributions',lambda:[])
    return root,runtime,destination


def test_builder_inventory_binds_source_snapshot(environment):
    root,_,destination=environment;builder.build(destination)
    assert read(destination/'build-status.json')['status']=='complete'
    install=read(destination/'installation.json');source=read(destination/'project-source.json')
    assert install['project_source_sha256']==sha256(destination/'project-source.json')
    for relative,digest in source['files_sha256'].items():
        assert sha256(destination/relative)==sha256(root/relative)==digest
        assert install['files_sha256'][relative]==digest


def test_source_change_before_final_inventory_prevents_completion(environment,monkeypatch):
    root,runtime,destination=environment;original=builder.copy_tree
    def copy_and_change(source,target):
        original(source,target)
        if source==runtime:(root/'scripts/scene-feedback.js').write_text('// changed mid-build')
    monkeypatch.setattr(builder,'copy_tree',copy_and_change)
    with pytest.raises(RuntimeError,match='source changed'):builder.build(destination)
    assert read(destination/'build-status.json')['status']!='complete'
    assert not (destination/'installation.json').exists()


def test_copied_source_change_during_final_inventory_prevents_completion(environment,monkeypatch):
    _,_,destination=environment;original=builder.sha256
    def change_before_hash(path):
        if path==destination/'scripts/scene-feedback.js':path.write_text('// changed during inventory')
        return original(path)
    monkeypatch.setattr(builder,'sha256',change_before_hash)
    with pytest.raises(RuntimeError,match='during inventory'):builder.build(destination)
    assert read(destination/'build-status.json')['status']!='complete'
    assert not (destination/'installation.json').exists()
