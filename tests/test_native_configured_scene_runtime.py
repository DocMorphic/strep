"""Exact selected root-mask verification with explicit source-only engine doubles."""
import copy,hashlib,inspect,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
import native_configured_scene_runtime as selected
import native_scene_runtime as original
import test_native_scene_runtime as fixtures


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    folder=tmp_path_factory.mktemp('configured-root-mask')
    _,package,_,_,scene,times,events,asset=fixtures.fixture(folder)
    actual=fixtures.observations(scene,times,events,asset)
    return package,scene,times,events,asset,actual


def observations(actual,modes):
    """Compose each actor's selected test-double state at every callback/pose."""
    embedded=copy.deepcopy(actual['modes']['embedded'])
    configured=copy.deepcopy(embedded)
    def snapshot(target,alternatives):
        for name,mode in modes.items():
            target['actors'][name]=copy.deepcopy(alternatives[mode]['actors'][name])
            if 'root_deltas' in target:target['root_deltas'][name]=copy.deepcopy(alternatives[mode]['root_deltas'][name])
    for name,mode in modes.items():configured['actors'][name]=copy.deepcopy(actual['modes'][mode]['actors'][name])
    for field in ('frames','previews'):
        for i,target in enumerate(configured[field]):
            snapshot(target,{m:actual['modes'][m][field][i] for m in ('embedded','extracted')})
    for i,callback in enumerate(configured['events']):
        snapshot(callback['scene'],{m:actual['modes'][m]['events'][i]['scene'] for m in ('embedded','extracted')})
    for trace in configured['traces']:
        for i,callback in enumerate(configured['traces'][trace]):
            snapshot(callback['scene'],{m:actual['modes'][m]['traces'][trace][i]['scene'] for m in ('embedded','extracted')})
    embedded['root_modes']={n:'embedded' for n in modes};configured['root_modes']=dict(modes)
    return dict(engine=actual['engine'],bootstrap=actual['bootstrap'],modes=dict(embedded=embedded,configured=configured))


@pytest.mark.parametrize('a,b',[('embedded','embedded'),('extracted','extracted'),('extracted','embedded'),('embedded','extracted')])
def test_every_two_actor_root_mask_retains_full_pose_skin_event_and_object_checks(fixture,a,b):
    _,scene,times,events,asset,actual=fixture;modes=dict(A=a,B=b)
    value=observations(actual,modes)
    result,arrays=selected.compare(scene,times,events,value,object_asset=asset,root_modes=modes)
    assert result['all_sampled_runtime_conditions_pass'] and result['configured_mode_observed']
    assert result['configured_root_modes']==modes and result['samples']==len(times)
    assert set(result['modes'])=={'embedded','configured'}
    for i,name in enumerate(scene.actors):
        if modes[name]=='extracted':assert f'configured_actor_{i}_extracted_world' in arrays
        else:assert f'configured_actor_{i}_world' in arrays
        assert result['modes']['configured']['actors'][name]['affine_skin']['passed']
    assert result['modes']['configured']['callback_scenarios']==4


def test_three_actor_non_alternating_mask_is_checked_for_each_actor(fixture):
    _,scene,times,events,asset,_=fixture
    scene=copy.copy(scene);scene.actors=dict(scene.actors)
    scene.actors['C']=dict(scene.actors['A'],placement=(np.array([4.,0.,0.]),np.eye(3)))
    actual=fixtures.observations(scene,times,events,asset)
    modes=dict(A='embedded',B='extracted',C='extracted')
    result,arrays=selected.compare(scene,times,events,observations(actual,modes),object_asset=asset,root_modes=modes)
    assert result['all_sampled_runtime_conditions_pass'] and result['configured_root_modes']==modes
    assert set(result['modes']['configured']['actors'])=={'A','B','C'}
    assert 'configured_actor_0_world' in arrays
    assert all(f'configured_actor_{i}_extracted_world' in arrays for i in (1,2))


@pytest.mark.parametrize('mode',['embedded','extracted','mixed'])
def test_known_mode_outputs_and_every_array_match_original_comparator(fixture,mode):
    _,scene,times,events,asset,actual=fixture
    modes={n:('extracted' if mode=='extracted' or mode=='mixed' and i%2==0 else 'embedded') for i,n in enumerate(scene.actors)}
    expected,original_arrays=original.compare(scene,times,events,actual,object_asset=asset)
    result,arrays=selected.compare(scene,times,events,observations(actual,modes),object_asset=asset,root_modes=modes)
    assert result['modes']['configured']==expected['modes'][mode]
    assert result['modes']['embedded']==expected['modes']['embedded'] and result['bootstrap']==expected['bootstrap']
    expected_arrays={k.replace(mode+'_','configured_',1):v for k,v in original_arrays.items() if k.startswith(mode+'_')}
    expected_arrays.update({k:v for k,v in original_arrays.items() if k.startswith('embedded_') or k=='times_s'})
    assert set(arrays)==set(expected_arrays)
    for key,value in arrays.items():
        other=expected_arrays[key]
        assert value.dtype==other.dtype and value.shape==other.shape and value.tobytes()==other.tobytes()


@pytest.mark.parametrize('fault',['echo','missing-frame','clock','callback','preview','bootstrap','object-value','actor-value'])
def test_incomplete_or_incorrect_configured_observations_cannot_pass(fixture,fault):
    _,scene,times,events,asset,actual=fixture;modes=dict(A='embedded',B='extracted')
    value=observations(actual,modes);entry=value['modes']['configured']
    if fault=='echo':entry['root_modes']['B']='embedded'
    if fault=='missing-frame':entry['frames'].pop()
    if fault=='clock':entry['frames'][1]['pose_time_s']+=.001
    if fault=='callback':entry['events'].pop()
    if fault=='preview':entry['previews'][0]['pose_time_s']=.123456789
    if fault=='bootstrap':value['bootstrap']=dict(value['bootstrap'],parent_ready_listener=False)
    if fault=='object-value':entry['frames'][-1]['objects']['item'][3][0]+=.02
    if fault=='actor-value':entry['frames'][-1]['actors']['B']['bones'][-1][3][0]+=.02
    if fault in ('object-value','actor-value'):
        result,_=selected.compare(scene,times,events,value,object_asset=asset,root_modes=modes)
        assert result['all_sampled_runtime_conditions_pass'] is False
    else:
        with pytest.raises(ValueError):selected.compare(scene,times,events,value,object_asset=asset,root_modes=modes)


@pytest.mark.parametrize('modes',[{},dict(A='embedded'),dict(A='embedded',B='extracted',C='embedded'),dict(A=True,B='embedded')])
def test_partial_extra_or_boolean_root_choices_reject(fixture,modes):
    _,scene,times,events,asset,actual=fixture
    with pytest.raises(ValueError):selected.compare(scene,times,events,observations(actual,dict(A='embedded',B='extracted')),object_asset=asset,root_modes=modes)


def wire(folder,actual):
    header=dict(schema=selected.SCHEMA,engine=actual['engine'],bootstrap=actual['bootstrap'],modes={})
    for name in selected.MODES:
        path=folder/f'engine-mode-{name}.json';save(path,actual['modes'][name])
        header['modes'][name]=dict(path=path.name,sha256=sha256(path))
    return header


@pytest.mark.parametrize('failed',[False,True])
def test_whole_worker_exports_the_exact_observed_mask_and_retains_failed_status(tmp_path,monkeypatch,fixture,failed):
    package,_,_,_,_,actual=fixture;modes=dict(A='embedded',B='extracted');value=observations(actual,modes)
    if failed:value['modes']['configured']['frames'][-1]['objects']['item'][3][0]+=.02
    engine=tmp_path/'engine';engine.write_bytes(b'explicit-source-test-double')
    def fake(command,**kwargs):
        path=Path(command[-1]);save(path,wire(path.parent,value));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(selected.subprocess,'run',fake);before=sha256(package)
    result=selected.run(package,tmp_path/'runtime',modes,engine=engine)
    assert result['status']=='complete' and result['all_sampled_runtime_conditions_pass'] is (not failed)
    assert result['configured_root_modes']==modes and result['configured_mode_observed']
    assert result['arrays_roundtrip_exact'] and result['complete_clock_retained'] and sha256(package)==before
    assert not any(result[k] for k in ('quality_approved','physics_verified','release_approved','real_time_playback_verified'))
    assert set(result['raw_mode_files_sha256'])=={'engine-output.json','engine-mode-embedded.json','engine-mode-configured.json'}
    assert selected.AUDIT in result['executed_script_sha256']
    with zipfile.ZipFile(tmp_path/'runtime/runtime-assets.zip') as z:
        manifest=read(tmp_path/'runtime/package.json')
        assert manifest['runtime_root_modes']==modes and manifest['finite_scene_controller_verified'] is (not failed)
        for name,digest in manifest['files_sha256'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        with zipfile.ZipFile(package) as source:
            for name in source.namelist():assert z.read('source-game-package.json' if name=='package.json' else name)==source.read(name)
        assert set(z.namelist())==set(manifest['files_sha256'])|{'package.json'}


def test_export_configuration_changed_during_engine_run_cannot_be_published(tmp_path,monkeypatch,fixture):
    package,_,_,_,_,actual=fixture;modes=dict(A='embedded',B='extracted');value=observations(actual,modes)
    engine=tmp_path/'engine';engine.write_bytes(b'explicit-source-test-double')
    def fake(command,**kwargs):
        path=Path(command[-1]);save(path,wire(path.parent,value))
        p=path.parent/'project/runtime-v1/scene-runtime.json';config=read(p);config['actors'][0]['extract']=True;save(p,config)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(selected.subprocess,'run',fake)
    with pytest.raises(ValueError,match='runtime configuration changed'):selected.run(package,tmp_path/'runtime',modes,engine=engine)
    assert not (tmp_path/'runtime/runtime-assets.zip').exists() and read(tmp_path/'runtime/pipeline.json')['status']=='failed'


def test_godot_sidecar_retains_all_original_audit_steps():
    expected=(ROOT/'scripts/godot_native_scene_runtime_mode_audit.gd').read_text()
    actual=(ROOT/'scripts'/selected.AUDIT).read_text()
    actual=actual.replace(selected.SCHEMA,'strep-native-scene-runtime-mode-files-v1')
    actual=actual.replace('for mode in ["embedded", "configured"]:','for mode in ["embedded", "extracted", "mixed"]:')
    actual=actual.replace('for index in range(config.actors.size()):\n\t\t\tif mode == "embedded": config.actors[index].extract = false',
        'for index in range(config.actors.size()): config.actors[index].extract = mode == "extracted" or (mode == "mixed" and index % 2 == 0)')
    actual=actual.replace('\t\tentry.root_modes = {}\n\t\tfor actor_config in config.actors:\n\t\t\tentry.root_modes[actor_config.id] = "extracted" if actor_config.extract else "embedded"\n','')
    assert actual==expected


@pytest.mark.parametrize('fault',['old-schema','missing-configured','escaping-file','changed-mode'])
def test_transport_cannot_substitute_another_producer_or_incomplete_mode(tmp_path,fault):
    actual=dict(engine={},bootstrap={},modes={name:dict(frames=[]) for name in selected.MODES})
    header=wire(tmp_path,actual)
    if fault=='old-schema':header['schema']='strep-native-scene-runtime-mode-files-v1'
    if fault=='missing-configured':header['modes'].pop('configured')
    if fault=='escaping-file':header['modes']['configured']['path']='../engine-mode-configured.json'
    if fault=='changed-mode':(tmp_path/'engine-mode-configured.json').write_bytes(b'changed')
    with pytest.raises(ValueError):selected.ModeFiles(tmp_path,header)


def test_comparator_changes_only_explicit_root_selection_and_scope():
    actual=inspect.getsource(selected.compare);expected=inspect.getsource(original.compare)
    actual=actual.replace('def compare(scene,times,events,actual,*,object_asset,root_modes):','def compare(scene,times,events,actual,*,object_asset):')
    actual=actual.replace("require(set(actual['modes'])==set(MODES),'Complete configured root-mode comparisons required')\n    require(isinstance(root_modes,dict) and set(root_modes)==set(scene.actors)\n        and all(v in ('embedded','extracted') for v in root_modes.values()),'Explicit root mode for every actor required')",
        "require(set(actual['modes'])=={'embedded','extracted','mixed'},'Complete root-mode comparisons required')")
    actual=actual.replace("        expected_modes={name:('embedded' if mode=='embedded' else root_modes[name]) for name in scene.actors}\n        require(observed['root_modes']==expected_modes,'Actual captured root mask differs from selected configuration')\n",'')
    actual=actual.replace("if mode=='configured' and root_modes[name]=='extracted':","if mode=='extracted' or (mode=='mixed' and index%2==0):")
    actual=actual.replace('samples=len(times),\n        configured_root_modes=dict(root_modes),configured_mode_observed=True),arrays','samples=len(times)),arrays')
    assert actual==expected
