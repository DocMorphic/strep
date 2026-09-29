"""Test original root-peak restoration inside the unchanged root-only model."""
import argparse
import copy
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from study_breadth_root_cleanup import BreadthProblem,support_audit,snapshot
from authored_root_correction import export,verify
from verify_authored_root_correction import inspect,samples
from audit_authoring_intent import check_files


class PeakProblem(BreadthProblem):
    def additional_constraints(self,linear,norm,equal):
        counts=super().additional_constraints(linear,norm,equal)
        _,raw=samples(self.folder/'input/character.glb',self.frames)
        self.original_peak=float(np.linalg.norm(np.diff(raw[::2,self.root,:3,3],n=2,axis=0)*900,axis=1).max())
        for acceleration,matrix in zip(self.acceleration,self.acc_maps):norm(acceleration,matrix,self.original_peak)
        return dict(support=counts,original_peak_m_s2=self.original_peak,peak_constraints=len(self.acceleration))


def select_cases(request,summary):
    cases=request['cases'];rows=summary['rows']
    if len(cases)!=24 or len({c['id'] for c in cases})!=24 or [c['id'] for c in cases]!=[r['id'] for r in rows]:raise ValueError('Complete ordered parent population required')
    if any(r['status']=='failed' for r in rows):raise ValueError('Resolve parent execution failures first')
    if any(type(r.get('original_root_peak_recovered')) is not bool for r in rows):raise ValueError('Explicit original-peak comparisons required')
    # Selection uses the independently recorded comparison, not action names or scores chosen by hand.
    return [copy.deepcopy(c) for c,r in zip(cases,rows) if not r['original_root_peak_recovered']]


def prepare(parent,summary_path,output):
    if output.exists():raise ValueError('Preserve prior experiment')
    request=read(parent/'request.json');done=read(parent/'completion.json');summary=read(summary_path)
    if done['request_sha256']!=sha256(parent/'request.json') or done['results_sha256']!=sha256(parent/'results.json') or summary['study_completion_sha256']!=sha256(parent/'completion.json'):raise ValueError('Parent/summary identity changed')
    if done['engine_sha256']!=sha256(parent/'engine/verification.json'):raise ValueError('Parent engine evidence changed')
    cases=select_cases(request,summary);results=read(parent/'results.json')['rows']
    output.mkdir(parents=True)
    for case in cases:
        source=parent/'takes'/case['id'];folder=output/'takes'/case['id'];folder.mkdir(parents=True)
        check_files(source,case['files'])
        for name in case['files']:
            dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
        # Start from the same whole-support input and original 1cm radius as the
        # prior experiment, so repeated cleanup never accumulates an edit budget.
        previous=next(r for r in results if r['id']==case['id']);best=Path(previous['selected'])
        if not best.resolve().is_relative_to(source.resolve()) or sha256(best)!=previous['selected_sha256']:raise ValueError('Previous selected output changed')
        shutil.copyfile(best,folder/'previous-selected.glb')
        case['files']['previous-selected.glb']=sha256(best)
    methods=snapshot(output);shutil.copyfile(__file__,output/'implementation'/Path(__file__).name);methods[Path(__file__).name]=sha256(__file__)
    save(output/'request.json',dict(at=now(),parent=str(parent),parent_completion_sha256=sha256(parent/'completion.json'),summary_path=str(summary_path),summary_sha256=sha256(summary_path),
        cases=cases,excluded=[c['id'] for c in request['cases'] if c['id'] not in {s['id'] for s in cases}],policy=request['policy'],resources=request['resources'],implementation=methods,
        scope='All remaining original-peak failures in the 24-case parent, same original whole-support inputs and budgets, with a hard original root-peak cap. Numerical infeasibility is specific to this conservative root-only model, not proof that realistic motion is impossible.'))
    save(output/'freeze.json',dict(request_sha256=sha256(output/'request.json')))
    save(output/'results.json',dict(rows=[dict(id=c['id'],status='pending') for c in cases],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',at=now()))


def root_metrics(path,frames,root):
    _,world=samples(path,frames);a=np.linalg.norm(np.diff(world[::2,root,:3,3],n=2,axis=0)*900,axis=1)
    return dict(peak_m_s2=float(a.max()),energy=float(a@a),peak_center_frame=int(a.argmax()+1))


def run(output):
    from action_worker_lock import worker_lock
    from run_godot_rig_import import run as engine_import
    request=read(output/'request.json')
    if read(output/'freeze.json')['request_sha256']!=sha256(output/'request.json') or read(output/'pipeline.json')['status']!='prepared':raise ValueError('Fresh frozen experiment required')
    check_files(ROOT/'scripts',request['implementation']);check_files(output/'implementation',request['implementation'])
    for name,digest in request['resources'].items():
        if sha256(name)!=digest:raise ValueError('Frozen resource changed')
    results=read(output/'results.json');engine=[]
    save(output/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    with worker_lock(),threadpool_limits(limits=1):
        for case,row in zip(request['cases'],results['rows']):
            folder=output/'takes'/case['id'];row['status']='running';save(output/'results.json',results);save(output/'pipeline.json',dict(status='processing',case=case['id'],at=now()))
            try:
                problem=PeakProblem(folder,case,request['policy']);offsets,solver=problem.propose();save(folder/'solver.json',solver)
                row.update(solver=solver,original=root_metrics(folder/'input/character.glb',case['frames'],problem.root),previous=root_metrics(folder/'previous-selected.glb',case['frames'],problem.root),attempts=[])
                row['status']='no_solver_proposal' if offsets is None else 'no_verified_restoration';selected=folder/'previous-selected.glb'
                if offsets is not None:
                    np.save(folder/'offsets.npy',offsets)
                    for fraction in request['policy']['fractions']:
                        path=folder/('proposal-'+str(fraction)+'.glb');export(problem.rig,problem.root,offsets*fraction,path)
                        check=verify(problem,path);audit=inspect(problem.source,path,folder/'input/character.glb',folder/'contact-spec.json',case['frames'],request['policy']);support=support_audit(folder,path)
                        measured=root_metrics(path,case['frames'],problem.root)
                        restored=measured['peak_m_s2']<=row['original']['peak_m_s2']+request['policy']['acceleration_tolerance_m_s2']
                        accepted=restored and check['all_preservation_checks_passed'] and check['objective_improved'] and audit['all_checks_passed'] and support['passed']
                        row['attempts'].append(dict(fraction=fraction,verification=check,independent=audit,support=support,root=measured,peak_restored=restored,accepted=accepted))
                        save(folder/'attempts.json',row['attempts'])
                        if accepted:row['status']='restored';selected=path;break
                row.update(selected=str(selected),selected_sha256=sha256(selected),selected_metrics=root_metrics(selected,case['frames'],problem.root))
                if row['status']=='restored':engine.append(dict(id=case['id'],path=str(selected),sha256=sha256(selected),frames=case['frames'],fps=30,sample_by_time=True))
                del problem
            except Exception as exc:row.update(status='failed',error=str(exc))
            save(output/'results.json',results);print(case['id'],row['status'],row.get('solver',{}).get('status'),flush=True)
        save(output/'manifest.json',dict(cases=engine));engine_digest=None
        if engine:
            save(output/'pipeline.json',dict(status='engine_validation',at=now()));engine_import(output,output/'engine')
            proof=read(output/'engine/verification.json')
            if [c['id'] for c in proof['checks']]!=[c['id'] for c in engine]:raise ValueError('Incomplete new engine population')
            for actual,expected in zip(proof['checks'],engine):
                if actual['source_sha256']!=expected['sha256'] or actual['frames']!=expected['frames']:raise ValueError('Wrong new engine input')
            engine_digest=sha256(output/'engine/verification.json')
        for case in request['cases']:check_files(output/'takes'/case['id'],case['files'])
        check_files(ROOT/'scripts',request['implementation'])
        save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),results_sha256=sha256(output/'results.json'),engine_sha256=engine_digest,
            planned=len(request['cases']),restored=sum(r['status']=='restored' for r in results['rows']),failed=sum(r['status']=='failed' for r in results['rows']),new_engine_actor_frames=sum(c['frames'] for c in engine),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete_with_failures' if any(r['status']=='failed' for r in results['rows']) else 'complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--parent',type=Path);p.add_argument('--summary',type=Path);a=p.parse_args()
    if a.command=='prepare':prepare(a.parent.resolve(),a.summary.resolve(),a.output.resolve())
    else:
        try:run(a.output.resolve())
        except Exception as exc:save(a.output/'failure.json',dict(at=now(),error=str(exc),quality_approved=False));raise
