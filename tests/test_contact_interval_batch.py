"""A coverage attempt is not an approved motion or an adopted rejected state."""
import sys
from pathlib import Path
from contextlib import contextmanager,nullcontext
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import batch_contact_interval as module


def pose_recovery(tmp_path,source,frames,width,parent,name='recovered'):
    from contact_candidate_recovery import SCHEMA,FILES
    directory=tmp_path/name;directory.mkdir()
    protocol=dict(schema=SCHEMA,source_study=source.relative_to(tmp_path).as_posix(),frames=frames,width=width,fps=30,
        interval_resume=dict(directory=parent.relative_to(tmp_path).as_posix(),result_sha256=module.sha256(parent/'result.json')),
        metadata_approved=False,quality_approved=False,release_approved=False)
    module.save(directory/'protocol.json',protocol)
    for filename in FILES:(directory/filename).write_text('bound toy geometry output')
    result=dict(status='complete',protocol_sha256=module.sha256(directory/'protocol.json'),interrupted_stage_complete=False,
        decision=dict(update_retained=True,source_rows_preserved=True),files_sha256={n:module.sha256(directory/n) for n in FILES},
        quality_approved=False,release_approved=False)
    module.save(directory/'result.json',result);module.save(directory/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    return directory


def test_pose_only_recovery_does_not_count_an_unfinished_window(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,first_rejected=True);frames=list(range(8))
    first=tmp_path/'first';module.run(source,first,frames,width=2,stages=2)
    recovered=pose_recovery(tmp_path,source,frames,2,first/'stage-2')
    attempted,bindings=module.batch_attempted_history(first,source,frames,2,recovered)
    assert attempted==[[0,1],[2,3]] and str(recovered/'retained-motion.npz') in bindings
    inferred,_=module.attempted_history(recovered,source,frames,2)
    assert inferred==attempted
    second=tmp_path/'second';result=module.run(source,second,frames,width=2,stages=1,resume=recovered,resume_batch=first)
    assert calls[-1][0]==recovered and calls[-1][2]==[4,5]
    assert result['attempted_windows']==[[0,1],[2,3],[4,5]]
    replayed,_=module.batch_attempted_history(second,source,frames,2,second/'stage-1')
    assert replayed==result['attempted_windows']


@pytest.mark.parametrize('change',['pose','completion','approval','clock','ancestor','cycle'])
def test_changed_recovery_cannot_bridge_completed_schedule(tmp_path,monkeypatch,change):
    source,_,_=fixture(tmp_path,monkeypatch);frames=list(range(8));first=tmp_path/'first'
    module.run(source,first,frames,width=2,stages=1)
    recovered=pose_recovery(tmp_path,source,frames,2,first/'stage-1')
    protocol=module.read(recovered/'protocol.json');result=module.read(recovered/'result.json')
    if change=='pose':(recovered/'retained-motion.npz').write_text('changed geometry')
    elif change=='completion':result['interrupted_stage_complete']=True
    elif change=='approval':result['quality_approved']=True
    elif change=='clock':protocol['fps']=60
    elif change=='ancestor':protocol['interval_resume']['result_sha256']='0'*64
    elif change=='cycle':protocol['interval_resume']['directory']='recovered'
    module.save(recovered/'protocol.json',protocol);result['protocol_sha256']=module.sha256(recovered/'protocol.json');module.save(recovered/'result.json',result)
    with pytest.raises(ValueError):module.batch_attempted_history(first,source,frames,2,recovered)


def fixture(tmp_path,monkeypatch,*,first_rejected=False,all_rejected=False,elapsed_per_stage=0):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module.repair,'METHODS',['toy.py'])
    source=tmp_path/'source';source.mkdir();scripts=tmp_path/'scripts';scripts.mkdir()
    for name in ['toy.py','batch_contact_interval.py']:(scripts/name).write_text('immutable source')
    active=[];calls=[];clock=[0.]
    @contextmanager
    def lock():
        active.append(True);owned_session.clear()
        try:yield
        finally:active.pop()
    owned_session=[]
    def stage(study,directory,frames,width,*args,replay_session=None,proposal_geometry_solver='supporting-planes'):
        assert active and study==source
        assert type(replay_session) is module.repair.IntervalReplaySession
        if owned_session:assert replay_session is owned_session[0]
        else:owned_session.append(replay_session)
        latest,excluded=args[-2:];windows=module.partition_frames(frames,width)
        block=next(w for w in windows if w not in excluded);calls.append((latest,excluded.copy(),block))
        directory.mkdir()
        protocol=dict(source_study='source',frames=frames,width=width,selected_frames=block,selection_exclusions=excluded.copy(),
            interval_resume=None if latest is None else dict(directory=latest.relative_to(tmp_path).as_posix(),result_sha256=module.sha256(latest/'result.json')),
            quality_approved=False,release_approved=False)
        module.save(directory/'protocol.json',protocol)
        module.save(directory/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
        result=dict(status='complete',protocol_sha256=module.sha256(directory/'protocol.json'),selected_frames=block,decision=dict(update_retained=not(all_rejected or (first_rejected and len(calls)==1)),source_rows_preserved=True),
            local_stop='iteration_limit',quality_approved=False,release_approved=False)
        module.save(directory/'result.json',result);clock[0]+=elapsed_per_stage
        return result
    monkeypatch.setattr(module,'worker_lock',lock);monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0]);monkeypatch.setattr(module.repair,'_run',stage)
    return source,calls,active


def test_complete_pass_holds_one_lock_and_carries_only_retained_states(tmp_path,monkeypatch):
    source,calls,active=fixture(tmp_path,monkeypatch,first_rejected=True)
    result=module.run(source,tmp_path/'batch',list(range(6)),width=2,stages=4)
    assert [c[2] for c in calls]==[[0,1],[2,3],[4,5]]
    assert calls[0][0] is None and calls[1][0] is None and calls[2][0]==tmp_path/'batch/stage-2'
    assert result['coverage_schedule_exhausted'] and result['stop']=='coverage_schedule_exhausted'
    assert result['latest_retained_interval']=='batch/stage-3' and not result['quality_approved'] and not result['release_approved']
    assert not active and module.read(tmp_path/'batch/stage-1/result.json')['decision']['update_retained'] is False


def test_private_matched_branches_can_share_an_owned_starting_history_session(tmp_path,monkeypatch):
    source,_,_=fixture(tmp_path,monkeypatch);session=module.repair.IntervalReplaySession()
    # The caller owns one lock and explicitly supplies the same session. Each
    # branch still starts from the same source/schedule, never the previous fit.
    with module.worker_lock():
        for index in range(2):
            result=module._run(source,tmp_path/('branch-'+str(index)),list(range(4)),2,None,1,300,8,.03,10,1800,replay_session=session)
            assert result['attempted_windows']==[[0,1]]


def test_private_batch_rejects_a_saved_or_unowned_session_before_writing(tmp_path,monkeypatch):
    source,_,_=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='Owned in-memory'):
        module._run(source,tmp_path/'branch',list(range(4)),2,None,1,300,8,.03,10,1800,replay_session={})
    assert not (tmp_path/'branch').exists()


def test_admission_budget_keeps_complete_stage_and_remaining_failures_visible(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,elapsed_per_stage=1300)
    result=module.run(source,tmp_path/'batch',list(range(6)),width=2,stages=3)
    assert len(calls)==1 and result['stop']=='admission_budget' and result['remaining_windows']==[[2,3],[4,5]]
    assert not result['coverage_schedule_exhausted'] and result['latest_retained_interval']=='batch/stage-1'


@pytest.mark.parametrize('solver',['supporting-planes','conic'])
def test_solver_choice_reaches_every_stage_and_preserves_rejected_state(tmp_path,monkeypatch,solver):
    source,calls,_=fixture(tmp_path,monkeypatch,first_rejected=True)
    original=module.repair._run;choices=[]
    def stage(*args,**kwargs):
        choices.append(kwargs.get('proposal_geometry_solver','supporting-planes'))
        assert ('proposal_geometry_solver' in kwargs)==(solver=='conic')
        return original(*args,**kwargs)
    monkeypatch.setattr(module.repair,'_run',stage)
    output=tmp_path/'batch'
    result=module.run(source,output,list(range(6)),width=2,stages=3,proposal_geometry_solver=solver)
    assert choices==[solver]*3 and calls[1][0] is None
    protocol=module.read(output/'protocol.json')
    if solver=='conic':assert protocol['proposal_geometry_solver']=='conic'
    else:assert 'proposal_geometry_solver' not in protocol
    assert not result['quality_approved'] and not result['release_approved']
    assert all(module.sha256(output/'implementation'/n)==h for n,h in protocol['methods_sha256'].items())


def test_rewritten_stage_result_is_detected_before_batch_publication(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch);stage=module.repair._run
    def corrupt(*args,**kwargs):
        result=stage(*args,**kwargs)
        if len(calls)==2:module.save(tmp_path/'batch/stage-1/result.json',{})
        return result
    monkeypatch.setattr(module.repair,'_run',corrupt)
    with pytest.raises(ValueError):module.run(source,tmp_path/'batch',list(range(4)),width=2)
    assert module.read(tmp_path/'batch/pipeline.json')['status']=='failed'
    before=(tmp_path/'batch/pipeline.json').read_bytes()
    with pytest.raises(FileExistsError):module.run(source,tmp_path/'batch',list(range(4)),width=2)
    assert (tmp_path/'batch/pipeline.json').read_bytes()==before


@pytest.mark.parametrize('options',[dict(stages=0),dict(stages=True),dict(stages=33),dict(seconds=True),dict(seconds=0),
    dict(max_seconds=599),dict(max_seconds=3601),dict(max_seconds=float('inf')),dict(iterations=0),dict(trust=True),dict(resume=False),dict(resume=''),
    dict(proposal_geometry_solver=None),dict(proposal_geometry_solver='unknown'),dict(proposal_geometry_solver=True),dict(resume_batch=False),dict(resume_batch='')])
def test_invalid_batch_never_acquires_worker(tmp_path,monkeypatch,options):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Invalid batch acquired worker'))
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/'batch',[1,2],**options)
    assert not (tmp_path/'batch').exists()


def test_ancestral_attempts_are_bound_and_deduplicated_without_quality_claims(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);source=tmp_path/'source';source.mkdir();first=tmp_path/'first';first.mkdir()
    p=dict(source_study='source',frames=list(range(4)),width=2,selected_frames=[0,1],selection_exclusions=[],quality_approved=False,release_approved=False)
    module.save(first/'protocol.json',p);module.save(first/'result.json',dict(status='complete',protocol_sha256=module.sha256(first/'protocol.json'),decision=dict(update_retained=True,source_rows_preserved=True),quality_approved=False,release_approved=False))
    module.save(first/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    excluded,bindings=module.attempted_history(first,source,list(range(4)),2)
    assert excluded==[[0,1]] and len(bindings)==3
    p['selected_frames']=[1,2];module.save(first/'protocol.json',p)
    r=module.read(first/'result.json');r['protocol_sha256']=module.sha256(first/'protocol.json');module.save(first/'result.json',r)
    with pytest.raises(ValueError):module.attempted_history(first,source,list(range(4)),2)


def test_rejected_only_batch_resumes_schedule_without_adopting_motion(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,all_rejected=True);frames=list(range(8))
    first=tmp_path/'first';module.run(source,first,frames,width=2,stages=2)
    attempted,bindings=module.batch_attempted_history(first,source,frames,2,None)
    assert attempted==[[0,1],[2,3]] and str(first/'result.json') in bindings
    second=tmp_path/'second';result=module.run(source,second,frames,width=2,stages=1,resume_batch=first)
    assert calls[-1][2]==[4,5] and all(c[0] is None for c in calls)
    assert result['latest_retained_interval'] is None and result['remaining_windows']==[[6,7]]
    protocol=module.read(second/'protocol.json')
    assert protocol['schedule_resume']==dict(directory='first',result_sha256=module.sha256(first/'result.json'))
    assert not result['quality_approved'] and not result['release_approved']
    third=tmp_path/'third';module.run(source,third,frames,width=2,stages=2,resume_batch=second)
    assert [c[2] for c in calls]==[[0,1],[2,3],[4,5],[6,7]]
    attempts,_=module.batch_attempted_history(third,source,frames,2,None)
    assert attempts==[[0,1],[2,3],[4,5],[6,7]]
    exhausted=module.run(source,tmp_path/'done',frames,width=2,resume_batch=third)
    assert exhausted['stop']=='coverage_schedule_exhausted' and exhausted['records']==[] and len(calls)==4


def test_mixed_batch_requires_exact_retained_resume_and_carries_failed_attempt(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,first_rejected=True);frames=list(range(8))
    first=tmp_path/'first';module.run(source,first,frames,width=2,stages=2)
    native=first/'stage-2'
    with pytest.raises(ValueError,match='native resume'):
        module.run(source,tmp_path/'wrong',frames,width=2,resume_batch=first)
    assert not (tmp_path/'wrong').exists() and len(calls)==2
    second=tmp_path/'second';result=module.run(source,second,frames,width=2,stages=1,resume=native,resume_batch=first)
    assert calls[-1][0]==native and calls[-1][2]==[4,5]
    assert result['attempted_windows']==[[0,1],[2,3],[4,5]]
    attempted,_=module.batch_attempted_history(second,source,frames,2,second/'stage-1')
    assert attempted==result['attempted_windows']


@pytest.mark.parametrize('change',['result_hash','pipeline','approval','scope','archive','record_bool','record_path',
    'attempts','remaining','latest','duplicate','exclusions','stage_resume','source_rows','input_binding'])
def test_corrupt_batch_schedule_never_skips_work_or_starts_native_fit(tmp_path,monkeypatch,change):
    source,calls,_=fixture(tmp_path,monkeypatch,first_rejected=True);frames=list(range(8))
    first=tmp_path/'first';module.run(source,first,frames,width=2,stages=2)
    protocol=module.read(first/'protocol.json');result=module.read(first/'result.json')
    stage=first/'stage-2';sp=module.read(stage/'protocol.json');sr=module.read(stage/'result.json')
    if change=='result_hash':result['records'][0]['result_sha256']='0'*64
    elif change=='pipeline':module.save(first/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    elif change=='approval':result['quality_approved']=True
    elif change=='scope':protocol['width']=3
    elif change=='archive':(first/'implementation/toy.py').write_text('changed')
    elif change=='record_bool':result['records'][0]['update_retained']=0
    elif change=='record_path':result['records'][0]['directory']='outside'
    elif change=='attempts':result['attempted_windows'].append([4,5])
    elif change=='remaining':result['remaining_windows']=[]
    elif change=='latest':result['latest_retained_interval']='first/stage-1'
    elif change=='duplicate':sp['selected_frames']=sr['selected_frames']=result['records'][1]['selected_frames']=[0,1]
    elif change=='exclusions':sp['selection_exclusions']=[]
    elif change=='stage_resume':sp['interval_resume']=dict(directory='first/stage-1',result_sha256=module.sha256(first/'stage-1/result.json'))
    elif change=='source_rows':sr['decision']['source_rows_preserved']=False
    elif change=='input_binding':protocol['scheduling_inputs_sha256']={str(source/'missing.json'):'0'*64}
    module.save(stage/'protocol.json',sp);sr['protocol_sha256']=module.sha256(stage/'protocol.json')
    module.save(stage/'result.json',sr);result['records'][1]['result_sha256']=module.sha256(stage/'result.json')
    module.save(first/'protocol.json',protocol);result['protocol_sha256']=module.sha256(first/'protocol.json');module.save(first/'result.json',result)
    with pytest.raises((ValueError,FileNotFoundError)):
        module.run(source,tmp_path/'next',frames,width=2,resume=stage,resume_batch=first)
    assert len(calls)==2 and not (tmp_path/'next').exists()


def test_rejected_schedule_changed_during_new_stage_is_not_published(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,all_rejected=True);frames=list(range(6))
    first=tmp_path/'first';module.run(source,first,frames,width=2,stages=1)
    original=module.repair._run
    def stage(*args,**kwargs):
        result=original(*args,**kwargs)
        module.save(first/'stage-1/result.json',{})
        return result
    monkeypatch.setattr(module.repair,'_run',stage)
    with pytest.raises(ValueError,match='history changed'):
        module.run(source,tmp_path/'next',frames,width=2,stages=1,resume_batch=first)
    assert module.read(tmp_path/'next/pipeline.json')['status']=='failed'
    assert not (tmp_path/'next/result.json').exists()


@pytest.mark.parametrize('change',['cycle','prior_digest','changed_scope','outside','initial','exhausted'])
def test_continuation_chain_rejects_corrupt_history(tmp_path,monkeypatch,change):
    source,calls,_=fixture(tmp_path,monkeypatch,all_rejected=True);frames=list(range(8))
    first=tmp_path/'first';second=tmp_path/'second'
    module.run(source,first,frames,width=2,stages=1)
    module.run(source,second,frames,width=2,stages=1,resume_batch=first)
    p=module.read(second/'protocol.json');r=module.read(second/'result.json')
    if change=='cycle':p['schedule_resume']['directory']='second'
    elif change=='prior_digest':p['schedule_resume']['result_sha256']='0'*64
    elif change=='changed_scope':p['frames']=[2,3,4,5,6,7,8,9]
    elif change=='outside':p['schedule_resume']['directory']='../outside'
    elif change=='initial':p['initial_exclusions']=[]
    elif change=='exhausted':r['coverage_schedule_exhausted']=True
    module.save(second/'protocol.json',p);r['protocol_sha256']=module.sha256(second/'protocol.json');module.save(second/'result.json',r)
    with pytest.raises(ValueError):module.run(source,tmp_path/'third',frames,width=2,resume_batch=second)
    assert len(calls)==2 and not (tmp_path/'third').exists()
