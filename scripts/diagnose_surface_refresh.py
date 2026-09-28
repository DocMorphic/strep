"""Locate guard violations absent from or misrepresented by frozen surfaces."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from load_contact_trial import load
from projected_temporal_surface import ProjectedTemporalSurface
from frame_capped_restoration import frame_caps
from screen_path_guard import SCREEN


def flatten(records):
    return [dict(key=(r['source'],r['target'],p[0]),triangle=p[1],barycentric=p[2],normal=p[3]) for r in records for p in r['points']]


def run(proof,output):
    proof,output=Path(proof).resolve(),Path(output).resolve();preq=read(proof/'request.json')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=sorted(set(preq['implementation'])|{'diagnose_surface_refresh.py','load_contact_trial.py','frame_capped_restoration.py','screen_path_guard.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),proof=str(proof),proof_request_sha256=sha256(proof/'request.json'),owner=dict(pid=preq['pid'],created=preq['created']),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_hull_proof_owner');await_owner(request['owner'],'pid','created',proof,{'complete'})
        done=read(proof/'completion.json')
        if sha256(proof/'request.json')!=request['proof_request_sha256'] or done['results_sha256']!=sha256(proof/'results.json') or done['comparisons']!=33:
            raise ValueError('Hull verification changed/incomplete')
        changed=Path(preq['changed']);initial_proof=Path(preq['proof']);initial_req=read(initial_proof/'request.json')
        if sha256(changed/'candidate.json')!=preq['changed_candidate_sha256']:raise ValueError('Candidate changed')
        _,fitter,_,initial=load(initial_req['source']);candidate=read(changed/'candidate.json');controls=np.asarray(candidate['controls'])
        bounds=read(changed/'budgets.json');caps=frame_caps(bounds['depths_m'],SCREEN['max_sample_penetration_m']);all_rows=[]
        with threadpool_limits(limits=1):
            for frame in preq['changed_frames']:
                phase('evaluating_saved_rows',frame=frame)
                oldpath=initial_proof/'surfaces'/f'{float(frame):06.1f}.json';newpath=proof/'surfaces'/f'changed-{float(frame)}.json'
                old=read(oldpath);new=read(newpath)
                old_records=old['records'];new_records=new['records'];old_flat=flatten(old_records);new_flat=flatten(new_records)
                old_depths=-ProjectedTemporalSurface(fitter,frame,old_records).clearance(controls,0.)[0]
                surface=ProjectedTemporalSurface(fitter,frame,new_records)
                actual=-surface.clearance(controls,0.)[0]
                refreshed_at_seed=-surface.clearance(initial,0.)[0]
                for source in [0,1]:
                    values=[actual[i] for i,r in enumerate(new_flat) if r['key'][0]==source]
                    expected=next(d['max_depth_m'] for d in new['diagnostics'] if d['source']==source)
                    if abs(max([0.,*values])-expected)>1e-10:raise ValueError('Saved closest surfaces do not reconstruct actual depths')
                index={r['key']:i for i,r in enumerate(old_flat)}
                if len(index)!=len(old_flat) or len({r['key'] for r in new_flat})!=len(new_flat):raise ValueError('Duplicate source witness')
                cap=float(caps[bounds['frames'].index(frame)]);violations=[]
                for i,r in enumerate(new_flat):
                    if actual[i]<=cap+1e-9:continue
                    j=index.get(r['key']);prior=None if j is None else old_flat[j]
                    angle=None if prior is None else float(np.degrees(np.arccos(np.clip(np.dot(r['normal'],prior['normal']),-1,1))))
                    violations.append(dict(source=r['key'][0],target=r['key'][1],vertex=r['key'][2],actual_depth_m=float(actual[i]),
                        fixed_depth_m=None if j is None else float(old_depths[j]),kind='absent_initial_row' if j is None else 'changed_surface_projection',
                        target_triangle_changed=None if prior is None else prior['triangle']!=r['triangle'],normal_change_degrees=angle,
                        refreshed_projection_at_initializer_m=float(refreshed_at_seed[i]),new_row_seed_within_frame_cap=bool(refreshed_at_seed[i]<=cap+1e-9)))
                row=dict(frame=frame,frame_guard_cap_m=cap,old_rows=len(old_flat),fresh_rows=len(new_flat),
                    newly_active_vertices=sum(r['key'] not in index for r in new_flat),
                    violations=sorted(violations,key=lambda v:-v['actual_depth_m']),old_correspondences_sha256=sha256(oldpath),fresh_correspondences_sha256=sha256(newpath))
                all_rows.append(row)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
        save(output/'summary.json',dict(at=now(),rows=all_rows,proof_completion_sha256=sha256(proof/'completion.json'),quality_approved=False,
            scope='Three frozen candidate frames; no new geometric query or corrected solve. Saved closest-point constraints reconstruct measured depths. Classifies guard violations by initial active-set membership and fixed projection, not a proof of repair feasibility.'))
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('proof',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.proof,a.output)
