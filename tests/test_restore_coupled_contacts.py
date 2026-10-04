"""Saved curves, fixed original limits and full geometry decide repair retention."""
from pathlib import Path
import sys
import os
import subprocess
import shutil
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import restore_coupled_contacts as flow
import action_worker_lock as locks
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_contact_norms import ContactNorms
from test_cumulative_coupled_contacts import fixture, independently_check
from test_native_contact_norms import prepared
from test_native_scene_geometry import policy as geometry_policy
from strep import read, save, sha256


def rejected_file(tmp_path, value=.001):
    path=tmp_path/'rejected.npy';np.save(path,[value,0.,0.]);return path


def to_value(target):
    def solve(system,jac,x,*args,**kwargs):
        return np.array([target,0.,0.])-x,dict(status='test-external-proposal')
    return solve


@pytest.mark.parametrize('fault',['nan','empty','dimensions','population'])
def test_invalid_repair_populations_cannot_authorize_progress(fault):
    current=np.array([.01,-1.]);after=np.array([.005,-1.]);before=np.array([1.,-.1]);contact=np.array([.9,-.05])
    if fault=='nan':after[0]=np.nan
    if fault=='empty':after=after[:0]
    if fault=='dimensions':after=after[None]
    if fault=='population':after=after[:1]
    with pytest.raises(ValueError):flow.repair_decision(current,after,before,contact)


@pytest.mark.parametrize('fault',['native-regression','individual-contact','native-stall'])
def test_each_guard_and_native_merit_must_pass_for_intermediate_repair(fault):
    current=np.array([.01,-1.]);after=np.array([.005,-1.]);before=np.array([1.,-.1]);contact=np.array([.9,-.05])
    if fault=='native-regression':after[0]=.01000000001
    if fault=='individual-contact':contact[-1]=1e-15
    if fault=='native-stall':after=current.copy()
    result=flow.repair_decision(current,after,before,contact)
    assert not result['provisional_repair_progress'] and not result['retained']


def test_eliminating_tiny_native_failure_is_progress_without_any_limit_slack():
    result=flow.repair_decision([1e-15,-1.],[0.,-1.],[1.,-.1],[.9,-.05])
    assert result['provisional_repair_progress'] and result['feasible_improved_motion']
    still_failed=flow.repair_decision([2e-15,-1.],[1e-15,-1.],[1.,-.1],[.9,-.05])
    assert not still_failed['feasible_improved_motion']


def test_native_feasibility_without_better_contact_is_not_retention_eligibility():
    result=flow.repair_decision([.1,-1.],[0.,-1.],[1.,-.1],[1.,-.1])
    assert result['provisional_repair_progress'] and not result['feasible_improved_motion']


def test_two_repair_origins_keep_one_feasible_reference_and_independent_complete_geometry(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);origins=[];references=[]
    original=flow.RecenteredCoupledContactModel.linearize
    def observe(self,x,worlds,baseline,anchor,*a,**k):
        origins.append(x.copy());references.append((baseline.copy(),{n:w.copy() for n,w in anchor.items()}))
        return original(self,x,worlds,baseline,anchor,*a,**k)
    monkeypatch.setattr(flow.RecenteredCoupledContactModel,'linearize',observe)
    def solve(system,jac,x,*a,**k):return to_value(.0005 if len(origins)==1 else 1e-7)(system,jac,x)
    monkeypatch.setattr(flow,'direction',solve);output=tmp_path/'out'
    result=flow.run(*paths,output,rejected_controls=rejected,iterations=2,backoffs=1)
    assert result['provisional_steps']==2 and result['retained_partial_improvement']
    assert result['rejected']['native_failed_rows']>0 and result['final']['native_pass']
    assert result['final']['surface_failed_rows']>0 and result['complete_geometry_pass']
    assert result['fixed_previous_contact_anchor'] and not result['rejected_pose_becomes_new_baseline']
    np.testing.assert_array_equal(references[0][0],references[1][0])
    for n in references[0][1]:np.testing.assert_array_equal(references[0][1][n],references[1][1][n])
    assert origins[0][0]==.001 and origins[1][0]==.0005
    first=read(output/'iteration-1/backoff-0/decision.json')
    assert first['provisional_repair_progress'] and not first['native_pass'] and not first['full_geometry_checked']
    assert not result['quality_approved'] and not result['release_approved'] and result['original_selected']
    independently_check(paths,output,result)
    for name,digest in result['files_sha256'].items():assert sha256(output/name)==digest


@pytest.mark.parametrize('hold',[False,True])
def test_partner_target_repair_rejects_unavailable_containment_and_preserves_partner(tmp_path,monkeypatch,hold):
    paths=fixture(tmp_path,monkeypatch);source,p,s,g=paths
    _,surface,digest=prepared(tmp_path,partner=True,hold=hold)
    permissions=read(p);permissions['contacts_sha256']=digest;save(p,permissions);save(s,surface)
    save(g,geometry_policy(source,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-10.))))
    rejected=tmp_path/'rejected.npy';np.save(rejected,[0.,0.,-.001])
    def solve(system,jac,x,*a,**k):return np.array([0.,0.,-1e-7])-x,dict(status='test-external-proposal')
    monkeypatch.setattr(flow,'direction',solve);output=tmp_path/'out'
    partner_before=read(source)['actors']['B'].copy()
    result=flow.run(*paths,output,rejected_controls=rejected,iterations=1,backoffs=1)
    assert result['provisional_steps']==1 and result['final']['native_pass']
    assert result['geometry_checked'] and not result['complete_geometry_pass']
    assert not result['retained_partial_improvement'] and result['baseline_fallback_preserved']
    for folder in ('baseline','rejected','iteration-1/backoff-0'):
        with np.load(output/folder/'conditions.npz',allow_pickle=False) as observations:
            assert 'world_A' in observations.files and 'world_B' in observations.files
    candidate=read(output/'candidate-contacts.json')
    assert candidate['actors']['B']['sha256']==partner_before['sha256']
    assert candidate['actors']['B']['placement']==partner_before['placement']
    assert sha256(candidate['actors']['B']['glb'])==partner_before['sha256']
    geometry=read(output/'geometry/geometry.json')
    for sample in geometry['samples']:
        pair=sample['actor_pairs'][0]
        assert pair['actors']==['A','B'] and not pair['passed']
        assert all(not row['available'] for row in pair['vertex_containment'])
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'),np.zeros(3))
    independently_check(paths,output,result)


def test_failed_geometry_preserves_trials_and_falls_back_to_nonzero_baseline(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch,unsafe_floor=True);rejected=rejected_file(tmp_path)
    baseline=tmp_path/'baseline.npy';np.save(baseline,[1e-7,0.,0.])
    monkeypatch.setattr(flow,'direction',to_value(2e-7));output=tmp_path/'out'
    result=flow.run(*paths,output,rejected_controls=rejected,baseline_controls=baseline,iterations=1)
    assert result['geometry_checked'] and not result['complete_geometry_pass'] and not result['retained_partial_improvement']
    assert result['baseline_fallback_preserved'] and result['provisional_steps']==1
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'),np.load(baseline))
    assert (output/'iteration-1/backoff-0/A.glb').exists()
    independently_check(paths,output,result)


def test_contact_regression_cannot_be_reanchored_to_rejected_pose(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path,-.001)
    monkeypatch.setattr(flow,'direction',to_value(-1e-7));output=tmp_path/'out'
    result=flow.run(*paths,output,rejected_controls=rejected,iterations=1,backoffs=1)
    decision=read(output/'iteration-1/backoff-0/decision.json')
    assert decision['native_pass'] and not decision['individual_baseline_contact_guard_pass']
    assert not decision['provisional_repair_progress'] and not result['geometry_checked']
    assert not result['retained_partial_improvement'] and result['provisional_steps']==0


def test_native_merit_improvement_remains_infeasible_without_geometry_or_retention(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path)
    monkeypatch.setattr(flow,'direction',to_value(.0005));output=tmp_path/'out'
    result=flow.run(*paths,output,rejected_controls=rejected,iterations=1,backoffs=1)
    assert result['provisional_steps']==1 and result['final']['native_failed_rows']>0
    assert not result['geometry_checked'] and not result['retained_partial_improvement']
    np.testing.assert_array_equal(np.load(output/'retained-controls.npy'),np.zeros(3))


def test_solver_timeout_cannot_invent_a_repaired_clip(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path)
    monkeypatch.setattr(flow,'direction',lambda *a,**k:(None,dict(status='MaxTime')))
    output=tmp_path/'out';result=flow.run(*paths,output,rejected_controls=rejected)
    assert result['provisional_steps']==0 and result['history'][0]['solver_status']=='MaxTime'
    assert not result['geometry_checked'] and not result['retained_partial_improvement']
    assert not (output/'geometry').exists() and (output/'rejected/A.glb').exists()


@pytest.mark.parametrize('baseline',[.001,-1e-7])
def test_invalid_native_or_original_contact_baseline_preserved_then_rejected(tmp_path,monkeypatch,baseline):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path)
    previous=tmp_path/'previous.npy';np.save(previous,[baseline,0.,0.]);output=tmp_path/'out'
    with pytest.raises(ValueError,match='Serialized baseline'):
        flow.run(*paths,output,rejected_controls=rejected,baseline_controls=previous)
    assert (output/'baseline/A.glb').exists() and read(output/'pipeline.json')['status']=='failed'
    assert not (output/'result.json').exists()


def test_feasible_origin_is_not_misreported_as_a_repair_experiment(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path,0.);output=tmp_path/'out'
    with pytest.raises(ValueError,match='fail native'):
        flow.run(*paths,output,rejected_controls=rejected)
    assert read(output/'pipeline.json')['status']=='failed' and (output/'rejected/A.glb').exists()


@pytest.mark.parametrize('value',[[2.,0.,0.],[np.nan,0.,0.],[0.,0.]])
def test_invalid_rejected_controls_reject_before_output(tmp_path,monkeypatch,value):
    paths=fixture(tmp_path,monkeypatch);rejected=tmp_path/'rejected.npy';np.save(rejected,value)
    with pytest.raises(ValueError):flow.run(*paths,tmp_path/'out',rejected_controls=rejected)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('name,value',[('iterations',0),('backoffs',11),('trust',True),('phase_seconds',301.),('maximum_logical_bytes',1)])
def test_invalid_settings_reject_before_acquisition(tmp_path,name,value):
    with pytest.raises(ValueError,match='bounded'):
        flow.run(*[tmp_path/'missing']*4,tmp_path/'out',rejected_controls=tmp_path/'missing',**{name:value})
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('target',['source','request','baseline-curve','source-copy','model','conditions'])
def test_altered_source_or_closed_observation_cannot_approve_repair(tmp_path,monkeypatch,target):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);output=tmp_path/'out'
    monkeypatch.setattr(flow,'direction',to_value(1e-7));mutated=[]
    def mutate(record):
        if record['stage']=='bounded-conic-proposal' and not mutated:
            candidates={'source':paths[1],'request':output/'request.json','baseline-curve':output/'baseline/A.glb',
                'source-copy':output/'source-contacts.json','model':output/'iteration-1/model.npz',
                'conditions':output/'baseline/conditions.npz'}
            path=candidates[target];path.write_bytes(path.read_bytes()+b' ');mutated.append(path)
    with pytest.raises(ValueError,match='changed'):
        flow.run(*paths,output,rejected_controls=rejected,progress=mutate)
    assert len(mutated)==1 and read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()


def test_source_rate_caps_cannot_be_reset_at_an_infeasible_origin(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);output=tmp_path/'out'
    original=flow.RecenteredCoupledContactModel.linearize
    def reset(self,*a,**k):
        self.problem.caps['A'].caps[0][0,0]+=1e-8
        return original(self,*a,**k)
    monkeypatch.setattr(flow.RecenteredCoupledContactModel,'linearize',reset)
    with pytest.raises(ValueError,match='source-rate'):flow.run(*paths,output,rejected_controls=rejected)
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()


def test_nonfinite_raw_direction_is_preserved_before_rejection(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);output=tmp_path/'out'
    monkeypatch.setattr(flow,'direction',lambda *a,**k:(np.array([np.nan,0.,0.]),dict(status='test-external-proposal')))
    with pytest.raises(ValueError):flow.run(*paths,output,rejected_controls=rejected)
    assert np.isnan(np.load(output/'iteration-1/raw-direction.npy')[0])
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()


def test_busy_worker_and_existing_output_are_not_overwritten(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);output=tmp_path/'out'
    with locks.worker_lock(),pytest.raises(RuntimeError,match='Another'):
        flow.run(*paths,output,rejected_controls=rejected)
    assert not output.exists()
    output.mkdir();(output/'sentinel').write_text('keep',encoding='utf-8')
    with pytest.raises(ValueError,match='Fresh'):flow.run(*paths,output,rejected_controls=rejected)
    assert (output/'sentinel').read_text(encoding='utf-8')=='keep'


def test_command_runs_actual_bounded_cpu_solver_without_assuming_success(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);rejected=rejected_file(tmp_path);output=tmp_path/'command'
    # The tiny fixture is a separate checkout. Its subprocess must not acquire
    # or bypass a running production checkout's worker lock.
    scripts=tmp_path/'command-source/scripts';scripts.mkdir(parents=True)
    for source in Path(flow.__file__).parent.glob('*.py'):shutil.copyfile(source,scripts/source.name)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    completed=subprocess.run([sys.executable,str(scripts/'restore_coupled_contacts.py'),*map(str,paths),str(output),
        '--rejected-controls',str(rejected),'--iterations','1','--phase-seconds','1','--maximum-iterations','30'],
        capture_output=True,text=True,env=env,timeout=90)
    assert completed.returncode==0,completed.stdout+completed.stderr
    result=read(output/'result.json');proposal=read(output/'iteration-1/proposal.json')
    assert result['status']=='complete' and result['history'][0]['solver_status']==proposal['status']
    assert proposal['phase_time_limit_seconds']==1. and proposal['phase_maximum_iterations']==30
    assert not result['quality_approved'] and not result['release_approved']
    if result['retained_partial_improvement']:independently_check(paths,output,result)
    else:np.testing.assert_array_equal(np.load(output/'retained-controls.npy'),np.zeros(3))
