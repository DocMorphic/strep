"""Mode-file transport retains the original complete runtime comparison."""
import copy,json,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256,ROOT
import native_scene_runtime as original
import native_scene_runtime_modes as modes
from test_native_scene_runtime import fixture,observations


def wire(folder,actual):
    header=dict(schema=modes.SCHEMA,engine=actual['engine'],bootstrap=actual['bootstrap'],modes={})
    for name in modes.MODES:
        path=folder/f'engine-mode-{name}.json';save(path,actual['modes'][name])
        header['modes'][name]=dict(path=path.name,sha256=sha256(path))
    return header


def test_lazy_modes_retain_every_original_result_and_array(tmp_path):
    _,_,_,_,scene,times,events,asset=fixture(tmp_path);actual=observations(scene,times,events,asset)
    expected,arrays=original.compare(scene,times,events,actual,object_asset=asset)
    lazy=modes.ModeFiles(tmp_path,wire(tmp_path,actual))
    assert lazy.baseline is None and len(lazy)==3 and set(lazy)==set(modes.MODES)
    assert lazy['embedded'] is lazy['embedded'] and lazy['extracted'] is not lazy['extracted']
    with pytest.raises(KeyError):lazy['partial']
    result,found=original.compare(scene,times,events,dict(actual,modes=lazy),object_asset=asset)
    assert result==expected and set(found)==set(arrays)
    for name,value in arrays.items():np.testing.assert_array_equal(found[name],value)


@pytest.mark.parametrize('fault',['missing','extra','path','absolute','hash','mutated','header','fields'])
def test_incomplete_changed_or_escaping_mode_files_reject(tmp_path,fault):
    actual=dict(engine={},bootstrap={},modes={name:dict(frames=[]) for name in modes.MODES})
    header=wire(tmp_path,actual)
    if fault=='missing':header['modes'].pop('mixed')
    if fault=='extra':header['modes']['extra']=header['modes']['mixed']
    if fault=='path':header['modes']['mixed']['path']='../engine-mode-mixed.json'
    if fault=='absolute':header['modes']['mixed']['path']=str(tmp_path/'engine-mode-mixed.json')
    if fault=='hash':header['modes']['mixed']['sha256']='0'*64
    if fault=='mutated':(tmp_path/'engine-mode-mixed.json').write_bytes(b'{}')
    if fault=='header':header['schema']='unknown'
    if fault=='fields':header['modes']['mixed']['sample_subset']=[0]
    with pytest.raises(ValueError):modes.ModeFiles(tmp_path,header)


def test_late_change_of_cached_or_unloaded_file_is_not_hidden(tmp_path):
    actual=dict(engine={},bootstrap={},modes={name:dict(frames=[]) for name in modes.MODES})
    lazy=modes.ModeFiles(tmp_path,wire(tmp_path,actual));lazy['embedded']
    (tmp_path/'engine-mode-embedded.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='changed'):lazy.verify()
    (tmp_path/'engine-mode-mixed.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='changed'):lazy['mixed']


def test_whole_worker_preserves_failed_conditions_and_actual_package_entries(tmp_path,monkeypatch):
    _,package,_,_,scene,times,events,asset=fixture(tmp_path);actual=observations(scene,times,events,asset)
    actual['modes']['mixed']['frames'][-1]['objects']['item'][3][0]+=.02
    engine=tmp_path/'engine';engine.write_bytes(b'explicit-engine-test-double')
    def fake(command,**kwargs):
        path=Path(command[-1]);save(path,wire(path.parent,actual));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(modes.subprocess,'run',fake);before=sha256(package)
    result=modes.run(package,tmp_path/'runtime',{'A':'extracted','B':'embedded'},engine=engine)
    assert result['status']=='complete' and not result['all_sampled_runtime_conditions_pass']
    assert result['complete_clock_retained'] and result['original_comparator_unchanged'] and result['arrays_roundtrip_exact']
    assert not result['quality_approved'] and not result['release_approved'] and sha256(package)==before
    assert set(result['raw_mode_files_sha256'])=={'engine-output.json',*[f'engine-mode-{name}.json' for name in modes.MODES]}
    assert modes.AUDIT in result['executed_script_sha256'] and 'godot_native_scene_runtime_audit.gd' not in result['executed_script_sha256']
    with zipfile.ZipFile(package) as source,zipfile.ZipFile(tmp_path/'runtime/runtime-assets.zip') as final:
        for name in source.namelist():assert source.read(name)==final.read('source-game-package.json' if name=='package.json' else name)
    with pytest.raises(ValueError,match='Fresh'):modes.run(package,tmp_path/'runtime',{'A':'extracted','B':'embedded'},engine=engine)


def test_engine_failure_keeps_original_and_unapproved_failure(tmp_path,monkeypatch):
    _,package,_,_,_,_,_,_=fixture(tmp_path);engine=tmp_path/'engine';engine.write_bytes(b'explicit-engine-double')
    monkeypatch.setattr(modes.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=2))
    with pytest.raises(ValueError,match='Actual scene mode'):modes.run(package,tmp_path/'failed',{'A':'embedded','B':'embedded'},engine=engine)
    assert read(tmp_path/'failed/pipeline.json')['status']=='failed' and not (tmp_path/'failed/result.json').exists()


def test_engine_audit_diff_changes_only_mode_transport():
    source=(ROOT/'scripts/godot_native_scene_runtime_audit.gd').read_text()
    streamed=(ROOT/'scripts'/modes.AUDIT).read_text()
    source=source.replace('var report := {"engine": Engine.get_version_info(), "modes": {}}',
        'var report := {"schema": "strep-native-scene-runtime-mode-files-v1", "engine": Engine.get_version_info(), "modes": {}}')
    first=streamed.index('\t\t# Flush the complete mode')
    last=streamed.index('\n\t\tfor connection',first)
    streamed=streamed[:first]+'\t\treport.modes[mode] = entry'+streamed[last:]
    assert streamed==source
    assert 'mode_output.close()' in (ROOT/'scripts'/modes.AUDIT).read_text()
