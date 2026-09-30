"""Bounded relinearization with original-reference limits and retained trials."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_problem import PairProblem
from coupled_pair_proposal import solve
from coupled_pair_reserve import tightened_radii
from coupled_continuation_checks import ContinuationReview
from coupled_continuation_policy import acceptance


def run(start,geometry,witnesses,output):
    start,geometry,output=map(lambda p:Path(p).resolve(),[start,geometry,output])
    if output.exists():raise ValueError('Preserve earlier continuation')
    problem=PairProblem(witnesses);sr,sp=read(start/'result.json'),read(start/'request.json');ss=read(start/'solver.json')
    gp,gr=read(geometry/'request.json'),read(geometry/'verification.json')
    if sr['status']!='complete' or sr['selected'] is None or sr['request_sha256']!=sha256(start/'request.json') or sr['solver_sha256']!=sha256(start/'solver.json'):
        raise ValueError('Completed bound starting proposal required')
    if not sp['penetrating_surface_norms'] or sp['fitting_reserve'] is None:raise ValueError('Validated full-vector starting condition required')
    if gr['request_sha256']!=sha256(geometry/'request.json') or gr['samples_sha256']!=sha256(geometry/'samples.json') or gr['samples']!=57 or gr['fresh_directional_queries']!=114 or gr['cap_failures_over_1e_6']!=0 or gr['maximum_floor_increase_m']>1e-6:
        raise ValueError('Completed nonregressing geometry starting condition required')
    reserve=Path(sp['fitting_reserve']);rp,rr=read(reserve/'request.json'),read(reserve/'result.json')
    if rr['request_sha256']!=sha256(reserve/'request.json') or rr['reserve_sha256']!=sha256(reserve/'reserve.npz'):raise ValueError('Bound reserve required')
    inputs={**problem.inputs,**sp['inputs'],**gp['inputs'],**rp['inputs']}
    for folder,names in [(start,['result.json','request.json','solver.json','linearization.npz']),
                         (geometry,['request.json','verification.json','samples.json']),(reserve,['request.json','result.json','reserve.npz'])]:
        for name in names:inputs[str(folder/name)]=sha256(folder/name)
    for check in sr['selected']['actors']:
        path=start/'candidate'/(check['actor']+'.glb')
        if gp['inputs'].get(str(path))!=check['sha256']:raise ValueError('Starting geometry uses another candidate')
        inputs[str(path)]=check['sha256']
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Bound continuation input changed')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['study_coupled_pair_continuation.py','coupled_continuation_checks.py','coupled_continuation_policy.py','coupled_pair_problem.py','coupled_pair_proposal.py',
        'coupled_pair_reserve.py','coupled_surface_norms.py','paired_approach_basis.py','paired_surface_witness.py','paired_guarded_temporal.py','paired_temporal_neighbor.py',
        'study_paired_guarded_temporal.py','study_paired_temporal_neighbor.py','audit_scene_joint_rates.py','verify_paired_stage_rates.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','conic_root_descent.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    request=dict(at=now(),inputs=inputs,implementation={name:sha256(snapshot/name) for name in methods},start=str(start),maximum_steps=12,maximum_seconds=900,
        trust_degrees_per_step=.2,line_factors=[1.,.5,.25,.125,.0625],minimum_retained_distance_improvement_m=1e-6,
        original_edit_limit_degrees=5.,export_edit_tolerance_degrees=1e-4,motion_tolerance=1e-5,surface_comparison_tolerance_m=1e-6,
        reserve=str(reserve),windows=problem.windows,quality_approved=False,
        scope='Original clips, edit balls, per-joint motion caps and per-time depth allowances remain fixed across every step. Relinearize kinematics at total controls; never reset the edit origin. Reuse empirically calibrated motion fitting margins by identical row layout, not as certified bounds. Fixed initial penetrating-witness norms and all scalar gaps screen every exported trial; only complete fresh mesh queries can qualify the final candidate. Stop on exhausted line search or bounded resources; no convergence claim.')
    save(output/'request.json',request)
    with np.load(start/'linearization.npz',allow_pickle=False) as archive:original=dict(archive)
    with np.load(reserve/'reserve.npz',allow_pickle=False) as archive:margins=archive['reserve'].copy()
    controls=np.array(ss['controls'])*sr['selected']['factor'];review=ContinuationReview(problem,original['gaps'])
    selected=review.export_and_check(controls,output/'start')
    for check in selected['actors']:
        if check['sha256']!=sha256(start/'candidate'/(check['actor']+'.glb')):raise ValueError('Starting controls do not reproduce selected exports')
        check['path']='start/'+check['path']
    if any(c['rate_failures'] or c['maximum_original_edit_degrees']>5.0001 or not c['preservation']['original_finger_limits_passed'] for c in selected['actors']) or selected['surface']['maximum_cap_excess_m']>1e-6:
        raise ValueError('Starting candidate does not pass unchanged exported gates')
    selected['iteration']=0;save(output/'start-review.json',selected)
    initial_peak=selected['surface']['peak_m'];peak=initial_peak;history=[];trial_count=0;peak_count=selected['verified_peak_values'];replay_error=selected['maximum_replay_error']
    started=time.monotonic();termination='maximum_steps'
    for iteration in range(1,request['maximum_steps']+1):
        if time.monotonic()-started>request['maximum_seconds']:termination='time_limit';break
        folder=output/f'iteration-{iteration:02d}';folder.mkdir();save(output/'progress.json',dict(status='linearizing',iteration=iteration,accepted_steps=len(history),retained_peak_m=peak))
        linear=problem.linearize(controls,include_surface_vectors=True)
        for key in ['radii','kinds','depth_caps']:np.testing.assert_array_equal(linear[key],original[key])
        inside=review.initial_inside
        vectors=np.concatenate([linear['vectors'],linear['surface_vectors'][inside]])
        jacobians=np.concatenate([linear['jacobians'],linear['surface_jacobians'][inside]])
        radii=np.r_[tightened_radii(linear['radii'],margins,linear['kinds']),linear['depth_caps'][inside]]
        np.savez_compressed(folder/'linearization.npz',**linear)
        step,solver=solve(**{key:linear[key] for key in ['gaps','gap_jacobian','depth_caps']},vectors=vectors,jacobians=jacobians,radii=radii,
                          trust=np.deg2rad(.2),norm_tolerances=np.r_[np.where(linear['kinds']=='edit',1e-8,1e-6),np.full(inside.sum(),1e-8)])
        save(folder/'solver.json',dict(at=now(),base_controls=controls.tolist(),step=None if step is None else step.tolist(),solver=solver,linearization_sha256=sha256(folder/'linearization.npz')))
        if step is None:termination='no_accepted_affine_proposal';break
        accepted=None;trials=[];save(folder/'trials.json',trials)
        for index,factor in enumerate(request['line_factors']):
            if time.monotonic()-started>request['maximum_seconds']:termination='time_limit';break
            trial_folder=folder/f'trial-{index}';candidate_controls=controls+step*factor
            candidate=review.export_and_check(candidate_controls,trial_folder);trial_count+=1
            peak_count+=candidate['verified_peak_values'];replay_error=max(replay_error,candidate['maximum_replay_error'])
            for check in candidate['actors']:check['path']=(trial_folder/check['path']).relative_to(output).as_posix()
            decision=acceptance(peak,candidate['surface']['peak_m'],candidate['surface']['maximum_cap_excess_m'],
                [c['rate_failures'] for c in candidate['actors']],[c['maximum_original_edit_degrees'] for c in candidate['actors']],
                [c['preservation']['original_finger_limits_passed'] for c in candidate['actors']])
            record=dict(iteration=iteration,factor=factor,controls=candidate_controls.tolist(),decision=decision,**candidate);trials.append(record)
            save(folder/'trials.json',trials);print(dict(iteration=iteration,factor=factor,peak_mm=candidate['surface']['peak_m']*1000,cap_excess_m=candidate['surface']['maximum_cap_excess_m'],reasons=decision['reasons']),flush=True)
            if decision['accepted']:accepted=record;break
        if accepted is None:
            if termination!='time_limit':termination='exported_line_search_exhausted'
            break
        controls=np.array(accepted['controls']);selected=accepted;peak=selected['surface']['peak_m'];history.append(selected)
        save(output/'accepted.json',history);save(output/'progress.json',dict(status='running',accepted_steps=len(history),retained_peak_m=peak))
        if peak<=.005:termination='retained_witness_screen_met';break
    cases=[]
    for variant in ['input','candidate']:(output/variant).mkdir()
    for actor,check in zip(problem.actors,selected['actors']):
        for variant,source in [('input',actor['source']),('candidate',output/check['path'])]:
            target=output/variant/(actor['name']+'.glb');shutil.copyfile(source,target)
            cases.append(dict(id=variant+'-'+actor['name'],path=target.relative_to(output).as_posix(),sha256=sha256(target),frames=150,fps=30,sample_by_time=True))
    save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during continuation')
    for name,digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during continuation')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),termination=termination,accepted_steps=len(history),trial_count=trial_count,
        initial_retained_peak_m=initial_peak,final_retained_peak_m=peak,total_controls=controls.tolist(),selected=selected,elapsed_seconds=time.monotonic()-started,
        verified_peak_values=peak_count,maximum_replay_error=replay_error,geometry_checked=False,quality_approved=False))
    save(output/'progress.json',dict(status='complete'));print(dict(status='complete',termination=termination,accepted_steps=len(history),peak_mm=peak*1000),flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['start','geometry','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.start,a.geometry,a.witnesses,a.output)
