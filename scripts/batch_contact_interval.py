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


def recovered_schedule_parent(directory,study,frames,width,bindings):
    """Bind a pose-only recovery; it contributes no completed window attempt."""
    from contact_candidate_recovery import SCHEMA,FILES
    root=ROOT.resolve();directory=Path(directory).resolve()
    def bind(path,expected=None):
        path=Path(path).resolve()
        if not path.is_relative_to(root):raise ValueError('In-project recovery schedule required')
        digest=sha256(path)
        if expected is not None and digest!=expected:raise ValueError('Recovery scheduling binding changed')
        if str(path) in bindings and bindings[str(path)]!=digest:raise ValueError('Recovery scheduling input changed')
        bindings[str(path)]=digest
        return digest
    protocol=read(directory/'protocol.json');result=read(directory/'result.json');pipeline=read(directory/'pipeline.json')
    if (protocol.get('schema')!=SCHEMA or protocol.get('source_study')!=study.relative_to(root).as_posix()
            or protocol.get('frames')!=frames or protocol.get('width')!=width or protocol.get('fps')!=30
            or protocol.get('metadata_approved') is not False or result.get('interrupted_stage_complete') is not False
            or result.get('status')!='complete' or pipeline.get('status')!='complete'
            or result.get('decision',{}).get('update_retained') is not True or result['decision'].get('source_rows_preserved') is not True
            or any(d.get(k) is not False for d in [protocol,result,pipeline] for k in ['quality_approved','release_approved'])
            or set(result.get('files_sha256',{}))!=FILES):
        raise ValueError('Complete unapproved pose-only recovery required for scheduling')
    bind(directory/'protocol.json',result['protocol_sha256'])
    for name in ['result.json','pipeline.json']:bind(directory/name)
    for name,digest in result['files_sha256'].items():bind(directory/name,digest)
    prior=protocol.get('interval_resume')
    if not isinstance(prior,dict) or not isinstance(prior.get('directory'),str):raise ValueError('Original recovery ancestor required')
    parent=(root/prior['directory']).resolve();bind(parent/'result.json',prior['result_sha256'])
    return parent


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
        if protocol.get('schema')=='strep-saved-contact-candidate-recovery-v1':
            directory=recovered_schedule_parent(directory,study,frames,width,bindings)
            expected=protocol['interval_resume']['result_sha256']
            continue
        candidates=protocol.get('selection_exclusions',[])+[protocol['selected_frames']]
        for block in candidates:
            select_window(frames,canonical,width,[block])
            if block not in attempted:attempted.append(block.copy())
        for name in ['protocol.json','result.json','pipeline.json']:bindings[str(directory/name)]=sha256(directory/name)
        prior=protocol.get('interval_resume');directory=ROOT/prior['directory'] if prior is not None else None
        expected=prior['result_sha256'] if prior is not None else None
    return attempted,bindings


def batch_attempted_history(directory,study,frames,width,resume):
    """Replay completed schedules separately from retained native motion.

    Rejected stages count as attempts, never as pose initialization. This checks
    saved scheduling provenance; a new native stage still replays its motion.
    """
    root=ROOT.resolve();seen=set();bindings={}
    windows=partition_frames(frames,width);canonical=dict(ranked_windows=[dict(frames=w) for w in windows])
    def path(value):
        if not isinstance(value,(str,Path)) or not str(value):raise ValueError('Bound in-project schedule path required')
        p=(root/ value).resolve()
        if not p.is_relative_to(root):raise ValueError('Bound in-project schedule path required')
        return p
    def bind(p):
        digest=sha256(p)
        if str(p) in bindings and bindings[str(p)]!=digest:raise ValueError('Scheduling input changed during replay')
        bindings[str(p)]=digest
        return digest
    def completed(p):
        protocol=read(p/'protocol.json');result=read(p/'result.json');pipeline=read(p/'pipeline.json')
        if (bind(p/'protocol.json')!=result.get('protocol_sha256') or result.get('status')!='complete'
                or pipeline.get('status')!='complete' or protocol.get('source_study')!=study.relative_to(root).as_posix()
                or protocol.get('frames')!=frames or protocol.get('width')!=width
                or any(d.get(k) is not False for d in [protocol,result,pipeline] for k in ['quality_approved','release_approved'])):
            raise ValueError('Complete unapproved original-scope schedule required')
        for name in ['result.json','pipeline.json']:bind(p/name)
        return protocol,result
    def bridge(current,target):
        walked=set()
        while current!=target:
            if current is None or current in walked or len(walked)>=32:
                raise ValueError('Explicit native resume must match completed batch through bound pose-only recovery')
            walked.add(current)
            if read(current/'protocol.json').get('schema')!='strep-saved-contact-candidate-recovery-v1':
                raise ValueError('Explicit native resume must match completed batch through bound pose-only recovery')
            current=recovered_schedule_parent(current,study,frames,width,bindings)
    def visit(p,expected=None):
        if p in seen or len(seen)>=32:raise ValueError('Bound acyclic batch scheduling history required')
        seen.add(p);protocol,result=completed(p)
        if expected is not None and bind(p/'result.json')!=expected:raise ValueError('Prior batch result changed')
        latest=path(protocol['resume']) if protocol.get('resume') is not None else None
        prior=protocol.get('schedule_resume')
        if prior is not None:
            attempted,prior_latest=visit(path(prior['directory']),prior['result_sha256'])
            bridge(latest,prior_latest)
        else:
            attempted,native_bindings=attempted_history(latest,study,frames,width) if latest is not None else ([],{})
            for name,digest in native_bindings.items():
                if bind(path(name))!=digest:raise ValueError('Native scheduling history changed')
        if protocol.get('initial_exclusions')!=attempted:raise ValueError('Initial schedule must replay exactly')
        for name,digest in protocol.get('scheduling_inputs_sha256',{}).items():
            if bind(path(name))!=digest:raise ValueError('Recorded scheduling input changed')
        methods=protocol.get('methods_sha256')
        if not isinstance(methods,dict) or not methods:raise ValueError('Archived batch implementation required')
        for name,digest in methods.items():
            if Path(name).name!=name or bind(p/'implementation'/name)!=digest:raise ValueError('Archived batch implementation changed')
        records=result.get('records')
        if (not isinstance(records,list) or type(protocol.get('max_stages')) is not int
                or not 1<=protocol['max_stages']<=32 or len(records)>protocol['max_stages']):
            raise ValueError('Bounded complete batch records required')
        for index,record in enumerate(records,1):
            stage=path(record['directory'])
            if stage!=p/('stage-'+str(index)):raise ValueError('Ordered owned batch stages required')
            sp,sr=completed(stage);block=sr.get('selected_frames');decision=sr.get('decision',{})
            select_window(frames,canonical,width,[block])
            if (bind(stage/'result.json')!=record.get('result_sha256') or block in attempted
                    or sp.get('selected_frames')!=block or record.get('selected_frames')!=block
                    or sp.get('selection_exclusions')!=attempted or type(decision.get('update_retained')) is not bool
                    or record.get('update_retained') is not decision['update_retained']
                    or sr.get('local_stop')!=record.get('local_stop')):
                raise ValueError('Each attempt must replay its bound stage and preceding exclusions')
            interval=sp.get('interval_resume')
            if latest is None:
                if interval is not None:raise ValueError('Unexpected native interval resume')
            elif (interval is None or path(interval['directory'])!=latest
                    or bind(latest/'result.json')!=interval['result_sha256']):
                raise ValueError('Stage must resume the last retained native state')
            attempted.append(block.copy())
            if decision['update_retained']:
                if decision.get('source_rows_preserved') is not True:raise ValueError('Retained source preservation required')
                latest=stage
        remaining=[w for w in windows if w not in attempted]
        saved_latest=path(result['latest_retained_interval']) if result.get('latest_retained_interval') is not None else None
        if (result.get('attempted_windows')!=attempted or result.get('remaining_windows')!=remaining
                or result.get('coverage_schedule_exhausted') is not (not remaining) or saved_latest!=latest):
            raise ValueError('Final attempted coverage and retained state must reconstruct exactly')
        return attempted,latest
    attempted,latest=visit(path(directory))
    bridge(resume,latest)
    if any(sha256(Path(name))!=digest for name,digest in bindings.items()):raise ValueError('Scheduling history changed')
    return attempted,bindings


def _run(study,output,frames,width,resume,stages,seconds,iterations,trust,solve_iterations,max_seconds,*,proposal_geometry_solver='supporting-planes',resume_batch=None,replay_session=None):
    if replay_session is not None and type(replay_session) is not repair.IntervalReplaySession:
        raise ValueError('Owned in-memory interval replay session required')
    if resume_batch is not None:exclusions,bindings=batch_attempted_history(resume_batch,study,frames,width,resume)
    else:exclusions,bindings=attempted_history(resume,study,frames,width) if resume is not None else ([],{})
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
    if proposal_geometry_solver!='supporting-planes':protocol['proposal_geometry_solver']=proposal_geometry_solver
    if resume_batch is not None:protocol['schedule_resume']=dict(directory=resume_batch.relative_to(ROOT).as_posix(),result_sha256=bindings[str(resume_batch/'result.json')])
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    started=time.monotonic();records=[];latest=resume;stop='stage_limit';replay_session=repair.IntervalReplaySession() if replay_session is None else replay_session
    for index in range(stages):
        if select_window(frames,canonical,width,exclusions) is None:stop='coverage_schedule_exhausted';break
        if max_seconds-(time.monotonic()-started)<seconds+300:stop='admission_budget';break
        directory=output/('stage-'+str(index+1))
        options={} if proposal_geometry_solver=='supporting-planes' else dict(proposal_geometry_solver=proposal_geometry_solver)
        result=repair._run(study,directory,frames,width,iterations,trust,seconds,solve_iterations,latest,exclusions.copy(),replay_session=replay_session,**options)
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


def run(study,output,frames,*,width=3,resume=None,stages=3,seconds=300,iterations=8,trust=.03,solve_iterations=10,max_seconds=1800,proposal_geometry_solver='supporting-planes',resume_batch=None):
    partition_frames(frames,width)
    if (type(stages) is not int or not 1<=stages<=32 or type(iterations) is not int or not 1<=iterations<=100
            or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 1<=seconds<=1800
            or type(max_seconds) not in [int,float] or not np.isfinite(max_seconds) or not seconds+300<=max_seconds<=3600
            or type(trust) not in [int,float] or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or (resume is not None and (not isinstance(resume,(str,Path)) or not str(resume)))
            or (resume_batch is not None and (not isinstance(resume_batch,(str,Path)) or not str(resume_batch)))
            or proposal_geometry_solver not in ['supporting-planes','conic']):
        raise ValueError('Explicit guarded stage and between-stage admission budgets required')
    study=Path(study).resolve();output=Path(output).resolve();resume=Path(resume).resolve() if resume is not None else None
    resume_batch=Path(resume_batch).resolve() if resume_batch is not None else None
    inputs=[study]+([resume] if resume is not None else [])+([resume_batch] if resume_batch is not None else [])
    if any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output]) or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs):
        raise ValueError('Separate immutable in-project batch sources and output required')
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=2):
        try:
            options={} if proposal_geometry_solver=='supporting-planes' else dict(proposal_geometry_solver=proposal_geometry_solver)
            if resume_batch is not None:options['resume_batch']=resume_batch
            return _run(study,output,frames,width,resume,stages,seconds,iterations,trust,solve_iterations,max_seconds,**options)
        except Exception as exc:
            if output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output')
    parser.add_argument('--start',type=int,required=True);parser.add_argument('--end',type=int,required=True)
    parser.add_argument('--resume-interval',type=Path);parser.add_argument('--width',type=int,default=3)
    parser.add_argument('--resume-batch',type=Path,help='Completed attempted-window schedule; kept separate from retained motion')
    parser.add_argument('--stages',type=int,default=3);parser.add_argument('--max-seconds',type=float,default=1800)
    parser.add_argument('--seconds',type=float,default=300);parser.add_argument('--iterations',type=int,default=8)
    parser.add_argument('--trust',type=float,default=.03);parser.add_argument('--solve-iterations',type=int,default=10)
    parser.add_argument('--proposal-geometry-solver',choices=['supporting-planes','conic'],default='supporting-planes');args=parser.parse_args()
    run(args.study,args.output,list(range(args.start,args.end+1)),width=args.width,resume=args.resume_interval,stages=args.stages,
        max_seconds=args.max_seconds,seconds=args.seconds,iterations=args.iterations,trust=args.trust,solve_iterations=args.solve_iterations,proposal_geometry_solver=args.proposal_geometry_solver,resume_batch=args.resume_batch)
