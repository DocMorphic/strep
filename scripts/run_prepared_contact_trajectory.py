"""Fit an explicitly prepared contact trajectory with frozen references and bounds."""
import argparse
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from analytic_patch_contact import AnalyticPatchFitter
from reference_temporal_patch_frame import evaluate, solve
from temporal_patch_frame import coordinate_bounds, pose_budget_pair
from rig_asset import RigAsset
from rig_transition import localize
from rig_loop import encode
from strep import ROOT, now, read, save, sha256


def load_plan(plan):
    protocol=read(plan/'protocol.json');spec=read(plan/'spec.json')
    for p,digest in protocol['inputs'].items():
        if sha256(p)!=digest:raise ValueError('Prepared input changed: '+p)
    for p,digest in protocol['implementation'].items():
        if sha256(ROOT/p)!=digest:raise ValueError('Prepared implementation changed: '+p)
    if sha256(plan/'prepared.npz')!=protocol['prepared_sha256'] or sha256(plan/'spec.json')!=protocol['spec_sha256']:
        raise ValueError('Prepared data or contract changed')
    rig=RigAsset.load(protocol['source_glb'])
    if sha256(protocol['source_glb'])!=spec['glb_sha256']:raise ValueError('Rig identity mismatch')
    with np.load(plan/'prepared.npz',allow_pickle=False) as z:data=dict(z)
    if set(data)!={'initial','reference','body','limb','weights'}:
        raise ValueError('Prepared arrays must contain only the declared trajectories and mask')
    n=spec['frames'];frames=np.asarray(protocol['frames'])
    if (frames.ndim!=1 or frames.dtype.kind not in 'iu' or not len(frames)
        or np.any(frames<1) or np.any(frames>=n-1) or np.any(np.diff(frames)<=0)):
        raise ValueError('Editable frames must be sorted unique interior keys')
    for name in ('body','limb'):
        if data[name].shape!=(n,len(rig.parents),4,4) or not np.isfinite(data[name]).all():
            raise ValueError('Invalid world transforms: '+name)
    fitter=AnalyticPatchFitter(rig,spec,localize(data['limb'],rig.parents))
    for name in ('initial','reference'):
        if data[name].shape!=(n,len(fitter.bounds)) or not np.isfinite(data[name]).all():
            raise ValueError('Invalid parameter trajectory: '+name)
    if data['weights'].shape!=(n,) or not np.array_equal(np.flatnonzero(data['weights']>0),frames):
        raise ValueError('Editable mask differs from planned frames')
    if not np.isfinite(data['weights']).all() or np.any((data['weights']<0)|(data['weights']>1)):
        raise ValueError('Invalid editable mask')
    if any(type(protocol[k]) is not int or protocol[k]<1 for k in ['max_sweeps','max_iterations_per_frame']):
        raise ValueError('Positive integer solver limits required')
    if np.max(abs(data['initial'][frames])-coordinate_bounds(fitter))>1e-6:
        raise ValueError('Initial trajectory exceeds coordinate bounds')
    if min(float(pose_budget_pair(fitter,data['initial'][f])[0].min()) for f in frames)<-1e-5:
        raise ValueError('Initial trajectory exceeds pose budgets')
    return protocol,spec,data,rig,fitter,frames


def run(plan,output):
    if output.exists():raise ValueError('Preserve earlier trajectory fits')
    with worker_lock():
        protocol,spec,data,rig,fitter,frames=load_plan(plan)
        output.mkdir(parents=True)
        save(output/'runner.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time()))
        names=set(protocol['implementation'])|{f'scripts/{n}' for n in [
            'run_prepared_contact_trajectory.py','rig_asset.py','rig_clip_import.py',
            'rig_transition.py','rig_loop.py']}
        (output/'implementation').mkdir()
        for p in names:shutil.copyfile(ROOT/p,output/'implementation'/Path(p).name)
        save(output/'protocol.json',dict(at=now(),plan=str(plan),plan_protocol_sha256=sha256(plan/'protocol.json'),
            prepared_sha256=sha256(plan/'prepared.npz'),spec_sha256=sha256(plan/'spec.json'),case=protocol['case'],
            frames=frames.tolist(),max_sweeps=protocol['max_sweeps'],max_iterations_per_frame=protocol['max_iterations_per_frame'],
            implementation={p:sha256(ROOT/p) for p in sorted(names)},quality_approved=False))
        save(output/'spec.json',spec)
        values=data['initial'].copy();reference=data['reference'];history=[];sweeps=[]
        bound=coordinate_bounds(fitter)
        clip_error=float(abs(values[frames]-np.clip(values[frames],-bound,bound)).max())
        values[frames]=np.clip(values[frames],-bound,bound)
        with threadpool_limits(limits=1):
            for sweep in range(protocol['max_sweeps']):
                previous=values.copy();accepted=0
                for frame in (frames if sweep%2==0 else frames[::-1]):
                    neighbors=[values[frame-1].copy(),values[frame+1].copy()]
                    refs=[reference[frame-1],reference[frame+1]]
                    before=evaluate(fitter,int(frame),values[frame],neighbors,reference[frame],refs)
                    fit,info=solve(fitter,int(frame),values[frame],neighbors,reference[frame],refs,
                        maxiter=protocol['max_iterations_per_frame'])
                    after=evaluate(fitter,int(frame),fit.x,neighbors,reference[frame],refs)
                    admissible=bool(fit.success and info['minimum_scaled_inequality']>=-1e-8 and
                        (before[2].min() < -1e-8 or after[0]<=before[0]+1e-10))
                    if admissible:values[frame]=fit.x;accepted+=1
                    history.append(dict(sweep=sweep,frame=int(frame),accepted=admissible,
                        solver_success=bool(fit.success),status=int(fit.status),iterations=int(fit.nit),
                        objective_before=before[0],objective_after=after[0],
                        minimum_before=float(before[2].min()),minimum_after=info['minimum_scaled_inequality']))
                    save(output/'solver.json',dict(history=history))
                    save(output/'pipeline.json',dict(at=now(),status='fitting',sweep=sweep,frame=int(frame),accepted=accepted))
                change=float(abs(values-previous).max())
                sweeps.append(dict(sweep=sweep,accepted=accepted,max_coordinate_change=change))
                save(output/'sweeps.json',dict(rows=sweeps));np.savez_compressed(output/f'sweep-{sweep}.npz',parameters=values)
                print(sweeps[-1],flush=True)
                if change<1e-6:break
            world=data['body'].copy()
            for f in frames:world[f]=fitter.pose(int(f),values[f])[0]
            np.testing.assert_array_equal(world[data['weights']==0],data['body'][data['weights']==0])
            animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
            _,roundtrip=encode(rig,world,animated,spec['root_node'],output/'candidate.glb','Experimental authored contact interval')
            residuals=[dict(frame=int(f),minimum=float(evaluate(fitter,int(f),values[f],
                [values[f-1],values[f+1]],reference[f],[reference[f-1],reference[f+1]])[2].min())) for f in frames]
        np.savez_compressed(output/'fit.npz',**data,parameters=values,world=world)
        save(output/'result.json',dict(at=now(),case=protocol['case'],constraints=residuals,
            all_editable_key_constraints_passed=all(r['minimum']>=-1e-8 for r in residuals),
            initial_coordinate_roundtrip_clip_max=clip_error,roundtrip=roundtrip,
            candidate_sha256=sha256(output/'candidate.glb'),fit_sha256=sha256(output/'fit.npz'),quality_approved=False))
        save(output/'manifest.json',dict(cases=[dict(id=protocol['case'],path=str((output/'candidate.glb').resolve()),
            sha256=sha256(output/'candidate.glb'),frames=spec['frames'],fps=spec['fps'],sample_by_time=True)]))
        save(output/'pipeline.json',dict(at=now(),status='complete',quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path)
    parser.add_argument('output',type=Path);parser.add_argument('--validate-only',action='store_true');a=parser.parse_args()
    if a.validate_only:
        protocol,spec,data,rig,fitter,frames=load_plan(a.plan.resolve())
        print(dict(valid=True,case=protocol['case'],frames=len(frames),contacts=len(spec['contacts']),fit_run=False))
    else:run(a.plan.resolve(),a.output.resolve())
