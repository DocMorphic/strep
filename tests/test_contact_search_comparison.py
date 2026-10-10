"""Search comparisons cannot change the saved origin or physical acceptance gates."""
import sys,json
from pathlib import Path
from contextlib import contextmanager,nullcontext
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import compare_contact_search as module


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    for name in ['source','resume','schedule','scripts']:(tmp_path/name).mkdir()
    (tmp_path/'resume/result.json').write_text('bound starting result')
    methods=['toy.py','batch_contact_interval.py','compare_contact_search.py']+module.RESOURCE_METHODS
    for name in methods:(tmp_path/'scripts'/name).write_text('immutable worker code')
    monkeypatch.setattr(module.batch.repair,'METHODS',['toy.py'])
    monkeypatch.setattr(module.batch,'batch_attempted_history',lambda *args:([[0,1]],{}))
    active=[];sessions=[];calls=[]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    monkeypatch.setattr(module,'worker_lock',lock)
    monkeypatch.setattr(module,'threadpool_limits',lambda **kw:nullcontext())
    def batch(study,directory,frames,width,resume,stages,seconds,iterations,trust,solve,max_seconds,**kw):
        assert active and stages==1 and resume==tmp_path/'resume'
        assert kw['resume_batch']==tmp_path/'schedule' and kw['proposal_geometry_solver']=='conic'
        session=kw['replay_session'];sessions.append(session);calls.append((trust,seconds,iterations,solve))
        stage=directory/'stage-1';stage.mkdir(parents=True)
        protocol={name:'identical original '+name for name in module.SAME_FIELDS}
        protocol.update(frames=frames,width=width,fps=30,selected_frames=[2,3],selection_exclusions=[[0,1]],
            interval_resume=dict(directory='resume',result_sha256=module.sha256(resume/'result.json')),
            trust_normalized=trust,metadata_approved=False,quality_approved=False,release_approved=False)
        module.save(stage/'protocol.json',protocol)
        np.savez_compressed(stage/'baseline-motion.npz',root_positions=np.zeros((4,3),np.float64))
        module.save(stage/'baseline.json',dict(physical_contact_keys_passed=False,complete_keyed_rows_passed=False,
            per_frame_physical=[dict(frame=f,pose_checks_passed=False) for f in frames],frames=[dict(frame=f,keyed_rows_passed=False) for f in frames]))
        module.save(stage/'proposed.json',dict(physical_contact_keys_passed=False,complete_keyed_rows_passed=False,
            per_frame_physical=[dict(frame=f,pose_checks_passed=f<2) for f in frames],frames=[dict(frame=f,keyed_rows_passed=f<2) for f in frames]))
        module.save(stage/'row-diagnostics.json',dict(rows=[dict(label='original',initial_slack=-1.,final_slack=-.5)]))
        for filename in ['proposed-motion.npz','retained-motion.npz']:
            np.savez_compressed(stage/filename,root_positions=np.zeros((4,3),np.float64))
        module.save(stage/'preflight.json',{})
        record=dict(status='complete',selected_frames=[2,3],decision=dict(update_retained=trust>.03,source_rows_preserved=True),
            local_stop='iteration_limit',fit=dict(seconds=.2),protocol_sha256=module.sha256(stage/'protocol.json'),
            files_sha256={n:module.sha256(stage/n) for n in module.FILES},
            quality_approved=False,release_approved=False)
        module.save(stage/'result.json',record);module.save(stage/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
        module.save(directory/'result.json',dict(status='complete',records=[dict(directory=stage.relative_to(tmp_path).as_posix(),result_sha256=module.sha256(stage/'result.json'))],
            quality_approved=False,release_approved=False))
    monkeypatch.setattr(module.batch,'_run',batch)
    args=[tmp_path/'source',tmp_path/'comparison',list(range(4)),tmp_path/'resume',tmp_path/'schedule']
    return args,calls,sessions,active


def test_two_branches_share_only_starting_history_and_keep_distinct_retention(tmp_path,monkeypatch):
    args,calls,sessions,active=fixture(tmp_path,monkeypatch)
    result=module.run(*args)
    assert calls==[(.03,300,8,10),(.1,300,8,10)] and sessions[0] is sessions[1]
    assert type(sessions[0]) is module.batch.repair.IntervalReplaySession
    assert not active and result['selected_branch'] is None and result['matched_start_and_original_limits']
    assert result['records'][0]['retained_physical_contact_keys_passed']==0
    assert result['records'][0]['retained_squared_violation']==1.
    assert result['records'][1]['retained_physical_contact_keys_passed']==2
    assert result['records'][1]['retained_all_physical_contact_keys_passed'] is False
    assert result['records'][1]['retained_squared_violation']==.25
    assert result['quality_approved'] is False and result['release_approved'] is False


def reseal(stage):
    r=module.read(stage/'result.json');r['protocol_sha256']=module.sha256(stage/'protocol.json')
    for n in r['files_sha256']:r['files_sha256'][n]=module.sha256(stage/n)
    module.save(stage/'result.json',r)
    parent=module.read(stage.parent/'result.json');parent['records'][0]['result_sha256']=module.sha256(stage/'result.json');module.save(stage.parent/'result.json',parent)


@pytest.mark.parametrize('change',['limit','origin','dtype','rows','initial_slack','selection','ancestry','budget','approval'])
def test_resealed_mismatch_cannot_be_called_a_matched_experiment(tmp_path,monkeypatch,change):
    args,_,_,_=fixture(tmp_path,monkeypatch);original=module.batch._run
    def altered(*a,**kw):
        original(*a,**kw)
        if a[8]!=.1:return
        stage=a[1]/'stage-1';protocol=module.read(stage/'protocol.json')
        if change=='limit':protocol['original_limits']='relaxed constraints'
        elif change=='selection':protocol['selected_frames']=[0,1]
        elif change=='ancestry':protocol['interval_resume']['result_sha256']='0'*64
        elif change=='budget':protocol['seconds']=999
        elif change=='approval':protocol['quality_approved']=True
        elif change in ['origin','dtype']:
            np.savez_compressed(stage/'baseline-motion.npz',root_positions=np.ones((4,3),np.float64) if change=='origin' else np.zeros((4,3),np.float32))
        else:
            d=module.read(stage/'row-diagnostics.json');d['rows'][0]['label' if change=='rows' else 'initial_slack']='replacement row' if change=='rows' else -.8
            module.save(stage/'row-diagnostics.json',d)
        module.save(stage/'protocol.json',protocol);reseal(stage)
    monkeypatch.setattr(module.batch,'_run',altered)
    with pytest.raises((ValueError,AssertionError)):module.run(*args)
    assert module.read(args[1]/'pipeline.json')['status']=='failed' and not (args[1]/'result.json').exists()
    assert (args[1]/'branch-1/result.json').exists()


@pytest.mark.parametrize('options',[dict(trusts=[.03]),dict(trusts=[.03,.03]),dict(trusts=[.03,True]),dict(trusts=[.03,float('nan')]),
    dict(trusts=[.03,.31]),dict(seconds=True),dict(iterations=False),dict(solve_iterations=0),dict(max_seconds=1)])
def test_invalid_comparison_never_acquires_a_worker(tmp_path,monkeypatch,options):
    args,_,_,_=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Invalid comparison acquired worker'))
    with pytest.raises(ValueError):module.run(*args,**options)
    assert not args[1].exists()


def test_completed_comparison_is_immutable(tmp_path,monkeypatch):
    args,_,_,_=fixture(tmp_path,monkeypatch);module.run(*args);before=(args[1]/'result.json').read_bytes()
    with pytest.raises(FileExistsError):module.run(*args)
    assert (args[1]/'result.json').read_bytes()==before


def test_changed_input_during_second_branch_rejects_final_comparison(tmp_path,monkeypatch):
    args,_,_,_=fixture(tmp_path,monkeypatch);original=module.batch._run
    def altered(*a,**kw):
        original(*a,**kw)
        if a[8]==.1:(tmp_path/'scripts/toy.py').write_text('changed implementation')
    monkeypatch.setattr(module.batch,'_run',altered)
    with pytest.raises(ValueError,match='methods'):module.run(*args)
    assert not (args[1]/'result.json').exists()


def test_missing_pose_output_cannot_complete_a_comparison(tmp_path,monkeypatch):
    args,_,_,_=fixture(tmp_path,monkeypatch);original=module.batch._run
    def altered(*a,**kw):
        original(*a,**kw)
        stage=a[1]/'stage-1';record=module.read(stage/'result.json');record['files_sha256'].pop('retained-motion.npz')
        module.save(stage/'result.json',record);parent=module.read(stage.parent/'result.json')
        parent['records'][0]['result_sha256']=module.sha256(stage/'result.json');module.save(stage.parent/'result.json',parent)
    monkeypatch.setattr(module.batch,'_run',altered)
    with pytest.raises(ValueError,match='immutable'):module.run(*args)
