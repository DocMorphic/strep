"""Finite event-preserving descent probe at the retained worst forearm witness."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from load_contact_trial import load
from dynamic_contact_witness import DynamicWitnessSurface
from hull_surface_correspondences import correspondences


def run(study, component_audit, output):
    study, component_audit, output = [p.resolve() for p in (study,component_audit,output)]
    if output.exists(): raise ValueError('Preserve earlier probe')
    component=read(component_audit/'summary.json')
    if not component['complete'] or component['completed_states']!=7:
        raise ValueError('Completed independent component audit required')
    recipe=read(study/'request.json')
    output.mkdir(parents=True);(output/'implementation').mkdir()
    names=sorted(set(recipe['implementation'])|{'probe_contact_approach.py'})
    for name in names:
        if name in recipe['implementation'] and sha256(ROOT/'scripts'/name)!=recipe['implementation'][name]:
            raise ValueError('Trial implementation changed')
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    inputs=[study/n for n in ['request.json','parameters.json','initial-parameters.json','A-source-local.npz','B-source-local.npz','palm-region.json']]
    inputs += [component_audit/'summary.json',Path(recipe['source_scene'])]
    owner=psutil.Process()
    request=dict(at=now(),pid=owner.pid,created=owner.create_time(),study=str(study),component_audit=str(component_audit),
         inputs={str(p):sha256(p) for p in inputs},implementation={n:sha256(output/'implementation'/n) for n in names},
         witness=dict(frame=66.5,source=0,target=1,vertex=6702),probe_degrees=[.25,.5,1.],frames=[66.5,67.,74.5,75.],
         derivative_step_radians=1e-5,derivative_absolute_tolerance=1e-5,quality_approved=False,
         scope='Fixed3-step forearm approach diagnostic, preserving all event-pose controls exactly. Fresh4-frame full-mesh checks. '
         'No objective optimization, export, candidate promotion, full-clock or quality certification.')
    save(output/'request.json',request)
    def phase(status,**details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        with threadpool_limits(limits=1):
            _,fitter,faces,_=load(study);fitter.witness_faces=faces
            base=np.asarray(read(study/'parameters.json')['controls'],float)
            # This experiment locks the middle knot, which solely determines
            # the event. Reject a different basis instead of approximating it.
            event_basis=fitter.matrix[fitter.event]
            if not np.array_equal(event_basis,[0,0,1,0,0]) or fitter.sizes!=[60,60]:
                raise ValueError('Unexpected control basis')
            free=np.tile(np.repeat(event_basis==0,12),2)
            surface=DynamicWitnessSurface(fitter,66.5,[(0,1,6702)])
            clearance,jac=surface.clearance(base,0.)
            direction=jac[0].copy();direction[~free]=0.
            maximum=np.linalg.norm(direction.reshape(-1,3),axis=1).max()
            if maximum<1e-12:raise ValueError('No event-preserving witness direction')
            direction/=maximum
            step=request['derivative_step_radians']
            finite=float((surface.clearance(base+step*direction,0.)[0][0]-surface.clearance(base-step*direction,0.)[0][0])/(2*step))
            predicted=float(jac[0]@direction)
            if abs(finite-predicted)>request['derivative_absolute_tolerance'] or predicted<=0:
                raise ValueError('Descent direction failed true-distance derivative check')
            save(output/'direction.json',dict(base_controls=base.tolist(),direction=direction.tolist(),locked_coordinates=np.flatnonzero(~free).tolist(),
                 base_witness_depth_m=float(-clearance[0]),predicted_clearance_derivative=predicted,finite_clearance_derivative=finite,
                 derivative_error=abs(finite-predicted),quality_approved=False))
            def event_points(x):
                parts=np.split(x,[fitter.sizes[0]])
                return [a.rig.vertices(a.pose(fitter.event,v))@a.rotation.T+a.translation for a,v in zip(fitter.actors,parts)]
            event=event_points(base);rows=[]
            for degrees in request['probe_degrees']:
                candidate=base+np.radians(degrees)*direction
                slack=float(fitter.step_pair(candidate)[0].min())
                inside=bool(np.all(np.abs(candidate)<=fitter.bounds+1e-10) and slack>=-1e-8)
                preserved=all(np.array_equal(a,b) for a,b in zip(event,event_points(candidate)))
                if not preserved:raise ValueError('Event geometry changed')
                row=dict(degrees=degrees,hard_bounds_pass=inside,minimum_hard_slack=slack,event_geometry_exactly_preserved=True,
                         witness_depth_m=float(-surface.clearance(candidate,0.)[0][0]),controls=candidate.tolist())
                if inside:
                    samples=[];start=time.perf_counter()
                    for frame in request['frames']:
                        phase('geometry',degrees=degrees,frame=frame)
                        _,collision=correspondences(fitter.actors,frame,candidate,faces,margin=.003)
                        samples.append(dict(frame=frame,collision=collision))
                    name=f'probe-{degrees}.json';save(output/name,dict(rows=samples,quality_approved=False))
                    row.update(samples=name,samples_sha256=sha256(output/name),seconds=time.perf_counter()-start,
                               maximum_depth_m=max(c['max_depth_m'] for s in samples for c in s['collision']))
                rows.append(row);save(output/'summary.json',dict(rows=rows,quality_approved=False))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
        save(output/'completion.json',dict(at=now(),probes=len(rows),summary_sha256=sha256(output/'summary.json'),
             direction_sha256=sha256(output/'direction.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for n in ['study','component_audit','output']:parser.add_argument(n,type=Path)
    args=parser.parse_args();run(args.study,args.component_audit,args.output)
