"""A coverage attempt is not an approved motion or an adopted rejected state."""
import sys
from pathlib import Path
from contextlib import contextmanager,nullcontext
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import batch_contact_interval as module


def fixture(tmp_path,monkeypatch,*,first_rejected=False,elapsed_per_stage=0):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module.repair,'METHODS',['toy.py'])
    source=tmp_path/'source';source.mkdir();scripts=tmp_path/'scripts';scripts.mkdir()
    for name in ['toy.py','batch_contact_interval.py']:(scripts/name).write_text('immutable source')
    active=[];calls=[];clock=[0.]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    def stage(study,directory,frames,width,*args):
        assert active and study==source
        latest,excluded=args[-2:];windows=module.partition_frames(frames,width)
        block=next(w for w in windows if w not in excluded);calls.append((latest,excluded.copy(),block))
        directory.mkdir();result=dict(status='complete',selected_frames=block,decision=dict(update_retained=not(first_rejected and len(calls)==1),source_rows_preserved=True),
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


def test_admission_budget_keeps_complete_stage_and_remaining_failures_visible(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch,elapsed_per_stage=1300)
    result=module.run(source,tmp_path/'batch',list(range(6)),width=2,stages=3)
    assert len(calls)==1 and result['stop']=='admission_budget' and result['remaining_windows']==[[2,3],[4,5]]
    assert not result['coverage_schedule_exhausted'] and result['latest_retained_interval']=='batch/stage-1'


def test_rewritten_stage_result_is_detected_before_batch_publication(tmp_path,monkeypatch):
    source,calls,_=fixture(tmp_path,monkeypatch);stage=module.repair._run
    def corrupt(*args):
        result=stage(*args)
        if len(calls)==2:module.save(tmp_path/'batch/stage-1/result.json',{})
        return result
    monkeypatch.setattr(module.repair,'_run',corrupt)
    with pytest.raises(ValueError):module.run(source,tmp_path/'batch',list(range(4)),width=2)
    assert module.read(tmp_path/'batch/pipeline.json')['status']=='failed'
    before=(tmp_path/'batch/pipeline.json').read_bytes()
    with pytest.raises(FileExistsError):module.run(source,tmp_path/'batch',list(range(4)),width=2)
    assert (tmp_path/'batch/pipeline.json').read_bytes()==before


@pytest.mark.parametrize('options',[dict(stages=0),dict(stages=True),dict(stages=33),dict(seconds=True),dict(seconds=0),
    dict(max_seconds=599),dict(max_seconds=3601),dict(max_seconds=float('inf')),dict(iterations=0),dict(trust=True),dict(resume=False),dict(resume='')])
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
