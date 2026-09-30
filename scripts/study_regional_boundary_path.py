"""Fit approach/release paths jointly in time while protecting grasp and root."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from regional_boundary_path import BoundaryPath,assemble
from scene_solver_context import context_primitives
from build_soma_preview import make_preview
from gltf_tools import write_glb


def run(study,output,saved_fit=None):
    torch.set_num_threads(2); study,output=Path(study).resolve(),Path(output).resolve()
    prior,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or result['candidate_sha256']!=sha256(study/'motion.npz') or result['protocol_sha256']!=sha256(study/'protocol.json'):
        raise ValueError('Completed unchanged input required')
    if 'floor_settings' not in prior:raise ValueError('Verified boundary and prefix floor input required')
    inputs=dict(prior['inputs']);inputs.update({str(study/n):sha256(study/n) for n in ['protocol.json','result.json','motion.npz','source-motion.npz','source.glb','authored-scene.json']})
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in prior['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Input implementation snapshot changed')
    p=RegionalPoseProblem(ROOT/prior['fit'],prior['reference_frame']);source=dict(np.load(study/'motion.npz',allow_pickle=False))
    objects=context_primitives(p.context)
    if len(objects)!=1:raise ValueError('One cylinder required for this path experiment')
    geometry,obj=objects[0];track=(geometry,np.array(obj['positions_m']),np.array(obj['rotations']))
    left,right=prior['edited_interval'];start,end=prior['projection_interval']
    windows=[list(range(left+1,start)),list(range(end+1,right))]
    settings=dict(rotation_curvature_scale=.02,position_curvature_scale_m=.002,position_reference_scale_m=.05,
                  geometry_scale_m=.00005,clearance_reserve_m=.0001,maximum_iterations=120,maximum_evaluations=180,
                  maximum_seconds_per_window=180.,maximum_rss_bytes=3*1024**3,minimum_available_bytes=768*1024**2)
    saved_rows=None
    if saved_fit is not None:
        saved_fit=Path(saved_fit).resolve();old=read(saved_fit/'protocol.json')
        if old['path_input']!=study.relative_to(ROOT).as_posix() or old['path_windows']!=windows or old['path_settings']!=settings:
            raise ValueError('Saved optimization belongs to another path problem')
        for file,digest in old['inputs'].items():
            if sha256(file)!=digest:raise ValueError('Saved optimization input changed')
        for name,digest in old['implementation'].items():
            if sha256(saved_fit/'implementation'/name)!=digest:raise ValueError('Saved optimization method changed')
        saved_rows=read(saved_fit/'windows.json')
        if [r['frames'] for r in saved_rows]!=windows:raise ValueError('Incomplete saved windows')
        inputs.update({str(saved_fit/n):sha256(saved_fit/n) for n in ['protocol.json','windows.json']})
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for file in (ROOT/'scripts').glob('*.py'):shutil.copyfile(file,snap/file.name)
    protocol={**prior,**dict(at=now(),path_input=study.relative_to(ROOT).as_posix(),path_windows=windows,path_settings=settings,optimization_origin=None if saved_fit is None else saved_fit.relative_to(ROOT).as_posix(),
        inputs=inputs,implementation={q.name:sha256(q) for q in snap.iterdir()},
        scope='Joint temporal fit of each boundary with two protected neighbor keys. Only eight arm joints on declared free keys change; grasp/guard/non-arm rotations/root exact. Source-relative native arm norms by construction. Full-skin quarter-frame cylinder/floor and native position/rotation curvature are soft objectives, not guaranteed feasibility or exact endpoint velocity constraints. Fresh exported audit required.',quality_approved=False)}
    save(output/'protocol.json',protocol);candidate={k:v.copy() for k,v in source.items()};rows=[];total=time.monotonic()
    for frames in windows:
        path=BoundaryPath(p,source,frames,track,settings);began=time.monotonic();peak=0;history=[];best=None;last=None
        if saved_rows is not None:
            saved=saved_rows[windows.index(frames)]
            best=(saved['best_objective'],np.array(saved['best_raw']),saved['best_terms'])
            last=np.array(saved['last_raw']);solver=saved['solver'];proof=saved['derivative_proof'];history=saved['history'];peak=saved['peak_rss_bytes']
        else:
            def guard():
                nonlocal peak
                peak=max(peak,psutil.Process().memory_info().rss)
                if time.monotonic()-began>settings['maximum_seconds_per_window'] or peak>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:
                    raise TimeoutError('Boundary path resource guard')
            initial,gradient,terms=path.pair(path.initial);guard()
            direction=np.random.default_rng(330+frames[0]).normal(size=len(path.initial));direction/=np.linalg.norm(direction);h=1e-6
            with torch.no_grad():
                plus=float(sum(path.terms(p.t(path.initial+h*direction)).values()));minus=float(sum(path.terms(p.t(path.initial-h*direction)).values()))
            derivative=(plus-minus)/(2*h);prediction=float(gradient@direction)
            np.testing.assert_allclose(prediction,derivative,atol=.002,rtol=.0002)
            proof=dict(finite_difference=derivative,automatic=prediction,absolute_error=abs(derivative-prediction),initial_objective=initial,initial_terms=terms)
            best=(initial,path.initial.copy(),terms);last=path.initial.copy()
            def pair(raw):
                nonlocal best,last
                guard();value,deriv,components=path.pair(raw);last=raw.copy()
                if value<best[0]:best=(value,raw.copy(),components)
                history.append(dict(evaluation=len(history)+1,value=value,terms=components,seconds=time.monotonic()-began))
                save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,window=frames,evaluation=len(history),best_objective=best[0],seconds=time.monotonic()-began))
                if len(history)%10==0:print(dict(window=frames[0],evaluations=len(history),best=best[0],seconds=time.monotonic()-began),flush=True)
                return value,deriv
            try:
                fit=minimize(pair,path.initial,jac=True,method='L-BFGS-B',options=dict(maxiter=settings['maximum_iterations'],maxfun=settings['maximum_evaluations'],maxls=20,ftol=1e-12,gtol=1e-7,maxcor=20))
                solver=dict(success=bool(fit.success),message=str(fit.message),iterations=int(fit.nit),evaluations=int(fit.nfev))
            except TimeoutError as exc:solver=dict(success=False,message=str(exc),evaluations=len(history))
        # Keep both the last trial and best objective; neither is quality-approved.
        locals=source['local_rot_mats'].astype(float).copy()
        with torch.no_grad():selected=path.locals(p.t(best[1])).numpy()
        locals[frames]=selected[np.array(frames)-path.support[0]]
        rebuilt=assemble(source,locals,frames,p.parents)
        for key in candidate:candidate[key][frames]=rebuilt[key][frames]
        rows.append(dict(frames=frames,solver=solver,derivative_proof=proof,history=history,best_raw=best[1].tolist(),
                         last_raw=last.tolist(),best_objective=best[0],best_terms=best[2],seconds=saved['seconds'] if saved_rows is not None else time.monotonic()-began,peak_rss_bytes=peak))
        save(output/'windows.json',rows)
    changed=[f for frames in windows for f in frames];locked=np.setdiff1d(np.arange(prior['frame_count']),changed)
    for key in source:np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    np.testing.assert_array_equal(source['root_positions'],candidate['root_positions'])
    frozen=np.setdiff1d(np.arange(len(p.names)),path.arms)
    np.testing.assert_array_equal(source['local_rot_mats'][:,frozen],candidate['local_rot_mats'][:,frozen])
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:shutil.copyfile(study/name,output/name)
    np.savez(output/'motion.npz',**candidate);save(output/'recipe.json',dict(kind='coupled-cylinder-boundary-v1',windows=rows,quality_approved=False))
    doc,binary,_,_=make_preview(p.skin,candidate,np.zeros(3),repeat=False);write_glb(output/'candidate.glb',doc,binary)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during fitting')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed during fitting')
    save(output/'result.json',dict(at=now(),status='complete',solver_converged=all(r['solver']['success'] for r in rows),windows=rows,
         protected_frames_exact=len(locked),seconds=time.monotonic()-total,quality_approved=False,candidate_sha256=sha256(output/'motion.npz'),
         candidate_glb_sha256=sha256(output/'candidate.glb'),source_glb_sha256=sha256(output/'source.glb'),recipe_sha256=sha256(output/'recipe.json'),
         authored_scene_sha256=sha256(output/'authored-scene.json'),protocol_sha256=sha256(output/'protocol.json')))
    save(output/'progress.json',dict(status='complete',seconds=time.monotonic()-total));print('Completed boundary path experiment',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--saved-fit',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.saved_fit)
