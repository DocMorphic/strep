"""Bounded, audited angular correction for completed contact-study exports."""
import argparse
import ast
import contextlib
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from strep import ROOT, read, save, sha256, now
from angular_source import audited_source
from verify_angular_release import angles
from study_branch_angular_release import prepare as prepare_trial, run as run_trial
from verify_projected_angular import run as audit_trial


def completed_files(source):
    completion=read(source/'completion.json')
    if read(source/'pipeline.json')['status']!='complete' or completion['request_sha256']!=sha256(source/'request.json'):
        raise ValueError('Source is incomplete or request binding changed')
    for name,digest in completion['files'].items():
        if sha256(source/name)!=digest:raise ValueError('Completed source artifact changed: '+name)
    return completion


def assess(source,audit):
    completed_files(source)
    decoded,_=audited_source(source,audit)
    if decoded['failed_full_checks']:
        return dict(eligible=False,failed_checks=decoded['failed_full_checks'])
    spec=read(source/'take/spec.json');request=read(source/'request.json')
    nodes=[j['node'] for j in spec['edit_joints'].values()]
    paths=[source/'take/input/character.glb',Path(request['prior'])/'candidate/character.glb',source/'take/candidate/character.glb']
    tracks=[angles(p,nodes,spec['frames'],spec['fps']) for p in paths]
    reference=np.maximum(tracks[0].max(axis=0),tracks[1].max(axis=0))+np.radians(1e-5)
    excess=np.degrees(np.maximum(tracks[2]-reference[None],0))
    if not np.isfinite(excess).all():raise ValueError('Nonfinite angular measurements')
    return dict(eligible=True,peaks_complete=bool(not excess.any()),excess_score=float(np.square(excess).sum()),
        failed_joints=[dict(role=role,peak_degrees=float(np.degrees(tracks[2][:,j]).max()),limit_degrees=float(np.degrees(reference[j]))) for j,role in enumerate(spec['edit_joints']) if excess[:,j].any()],
        completion_sha256=sha256(source/'completion.json'),audit_sha256=sha256(audit),candidate_sha256=sha256(paths[2]))


def correction_chain(source,audit,output,max_blocks,inspect,repair,checkpoint):
    """Keep last verified source when a proposal fails; never promote partial work."""
    if not isinstance(max_blocks,int) or isinstance(max_blocks,bool) or not 1<=max_blocks<=8:
        raise ValueError('max_blocks must be an integer from1 to8')
    output.mkdir(parents=True,exist_ok=False);history=[];current_source=source;current_audit=audit
    def finish(status,**extra):
        result=dict(at=now(),status=status,initial_source=str(source),initial_audit=str(audit),final_source=str(current_source),final_audit=str(current_audit),history=history,quality_approved=False,**extra)
        checkpoint();save(output/'completion.json',result);return result
    try:
        checkpoint();state=inspect(current_source,current_audit)
        if not state['eligible']:return finish('ineligible',assessment=state)
        if state['peaks_complete']:return finish('already_passed',assessment=state)
        for index in range(max_blocks):
            checkpoint();trial=output/f'block-{index+1:02d}';audit_dir=output/f'audit-{index+1:02d}'
            entry=dict(index=index+1,source=str(current_source),source_audit=str(current_audit),before=state,trial=str(trial),audit=str(audit_dir/'completion.json'),status='running')
            history.append(entry);save(output/'progress.json',dict(at=now(),history=history,quality_approved=False))
            repair(trial,current_source,current_audit,audit_dir)
            checkpoint();after=inspect(trial,audit_dir/'completion.json');entry['after']=after
            if not after['eligible']:
                entry['status']='rejected';return finish('preservation_failed',assessment=after)
            if not after['peaks_complete'] and state['excess_score']-after['excess_score']<=1e-10:
                entry['status']='no_progress';return finish('no_progress',assessment=after)
            current_source=trial;current_audit=audit_dir/'completion.json';state=after;entry['status']='verified'
            if state['peaks_complete']:return finish('numerical_pass',assessment=state)
        return finish('budget_exhausted',assessment=state)
    except Exception as exc:
        # Failed preparation/engine/audit artifacts remain in their original directories.
        if history and history[-1]['status']=='running':history[-1]['status']='failed'
        return finish('failed',error=str(exc),traceback=traceback.format_exc())


def implementation_closure(names):
    pending=set(names);found=set()
    while pending:
        name=pending.pop()
        if name in found:continue
        path=ROOT/'scripts'/name
        if not path.is_file():raise ValueError('Missing implementation '+name)
        found.add(name)
        if path.suffix!='.py':continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            imports=[alias.name for alias in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) and node.module else []
            for module in imports:
                dependency=module.split('.')[0]+'.py'
                if (ROOT/'scripts'/dependency).is_file():pending.add(dependency)
    return sorted(found)


def prepare(manifest,output):
    if output.exists():raise ValueError('Preserve prior chain')
    data=read(manifest);cases=data['cases'];budget=data['max_blocks']
    if type(budget) is not int or not 1<=budget<=8:raise ValueError('Invalid block budget')
    if not cases or len({c['id'] for c in cases})!=len(cases):raise ValueError('Nonempty unique case IDs required')
    names={'angular_chain.py','study_branch_angular_release.py','verify_projected_angular.py'};inputs={str(manifest):sha256(manifest)};normalized=[]
    for case in cases:
        if not case['id'].replace('-','').replace('_','').isalnum():raise ValueError('Case ID must be a simple directory name')
        source=(ROOT/case['source']).resolve();audit=(ROOT/case['audit']).resolve();completion=completed_files(source);request=read(source/'request.json')
        names.update(request['implementation']);inputs.update(request['inputs'])
        bindings=[source/'completion.json',source/'request.json',source/'envelope.json',source/'pipeline.json',audit,*[source/n for n in completion['files']]]
        certificate=read(audit)
        if 'inputs' in certificate:inputs.update(certificate['inputs'])
        for path in bindings:inputs[str(path)]=sha256(path)
        normalized.append(dict(id=case['id'],source=str(source),audit=str(audit)))
    for name,digest in inputs.items():
        if sha256(name)!=digest:raise ValueError('Input changed before freeze: '+name)
    dependencies=implementation_closure(names)
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in dependencies:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    protocol=dict(at=now(),cases=normalized,max_blocks=budget,inputs=inputs,implementation={p.name:sha256(p) for p in sorted((output/'implementation').iterdir())},quality_approved=False,
        scope='Bounded angular correction of completed audited contact-study exports only. No automatic root/contact repair, arbitrary-file intake, UI promotion or human approval. All declared cases retained, including ineligible and no-op cases.')
    save(output/'protocol.json',protocol);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')));save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False))


def run(output):
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve prior chain execution')
    protocol=read(output/'protocol.json');freeze=read(output/'freeze.json');owner=psutil.Process()
    save(output/'runner.json',dict(at=now(),pid=owner.pid,created=owner.create_time()))
    def checkpoint():
        if sha256(output/'protocol.json')!=freeze['protocol_sha256']:raise ValueError('Frozen chain protocol changed')
        for name,digest in protocol['inputs'].items():
            if sha256(name)!=digest:raise ValueError('Frozen chain input changed: '+name)
        for name,digest in protocol['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Frozen chain implementation changed: '+name)
    def repair(trial,source,audit,audit_dir):
        with (trial.parent/(trial.name+'.log')).open('w',encoding='utf8') as log,contextlib.redirect_stdout(log):
            prepare_trial(trial,source,audit);run_trial(trial);audit_trial(trial,audit_dir)
    rows=[]
    try:
        checkpoint()
        for case in protocol['cases']:
            save(output/'pipeline.json',dict(at=now(),status='running',case=case['id'],quality_approved=False));print('case',case['id'],flush=True)
            result=correction_chain(Path(case['source']),Path(case['audit']),output/'cases'/case['id'],protocol['max_blocks'],assess,repair,checkpoint)
            rows.append(dict(id=case['id'],status=result['status'],completion_sha256=sha256(output/'cases'/case['id']/'completion.json')))
            save(output/'results.json',dict(at=now(),rows=rows,planned=len(protocol['cases']),quality_approved=False));print(case['id'],result['status'],len(result['history']),flush=True)
        checkpoint();save(output/'completion.json',dict(at=now(),protocol_sha256=sha256(output/'protocol.json'),results_sha256=sha256(output/'results.json'),rows=rows,quality_approved=False))
        save(output/'pipeline.json',dict(at=now(),status='complete',quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);parser.add_argument('output',type=Path);parser.add_argument('--manifest',type=Path);args=parser.parse_args()
    if args.command=='prepare':
        if not args.manifest:parser.error('--manifest required')
        prepare(args.manifest.resolve(),args.output.resolve())
    else:run(args.output.resolve())
