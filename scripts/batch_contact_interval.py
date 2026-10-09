"""Bounded failure-first coverage passes; attempted windows are never approvals."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from action_worker_lock import worker_lock
from contact_interval_coverage import partition_frames,select_window
import repair_contact_interval as repair


def attempted_history(directory,study,frames,width):
    """Bind schedule provenance; native state is fully replayed by each stage."""
    attempted=[];bindings={};seen=set();expected=None
    canonical=dict(ranked_windows=[dict(frames=w) for w in partition_frames(frames,width)])
    while directory is not None:
        directory=Path(directory).resolve()
        if not directory.is_relative_to(ROOT.resolve()) or directory in seen or len(seen)>=32:
            raise ValueError('Bound in-project acyclic scheduling history required')
        seen.add(directory);protocol=read(directory/'protocol.json');result=read(directory/'result.json');pipeline=read(directory/'pipeline.json')
        if (sha256(directory/'protocol.json')!=result['protocol_sha256'] or (expected is not None and sha256(directory/'result.json')!=expected)
                or protocol.get('source_study')!=study.relative_to(ROOT).as_posix() or protocol.get('frames')!=frames or protocol.get('width')!=width
                or result.get('status')!='complete' or pipeline.get('status')!='complete' or result.get('decision',{}).get('update_retained') is not True
                or result['decision'].get('source_rows_preserved') is not True
                or any(d.get(k) is not False for d in [protocol,result,pipeline] for k in ['quality_approved','release_approved'])):
            raise ValueError('Retained original-source interval schedule with identical scope required')
        candidates=protocol.get('selection_exclusions',[])+[protocol['selected_frames']]
        for block in candidates:
            select_window(frames,canonical,width,[block])
            if block not in attempted:attempted.append(block.copy())
        for name in ['protocol.json','result.json','pipeline.json']:bindings[str(directory/name)]=sha256(directory/name)
        prior=protocol.get('interval_resume');directory=ROOT/prior['directory'] if prior is not None else None
        expected=prior['result_sha256'] if prior is not None else None
    return attempted,bindings


def _run(study,output,frames,width,resume,stages,seconds,iterations,trust,solve_iterations,max_seconds):
    exclusions,bindings=attempted_history(resume,study,frames,width) if resume is not None else ([],{})
    windows=partition_frames(frames,width);canonical=dict(ranked_windows=[dict(frames=w) for w in windows])
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    methods=repair.METHODS+['batch_contact_interval.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    method_hashes={name:sha256(archive/name) for name in methods}
    protocol=dict(at=now(),source_study=study.relative_to(ROOT).as_posix(),frames=frames,width=width,
        resume=None if resume is None else resume.relative_to(ROOT).as_posix(),initial_exclusions=exclusions.copy(),
        scheduling_inputs_sha256=bindings,methods_sha256=method_hashes,max_stages=stages,
        local_fit_seconds=seconds,iterations=iterations,trust_normalized=trust,proposal_solve_iterations=solve_iterations,
        admission_budget_seconds=max_seconds,minimum_admission_seconds=seconds+300,
        history_reuse_policy='same-worker-last-verified-state-bindings-v1',
        scope='An attempted-window coverage pass; newly seen states receive full native replay, and previously verified ancestors can be reused within this worker after complete binding checks. Original retention gates remain unchanged. Admission budget is checked between stages; use an owned hard time/memory supervisor. No quality, metadata, engine or human approval.',quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    started=time.monotonic();records=[];latest=resume;stop='stage_limit';replay_session=repair.IntervalReplaySession()
    for index in range(stages):
        if select_window(frames,canonical,width,exclusions) is None:stop='coverage_schedule_exhausted';break
        if max_seconds-(time.monotonic()-started)<seconds+300:stop='admission_budget';break
        directory=output/('stage-'+str(index+1))
        result=repair._run(study,directory,frames,width,iterations,trust,seconds,solve_iterations,latest,exclusions.copy(),replay_session=replay_session)
        if (result.get('status')!='complete' or any(result.get(k) is not False for k in ['quality_approved','release_approved'])
                or result['selected_frames'] in exclusions):raise ValueError('Complete unapproved new-window diagnostic required')
        block=result['selected_frames'];select_window(frames,canonical,width,[block]);exclusions.append(block.copy())
        # A rejected diagnostic cannot become the starting state for another fit.
        if result['decision']['update_retained']:
            if result['decision']['source_rows_preserved'] is not True:raise ValueError('Original-source preservation required')
            latest=directory
        records.append(dict(directory=directory.relative_to(ROOT).as_posix(),result_sha256=sha256(directory/'result.json'),
            selected_frames=block,update_retained=result['decision']['update_retained'],local_stop=result['local_stop']))
        save(output/'progress.json',dict(status='processing',records=records,attempted_windows=exclusions,
            latest_retained_interval=None if latest is None else latest.relative_to(ROOT).as_posix(),history_reuse=replay_session.statistics(),quality_approved=False,release_approved=False))
        print(dict(stage='batch_retained' if result['decision']['update_retained'] else 'batch_rejected',index=index+1,frames=block),flush=True)
    remaining=[w for w in windows if w not in exclusions]
    if any(sha256(Path(path))!=digest for path,digest in bindings.items()):raise ValueError('Bound scheduling history changed')
    if any(sha256(ROOT/'scripts'/name)!=digest or sha256(archive/name)!=digest for name,digest in method_hashes.items()):raise ValueError('Batch implementation changed')
    for record in records:
        if sha256(ROOT/record['directory']/'result.json')!=record['result_sha256']:raise ValueError('Completed batch stage changed')
    result=dict(at=now(),status='complete',stop=stop,seconds=time.monotonic()-started,records=records,
        attempted_windows=exclusions,remaining_windows=remaining,coverage_schedule_exhausted=not remaining,
        latest_retained_interval=None if latest is None else latest.relative_to(ROOT).as_posix(),protocol_sha256=sha256(output/'protocol.json'),
        scope=protocol['scope'],history_reuse=replay_session.statistics(),quality_approved=False,release_approved=False)
    save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    return result


def run(study,output,frames,*,width=3,resume=None,stages=3,seconds=300,iterations=8,trust=.03,solve_iterations=10,max_seconds=1800):
    partition_frames(frames,width)
    if (type(stages) is not int or not 1<=stages<=32 or type(iterations) is not int or not 1<=iterations<=100
            or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 1<=seconds<=1800
            or type(max_seconds) not in [int,float] or not np.isfinite(max_seconds) or not seconds+300<=max_seconds<=3600
            or type(trust) not in [int,float] or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or (resume is not None and (not isinstance(resume,(str,Path)) or not str(resume)))):
        raise ValueError('Explicit guarded stage and between-stage admission budgets required')
    study=Path(study).resolve();output=Path(output).resolve();resume=Path(resume).resolve() if resume is not None else None
    inputs=[study]+([resume] if resume is not None else [])
    if any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output]) or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs):
        raise ValueError('Separate immutable in-project batch sources and output required')
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=2):
        try:return _run(study,output,frames,width,resume,stages,seconds,iterations,trust,solve_iterations,max_seconds)
        except Exception as exc:
            if output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output')
    parser.add_argument('--start',type=int,required=True);parser.add_argument('--end',type=int,required=True)
    parser.add_argument('--resume-interval',type=Path);parser.add_argument('--width',type=int,default=3)
    parser.add_argument('--stages',type=int,default=3);parser.add_argument('--max-seconds',type=float,default=1800)
    parser.add_argument('--seconds',type=float,default=300);parser.add_argument('--iterations',type=int,default=8)
    parser.add_argument('--trust',type=float,default=.03);parser.add_argument('--solve-iterations',type=int,default=10);args=parser.parse_args()
    run(args.study,args.output,list(range(args.start,args.end+1)),width=args.width,resume=args.resume_interval,stages=args.stages,
        max_seconds=args.max_seconds,seconds=args.seconds,iterations=args.iterations,trust=args.trust,solve_iterations=args.solve_iterations)
