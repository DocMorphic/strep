"""Bounded coordinate repair of the first frozen knee-contact window."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

from analytic_patch_contact import AnalyticPatchFitter
from temporal_patch_frame import solve,evaluate,coordinate_bounds,pose_budget_pair
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from rig_loop import encode
from probe_knee_patch_support import measurements
from strep import ROOT,now,read,save,sha256


def run(output):
    if output.exists():raise ValueError('Preserve earlier temporal probe')
    windows=ROOT/'reports/knee-contact-windows-v1'
    if read(windows/'pipeline.json')['status']!='complete':raise ValueError('Require finished window comparison')
    # First declared case, not selected by success or ease of correction.
    case=read(windows/'results.json')['rows'][0];name=case['id'];src=windows/name
    for file,digest in case['detail_hashes'].items():
        if sha256(src/file)!=digest:raise ValueError('Window diagnostic changed')
    soft=ROOT/'reports/knee-patch-feasibility-v1';old=next(c for c in read(soft/'protocol.json')['cases'] if c['id']==name)
    spec=copy.deepcopy(read(soft/name/'spec.json'));spec['frames']=180
    for contact in spec['contacts']:contact.update(start_frame=case['source_frame'],end_frame_exclusive=case['source_frame']+1)
    if sha256(old['source_glb'])!=old['source_glb_sha256']:raise ValueError('Limb source changed')
    rig=RigAsset.load(old['source_glb'])
    with np.load(src/'poses.npz',allow_pickle=False) as z:data=dict(z)
    original=localize(data['limb'],rig.parents);start=localize(data['after'],rig.parents)
    fitter=AnalyticPatchFitter(rig,spec,original);values=np.zeros((180,len(fitter.bounds)))
    values[:,:3]=data['after'][:,spec['root_node'],:3,3]-data['limb'][:,spec['root_node'],:3,3]
    for i,node in enumerate(fitter.nodes):values[:,3+i*3:6+i*3]=Rotation.from_matrix(original[:,node,:3,:3].transpose(0,2,1)@start[:,node,:3,:3]).as_rotvec()
    frames=np.flatnonzero(data['weights']>0)
    bounds=coordinate_bounds(fitter)
    excess=float(np.maximum(abs(values[frames])-bounds,0).max())
    budget_min=min(float(pose_budget_pair(fitter,values[f])[0].min()) for f in frames)
    if excess>1e-6 or budget_min < -1e-5:raise ValueError('Prepared window exceeds declared pose budgets')
    values[frames]=np.clip(values[frames],-bounds,bounds)
    output.mkdir(parents=True);save(output/'spec.json',spec)
    names=['probe_temporal_knee_patch.py','temporal_patch_frame.py','analytic_patch_contact.py','constrained_patch_pose.py','rig_periodic_contact.py','target_rig_contact.py','rig_clearance_fit.py','rig_loop.py','rig_asset.py','rig_clip_import.py']
    snapshot=output/'implementation';snapshot.mkdir()
    for n in names:shutil.copyfile(ROOT/'scripts'/n,snapshot/n)
    save(output/'protocol.json',dict(at=now(),case=name,selection='First case in the frozen eight-case window population',
        input_result_sha256=sha256(src/'result.json'),input_pose_sha256=sha256(src/'poses.npz'),spec_sha256=sha256(output/'spec.json'),
        implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in names},frames=frames.tolist(),max_sweeps=4,max_iterations_per_frame=80,
        initial_coordinate_roundtrip_clip_max=excess,initial_scaled_pose_budget_minimum=budget_min,
        budget_domain='Exact Euclidean root-horizontal and joint-rotation magnitudes from spec, replacing legacy conservative angle/sqrt3 component boxes. Advertised pose limits unchanged; this expands the internal parameter subset, not the declared budgets.',
        contact_contract='Only the original center-frame target is declared; surrounding patch drift is not hard constrained.',
        scope='All-vertex keyframe floor constraints, exact center contact, absolute pose budgets and neighbor edit limits. Existing outer body motion stays fixed. Quarter-frame interpolation and preexisting outer failures require separate audit. No full support-interval or dynamics guarantee.',quality_approved=False))
    save(output/'pipeline.json',dict(status='fitting',at=now()));history=[];initial=values.copy()
    with threadpool_limits(limits=1):
        for sweep in range(4):
            previous=values.copy();accepted=0
            for frame in (frames if sweep%2==0 else frames[::-1]):
                neighbors=[values[n].copy() for n in (frame-1,frame+1)]
                before=evaluate(fitter,int(frame),values[frame],neighbors)
                fit,info=solve(fitter,int(frame),values[frame],neighbors,maxiter=80)
                after=evaluate(fitter,int(frame),fit.x,neighbors)
                admissible=bool(fit.success and info['minimum_scaled_inequality']>=-1e-8 and
                    (before[2].min()<-1e-8 or after[0]<=before[0]+1e-10))
                if admissible:values[frame]=fit.x;accepted+=1
                history.append(dict(sweep=sweep,frame=int(frame),accepted=admissible,solver_success=bool(fit.success),status=int(fit.status),
                    objective_before=before[0],objective_after=after[0],minimum_before=float(before[2].min()),minimum_after=info['minimum_scaled_inequality'],iterations=fit.nit))
                save(output/'solver.json',dict(history=history));save(output/'pipeline.json',dict(status='fitting',sweep=sweep,frame=int(frame),accepted=accepted,at=now()))
            change=float(abs(values-previous).max());print(dict(sweep=sweep,accepted=accepted,max_coordinate_change=change),flush=True)
            np.savez_compressed(output/f'sweep-{sweep}.npz',parameters=values)
            if change<1e-6:break
        after=data['body'].copy()
        for f in frames:after[f]=fitter.pose(int(f),values[f])[0]
        outside=data['weights']==0;np.testing.assert_array_equal(after[outside],data['body'][outside])
        animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
        _,roundtrip=encode(rig,after,animated,spec['root_node'],output/'candidate.glb','Experimental temporally bounded knee target')
        encoded=RigAsset.load(output/'candidate.glb');sampler=AnimationSampler(encoded.document,encoded.binary,0)
        floor=[]
        for frame in np.arange(0,179.001,.25):
            p=encoded.vertices(sampler.sample(float(frame/30)));floor.append(dict(frame=float(frame),depth_m=max(0.,-float(p[:,1].min()))))
        center=measurements(encoded,spec,sampler.sample(case['source_frame']/30))
        residuals=[dict(frame=int(f),minimum=float(evaluate(fitter,int(f),values[f],[values[f-1],values[f+1]])[2].min())) for f in frames]
    np.savez_compressed(output/'fit.npz',initial=initial,parameters=values,world=after,limb=data['limb'],body=data['body'],weights=data['weights'])
    save(output/'floor.json',dict(samples=floor));save(output/'result.json',dict(at=now(),case=name,frames=frames.tolist(),
        constraints=residuals,all_editable_key_constraints_passed=all(r['minimum']>=-1e-8 for r in residuals),
        floor_max_m=max(r['depth_m'] for r in floor),floor_failed_quarter_samples=sum(r['depth_m']>spec['screen']['floor_depth_m'] for r in floor),
        center=center,roundtrip=roundtrip,candidate_sha256=sha256(output/'candidate.glb'),fit_sha256=sha256(output/'fit.npz'),quality_approved=False))
    save(output/'manifest.json',dict(cases=[dict(id=name,path=str((output/'candidate.glb').resolve()),sha256=sha256(output/'candidate.glb'),frames=180,fps=30,sample_by_time=True)]))
    save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))
    print(dict(floor_max_m=max(r['depth_m'] for r in floor),center_contact_m=center['contact_error_max_m']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();run(a.output.resolve())
