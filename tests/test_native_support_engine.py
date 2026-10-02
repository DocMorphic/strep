"""Bounded Godot audit routing; observations here are explicit CPU fixtures."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_native_support_engine as audit
from strep import read,save,sha256


@pytest.fixture
def study(tmp_path,monkeypatch):
    from test_native_support import fixture
    import native_support_job as job
    monkeypatch.setattr(job,'ROOT',tmp_path);monkeypatch.setattr(audit,'ROOT',tmp_path)
    (tmp_path/'reports').mkdir()
    source,rig,reader,spec=fixture(tmp_path,plane=.2)
    draft=tmp_path/'draft.json';save(draft,spec)
    folder=tmp_path/'reports'/'warm'
    job.run(source,draft,folder,joint_rates=True,joint_swivel=True,joint_foot_orientation=True,joint_evaluations=1)
    return folder,tmp_path/'reports'/'engine'


def observations(case,reference):
    rig,sampler,names=reference;order=list(reversed(range(len(rig.joints))))
    found=[]
    for t in case['sample_times_s']:
        worlds=sampler.sample(t)[[rig.joints[i] for i in order]]
        bones=[np.vstack([m[:3,:3].T,m[:3,3]]).tolist() for m in worlds]
        found.append(dict(requested_time_s=t,actual_time_s=t,bones=bones))
    return dict(id=case['id'],path=case['path'],frames=found,
        bone_names=[names[i] for i in order],animations=['Native'],import_error=0,
        duration_s=sampler.duration,imported_loop_mode=0,meshes=[dict(weights=[1.])])


def test_input_and_all_proposals_keep_native_and_nearby_authored_clock(study):
    folder,out=study;request,result,files=audit.bind_study(folder)
    cases,refs,rows=audit.prepare_cases(folder,request,result,out)
    assert [c['id'] for c in cases]==['input','trial-0','trial-1','trial-2','trial-3']
    for case,ref in zip(cases,refs):
        assert case['authoring_seek'] and not case['native_payload']['loop']
        stamps=case['sample_times_s'];assert .8 in stamps and float(np.float32(.8)) in stamps
        assert .8!=float(np.float32(.8)) and stamps[-1]==ref[1].duration
        assert stamps==sorted(set(stamps)) and len(stamps)==case['frames']
        check,errors,heights=audit.check_case(case,observations(case,ref),ref,rows)
        assert check['engine_pose_pass']
        assert check['engine_bones_original_skin_support_pass']==(case['id']!='input')
        assert check['position_error_m']==0 and check['basis_element_error']==0
        assert len(errors)==case['frames'] and heights[0]['times_s'][0]==.8
        assert heights[0]['source_lowest_heights_m']==heights[0]['engine_bone_lowest_heights_m']


def test_engine_bones_drive_reference_skin_without_claiming_imported_skin(study):
    folder,out=study;request,result,_=audit.bind_study(folder)
    cases,refs,rows=audit.prepare_cases(folder,request,result,out)
    case,ref=cases[1],refs[1];observed=observations(case,ref)
    foot=observed['bone_names'].index('ankle-Z')
    for frame in observed['frames']:frame['bones'][foot][3][1]+=.00001
    check,errors,heights=audit.check_case(case,observed,ref,rows)
    assert check['engine_pose_pass'] and check['engine_bones_original_skin_support_pass']
    h=check['supports'][0];assert abs(h['maximum_source_height_error_m']-.00001)<1e-14
    np.testing.assert_allclose(np.array(heights[0]['engine_bone_lowest_heights_m'])-heights[0]['source_lowest_heights_m'],.00001,atol=1e-14,rtol=0)
    # A larger displacement violates both the pose gate and authored foot plane.
    for frame in observed['frames']:frame['bones'][foot][3][1]-=.003
    check,_,_=audit.check_case(case,observed,ref,rows)
    assert not check['engine_pose_pass'] and not check['engine_bones_original_skin_support_pass']


@pytest.mark.parametrize('fault',['bones','frames','clock','clock_population','path','animations','import','nonfinite'])
def test_wrong_or_incomplete_observations_rejected(study,fault):
    folder,out=study;q,r,_=audit.bind_study(folder);cases,refs,rows=audit.prepare_cases(folder,q,r,out)
    case,ref=cases[0],refs[0];observed=observations(case,ref)
    if fault=='bones':observed['bone_names'][0]='different'
    if fault=='frames':observed['frames'].pop()
    if fault=='clock':observed['frames'][0]['requested_time_s']+=.001
    if fault=='clock_population':case['sample_times_s'].pop()
    if fault=='path':observed['path']='different.glb'
    if fault=='animations':observed['animations'].append('Another')
    if fault=='import':observed['import_error']=1
    if fault=='nonfinite':observed['frames'][0]['bones'][0][0][0]=float('nan')
    with pytest.raises(ValueError):audit.check_case(case,observed,ref,rows)


@pytest.mark.parametrize('fault',['seek','loop','skin','duration','pose'])
def test_actual_gate_failure_is_not_engine_quality_approval(study,fault):
    folder,out=study;q,r,_=audit.bind_study(folder);cases,refs,rows=audit.prepare_cases(folder,q,r,out)
    case,ref=cases[0],refs[0];observed=observations(case,ref)
    if fault=='seek':observed['frames'][-1]['actual_time_s']-=.0001
    if fault=='loop':observed['imported_loop_mode']=1
    if fault=='skin':observed['meshes']=[]
    if fault=='duration':observed['duration_s']+=.01
    if fault=='pose':observed['frames'][0]['bones'][0][3][0]+=.01
    check,_,_=audit.check_case(case,observed,ref,rows)
    assert not check['engine_pose_pass']


@pytest.mark.parametrize('fault',['unfinished','selection','retention','escape','conflict','proposal','unbound'])
def test_incomplete_or_misbound_study_rejected(study,fault):
    folder,out=study
    if fault=='unfinished':save(folder/'pipeline.json',dict(status='processing'))
    elif fault=='escape':
        q=read(folder/'request.json');q['implementation']['../evil.py']='0'*64;save(folder/'request.json',q)
    else:
        r=read(folder/'result.json')
        if fault=='selection':r['selected_trial']=True
        if fault=='retention':r['retained_input']=False
        if fault=='conflict':r['outputs']['request.json']='0'*64
        if fault=='proposal':r['trials'][0]['sha256']='0'*64
        if fault=='unbound':r['outputs'].pop('input.glb')
        save(folder/'result.json',r)
    with pytest.raises(ValueError):audit.bind_study(folder)
    assert not out.exists()


def test_completed_fixture_runner_archives_resources_checks_and_selection(study,monkeypatch):
    folder,out=study;engine=folder.parent/'fake-engine';engine.write_bytes(b'CPU fixture, not Godot')
    request,result,_=audit.bind_study(folder);cases,refs,rows=audit.prepare_cases(folder,request,result,out)
    frozen={str(p):sha256(p) for p in folder.rglob('*') if p.is_file()}
    def fake_execute(argv,**kw):
        actual=read(argv[-2]);assert len(actual['cases'])==5 and actual['authoring_seek']
        for case in actual['cases']:Path(case['native_animation_output']).write_bytes(b'explicit fixture resource')
        save(argv[-1],dict(engine=dict(test_fixture=True),cases=[observations(c,r) for c,r in zip(cases,refs)]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(audit.subprocess,'run',fake_execute)
    assert audit.run(folder,out,engine=engine)
    saved=read(out/'request.json');verification=read(out/'verification.json');result=read(out/'result.json')
    assert saved['inputs'][str(engine)]==sha256(engine)
    assert saved['fit_selected_trial']==read(folder/'result.json')['selected_trial']
    assert result['engine_pose_pass'] and not result['quality_approved'] and not result['selected_for_studio']
    assert not verification['gpu_skin_verified'] and len(verification['checks'])==5
    for p,digest in saved['inputs'].items():assert sha256(p)==digest
    for p,digest in result['outputs'].items():assert sha256(out/p)==digest
    assert all(sha256(p)==h for p,h in frozen.items())
    with pytest.raises(ValueError,match='Fresh'):audit.run(folder,out,engine=engine)


def test_changed_source_during_engine_execution_retains_failed_evidence(study,monkeypatch):
    folder,out=study;engine=folder.parent/'fake-engine';engine.write_bytes(b'fixture')
    q,r,_=audit.bind_study(folder);cases,refs,_=audit.prepare_cases(folder,q,r,out)
    def changed(argv,**kw):
        save(argv[-1],dict(engine=dict(test_fixture=True),cases=[observations(c,r) for c,r in zip(cases,refs)]))
        (folder/'trial-0.glb').write_bytes(b'changed')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(audit.subprocess,'run',changed)
    with pytest.raises(ValueError,match='changed'):audit.run(folder,out,engine=engine)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
    assert (out/'engine-output.json').exists()
