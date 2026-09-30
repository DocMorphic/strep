"""Continue a bound paired correction with refreshed geometry and original limits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def selected_controls(study, result):
    path = study/'trials.json'
    if sha256(path) != result['trials_sha256']: raise ValueError('Selected trial evidence changed')
    matches = [r for r in read(path) if r['folder'] == result['selected']]
    if len(matches) != 1 or matches[0]['accepted_local_step'] is not True or matches[0]['reasons']:
        raise ValueError('One previously accepted local correction required')
    controls = np.asarray(matches[0]['controls'], float)
    if controls.ndim != 1 or not len(controls) or len(controls)%3 or not np.isfinite(controls).all():
        raise ValueError('Finite cumulative control triples required')
    return controls


def run(study, output, reuse_current=None):
    from diagnose_scene_pair_limits import load_bound_study, constraint_population
    from scene_pair_problem import load_actors, ScenePairProblem
    from scene_pair_relinearization import refreshed_problem, angular_at, retain_original_surfaces
    from angular_motion_rows import AngularMotionRows
    from refined_reserve_inputs import install_refined_models
    from study_scene_pair_fit import METHODS, exported_motion
    from build_guarded_pair_witnesses import query
    from coupled_pair_reserve import tightened_radii
    from coupled_pair_proposal import solve
    from joint_angular_rates import compare_angular_rates
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh relinearization study required')
    request, previous, files = load_bound_study(study); result = read(study/'result.json')
    controls = selected_controls(study, result)
    files[str(study/'trials.json')] = result['trials_sha256']
    if sha256(study/'margins.npz') != result['margins_sha256']: raise ValueError('Bound margins changed')
    files[str(study/'margins.npz')] = result['margins_sha256']
    with np.load(study/'margins.npz', allow_pickle=False) as archive: margins = dict(archive)
    _, actors = load_actors(Path(request['prepared_request']).parent)
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in actors]
    install_refined_models(actors, request['curve_actors'])
    samples = [read(study/'source'/n) for n in read(study/'source-index.json')]
    problem = ScenePairProblem(actors, samples); parts = problem.split(controls)
    worlds = [a['model'].world(p) for a,p in zip(actors,parts)]
    recovered={}
    if reuse_current is not None:
        from recover_pair_geometry import recover_current
        recovered,recovered_files=recover_current(reuse_current,study,controls,files,actors,worlds)
        files.update(recovered_files)
    output.mkdir(); (output/'implementation').mkdir(); (output/'current').mkdir()
    methods = {}
    for name in sorted(set(METHODS)|{'study_scene_pair_relinearization.py','scene_pair_relinearization.py',
            'refined_reserve_inputs.py','diagnose_scene_pair_refinement.py','diagnose_scene_pair_limits.py','bound_evidence.py','coupled_pair_reserve.py','recover_pair_geometry.py'}):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name); methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,
        cumulative_controls=controls.tolist(),incremental_trust_degrees=.5,scale=.025,regularizer=5e-8,
        recovered_from=None if reuse_current is None else str(Path(reuse_current).resolve()),recovered_samples=len(recovered),
        scope='One continuation step with refreshed continuous-model witnesses. Original native budgets, motion bins, protected keys and surface bounds remain. Prior empirical margins are proposal aids only; every decoded trial is independently checked. No automatic publication or release approval.',quality_approved=False))
    current=[]; bindings={}; reused=0
    for index, source in enumerate(samples):
        if index in recovered:
            row,unchanged=recovered[index];reused+=int(unchanged)
            path=output/'current'/f'sample-{index:03d}.json';save(path,row)
            bindings[path.name]=sha256(path);current.append(row)
            continue
        if all(np.array_equal(w[index],a['model'].source_world[index]) for a,w in zip(actors,worlds)):
            row=source; reused+=1
        else:
            points=[a['rig'].vertices(w[index])@a['rotation'].T+a['translation'] for a,w in zip(actors,worlds)]
            directions=[dict(source=s,target=t,**query(points[s],points[t],actors[t]['faces'])) for s,t in [(0,1),(1,0)]]
            row=dict(sample=index,time_s=source['time_s'],directions=directions,floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points])
        path=output/'current'/f'sample-{index:03d}.json'; save(path,row); bindings[path.name]=sha256(path); current.append(row)
        save(output/'progress.json',dict(status='refreshing',completed=index+1,total=len(samples),unchanged_samples_reused=reused))
        if (index+1)%10==0: print(dict(phase='refreshing',completed=index+1,total=len(samples),reused=reused),flush=True)
    save(output/'current-index.json',bindings)
    original, refreshed=refreshed_problem(actors,samples,current)
    save(output/'progress.json',dict(status='linearizing'))
    linear=refreshed.linearize(controls); old=original.linearize(controls)
    linear=retain_original_surfaces(linear,old)
    direction=np.random.default_rng(1409).normal(size=problem.size)*1e-6
    moved_worlds=[a['model'].world(p) for a,p in zip(actors,problem.split(controls+direction))]
    moved=np.r_[refreshed.surface_rows(moved_worlds)['gaps'],original.surface_rows(moved_worlds)['gaps']]
    error=float(np.abs(moved-linear['gaps']-linear['gap_jacobian']@direction).max())
    if error>1e-9: raise ValueError('Refreshed surface directional derivative failed')
    save(output/'surface-proof.json',dict(cumulative_control_linearization=True,directional_error_m=error))
    linear, proofs=angular_at(actors,policies,linear,controls)
    save(output/'angular-proof.json',proofs)
    for key in ['radii','kinds']: np.testing.assert_array_equal(linear[key],previous[key])
    linear['radii']=tightened_radii(linear['radii'],margins['reserve'],linear['kinds'])
    np.savez_compressed(output/'linearization.npz',**linear)
    population=constraint_population(linear)
    delta,solver=solve(**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},
        **{k:population[k] for k in ['vectors','jacobians','radii']},norm_tolerances=population['tolerances'],
        trust=np.deg2rad(.5),scale=.025,regularizer=5e-8)
    save(output/'solver.json',dict(solver=solver,increment=None if delta is None else delta.tolist()))
    print(dict(phase='solved',**solver),flush=True); trials=[]
    if delta is not None:
        for index,factor in enumerate([1.,.5,.25,.125,.0625]):
            candidate=controls+factor*delta
            records,decoded,bounds=exported_motion(original,candidate,output/f'trial-{index}')
            fresh=refreshed.surface_rows(decoded)
            angular=[]
            for actor,world,policy in zip(actors,decoded,policies):
                joints=actor['rig'].joints
                names=[actor['rig'].document['nodes'][j]['name'] for j in joints]
                angular.append(dict(actor=actor['name'],rates=compare_angular_rates(
                    actor['model'].source_world[:,joints,:,:][:,:,:3,:3],world[:,joints,:,:][:,:,:3,:3],
                    actor['model'].times,policy.knots,names,speed_tolerance=1e-5,acceleration_tolerance=1e-5)))
            reasons=[]
            if any(r['rate_failures'] for r in records): reasons.append('exported_motion')
            if any(not r['preserved'] for r in records): reasons.append('preservation_or_budget')
            if max(bounds.values())>1e-6: reasons.append('original_surface_bounds')
            if any(v['exceeding_observations'] for a in angular for v in a['rates'].values()): reasons.append('exported_angular_motion')
            fresh_excess=float(np.maximum(-fresh['gaps']-fresh['depth_caps'],0).max(initial=0))
            if fresh_excess>1e-6: reasons.append('refreshed_surface_planes')
            trial=dict(factor=factor,controls=candidate.tolist(),actors=records,angular_rates=angular,bounds=bounds,
                refreshed_plane_excess_m=fresh_excess,reasons=reasons,preliminary_pass=not reasons,
                requires_full_mesh_and_engine_validation=True,accepted_for_publication=False,quality_approved=False)
            save(output/f'trial-{index}'/'review.json',trial); trials.append(trial); save(output/'trials.json',trials)
            print(dict(phase='decoded',factor=factor,reasons=reasons),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest: raise ValueError('Continuation input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest: raise ValueError('Continuation method changed')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),
        current_index_sha256=sha256(output/'current-index.json'),linearization_sha256=sha256(output/'linearization.npz'),
        solver_sha256=sha256(output/'solver.json'),trials_sha256=sha256(output/'trials.json') if trials else None,
        unchanged_samples_reused=reused,recovered_samples=len(recovered),
        fresh_directional_queries=2*sum(i not in recovered and not all(np.array_equal(w[i],a['model'].source_world[i]) for a,w in zip(actors,worlds)) for i in range(len(samples))),
        preliminary_passes=sum(t['preliminary_pass'] for t in trials),accepted_for_publication=False,quality_approved=False))
    save(output/'progress.json',dict(status='complete')); print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--reuse-current',type=Path);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1): run(a.study,a.output,a.reuse_current)
