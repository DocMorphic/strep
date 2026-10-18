"""Guarded scene fitting; all original and qualified-incumbent passes survive.

The v1 source stays intact for archived studies. Sampled pair constraints guide
optimization; complete policy geometry/contact/pose checks decide comparisons.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.optimize import minimize
from native_mesh_prop_scene_fit import SceneGuidance,signed,EvaluationLimit,METHODS as V1_METHODS
from native_mesh_prop_pose import GripPoseEdit,conditions,metrics,pareto_improvement
from native_mesh_prop_scene import MeshPropScene,_json,guarded_output
from native_observation_archive import ObservationArchive,verify
from strep import save,sha256

METHODS=tuple(sorted(set(V1_METHODS)|{'native_mesh_prop_scene_fit_v2.py'}))


def signed_upper(mesh,points,padding):
    """Complete query near the mesh box, conservative negative bound outside."""
    points=np.asarray(points)
    if points.dtype.kind not in 'fiu' or points.ndim!=2 or points.shape[1]!=3 or not len(points) or not np.isfinite(points).all():raise ValueError('Nonempty finite point array required')
    if type(padding) not in (float,int) or not np.isfinite(padding) or padding<=0:raise ValueError('Positive finite padding required')
    if not mesh.is_volume:raise ValueError('Closed outward guidance volume required')
    lo,hi=mesh.bounds;distance=np.linalg.norm(np.maximum(np.maximum(lo-points,points-hi),0),axis=1);values=-distance+padding
    reserve=max(padding,1e-7);ids=np.flatnonzero(np.all(points>=lo-reserve,axis=1)&np.all(points<=hi+reserve,axis=1));values[ids]=signed(mesh,points[ids])+padding
    if not np.isfinite(values).all():raise ValueError('Finite signed upper bounds required')
    return float(values.max())


def passing_entities(report,prop,time_s):
    rows=[r for r in report['samples'] if r['time_s']==time_s]
    if len(rows)!=1:raise ValueError('Exactly one complete edited-key geometry sample required')
    result=[];seen=set();edited=('prop',prop)
    for pair in rows[0]['mesh_pairs']:
        keys=[tuple(pair['left']),tuple(pair['right'])]
        if edited not in keys:continue
        other=keys[1] if keys[0]==edited else keys[0];name=':'.join(other)
        if name in seen or type(pair['passed']) is not bool:raise ValueError('Unique explicit pair decisions required')
        seen.add(name)
        if pair['passed']:result.append(name)
    return result


class PairGuards:
    def __init__(self,guide,names,reference):
        available={e['name']:e for e in guide.entities}
        if not isinstance(names,(list,tuple)) or any(not isinstance(n,str) or n not in available for n in names) or len(set(names))!=len(names):raise ValueError('Distinct existing mesh entity guards required')
        self.guide=guide;self.names=list(names);self.active=[e for e in guide.entities if e['name'] in names and not e['disjoint']]
        self.reference=guide.edit._value(reference)
        if not guide.edit.evaluate(self.reference)['report']['native_pose_permissions_pass']:raise ValueError('Guard reference must preserve original native permissions')
        self.initial_upper=self.upper(self.reference);self.limits=np.maximum(0,self.initial_upper)

    def upper(self,value):
        response=self.guide.edit.evaluate(value);p=response['position_m'];r=response['rotation_matrix'];world=self.guide.prop_points@r.T+p;pad=self.guide.policy['limits']['surface_tolerance_m'];values=[]
        for entity in self.active:
            pair=[signed_upper(entity['mesh'],world,pad)]
            if len(entity['points']):pair.append(signed_upper(self.guide.mesh,(entity['points']-p)@r,pad))
            values.append(max(pair))
        return np.asarray(values,float)

    def describe(self):
        return dict(guarded_entities=self.names,active_entities=[e['name'] for e in self.active],reference_controls=self.reference.tolist(),reference_signed_upper_m=self.initial_upper.tolist(),sampled_upper_limits_m=self.limits.tolist(),constraint_scale_m=.01,full_collision_certificate=False,author_permissions_changed=False)


def optimize(guide,initial,guards,output,*,maximum_evaluations=128,maximum_iterations=20):
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=512 or type(maximum_iterations) is not int or not 1<=maximum_iterations<=100:raise ValueError('Bounded evaluation/iteration limits required')
    initial=guide.edit._value(initial)
    if not guide.edit.evaluate(initial)['report']['native_pose_permissions_pass']:raise ValueError('Initial controls must satisfy original native permissions')
    output=Path(output);output.mkdir();history=[];cache={};calls=0
    def measure(x):
        nonlocal calls
        calls+=1;key=tuple(float(v) for v in x)
        if key not in cache:
            if len(history)>=maximum_evaluations:raise EvaluationLimit()
            value=np.r_[x,initial[3]];row=guide.evaluate(value);upper=guards.upper(value);margins=(guards.limits-upper)/.01
            row.update(evaluation=len(history),sampled_pair_upper_m=upper.tolist(),sampled_pair_guard_margins=margins.tolist(),sampled_pair_guards_pass=bool(np.all(margins>=0)))
            history.append(row);cache[key]=row;save(output/'history.json',history)
        return cache[key]
    measure(initial[:3]);optimizer=None;reason='rotation_locked'
    if guide.edit._angle:
        try:
            answer=minimize(lambda x:measure(x)['energy'],initial[:3],method='SLSQP',bounds=[(-1.,1.)]*3,constraints=[dict(type='ineq',fun=lambda x:np.r_[guide.margins(np.r_[x,initial[3]]),measure(x)['sampled_pair_guard_margins']])],options=dict(maxiter=maximum_iterations,ftol=1e-10,eps=1e-4))
            optimizer=dict(success=bool(answer.success),status=int(answer.status),message=str(answer.message),controls=np.r_[answer.x,initial[3]].tolist(),iterations=int(answer.nit));reason='optimizer_returned'
        except EvaluationLimit:reason='evaluation_limit'
    valid=[r for r in history if r['native_pose_permissions_pass'] and r['sampled_pair_guards_pass']];best=min(valid,key=lambda r:r['energy']) if valid else None
    result=dict(status='complete',stop_reason=reason,optimizer=optimizer,unique_guidance_evaluations=len(history),measure_calls=calls,maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations,starting_energy=history[0]['energy'],best_guidance_energy=None if best is None else best['energy'],best_guidance_controls=initial.tolist() if best is None else best['controls'],sampled_guard_feasible_found=best is not None,pair_guards=guards.describe(),clearance_fraction_fixed=float(initial[3]),source_rebased=False,geometry_approved=False,quality_approved=False)
    save(output/'result.json',result);return result


def evaluate_probe(edit,policy,folder,item,index):
    value=item['controls'];response=edit.evaluate(value);row=dict(probe=index,**item,native_pose_permissions_pass=response['report']['native_pose_permissions_pass'])
    if not row['native_pose_permissions_pass']:raise ValueError('Postcheck proposal violates original native permissions; no clipping')
    manifest=edit.write(value,folder);candidate=MeshPropScene(manifest)
    bound,arrays=edit.sampled_permissions(candidate,policy);save(folder/'sampled-permissions.json',bound);np.savez_compressed(folder/'sampled-permissions.npz',**arrays)
    contact,arrays=candidate.contact_audit();save(folder/'contacts.json',contact);np.savez_compressed(folder/'contact-observations.npz',**arrays)
    derived=copy.deepcopy(policy);derived['mesh_scene_sha256']=sha256(manifest);save(folder/'policy.json',derived)
    with ObservationArchive(folder/'geometry-observations.npz') as sink:geometry,_=candidate.geometry(derived,observation_sink=sink)
    verify(folder/'geometry-observations.npz');save(folder/'geometry.json',geometry)
    row.update(sampled_pose_permissions_pass=bound['all_sampled_pose_permissions_pass'],all_declared_point_contacts_pass=contact['all_declared_point_contacts_pass'],sampled_geometry_pass=geometry['sampled_conditions_pass'])
    return row,geometry,manifest


def compare(row,geometry,original,protected,baseline_measure,best_measure):
    current=conditions(geometry)
    if current.keys()!=original.keys() or current.keys()!=protected.keys():raise ValueError('Complete original condition identities required')
    measure=metrics(geometry);new_source=sum(original[k] and not current[k] for k in current);new_protected=sum(protected[k] and not current[k] for k in current)
    no_worse=all(measure[k]<=baseline_measure[k] for k in baseline_measure);allowed=bool(row['sampled_pose_permissions_pass'] and row['all_declared_point_contacts_pass'] and new_protected==0 and no_worse)
    row.update(metrics=measure,new_failed_original_conditions=new_source,new_failed_geometry_conditions=new_protected,collision_metrics_no_worse_than_source=no_worse,admissible_for_comparison=allowed,improves_best=bool(allowed and pareto_improvement(measure,best_measure)),sampled_candidate_pass=bool(allowed and row['sampled_geometry_pass']))
    return row


def fit(permissions_path,policy_path,warm_start_path,output,*,maximum_evaluations=128,maximum_iterations=20,backtrack_steps=8):
    if type(backtrack_steps) is not int or not 1<=backtrack_steps<=12:raise ValueError('Explicit line step count1-12 required')
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=512 or type(maximum_iterations) is not int or not 1<=maximum_iterations<=100:raise ValueError('Bounded evaluation/iteration limits required')
    edit=GripPoseEdit(permissions_path);policy_path=Path(policy_path).resolve();policy,policy_digest=_json(policy_path);times,_,_=edit.scene._clock(policy)
    requested_times=times.copy();key_time=edit._item['keyframes'][edit._key]['time_s']
    if not np.any(times==key_time):
        policy['clock']=dict(mode='explicit',times_s=np.unique(np.r_[times,key_time]).tolist());times,_,_=edit.scene._clock(policy)
    warm_start_path=Path(warm_start_path).resolve();warm,digest=_json(warm_start_path)
    if set(warm)!={'schema','permissions_sha256','controls'} or warm['schema']!='strep-prop-source-relative-warm-start-v1' or warm['permissions_sha256']!=sha256(permissions_path):raise ValueError('Original permission-bound warm start required')
    initial=edit._value(warm['controls'])
    if not edit.evaluate(initial)['report']['native_pose_permissions_pass']:raise ValueError('Initial controls violate original native permissions')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh v2 fitting output required')
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();bindings={**edit.inputs,str(policy_path):policy_digest,str(warm_start_path):digest};methods={n:sha256(Path(__file__).parent/n) for n in METHODS}
    for n in METHODS:shutil.copyfile(Path(__file__).parent/n,archive/n)
    save(output/'input.json',dict(schema='strep-native-mesh-prop-scene-fit-v2',inputs_sha256=bindings,implementation_sha256=methods,requested_geometry_clock_s=requested_times.tolist(),geometry_clock_s=times.tolist(),edited_key_added_to_geometry_clock=len(times)>len(requested_times),maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations,backtrack_steps=backtrack_steps,line_fractions=[.5**i for i in range(backtrack_steps)],source_rebased=False,quality_approved=False));save(output/'effective-policy.json',policy)
    table=[dict(kind='original',controls=[0.,0,0,0]),dict(kind='remeasured-original-relative-warm-start',controls=initial.tolist())];history=[];reports=[];manifests=[];best=None;best_measure=None;feasible=None
    for index,item in enumerate(table):
        folder=output/f'probe-{index:03d}';row,geometry,manifest=evaluate_probe(edit,policy,folder,item,index)
        if index==0:
            original=conditions(geometry);protected=original.copy();baseline_measure=metrics(geometry);save(output/'baseline.json',dict(metrics=baseline_measure,conditions=[dict(id=list(k),passed=v) for k,v in original.items()]))
        row=compare(row,geometry,original,protected,baseline_measure,best_measure)
        if row['improves_best']:best=index;best_measure=row['metrics'].copy()
        if row['sampled_candidate_pass'] and feasible is None:feasible=index
        history.append(row);reports.append(geometry);manifests.append(manifest);save(folder/'decision.json',dict(row,original_selected=True,quality_approved=False,release_approved=False));save(output/'history.json',history);print(row,flush=True)
    qualified_initial=history[1]['admissible_for_comparison'];initial_flags=conditions(reports[1])
    if qualified_initial:protected={k:original[k] or initial_flags[k] for k in original}
    save(output/'protected-conditions.json',dict(initial_qualified=qualified_initial,original_passing=sum(original.values()),protected_passing=sum(protected.values()),incumbent_repairs_added=sum(protected[k] and not original[k] for k in original),conditions=[dict(id=list(k),passed=protected[k]) for k in protected]))
    guide=SceneGuidance(edit,policy);save(output/'guidance-summary.json',guide.summary);np.savez_compressed(output/'guidance-surface-points.npz',**guide.arrays)
    names=passing_entities(reports[0],edit._name,guide.time)
    if qualified_initial:
        for name in passing_entities(reports[1],edit._name,guide.time):
            if name not in names:names.append(name)
    guards=PairGuards(guide,names,initial if qualified_initial else [0.,0,0,0]);save(output/'pair-guards.json',dict(reference_kind='qualified-initial' if qualified_initial else 'original',**guards.describe()))
    optimized=optimize(guide,initial,guards,output/'guidance',maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations);target=np.asarray(optimized['best_guidance_controls'])
    if target[3]!=initial[3]:raise ValueError('Optimizer changed fixed authored clearance fraction')
    if optimized['sampled_guard_feasible_found'] and np.any(target!=initial):table += [dict(kind='guarded-guidance-line-proposal',fraction=.5**i,controls=(initial+(.5**i)*(target-initial)).tolist()) for i in range(backtrack_steps)]
    save(output/'candidate-table.json',table)
    for index in range(2,len(table)):
        if feasible is not None:break
        folder=output/f'probe-{index:03d}';row,geometry,_=evaluate_probe(edit,policy,folder,table[index],index);row=compare(row,geometry,original,protected,baseline_measure,best_measure)
        if row['improves_best']:best=index;best_measure=row['metrics'].copy()
        if row['sampled_candidate_pass']:feasible=index
        history.append(row);save(folder/'decision.json',dict(row,original_selected=True,quality_approved=False,release_approved=False));save(output/'history.json',history);print(row,flush=True)
    edit.check_inputs()
    if any(sha256(p)!=d for p,d in bindings.items()) or any(sha256(Path(__file__).parent/n)!=sha256(archive/n) or sha256(archive/n)!=d for n,d in methods.items()):raise ValueError('Original input or method binding changed')
    result=dict(schema='strep-native-mesh-prop-scene-fit-result-v2',status='complete',best_admissible_probe=best,sampled_feasible_probe=feasible,candidates_recorded=len(history),candidate_table_size=len(table),history=history,guidance_evaluations=optimized['unique_guidance_evaluations'],guidance_stop_reason=optimized['stop_reason'],initial_qualified=qualified_initial,incumbent_repairs_protected=sum(protected[k] and not original[k] for k in original),geometry_times=len(times),source_assets_and_author_permissions_unchanged=True,source_rebased=False,character_motion_edited=False,original_selected=True,continuous_collision_certified=False,physics_verified=False,quality_approved=False,release_approved=False,scope='V2 passing mesh-pair sampled guidance guards and original-relative line proposals. ALL declared geometry/contact/pose-budget conditions and original plus QUALIFIED initial passing identities govern comparison. Guidance, optimizer status and partial collision improvement are not full-clock/continuous/dynamic/engine/semantic/human approval. Original selection retained.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['permissions','policy','warm_start','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--maximum-evaluations',type=int,default=128);parser.add_argument('--maximum-iterations',type=int,default=20);parser.add_argument('--backtrack-steps',type=int,default=8);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):print(fit(args.permissions,args.policy,args.warm_start,args.output,maximum_evaluations=args.maximum_evaluations,maximum_iterations=args.maximum_iterations,backtrack_steps=args.backtrack_steps))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.policy.resolve()),str(args.warm_start.resolve()),str(args.output/'fit'),'--worker','--maximum-evaluations',str(args.maximum_evaluations),'--maximum-iterations',str(args.maximum_iterations),'--backtrack-steps',str(args.backtrack_steps)]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result);raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
