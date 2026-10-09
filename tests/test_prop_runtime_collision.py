"""Source-preserving complete packages and immutable explicit physics choice."""
import copy,json,sys,zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prop_runtime_collision import profile_document,project_lines,verify_actual
from scene_collision_profile import PROFILES,TRACKED_SETTINGS,PREFIX,THRESHOLD
from scene_prop_runtime import compile_request,entry_files,package
from test_native_scene_runtime import fixture
from test_scene_prop_runtime import request_for
from strep import save,read,sha256


@pytest.mark.parametrize('rate',[60,120,240])
@pytest.mark.parametrize('profile',list(PROFILES))
def test_request_to_complete_zip_binds_all_collision_controls_without_changing_source(tmp_path,rate,profile):
    _,source,_,config,scene,_,events,_=fixture(tmp_path)
    r=request_for(source,scene);r.update(physics_fps=rate,collision_profile=profile)
    compiled=compile_request(r,config,scene,events,sha256(source))
    expected=profile_document(profile,rate)
    assert compiled['collision_profile']==expected and set(expected['settings'])==set(TRACKED_SETTINGS)
    path=tmp_path/'request.json';save(path,r);before=(source.read_bytes(),path.read_bytes())
    out=tmp_path/'export';result=package(source,path,out)
    with zipfile.ZipFile(out/'prop-runtime-assets.zip') as z,zipfile.ZipFile(source) as original:
        assert json.loads(z.read('ownership-v1/prop-runtime.json'))==compiled
        assert z.read('project.godot')==entry_files(rate,expected)['project.godot'].encode()
        assert z.read('ownership-v1/ownership-authoring-request.json')==before[1]
        for n in original.namelist():assert z.read('source-game-package.json' if n=='package.json' else n)==original.read(n)
    assert (source.read_bytes(),path.read_bytes())==before
    assert not any(result[k] for k in ('engine_executed','physics_verified','animation_quality_approved','release_approved'))


@pytest.mark.parametrize('fault',[None,False,'unknown',{},[],123])
def test_explicit_profile_is_never_silently_defaulted(tmp_path,fault):
    _,source,_,config,scene,_,events,_=fixture(tmp_path);r=request_for(source,scene);r['collision_profile']=fault
    with pytest.raises(ValueError):compile_request(r,config,scene,events,sha256(source))


@pytest.mark.parametrize('fault',['name','setting','hidden','boolean','rate','backend'])
def test_project_entry_cannot_accept_a_mutated_compiled_profile(fault):
    profile=profile_document('ccd-threshold',60)
    if fault=='name':profile['name']='unknown'
    elif fault=='setting':profile['settings'][THRESHOLD]=.75
    elif fault=='hidden':profile['settings']['undocumented']=1
    elif fault=='boolean':profile['settings'][PREFIX+'collisions/collision_margin_fraction']=False
    elif fault=='rate':profile['settings']['physics/common/physics_ticks_per_second']=120
    else:profile['backend']='Godot Physics'
    with pytest.raises(ValueError):project_lines(profile,60)


def test_absent_profile_retains_exact_legacy_configuration_and_entry(tmp_path):
    _,source,_,config,scene,_,events,_=fixture(tmp_path);r=request_for(source,scene)
    compiled=compile_request(r,config,scene,events,sha256(source))
    assert 'collision_profile' not in compiled and project_lines(None,120)==''
    expected='config_version=5\n[application]\nconfig/name="Strep explicit prop runtime"\nrun/main_scene="res://ownership-v1/scene.tscn"\n[physics]\ncommon/physics_ticks_per_second=120\n3d/physics_engine="Jolt Physics"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n'
    assert entry_files(120)['project.godot']==expected


@pytest.mark.parametrize('profile',list(PROFILES))
def test_completed_studio_download_replays_explicit_choice_and_refuses_rehashed_startup_drift(tmp_path,monkeypatch,profile):
    from test_studio_scene_prop_runtime import setup,rewrite_export
    import studio_scene_prop_runtime as studio
    payload,_=setup(tmp_path,monkeypatch);payload['request']['collision_profile']=profile
    folder=studio.folder_for('profile');studio.prepare(payload,folder);studio.run(folder)
    assert studio.manifest('profile')['status']=='complete'
    prepared=read(folder/'prepared.json')
    assert {'prop_runtime_collision.py','scene_collision_profile.py'}<=set(prepared['implementation_sha256'])
    entry=(folder/'runtime/project/project.godot').read_bytes()
    rewrite_export(folder,'project.godot',entry.replace(b'simulation/penetration_slop=0.001',b'simulation/penetration_slop=0.01'))
    with pytest.raises(ValueError,match='startup'):studio.manifest('profile')
    assert studio.served_file('scene-prop-runtime-jobs/profile/runtime/prop-runtime-assets.zip') is None


@pytest.mark.parametrize('profile',[None,'ccd-threshold'])
def test_legacy_helper_exception_is_only_for_old_completed_jobs_without_profile(tmp_path,monkeypatch,profile):
    from test_studio_scene_prop_runtime import setup
    import studio_scene_prop_runtime as studio
    payload,_=setup(tmp_path,monkeypatch)
    if profile is not None:payload['request']['collision_profile']=profile
    folder=studio.folder_for('legacy');studio.prepare(payload,folder)
    # Exercise method-population compatibility independently of completed ZIP checks.
    prepared=read(folder/'prepared.json')
    for name in ('prop_runtime_collision.py','scene_collision_profile.py'):prepared['implementation_sha256'].pop(name)
    save(folder/'prepared.json',prepared)
    if profile is None:studio.frozen(folder,current_methods=False)
    else:
        with pytest.raises(ValueError,match='Complete prop method'):studio.frozen(folder,current_methods=False)
    with pytest.raises(ValueError,match='Complete prop method'):studio.frozen(folder,current_methods=True)


@pytest.mark.parametrize('key',list(TRACKED_SETTINGS))
def test_independent_actual_setting_replay_checks_every_declared_control(key):
    profile=profile_document('ccd-threshold',60);echo=copy.deepcopy(profile['settings'])
    assert verify_actual(profile,echo,60)==echo
    echo[key]+=1
    with pytest.raises(ValueError,match='differs'):verify_actual(profile,echo,60)


@pytest.mark.parametrize('fault',['missing','extra','bool','nan','null'])
def test_actual_setting_replay_cannot_use_an_incomplete_or_non_numeric_echo(fault):
    profile=profile_document('strict-ccd',120);echo=copy.deepcopy(profile['settings'])
    if fault=='missing':echo.pop(THRESHOLD)
    elif fault=='extra':echo['undocumented']=1
    else:echo[THRESHOLD]={'bool':True,'nan':float('nan'),'null':None}[fault]
    with pytest.raises(ValueError):verify_actual(profile,echo,120)


def test_profiled_source_continues_to_editable_bake_and_capture_requires_matching_settings(tmp_path):
    import scene_prop_bake as bake
    from test_scene_prop_bake import setup,trace,request
    from native_scene_runtime import configure
    folder,source,scene,events,r,_,clock,poses=setup(tmp_path)
    r['collision_profile']='ccd-threshold';path=tmp_path/'runtime-request.json';save(path,r)
    exported=tmp_path/'runtime';package(source,path,exported)
    runtime=exported/'prop-runtime-assets.zip';loaded=bake.load_package(runtime,tmp_path/'capture-project')
    compiled=loaded[2];assert compiled['collision_profile']==profile_document('ccd-threshold',120)
    actual=trace(scene,events,compiled,clock,poses,'a'*64)
    actual['collision_settings']=copy.deepcopy(compiled['collision_profile']['settings'])
    author=request(runtime);audit,_=bake.audit_capture(actual,compiled,scene,events,author,'a'*64)
    assert not audit['quality_approved'] and not audit['release_approved']
    for echo in [None,{**actual['collision_settings'],THRESHOLD:.75}]:
        changed=copy.deepcopy(actual);changed['collision_settings']=echo
        with pytest.raises(ValueError):bake.audit_capture(changed,compiled,scene,events,author,'a'*64)
