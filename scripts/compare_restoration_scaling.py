"""Compare all fitting times after a complete-objective numerical rescaling."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from strep import ROOT,read,save,sha256,now
from screen_path_guard import select_step,SCREEN


def validate_pair(before,after):
    for key in ['proof','proof_request_sha256','proof_completion_sha256','source','source_request_sha256','frames','maxiter','selection_screen']:
        if before[key]!=after[key]:raise ValueError('Matched restoration field differs: '+key)
    if before['method']!='one_inner_solve_frame_capped_restoration' or after['method']!='scaled_complete_objective_frame_capped_restoration':
        raise ValueError('Unexpected restoration methods')
    if after['objective_scale']!=1000. or after['solver_ftol']!=1e-12:raise ValueError('Unexpected numerical scaling')


def load(folder):
    request=read(folder/'request.json');completion=read(folder/'completion.json')
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Diagnostic incomplete')
    for filename,key in [('candidate.json','candidate_sha256'),('geometry.json','geometry_sha256'),('decision.json','decision_sha256')]:
        if sha256(folder/filename)!=completion[key]:raise ValueError('Completed evidence changed: '+filename)
    rows=read(folder/'geometry.json')['rows'];decision=read(folder/'decision.json');candidate=read(folder/'candidate.json')
    if [r['frame'] for r in rows]!=request['frames'] or completion['frames']!=len(rows):raise ValueError('Geometry population differs')
    depths=[max(c['max_depth_m'] for c in r['collision']) for r in rows]
    if depths!=decision['after_depths_m']:raise ValueError('Decision depths differ from fresh geometry')
    checked=select_step(decision['before_depths_m'],depths,candidate['old_energy'],candidate['new_energy'],decision['event_region'])
    if checked['checks']!=decision['checks'] or (checked['accepted'] and decision['hard_edit_bounds_pass'])!=decision['accepted']:
        raise ValueError('Retained guard decision differs')
    for name,digest in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=digest:raise ValueError('Retained implementation changed')
    return dict(request=request,completion=completion,candidate=candidate,decision=decision,depths=depths)


def compare(before,after,output):
    a,b=load(before),load(after);validate_pair(a['request'],b['request'])
    if (Path(b['request']['matched_diagnostic']).resolve()!=before or b['request']['matched_completion_sha256']!=sha256(before/'completion.json')
        or b['request']['matched_candidate_sha256']!=sha256(before/'candidate.json') or sha256(before/'budgets.json')!=sha256(after/'budgets.json')):
        raise ValueError('Scaled diagnostic does not bind the original candidate and budgets')
    if a['decision']['before_depths_m']!=b['decision']['before_depths_m'] or a['candidate']['old_energy']!=b['candidate']['old_energy']:
        raise ValueError('Diagnostic initializer differs')
    derivatives=read(after/'derivatives.json')
    if b['completion']['derivatives_sha256']!=sha256(after/'derivatives.json') or not derivatives['passed'] or len(derivatives['rows'])!=42:
        raise ValueError('Derivative preflight incomplete')
    initial=a['decision']['before_depths_m'];frames=a['request']['frames'];rows=[]
    for label,value in [('capped',a),('scaled',b)]:
        c=value['candidate'];decision=value['decision'];depths=value['depths']
        regressions=[dict(frame=f,before_m=d,after_m=e,increase_m=e-d) for f,d,e in zip(frames,initial,depths) if d>SCREEN['max_sample_penetration_m'] and e>d+1e-9]
        rows.append(dict(method=label,success=c['success'],solver_message=c['message'],iterations=c['iterations'],solve_seconds=c['solve_seconds'],
            objective=c['new_energy'],restoration_fraction=c['restoration_fraction'],relaxed_constraint_min=c['relaxed_constraint_min'],
            step_accepted=decision['accepted'],guard_checks=decision['checks'],peak_depth_m=max(depths),
            failing_samples=sum(d>SCREEN['max_sample_penetration_m'] for d in depths),regressed_failing_frames=regressions))
    curves=[dict(frame=f,initial_m=i,capped_m=c,scaled_m=s) for f,i,c,s in zip(frames,initial,a['depths'],b['depths'])]
    save(output/'curves.json',curves)
    summary=dict(at=now(),rows=rows,frames=len(frames),initial_peak_m=max(initial),curves_sha256=sha256(output/'curves.json'),
        before_completion_sha256=sha256(before/'completion.json'),after_completion_sha256=sha256(after/'completion.json'),quality_approved=False,
        scope='Same frozen initializer, surface rows, motion/slack relative weights and physical guard. Complete objective divided by1000; SLSQP ftol tightened to1e-12. One inner solve each, no backtracking or full exported audit. Timings are local observations, not a general performance benchmark.')
    save(output/'summary.json',summary)
    lines=['# Restoration objective scaling: complete fitting-clock comparison','',
        '| Method | Inner solve | Iterations | Fixed-constraint minimum | Peak penetration (mm) | Regressed failing frames | Step accepted |',
        '|---|---|---:|---:|---:|---|---|']
    for r in rows:
        lines.append(f"| {r['method']} | {r['success']} | {r['iterations']} | {r['relaxed_constraint_min']:.3g} | {r['peak_depth_m']*1000:.4f} | {', '.join(str(v['frame']) for v in r['regressed_failing_frames']) or 'none'} | {r['step_accepted']} |")
    lines+=['','All30 times are retained below. Values are penetration depth in millimetres.','',
        '| Frame | Initial | Capped | Scaled |','|---:|---:|---:|---:|']
    for r in curves:lines.append(f"| {r['frame']} | {r['initial_m']*1000:.4f} | {r['capped_m']*1000:.4f} | {r['scaled_m']*1000:.4f} |")
    lines+=['','Inner convergence does not establish fresh-geometry feasibility or animation quality. Both candidates retain their actual failures. No human, held-out, whole-clip, continuous-time, export or engine approval follows.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def run(before,after,output):
    before,after,output=[Path(p).resolve() for p in (before,after,output)]
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=['compare_restoration_scaling.py','screen_path_guard.py','audit_paired_guides.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    owner=read(after/'request.json');proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),before=str(before),after=str(after),owner=dict(pid=owner['pid'],created=owner['created']),
        before_request_sha256=sha256(before/'request.json'),after_request_sha256=sha256(after/'request.json'),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_scaled_geometry_owner');await_owner(request['owner'],'pid','created',after,{'complete'})
        for folder,key in [(before,'before_request_sha256'),(after,'after_request_sha256')]:
            if sha256(folder/'request.json')!=request[key]:raise ValueError('Diagnostic request changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Comparison implementation changed')
        compare(before,after,output)
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['before','after','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.before,a.after,a.output)
