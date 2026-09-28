"""Preflight a frozen initial-pose contact band on the actual deformed rigs."""
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
from projected_temporal_surface import ProjectedTemporalSurface
from seeded_witness_selection import select


def run(prior,band_report,output):
    prior,band_report,output=[Path(p).resolve() for p in (prior,band_report,output)]
    recipe=read(prior/'request.json');done=read(prior/'completion.json');band_record=read(band_report)
    if done['accepted_step'] or done['solved_rounds']!=3 or done['history_sha256']!=sha256(prior/'history.json'):
        raise ValueError('Expected completed three-round rejected trial')
    old_proof=Path(recipe['dynamic_proof']);old_request=read(old_proof/'request.json');projected=Path(old_request['proof']);static=Path(old_request['static'])
    if band_record['trial_completion_sha256']!=sha256(prior/'completion.json') or band_record['proof_request_sha256']!=sha256(projected/'request.json') or band_record['proof_completion_sha256']!=sha256(projected/'completion.json'):
        raise ValueError('Band diagnostic provenance differs')
    band=.002;declared=next(r for r in band_record['bands'] if r['band_m']==band)
    history=read(prior/'history.json')['iterations'];last=prior/'round-03';candidate=read(last/'candidate.json')
    for name in ['candidate','witnesses','geometry','decision']:
        if history[-1][name+'_sha256']!=sha256(last/(name+'.json')):raise ValueError('Retained candidate changed')
    names=sorted(set(recipe['implementation'])|{'seeded_witness_selection.py','verify_seeded_dynamic_witnesses.py','study_seeded_dynamic_witness.py'})
    for name,digest in recipe['implementation'].items():
        if sha256(prior/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Prior implementation changed: '+name)
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    inputs={**recipe['inputs'],str(prior/'request.json'):sha256(prior/'request.json'),str(prior/'completion.json'):sha256(prior/'completion.json'),
        str(prior/'history.json'):sha256(prior/'history.json'),str(last/'candidate.json'):sha256(last/'candidate.json'),str(last/'geometry.json'):sha256(last/'geometry.json'),str(band_report):sha256(band_report)}
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),proof=str(projected),static=str(static),prior=str(prior),
        band_m=band,inputs=inputs,groups=declared['groups'],states=['initializer','last_rejected_candidate'],steps=[1e-4,1e-5,1e-6],
        decisive_step=1e-5,scaled_derivative_tolerance=1e-5,relative_floor=1.,value_tolerance_m=1e-10,random_seed=6139,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Fixed2mm initial-depth band. Recompute every selected identity, compare retained distances, check directional derivatives and cost at original and last rejected poses. Not conservative swept coverage or motion-quality approval.')
    save(output/'request.json',request)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    try:
        with threadpool_limits(limits=1):
            problem=FrozenContactProblem(projected);fitter=problem.fitter;fitter.witness_faces=problem.faces;groups=[];expected=[]
            for frame,cap,surface in zip(problem.frames,problem.caps,problem.surfaces):
                selected=select(surface.records,-surface.clearance(problem.initial,0.)[0],float(cap),band)
                if selected['keys']:
                    groups.append(dict(frame=frame,cap_m=float(cap),keys=[list(k) for k in selected['keys']]))
                    expected.extend(selected['original_depths_m'])
            if groups!=declared['groups'] or len(expected)!=113 or len(groups)!=15:raise ValueError('Declared seed population does not reproduce')
            surfaces=[DynamicWitnessSurface(fitter,g['frame'],[tuple(k) for k in g['keys']]) for g in groups]
            ids=[(g['frame'],*key) for g in groups for key in g['keys']]
            expected_by_state={'initializer':dict(zip(ids,expected))};reference={};x=np.asarray(candidate['controls'])
            for group in groups:
                frame=group['frame'];path=last/'surfaces'/f'after-{float(frame)}.json';saved=read(path)
                if saved['frame']!=frame:raise ValueError('Retained surface clock differs')
                measured=next(r for r in history[-1]['window'] if r['frame']==frame)
                if saved['diagnostics']!=measured['collision']:raise ValueError('Retained surface diagnostics differ')
                surface=ProjectedTemporalSurface(fitter,frame,saved['records']);depths=-surface.clearance(x,0.)[0]
                keys=[(frame,r['source'],r['target'],p[0]) for r in saved['records'] for p in r['points']]
                reference.update(zip(keys,depths));request['inputs'][str(path)]=sha256(path)
            expected_by_state['last_rejected_candidate']=reference;save(output/'request.json',request)
            def evaluate(values):
                pairs=[s.clearance(values,0.) for s in surfaces]
                return np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs])
            values=[];checks=[];timings=[]
            for label,x in [('initializer',problem.initial),('last_rejected_candidate',x)]:
                phase('probing',state=label,checks=len(checks));start=time.perf_counter();g,j=evaluate(x)
                timings.append(dict(state=label,seconds=time.perf_counter()-start,rows=len(g)))
                for identity,depth in zip(ids,-g):
                    frame,source,target,vertex=identity;cap=float(problem.caps[problem.frames.index(frame)]);reference=expected_by_state[label].get(identity)
                    values.append(dict(state=label,frame=frame,source=source,target=target,vertex=vertex,depth_m=float(depth),cap_m=cap,
                        seed_feasible=bool(depth<=cap+3e-10) if label=='initializer' else None,
                        retained_value_checked=reference is not None,retained_error_m=float(abs(depth-reference)) if reference is not None else None))
                rng=np.random.default_rng(request['random_seed']);directions=rng.normal(size=(6,len(x)));directions/=np.linalg.norm(directions,axis=1)[:,None]
                directions=np.vstack([directions,np.eye(len(x))[np.unravel_index(np.argmax(np.abs(j)),j.shape)[1]]])
                for index,direction in enumerate(directions):
                    expected=j@direction
                    for step in request['steps']:
                        start=time.perf_counter();gp,_=evaluate(x+step*direction);gm,_=evaluate(x-step*direction);fd=(gp-gm)/(2*step)
                        error=np.abs(fd-expected)/np.maximum(1.,np.maximum(np.abs(fd),np.abs(expected)))
                        worst=int(np.argmax(error));checks.append(dict(state=label,direction=index,step=step,seconds=time.perf_counter()-start,
                            max_scaled_error=float(error[worst]),max_absolute_error=float(np.max(np.abs(fd-expected))),worst_witness=ids[worst],
                            passes_declared_screen=bool(error[worst]<request['scaled_derivative_tolerance'])))
                    save(output/'results.json',dict(values=values,checks=checks,timings=timings,quality_approved=False));phase('probing',state=label,direction=index,checks=len(checks))
            decisive=[r for r in checks if r['step']==request['decisive_step']];compared=[r for r in values if r['retained_value_checked']]
            seed_pass=all(r['seed_feasible'] for r in values if r['state']=='initializer')
            passed=all(r['passes_declared_screen'] for r in decisive) and seed_pass and all(r['retained_error_m']<request['value_tolerance_m'] for r in compared)
            save(output/'summary.json',dict(passed=passed,vertices=len(ids),frames=len(groups),states=2,decisive_checks=len(decisive),
                decisive_passes=sum(r['passes_declared_screen'] for r in decisive),max_decisive_error=max(r['max_scaled_error'] for r in decisive),
                retained_value_checks=len(compared),uncompared_values=len(values)-len(compared),max_retained_value_error_m=max(r['retained_error_m'] for r in compared),
                original_seed_feasible=seed_pass,evaluation_timings=timings,quality_approved=False,scope=request['scope']))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed: '+path)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed: '+name)
        save(output/'completion.json',dict(at=now(),passed=passed,results_sha256=sha256(output/'results.json'),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete',passed=passed)
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['prior','band_report','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.prior,a.band_report,a.output)
