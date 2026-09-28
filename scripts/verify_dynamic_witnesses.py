"""Measure real-rig moving-surface witnesses before permitting a solver trial."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from contact_restoration_problem import FrozenContactProblem
from dynamic_contact_witness import DynamicWitnessSurface


def run(proof,static,output):
    proof,static,output=[Path(p).resolve() for p in (proof,static,output)]
    done=read(static/'completion.json');history=read(static/'history.json')['iterations']
    if done['history_sha256']!=sha256(static/'history.json') or done['accepted_step'] or done['solved_rounds']!=1:
        raise ValueError('Expected retained rejected static witness trial')
    for name in ['candidate','witnesses','geometry','decision']:
        if history[1][name+'_sha256']!=sha256(static/'round-01'/(name+'.json')):raise ValueError('Static round changed')
    groups={};witnesses=[]
    for number in [1,2]:
        path=static/f'round-{number:02d}'/'witnesses.json'
        for row in read(path)['rows']:
            frame=row['frame'];groups.setdefault(frame,set())
            for r in row['rows']:
                groups[frame].add((r['source'],r['target'],r['vertex']))
                witnesses.append(dict(round=number,frame=frame,**r))
    groups={f:sorted(keys) for f,keys in sorted(groups.items())}
    prior=Path(read(static/'request.json')['starting_candidate_study'])
    inputs=[proof/'request.json',proof/'completion.json',static/'request.json',static/'completion.json',
        static/'history.json',static/'round-01'/'candidate.json',static/'round-01'/'witnesses.json',
        static/'round-02'/'witnesses.json',prior/'candidate.json',prior/'completion.json']
    names=sorted(set(read(static/'request.json')['implementation'])|{'dynamic_contact_witness.py','verify_dynamic_witnesses.py'})
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),proof=str(proof),static=str(static),
        inputs={str(p):sha256(p) for p in inputs},groups=[dict(frame=f,keys=k) for f,k in groups.items()],
        states=['initializer','scaled_candidate','static_cut_candidate'],steps=[1e-4,1e-5,1e-6],decisive_step=1e-5,
        scaled_derivative_tolerance=1e-5,relative_floor=1.,value_tolerance_m=1e-10,random_seed=6139,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    try:
        with threadpool_limits(limits=1):
            problem=FrozenContactProblem(proof);problem.fitter.witness_faces=problem.faces
            surfaces=[DynamicWitnessSurface(problem.fitter,f,keys) for f,keys in groups.items()]
            identities=[(f,*key) for f,keys in groups.items() for key in keys]
            states=[('initializer',problem.initial),('scaled_candidate',np.asarray(read(prior/'candidate.json')['controls'])),
                ('static_cut_candidate',np.asarray(read(static/'round-01'/'candidate.json')['controls']))]
            def evaluate(x):
                pairs=[s.clearance(x,0.) for s in surfaces]
                return np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs])
            values=[];checks=[];timings=[]
            for label,x in states:
                phase('probing',state=label,checks=len(checks))
                start=time.perf_counter();g,j=evaluate(x);timings.append(dict(state=label,seconds=time.perf_counter()-start))
                for identity,depth in zip(identities,-g):
                    frame,source,target,vertex=identity;cap=float(problem.caps[problem.frames.index(frame)])
                    reference=[r for r in witnesses if (r['frame'],r['source'],r['target'],r['vertex'])==identity and
                        r['round']==(1 if label=='scaled_candidate' else 2)] if label!='initializer' else []
                    err=max([abs(float(depth)-r['actual_depth_m']) for r in reference],default=0.)
                    values.append(dict(state=label,frame=frame,source=source,target=target,vertex=vertex,depth_m=float(depth),
                        cap_m=cap,seed_feasible=bool(depth<=cap+3e-10) if label=='initializer' else None,
                        retained_value_checks=len(reference),retained_max_error_m=err))
                rng=np.random.default_rng(request['random_seed']);directions=rng.normal(size=(6,len(x)))
                directions/=np.linalg.norm(directions,axis=1)[:,None]
                directions=np.vstack([directions,np.eye(len(x))[np.unravel_index(np.argmax(np.abs(j)),j.shape)[1]]])
                for i,d in enumerate(directions):
                    expected=j@d
                    for step in request['steps']:
                        start=time.perf_counter();gp,_=evaluate(x+step*d);gm,_=evaluate(x-step*d);elapsed=time.perf_counter()-start
                        fd=(gp-gm)/(2*step);error=np.abs(fd-expected)/np.maximum(1.,np.maximum(np.abs(fd),np.abs(expected)))
                        checks.append(dict(state=label,direction=i,step=step,max_scaled_error=float(error.max()),
                            max_absolute_error=float(np.max(np.abs(fd-expected))),seconds=elapsed,
                            passes_declared_screen=bool(error.max()<request['scaled_derivative_tolerance'])))
                    save(output/'results.json',dict(values=values,checks=checks,timings=timings,quality_approved=False))
                    phase('probing',state=label,direction=i,checks=len(checks))
            decisive=[r for r in checks if r['step']==request['decisive_step']]
            passed=all(r['passes_declared_screen'] for r in decisive) and all(r['retained_max_error_m']<1e-10 for r in values) and all(r['seed_feasible'] for r in values if r['state']=='initializer')
            save(output/'summary.json',dict(passed=passed,vertices=len(identities),frames=len(groups),states=len(states),
                directional_checks=len(checks),decisive_checks=len(decisive),decisive_passes=sum(r['passes_declared_screen'] for r in decisive),
                max_decisive_error=max(r['max_scaled_error'] for r in decisive),
                retained_value_checks=sum(r['retained_value_checks'] for r in values),max_retained_value_error_m=max(r['retained_max_error_m'] for r in values),
                original_seed_feasible=all(r['seed_feasible'] for r in values if r['state']=='initializer'),
                evaluation_timings=timings,quality_approved=False,scope='Selected real-rig witnesses only; directional derivatives, not exhaustive Jacobian or solved motion quality.'))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed: '+path)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed: '+name)
        save(output/'completion.json',dict(at=now(),passed=passed,results_sha256=sha256(output/'results.json'),summary_sha256=sha256(output/'summary.json'),quality_approved=False))
        phase('complete',passed=passed)
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['proof','static','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.proof,a.static,a.output)
