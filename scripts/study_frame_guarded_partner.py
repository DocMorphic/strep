"""Finite per-frame-cap partner trial using frozen witnesses and fresh mesh checks."""
import argparse
import ast
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.linalg import block_diag
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from load_contact_trial import load
from projected_temporal_surface import ProjectedTemporalSurface
from hull_surface_correspondences import correspondences
from frame_guarded_partner_step import solve
from audit_authoring_intent import check_files
from finish_bounded_surface_path import complete as export_and_audit
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(source,proof,output,buffer_from=None):
    if output.exists():raise ValueError('Preserve previous trial')
    recipe,fitter,faces,x=load(source)
    initial=x.copy();proof_rows=read(proof/'results.json')['rows'];done=read(proof/'completion.json')
    assert done['results_sha256']==sha256(proof/'results.json')
    assert done['initial_history_sha256']==sha256(proof/'initial-history.json')
    assert np.array_equal(x,read(proof/'initial-history.json')['parameters'])
    assert [r['frame'] for r in proof_rows]==recipe['frames']
    output.mkdir(parents=True);(output/'implementation').mkdir()
    inputs={str(source/n):sha256(source/n) for n in ['request.json','initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz']}
    inputs.update({str(proof/n):sha256(proof/n) for n in ['request.json','results.json','completion.json','initial-history.json']})
    buffers={}
    if buffer_from is not None:
        prior=read(buffer_from/'request.json');done=read(buffer_from/'completion.json')
        if done['accepted'] or read(buffer_from/'pipeline.json')['status']!='complete_no_candidate':raise ValueError('Completed rejected trial required for proposal buffers')
        if Path(prior['source']).resolve()!=source or Path(prior['proof']).resolve()!=proof:raise ValueError('Buffer evidence must use the same source and proof')
        for name,h in prior['inputs'].items():
            if sha256(name)!=h:raise ValueError('Buffer trial inputs changed')
        for trial in done['history']:
            for sample in trial['samples']:
                if not sample['passed']:
                    frame=sample['frame'];buffers[frame]=max(buffers.get(frame,0.),1.5*(sample['depth_m']-sample['cap_m']))
        for name in ['request.json','completion.json','history.json']:
            path=buffer_from/name;inputs[str(path)]=sha256(path)
    records=[]
    for row in proof_rows:
        path=proof/'surfaces'/row['correspondences_file'];assert sha256(path)==row['correspondences_sha256']
        inputs[str(path)]=sha256(path);record=read(path);assert record['frame']==row['frame'];records.append(record)
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
    name='godot_scene_import_audit.gd';seen.add(name);shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    for name in ['initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz']:shutil.copyfile(source/name,output/name)
    owner=psutil.Process();request=dict(at=now(),pid=owner.pid,created=owner.create_time(),source=str(source),proof=str(proof),inputs=inputs,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(seen)},frames=recipe['frames'],trust_degrees=[.5,.125],fractions=[1.,.5,.125],
        per_frame_cap='max(5mm, original measured sample depth)',minimum_peak_improvement_m=1e-6,event_locked=True,
        proposal_buffers_m=buffers,buffer_rule='1.5 times the largest recorded actual cap excess at each failed frame; proposal-only tightening; original acceptance unchanged',
        solver='Convex epigraph with individual frame caps, exact rotation balls and adjacent-edit balls',quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,**kw));print(status,kw,flush=True)
    def integrity():
        for name,h in inputs.items():
            if sha256(name)!=h:raise ValueError('Input changed: '+name)
        check_files(ROOT/'scripts',request['implementation']);check_files(output/'implementation',request['implementation'])
    try:
        with threadpool_limits(limits=1):
            locked=np.concatenate([np.repeat(fitter.matrix[fitter.event]!=0,a.dim) for a in fitter.base.actors])
            if fitter.sizes!=[60,60] or np.count_nonzero(locked)!=24:raise ValueError('Unexpected event/control layout')
            edge=block_diag(*[np.diff(m.reshape(150,12,60),axis=0).reshape(-1,60) for m in fitter.maps])
            gaps=[];jac=[];caps=[];depths=[];tightening=[]
            for record in records:
                frame=record['frame'];phase('linearizing',frame=frame)
                g,j=ProjectedTemporalSurface(fitter,frame,record['records']).clearance(x,0.)
                depth=max(r['max_depth_m'] for r in record['diagnostics'])
                if abs(float(np.maximum(-g,0).max(initial=0))-depth)>1e-8:raise ValueError('Frozen plane depth does not match source geometry')
                gaps.append(g);jac.append(j);caps.append(np.full(len(g),max(.005,depth)));depths.append(depth)
                tightening.append(np.full(len(g),buffers.get(frame,0.)))
            gaps,jac,caps=np.concatenate(gaps),np.vstack(jac),np.concatenate(caps)
            tightening=np.concatenate(tightening)
            np.savez_compressed(output/'linearization.npz',base=x,gaps=gaps,jacobian=jac,caps=caps,tightening=tightening,locked=locked,edge_map=edge)
            event_before=[a.pose(fitter.event,v) for a,v in zip(fitter.actors,np.split(x,2))]
            order=np.argsort(depths)[::-1];history=[];selected=None
            for trust in request['trust_degrees']:
                phase('conic_proposal',trust_degrees=trust)
                candidate,info=solve(x,gaps,jac,caps,locked,fitter.control_radii,edge,np.radians(trust),tightening=tightening)
                save(output/f'proposal-{trust}.json',dict(**info,controls=candidate.tolist() if candidate is not None else None))
                if candidate is None or info['predicted_peak_m']>=max(depths)-request['minimum_peak_improvement_m']:continue
                for fraction in request['fractions']:
                    proposed=x+fraction*(candidate-x);trial=output/f'trial-{trust}-{fraction}';trial.mkdir()
                    save(trial/'controls.json',dict(controls=proposed.tolist()))
                    if fitter.step_pair(proposed)[0].min()<-1e-8:raise ValueError('Proposal violated exact hard bounds')
                    if not all(np.array_equal(before,a.pose(fitter.event,v)) for before,a,v in zip(event_before,fitter.actors,np.split(proposed,2))):raise ValueError('Contact event changed')
                    samples=[];passed=True
                    for index in order:
                        frame=recipe['frames'][int(index)];phase('fresh_geometry',trust_degrees=trust,fraction=fraction,frame=frame)
                        rec,diag=correspondences(fitter.actors,frame,proposed,faces,margin=.003)
                        depth=max(r['max_depth_m'] for r in diag)
                        save(trial/(str(float(frame))+'.json'),dict(frame=frame,records=rec,diagnostics=diag))
                        allowed=max(.005,depths[index]);ok=depth<=allowed+(1e-9 if depths[index]>.005 else 0.)
                        samples.append(dict(frame=frame,depth_m=depth,cap_m=allowed,passed=bool(ok)))
                        if not ok:passed=False;break
                    accepted=passed and max(s['depth_m'] for s in samples)<max(depths)-request['minimum_peak_improvement_m']
                    history.append(dict(trust_degrees=trust,fraction=fraction,samples=samples,complete_clock=passed,accepted=accepted))
                    save(output/'history.json',dict(rows=history,quality_approved=False))
                    if accepted:selected=proposed;break
                if selected is not None:break
            integrity()
            if selected is None:
                save(output/'completion.json',dict(at=now(),accepted=False,history=history,quality_approved=False))
                phase('complete_no_candidate');return
            save(output/'parameters.json',dict(controls=selected.tolist(),trajectory_values=fitter.values(selected).tolist(),basis=fitter.matrix.tolist(),
                control_radii=fitter.control_radii.tolist(),control_bounds=fitter.bounds.tolist(),quality_approved=False))
            export=output/'export';export.mkdir()
            validation=dict(frames=[i*.5 for i in range(299)],quality_approved=False)
            save(export/'request.json',validation)
            phase('export_and_full_geometry')
            export_and_audit(output,export,recipe,validation,phase)
            event_audit=[]
            for label,before in zip(['A','B'],event_before):
                path=export/'assets'/label/'candidate/character.glb';rig=RigAsset.load(path)
                sampler=AnimationSampler(rig.document,rig.binary,0);after=sampler.sample(float(np.float32(fitter.event/30)))
                error=float(np.abs(rig.vertices(before)-rig.vertices(after)).max())
                if error>1e-6:raise ValueError('Exported event geometry changed')
                event_audit.append(dict(actor=label,max_vertex_error_m=error))
            integrity()
            save(output/'completion.json',dict(at=now(),accepted=True,export_completion_sha256=sha256(export/'completion.json'),
                parameters_sha256=sha256(output/'parameters.json'),event_preservation=event_audit,history_sha256=sha256(output/'history.json'),quality_approved=False))
            phase('complete')
    except BaseException as error:
        phase('failed',error=str(error),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['source','proof','output']:p.add_argument(n,type=Path)
    p.add_argument('--buffer-from',type=Path)
    a=p.parse_args();run(a.source.resolve(),a.proof.resolve(),a.output.resolve(),a.buffer_from.resolve() if a.buffer_from else None)
