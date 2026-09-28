"""Apply hard surface/contact constraints to the exact retained soft pose probes."""
import argparse
import shutil
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from analytic_patch_contact import AnalyticPatchFitter
from constrained_patch_pose import solve
from probe_knee_patch_support import measurements
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_loop import encode
from strep import ROOT,now,read,save,sha256


def run(source,output):
    if output.exists():raise ValueError('Preserve earlier comparison')
    if read(source/'pipeline.json')['status']!='complete':raise ValueError('Require finished soft probes')
    old=read(source/'protocol.json');soft=read(source/'results.json')['rows']
    if [r['id'] for r in soft]!=[c['id'] for c in old['cases']]:raise ValueError('Incomplete source cohort')
    output.mkdir(parents=True)
    names=['probe_constrained_knee_support.py','constrained_patch_pose.py','analytic_patch_contact.py','probe_knee_patch_support.py','target_rig_contact.py','rig_clearance_fit.py','rig_asset.py','rig_clip_import.py','rig_loop.py']
    snapshot=output/'implementation';snapshot.mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    protocol=dict(at=now(),source=str(source),source_protocol_sha256=sha256(source/'protocol.json'),source_results_sha256=sha256(source/'results.json'),
        implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in names},cases=old['cases'],max_iterations=120,
        numerical_interior_margin_m=1e-5,quality_approved=False,scope='Same eight static poses, patch targets, screens, objective and pose bounds. Warm start from retained soft fit. Add all-vertex floor and Euclidean contact inequalities, tightened by10micrometres for numerical margin. A failed optimization is not proof of infeasibility. No temporal claim.')
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='fitting',at=now()))
    rows=[];manifest=[]
    with threadpool_limits(limits=1):
        for case,previous in zip(old['cases'],soft):
            src=source/case['id'];dest=output/case['id'];dest.mkdir()
            for path,digest in [(case['source_glb'],case['source_glb_sha256']),(src/'source-pose.npz',case['source_pose_sha256']),
                (src/'spec.json',case['spec_sha256']),(src/'fit.npz',previous['fit_sha256'])]:
                if sha256(path)!=digest:raise ValueError('Source probe changed')
            spec=read(src/'spec.json');rig=RigAsset.load(case['source_glb'])
            with np.load(src/'source-pose.npz',allow_pickle=False) as z:pose=dict(z)
            with np.load(src/'fit.npz',allow_pickle=False) as z:start=z['parameters']
            fitter=AnalyticPatchFitter(rig,spec,np.repeat(pose['local'][None],2,axis=0))
            begin=time.perf_counter();result,info=solve(fitter,start,maxiter=protocol['max_iterations'])
            world,_=fitter.pose(0,result.x)
            measured=measurements(rig,spec,world)
            animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
            _,roundtrip=encode(rig,np.repeat(world[None],2,axis=0),animated,spec['root_node'],dest/'candidate.glb','Hard-constrained isolated pose; not an animation')
            exported=RigAsset.load(dest/'candidate.glb');sampler=AnimationSampler(exported.document,exported.binary,0)
            decoded=measurements(exported,spec,sampler.sample(0.))
            bounds_ok=bool(np.all(np.abs(result.x)<=fitter.bounds+1e-10))
            geometry_ok=bool(decoded['floor_depth_m']<=spec['screen']['floor_depth_m'] and decoded['contact_error_max_m']<=spec['screen']['contact_error_m'])
            np.savez_compressed(dest/'fit.npz',parameters=result.x,world=world,bounds=fitter.bounds)
            row=dict(**case,soft=previous['after'],after=measured,decoded=decoded,solver_success=bool(result.success),solver_status=int(result.status),message=str(result.message),
                iterations=result.nit,seconds=time.perf_counter()-begin,objective_after=float(result.fun),inequalities=info,
                within_pose_bounds=bounds_ok,geometry_screen_passed=geometry_ok,pose_screen_passed=bool(result.success and bounds_ok and geometry_ok),
                roundtrip=roundtrip,candidate_sha256=sha256(dest/'candidate.glb'),fit_sha256=sha256(dest/'fit.npz'),quality_approved=False)
            rows.append(row);save(dest/'result.json',row);save(output/'results.json',dict(rows=rows))
            manifest.append(dict(id=case['id'],path=str((dest/'candidate.glb').resolve()),sha256=row['candidate_sha256'],frames=2,fps=30,sample_by_time=True))
            save(output/'pipeline.json',dict(status='fitting',completed=len(rows),at=now()))
            print(case['id'],dict(passed=row['pose_screen_passed'],floor_mm=decoded['floor_depth_m']*1000,contact_mm=decoded['contact_error_max_m']*1000,status=result.status),flush=True)
    save(output/'manifest.json',dict(cases=manifest));save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    run(a.source.resolve(),a.output.resolve())
