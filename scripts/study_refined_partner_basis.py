"""Finite nested-basis trial on the retained high-five, with unchanged physical limits."""
import argparse
import ast
import copy
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.linalg import block_diag
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from load_contact_trial import load
from refined_partner_basis import refine
from refined_partner_start import restore
from projected_temporal_surface import ProjectedTemporalSurface
from hull_surface_correspondences import correspondences
from frame_guarded_partner_step import solve
from finish_bounded_surface_path import complete as export_and_audit
from compare_partner_paths import full_curve
from compare_enriched_partner_path import changes


def run(source,warm,output):
    if output.exists():raise ValueError('Preserve earlier study')
    recipe,coarse,faces,original_controls=load(source);owner=read(warm/'request.json');done=read(warm/'completion.json')
    if Path(owner['source']).resolve()!=source or not done['accepted'] or read(warm/'pipeline.json')['status']!='complete':raise ValueError('Require the completed matched warm start')
    for path,digest in owner['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Warm input changed')
    if sha256(warm/'parameters.json')!=done['parameters_sha256'] or sha256(warm/'export/completion.json')!=done['export_completion_sha256']:raise ValueError('Warm completion changed')
    warm_params=read(warm/'parameters.json');warm_recipe_path=warm/'export-recipe.json'
    warm_recipe=read(warm_recipe_path) if warm_recipe_path.exists() else None
    if warm_recipe is not None:
        proof=read(warm/'independent-verification.json')
        if not done['full_clock_cap_pass'] or not proof['full_clock_cap_pass'] or proof['completion_sha256']!=sha256(warm/'completion.json'):
            raise ValueError('A continued refined trial requires verified full-clock preservation')
    coarse,xold=restore(coarse,original_controls,recipe,warm_params,read(warm/'initial-parameters.json'),warm_recipe)
    knots=[50,62.5,65,67.5,70,72.5,75,77.5,80,82.5,85,87.5,100]
    fitter,x,embedding=refine(coarse,xold,knots)
    output.mkdir(parents=True);(output/'implementation').mkdir();(output/'surfaces').mkdir()
    inputs={str(source/n):sha256(source/n) for n in ['request.json','initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz']}
    for name in ['request.json','parameters.json','completion.json','export/completion.json','export/geometry/candidate/samples.json','export/geometry/raw/samples.json']:
        inputs[str(warm/name)]=sha256(warm/name)
    inputs[str(warm/'initial-parameters.json')]=sha256(warm/'initial-parameters.json')
    if warm_recipe is not None:
        for name in ['export-recipe.json','independent-verification.json']:
            inputs[str(warm/name)]=sha256(warm/name)
    for name in ['palm-region.json','A-source-local.npz','B-source-local.npz']:shutil.copyfile(source/name,output/name)
    pending=[Path(__file__).name];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=ROOT/'scripts'/name;shutil.copyfile(path,output/'implementation'/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for module in modules:
                child=(module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists():pending.append(child)
    for name in ['godot_scene_import_audit.gd']:seen.add(name);shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    p=psutil.Process();request=dict(at=now(),pid=p.pid,created=p.create_time(),source=str(source),warm=str(warm),inputs=inputs,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(seen)},frames=recipe['frames'],embedding=embedding,
        trust_degrees=[3.,1.,.25],max_buffer_attempts_per_trust=3,proposal_buffer_rule='At violated fitting samples, add 1.5 times observed excess over the unchanged actual cap; never change acceptance',
        per_frame_cap='max(5mm, measured warm-start depth),1nm floating comparison only above5mm',minimum_peak_improvement_m=1e-6,
        unchanged_limits=dict(joint_edit_degrees=recipe['joint_edit_degrees'],adjacent_edit_degrees=5,root='fixed',event_frame=75,event_controls='fixed exactly'),
        intervention='nested timing refinement' if embedding['source_control_count']!=embedding['refined_control_count'] else 'same-basis nonlinear continuation',
        scope='Known one-pair development trial. Same event, envelope and hard edit limits. No floor repair or realism approval.',quality_approved=False)
    save(output/'request.json',request)
    initial=dict(controls=x.tolist(),basis=fitter.matrix.tolist(),control_bounds=fitter.bounds.tolist(),control_radii=fitter.control_radii.tolist())
    save(output/'initial-parameters.json',initial)
    export_recipe={**recipe,'knots':knots};save(output/'export-recipe.json',export_recipe)
    def phase(status,**kwargs):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    def integrity():
        for path,digest in inputs.items():
            if sha256(path)!=digest:raise ValueError('Input changed: '+path)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed: '+name)
    try:
        with threadpool_limits(limits=1):
            # Verify the actual interpolated skeleton before proposing any edit.
            pose_error=0.
            for frame in np.arange(299)*.5:
                for a,b,left,right in zip(coarse.actors,fitter.actors,np.split(xold,2),np.split(x,2)):
                    pose_error=max(pose_error,float(np.abs(a.pose(frame,left)-b.pose(frame,right)).max()))
            if pose_error>1e-12:raise ValueError('Embedding changed interpolated source pose')
            save(output/'embedding.json',dict(**embedding,half_frame_pose_max_error=pose_error,samples=299))
            locked=np.concatenate([np.repeat(fitter.matrix[fitter.event]!=0,a.dim) for a in fitter.base.actors])
            edge=block_diag(*[np.diff(m.reshape(150,12,size),axis=0).reshape(-1,size) for m,size in zip(fitter.maps,fitter.sizes)])
            gaps=[];jac=[];depths=[];slices=[];cursor=0
            for frame in request['frames']:
                phase('warm_surface_geometry',frame=frame)
                records,diagnostics=correspondences(fitter.actors,frame,x,faces,margin=.003)
                save(output/'surfaces'/(str(frame)+'.json'),dict(frame=frame,records=records,diagnostics=diagnostics))
                g,j=ProjectedTemporalSurface(fitter,frame,records).clearance(x,0.)
                depth=max(d['max_depth_m'] for d in diagnostics)
                if abs(np.maximum(-g,0).max(initial=0)-depth)>1e-8:raise ValueError('Source planes differ from geometry')
                gaps.append(g);jac.append(j);depths.append(depth);slices.append((cursor,cursor+len(g)));cursor+=len(g)
            gaps=np.concatenate(gaps);jac=np.vstack(jac)
            caps=np.concatenate([np.full(b-a,max(.005,d)) for (a,b),d in zip(slices,depths)])
            np.savez_compressed(output/'linearization.npz',base=x,gaps=gaps,jacobian=jac,caps=caps,locked=locked,edge_map=edge)
            event=[a.pose(75,v) for a,v in zip(fitter.actors,np.split(x,2))]
            order=np.argsort(depths)[::-1];buffers=np.zeros(len(depths));history=[];selected=None
            for trust in request['trust_degrees']:
                # Curvature buffers belong to a trust region. Reset for a smaller one.
                buffers[:]=0
                for attempt in range(request['max_buffer_attempts_per_trust']):
                    tightening=np.concatenate([np.full(b-a,d) for (a,b),d in zip(slices,buffers)])
                    phase('conic_proposal',trust_degrees=trust,attempt=attempt)
                    candidate,info=solve(x,gaps,jac,caps,locked,fitter.control_radii,edge,np.radians(trust),tightening=tightening)
                    trial=output/f'trial-{trust}-{attempt}';trial.mkdir()
                    save(trial/'proposal.json',dict(**info,controls=candidate.tolist() if candidate is not None else None,frame_buffers_m=buffers.tolist()))
                    if candidate is None or info['predicted_peak_m']>=max(depths)-1e-6:
                        history.append(dict(trust_degrees=trust,attempt=attempt,accepted=False,reason='No feasible predicted peak improvement',proposal=info));break
                    if fitter.step_pair(candidate)[0].min()<-1e-8:raise ValueError('Exact edit bounds violated')
                    if not all(np.array_equal(w,a.pose(75,v)) for w,a,v in zip(event,fitter.actors,np.split(candidate,2))):raise ValueError('Event changed')
                    samples=[];passed=True
                    for index in order:
                        index=int(index);frame=request['frames'][index];phase('candidate_geometry',trust_degrees=trust,attempt=attempt,frame=frame)
                        records,diagnostics=correspondences(fitter.actors,frame,candidate,faces,margin=.003)
                        depth=max(d['max_depth_m'] for d in diagnostics);cap=max(.005,depths[index]);ok=depth<=cap+(1e-9 if depths[index]>.005 else 0)
                        save(trial/(str(frame)+'.json'),dict(frame=frame,records=records,diagnostics=diagnostics))
                        samples.append(dict(frame=frame,depth_m=depth,cap_m=cap,passed=bool(ok)))
                        if not ok:
                            buffers[index]+=1.5*(depth-cap);passed=False;break
                    accepted=passed and max(s['depth_m'] for s in samples)<max(depths)-1e-6
                    history.append(dict(trust_degrees=trust,attempt=attempt,samples=samples,complete_clock=passed,accepted=accepted))
                    save(output/'history.json',dict(rows=history,quality_approved=False))
                    if accepted:selected=candidate;break
                    if any(buffers[i]>max(.005,depths[i]) for i in range(len(buffers))):break
                if selected is not None:break
            save(output/'history.json',dict(rows=history,quality_approved=False));integrity()
            if selected is None:
                save(output/'completion.json',dict(at=now(),accepted=False,history_sha256=sha256(output/'history.json'),quality_approved=False));phase('complete_no_candidate');return
            save(output/'parameters.json',dict(controls=selected.tolist(),trajectory_values=fitter.values(selected).tolist(),basis=fitter.matrix.tolist(),control_radii=fitter.control_radii.tolist(),control_bounds=fitter.bounds.tolist(),quality_approved=False))
            export=output/'export';export.mkdir();validation=dict(frames=[i*.5 for i in range(299)],quality_approved=False);save(export/'request.json',validation)
            phase('export_and_full_geometry');export_and_audit(output,export,export_recipe,validation,phase)
            before=full_curve(read(warm/'export/geometry/candidate/samples.json')['rows']);after=full_curve(read(export/'geometry/candidate/samples.json')['rows'])
            raw_before=full_curve(read(warm/'export/geometry/raw/samples.json')['rows']);raw_after=full_curve(read(export/'geometry/raw/samples.json')['rows'])
            if raw_before!=raw_after:raise ValueError('Original scene geometry changed')
            cap_pass=all(y<=max(.005,z)+(1e-9 if z>.005 else 0) for z,y in zip(before['body_depth_m'],after['body_depth_m']))
            event_rows=[next(r for r in read(path)['rows'] if r['frame']==75) for path in [warm/'export/geometry/candidate/samples.json',export/'geometry/candidate/samples.json']]
            save(output/'comparison.json',dict(before=before,after=after,raw=raw_after,changes=changes(before,after,request['frames']),event_before=event_rows[0],event_after=event_rows[1],full_clock_cap_pass=cap_pass,quality_approved=False))
            integrity();save(output/'completion.json',dict(at=now(),accepted=True,full_clock_cap_pass=cap_pass,parameters_sha256=sha256(output/'parameters.json'),comparison_sha256=sha256(output/'comparison.json'),export_completion_sha256=sha256(export/'completion.json'),quality_approved=False))
            phase('complete',full_clock_cap_pass=cap_pass)
    except BaseException as error:phase('failed',error=str(error),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source','warm','output']:p.add_argument(key,type=Path)
    a=p.parse_args();run(a.source.resolve(),a.warm.resolve(),a.output.resolve())
