"""Compare batched fractional derivatives with authoritative whole-FK differences."""
import argparse
import time
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from paired_palm_region import RegionActor
from paired_hand_trajectory import TrajectoryActor
from batched_fractional_skin import BatchedFractionalActor


def run(study,output,dense_from=None):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier derivative experiment')
    request=read(study/'request.json');initial=read(study/'initial-parameters.json')
    if sha256(request['source_scene'])!=request['source_scene_sha256']:raise ValueError('Scene changed')
    scene=read(request['source_scene'])['scene'];patches=read(study/'palm-region.json');matrix=np.asarray(initial['basis'])
    if sha256(study/'palm-region.json')!=request['palm_region_sha256']:raise ValueError('Patches changed')
    output.mkdir();(output/'implementation').mkdir()
    names=['verify_batched_fractional_skin.py','batched_fractional_skin.py','fast_path_skin.py','paired_hand_trajectory.py','paired_hand_clearance.py','paired_hand_fit.py','paired_palm_region.py','rig_asset.py','target_rig_contact.py','rig_clearance_fit.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    frames=[44.5,45.,45.5,50.25,64.5,65.5,66.5,67.5,68.5,69.5,72.5,73.5,74.5,75.,75.5,99.75,104.5,105.,105.5]
    batches=[(f,96) for f in frames];witness=None
    if dense_from is not None:
        history=Path(dense_from)/'history.json';body=history.read_bytes();(output/'witness-history.json').write_bytes(body)
        initial_history=read(output/'witness-history.json')['iterations'][0]
        ranked=sorted(initial_history['window'],key=lambda s:max(c['active_constraints'] for c in s['collision']),reverse=True)[:2]
        batches=[]
        for sample in ranked:
            count=max(c['active_constraints'] for c in sample['collision'])
            if count<=0 or float(sample['frame']).is_integer():raise ValueError('Need active fractional witness frames')
            batches.extend((sample['frame'],n) for n in [96,count,3*count])
        witness=dict(source=str(history.resolve()),snapshot_sha256=sha256(output/'witness-history.json'),scope='Synthetic uniformly spaced skin-index batches sized from the two largest per-direction active counts and their triangle-vertex expansion. These are not regenerated collision correspondences or a full solver timing.')
    save(output/'request.json',dict(at=now(),source_request_sha256=sha256(study/'request.json'),initial_parameters_sha256=sha256(study/'initial-parameters.json'),
        sample_batches=[dict(frame=f,vertices=n) for f,n in batches],dense_witness=witness,parameter_variants=['initializer','deterministic_small_perturbation'],repeats=3,
        position_tolerance_m=1e-11,derivative_element_tolerance=2e-6,random_seed=7481,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False))
    rows=[];rng=np.random.default_rng(7481)
    with threadpool_limits(limits=1):
        for actor_index,label in enumerate(['A','B']):
            source=request['sources'][label];path=Path(source['raw_glb']);local_path=study/f'{label}-source-local.npz'
            if sha256(path)!=source['raw_glb_sha256'] or sha256(local_path)!=source['local_npz_sha256']:raise ValueError('Source changed')
            rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local']
            primitive=rig.document['meshes'][0]['primitives'][0];faces=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            actor=RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,scene['actors'][label]['transform'],patch=patches[label])
            old,new=TrajectoryActor(actor,matrix),BatchedFractionalActor(actor,matrix)
            # Hand/forearm witnesses plus a uniform whole-skin sample exercise
            # blended influences and vertices unaffected by the edited chain.
            small_ids=np.unique(np.r_[patches[label]['vertices'][:32],np.linspace(0,old.rig.primitives[0]['positions'].shape[0]-1,64,dtype=int)])
            start=np.asarray(initial['controls'])[actor_index*60:(actor_index+1)*60]
            for variant,x in [('initializer',start),('deterministic_small_perturbation',start+rng.normal(0,.003,len(start)))]:
                for frame,count in batches:
                    ids=small_ids if count==96 else np.linspace(0,len(rig.primitives[0]['positions'])-1,count,dtype=int)
                    p,j=old.skin_pair(frame,x,ids);q,k=new.skin_pair(frame,x,ids)
                    error=float(np.abs(p-q).max());jac_error=float(np.abs(j-k).max())
                    if error>1e-11 or jac_error>2e-6:raise ValueError(f'Derivative mismatch {label}/{variant}/{frame}: {error}, {jac_error}')
                    timing={}
                    for name,adapter in [('finite_difference',old),('batched_fractional',new)]:
                        times=[]
                        for repeat in range(3):
                            adapter.cache=None
                            begin=time.perf_counter();adapter.skin_pair(frame,x,ids);times.append(time.perf_counter()-begin)
                        timing[name]=float(np.median(times))
                    rows.append(dict(actor=label,variant=variant,frame=frame,vertices=len(ids),position_error_m=error,derivative_max_element_error=jac_error,
                        median_seconds=timing,speedup=timing['finite_difference']/timing['batched_fractional']))
                    save(output/'results.json',dict(rows=rows,quality_approved=False))
    save(output/'completion.json',dict(at=now(),comparisons=len(rows),results_sha256=sha256(output/'results.json'),
        max_position_error_m=max(r['position_error_m'] for r in rows),max_derivative_error=max(r['derivative_max_element_error'] for r in rows),
        median_fractional_speedup=float(np.median([r['speedup'] for r in rows if not r['frame'].is_integer() and 45<r['frame']<105])),
        speedup_by_vertex_count={str(n):float(np.median([r['speedup'] for r in rows if r['vertices']==n and not r['frame'].is_integer() and 45<r['frame']<105])) for n in sorted({r['vertices'] for r in rows})},
        quality_approved=False,scope='Point/Jacobian equivalence at declared frames and parameter variants; three-repeat local timing in the current busy machine. Same local SLERP/time convention and finite-difference step; batch local derivatives followed by FK product rule. Integer skin route retains the prior analytic implementation. Not an end-to-end solver speedup or motion-quality result.'))
    print(read(output/'completion.json'),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);p.add_argument('--dense-from',type=Path);a=p.parse_args();run(a.study,a.output,a.dense_from)
