"""Original-source prop fitting with all-entity sampled surface guidance.

Guidance uses fixed, explicitly sampled surfaces at the edited key. Complete
declared geometry/contact/pose checks alone govern candidate comparison.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
import scipy
from scipy.optimize import minimize
import trimesh
from native_mesh_prop_pose import GripPoseEdit,conditions,metrics,pareto_improvement,METHODS as POSE_METHODS
from native_mesh_prop_scene import MeshPropScene,_json,guarded_output
from native_scene_geometry import faces_for
from native_observation_archive import ObservationArchive,verify
from triangle_primitive_depth import query as primitive_depth
from strep import save,sha256

METHODS=tuple(sorted(set(POSE_METHODS)|{'native_mesh_prop_scene_fit.py'}))
BARYCENTRIC=np.array([[1.,0,0],[0,1.,0],[0,0,1.],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1/3,1/3,1/3]])


def face_points(vertices,faces):
    return np.einsum('ij,fjk->fik',BARYCENTRIC,vertices[faces]).reshape(-1,3)


def signed(mesh,points):
    """Bound simultaneous expensive point-to-complete-mesh queries."""
    values=np.empty(len(points))
    for start in range(0,len(points),16):values[start:start+16]=trimesh.proximity.signed_distance(mesh,points[start:start+16])
    if not np.isfinite(values).all():raise ValueError('Finite complete signed-distance guidance required')
    return values


def positive_signed(mesh,points,padding):
    """Outside an expanded complete mesh box, positive residual is impossible."""
    values=np.zeros(len(points));reserve=max(1e-7,padding);lo,hi=mesh.bounds
    ids=np.flatnonzero(np.all(points>=lo-reserve,axis=1)&np.all(points<=hi+reserve,axis=1))
    values[ids]=np.maximum(0,signed(mesh,points[ids])+padding)
    return values


class SceneGuidance:
    def __init__(self,edit,policy,*,maximum_points=250000):
        if type(maximum_points) is not int or not 7<=maximum_points<=250000:raise ValueError('Explicit guidance point budget7-250000 required')
        edit.scene._clock(policy);self.edit=edit;self.policy=copy.deepcopy(policy)
        self.time=edit._item['keyframes'][edit._key]['time_s'];self.asset=edit.scene._props[edit._name]['asset']
        self.mesh=trimesh.Trimesh(self.asset.vertices_m,self.asset.faces,process=False)
        if not self.mesh.is_volume:raise ValueError('Outward closed prop volume required for signed guidance')
        if len(self.asset.faces)*7>maximum_points:raise ValueError('Complete prop guidance exceeds point budget; no faces dropped')
        self.prop_points=face_points(self.asset.vertices_m,self.asset.faces);owned=len(self.prop_points)
        self.radius=float(np.linalg.norm(self.asset.vertices_m-edit._point,axis=1).max()+edit._clearance)
        pad=policy['limits']['surface_tolerance_m'];lo=edit._pivot-self.radius-pad;hi=edit._pivot+self.radius+pad
        self.entities=[];self.arrays={'prop_local_points_m':self.prop_points,'prop_faces':self.asset.faces.copy()}
        worlds=[]
        for name,actor in edit.scene._scene.actors.items():
            p,r=actor['placement'];v=actor['rig'].vertices(actor['sampler'].sample(self.time))@r.T+p;f,_=faces_for(actor['rig']);worlds.append((f'actor:{name}',v,f))
        for name,prop in edit.scene._props.items():
            if name==edit._name:continue
            p,r=edit.scene.prop_poses(name,np.array([self.time]));worlds.append((f'prop:{name}',prop['asset'].vertices_m@r[0].T+p[0],prop['asset'].faces))
        summary=[]
        for index,(name,v,f) in enumerate(worlds):
            tri=v[f];disjoint=bool(np.any(v[f].max(axis=(0,1))<lo) or np.any(v[f].min(axis=(0,1))>hi))
            ids=np.array([],dtype=int) if disjoint else np.flatnonzero(np.all(tri.max(axis=1)>=lo,axis=1)&np.all(tri.min(axis=1)<=hi,axis=1))
            if owned+len(ids)*7>maximum_points:raise ValueError('Complete reachable-face guidance exceeds point budget; no faces dropped')
            points=face_points(v,f[ids]);owned+=len(points);mesh=None
            if not disjoint:
                mesh=trimesh.Trimesh(v,f,process=False)
                if not mesh.is_volume:raise ValueError('Outward closed entity volume required for signed guidance')
            self.entities.append(dict(name=name,points=points,mesh=mesh,disjoint=disjoint))
            self.arrays[f'entity_{index}_face_ids']=ids;self.arrays[f'entity_{index}_world_points_m']=points
            summary.append(dict(name=name,full_faces=len(f),reachable_faces=len(ids),sampled_points=len(points),whole_bounds_disjoint=disjoint,inverse_complete_prop_points=0 if disjoint else len(self.prop_points)))
        self.primitives=[]
        for name,obj in edit.scene._scene.objects.items():
            p,r=edit.scene._scene.object_poses(name,np.array([self.time]));self.primitives.append((name,obj['geometry'],p[0],r[0]))
        self.summary=dict(time_s=self.time,source_relative=True,sample_rule='All3 vertices, all3 edge midpoints, centroid per selected triangle; identities retained, no deduplication.',reachable_sphere_centre_m=edit._pivot.tolist(),reachable_sphere_radius_m=self.radius,geometry_padding_m=pad,positive_residual_box_screening_padding_m=max(1e-7,pad),entities=summary,primitive_objects=[v[0] for v in self.primitives],planes=list(policy['planes']),points_owned=owned,maximum_points=maximum_points,query_batch_size=16,energy_scale_m=.01,full_mesh_collision_certificate=False,continuous_collision_certified=False)

    def margins(self,value):
        report=self.edit.evaluate(value)['report']
        return np.array([report['native_rotation_ball_margin'],(self.edit._angle-report['rotation_change_degrees'])/max(1.,self.edit._angle),(self.edit._translation-report['translation_change_m'])/max(1.,self.edit._translation)])

    def evaluate(self,value):
        response=self.edit.evaluate(value);p=response['position_m'];r=response['rotation_matrix'];world=self.prop_points@r.T+p;terms=[]
        def term(name,depths):
            depths=np.maximum(0,np.asarray(depths,float));terms.append(dict(name=name,samples=len(depths),positive_samples=int((depths>0).sum()),maximum_residual_m=float(depths.max()) if len(depths) else 0.,mean_squared_scaled_residual=float(np.mean((depths/.01)**2)) if len(depths) else 0.))
        padding=self.policy['limits']['surface_tolerance_m']
        for entity in self.entities:
            if entity['disjoint']:
                term(entity['name']+'->prop',np.empty(0));term('prop->'+entity['name'],np.empty(0));continue
            term(entity['name']+'->prop',positive_signed(self.mesh,(entity['points']-p)@r,padding))
            term('prop->'+entity['name'],positive_signed(entity['mesh'],world,padding))
        vertices=self.asset.vertices_m@r.T+p
        for name,geometry,position,rotation in self.primitives:
            result=primitive_depth(vertices[self.asset.faces],geometry,position,rotation,resolution_m=self.policy['limits']['depth_resolution_m'])
            term('primitive:'+name,result['upper_m']-self.policy['limits']['penetration_m'])
        for name,plane in self.policy['planes'].items():term('plane:'+name,plane['offset_m']-vertices@np.asarray(plane['normal_world'])-self.policy['limits']['penetration_m'])
        energy=float(sum(item['mean_squared_scaled_residual'] for item in terms))
        if not np.isfinite(energy):raise ValueError('Finite guidance energy required')
        return dict(controls=np.asarray(value).tolist(),energy=energy,terms=terms,native_pose_permissions_pass=response['report']['native_pose_permissions_pass'],geometry_approved=False)


class EvaluationLimit(Exception):pass


def optimize(guide,initial,output,*,maximum_evaluations=96,maximum_iterations=12):
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=512 or type(maximum_iterations) is not int or not 1<=maximum_iterations<=100:raise ValueError('Bounded evaluation/iteration limits required')
    initial=guide.edit._value(initial)
    if not guide.edit.evaluate(initial)['report']['native_pose_permissions_pass']:raise ValueError('Initial controls must satisfy original native permissions')
    output=Path(output);output.mkdir();history=[]
    def objective(x):
        if len(history)>=maximum_evaluations:raise EvaluationLimit()
        value=np.r_[x,initial[3]];row=guide.evaluate(value);row['evaluation']=len(history);history.append(row);save(output/'history.json',history);return row['energy']
    objective(initial[:3]);optimizer=None;reason='rotation_locked'
    if guide.edit._angle:
        try:
            answer=minimize(objective,initial[:3],method='SLSQP',bounds=[(-1.,1.)]*3,constraints=[dict(type='ineq',fun=lambda x:guide.margins(np.r_[x,initial[3]]))],options=dict(maxiter=maximum_iterations,ftol=1e-10,eps=1e-4))
            optimizer=dict(success=bool(answer.success),status=int(answer.status),message=str(answer.message),controls=np.r_[answer.x,initial[3]].tolist(),iterations=int(answer.nit));reason='optimizer_returned'
        except EvaluationLimit:reason='evaluation_limit'
    valid=[row for row in history if row['native_pose_permissions_pass']];best=min(valid,key=lambda row:row['energy'])
    result=dict(status='complete',stop_reason=reason,optimizer=optimizer,evaluations=len(history),maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations,difference_step=1e-4,starting_controls=initial.tolist(),best_guidance_controls=best['controls'],starting_energy=history[0]['energy'],best_guidance_energy=best['energy'],scipy_version=scipy.__version__,trimesh_version=trimesh.__version__,clearance_fraction_fixed=float(initial[3]),source_rebased=False,geometry_approved=False,quality_approved=False)
    save(output/'result.json',result);return result


def fit(permissions_path,policy_path,warm_start_path,output,*,maximum_evaluations=96,maximum_iterations=12):
    edit=GripPoseEdit(permissions_path);policy_path=Path(policy_path).resolve();policy,policy_digest=_json(policy_path);times,_,_=edit.scene._clock(policy)
    warm_start_path=Path(warm_start_path).resolve();warm,digest=_json(warm_start_path)
    if set(warm)!={'schema','permissions_sha256','controls'} or warm['schema']!='strep-prop-source-relative-warm-start-v1' or warm['permissions_sha256']!=sha256(permissions_path):raise ValueError('Original permission-bound warm start required')
    initial=edit._value(warm['controls']);output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh fitting evidence output required')
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();bindings={**edit.inputs,str(policy_path):policy_digest,str(warm_start_path):digest};methods={name:sha256(Path(__file__).parent/name) for name in METHODS}
    for name in METHODS:shutil.copyfile(Path(__file__).parent/name,archive/name)
    save(output/'input.json',dict(inputs_sha256=bindings,implementation_sha256=methods,geometry_clock_s=times.tolist(),maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations,source_rebased=False,quality_approved=False))
    guide=SceneGuidance(edit,policy);save(output/'guidance-summary.json',guide.summary);np.savez_compressed(output/'guidance-surface-points.npz',**guide.arrays)
    optimized=optimize(guide,initial,output/'guidance',maximum_evaluations=maximum_evaluations,maximum_iterations=maximum_iterations)
    target=np.asarray(optimized['best_guidance_controls']);table=[dict(kind='original',controls=[0.,0,0,0]),dict(kind='remeasured-original-relative-warm-start',controls=initial.tolist())]
    if np.any(target!=initial):
        table += [dict(kind='guidance-line-proposal',fraction=f,controls=(initial+f*(target-initial)).tolist()) for f in [1.,.5,.25,.125]]
    save(output/'candidate-table.json',table);history=[];baseline=None;baseline_measure=None;best=None;best_measure=None;feasible=None
    for index,item in enumerate(table):
        value=item['controls'];response=edit.evaluate(value);row=dict(probe=index,**item,native_pose_permissions_pass=response['report']['native_pose_permissions_pass'])
        if not row['native_pose_permissions_pass']:
            row.update(accepted=False,reason='native_pose_permissions');history.append(row);save(output/'history.json',history);continue
        folder=output/f'probe-{index:03d}';manifest=edit.write(value,folder);candidate=MeshPropScene(manifest)
        bound,bound_arrays=edit.sampled_permissions(candidate,policy);save(folder/'sampled-permissions.json',bound);np.savez_compressed(folder/'sampled-permissions.npz',**bound_arrays)
        contact,arrays=candidate.contact_audit();save(folder/'contacts.json',contact);np.savez_compressed(folder/'contact-observations.npz',**arrays)
        derived=copy.deepcopy(policy);derived['mesh_scene_sha256']=sha256(manifest);save(folder/'policy.json',derived)
        with ObservationArchive(folder/'geometry-observations.npz') as sink:geometry,_=candidate.geometry(derived,observation_sink=sink)
        verify(folder/'geometry-observations.npz');save(folder/'geometry.json',geometry);current=conditions(geometry);measure=metrics(geometry)
        if baseline is None:
            assert index==0;baseline=current;baseline_measure=measure.copy();save(output/'baseline.json',dict(metrics=measure,conditions=[dict(id=list(k),passed=v) for k,v in baseline.items()]))
        if current.keys()!=baseline.keys():raise ValueError('Original condition population changed')
        new_failures=sum(baseline[k] and not current[k] for k in baseline);no_worse=all(measure[k]<=baseline_measure[k] for k in baseline_measure)
        allowed=bool(bound['all_sampled_pose_permissions_pass'] and contact['all_declared_point_contacts_pass'] and new_failures==0 and no_worse)
        improved=bool(allowed and pareto_improvement(measure,best_measure));clean=bool(allowed and geometry['sampled_conditions_pass'])
        if improved:best=index;best_measure=measure.copy()
        if clean:feasible=index
        row.update(sampled_pose_permissions_pass=bound['all_sampled_pose_permissions_pass'],all_declared_point_contacts_pass=contact['all_declared_point_contacts_pass'],new_failed_geometry_conditions=new_failures,metrics=measure,collision_metrics_no_worse_than_source=no_worse,admissible_for_comparison=allowed,improves_best=improved,sampled_geometry_pass=geometry['sampled_conditions_pass'],sampled_candidate_pass=clean)
        save(folder/'decision.json',dict(row,original_selected=True,quality_approved=False,release_approved=False));history.append(row);save(output/'history.json',history);print(row,flush=True)
        if clean:break
    edit.check_inputs()
    if any(sha256(p)!=d for p,d in bindings.items()) or any(sha256(Path(__file__).parent/n)!=sha256(archive/n) or sha256(archive/n)!=d for n,d in methods.items()):raise ValueError('Original inputs or implementation changed')
    result=dict(status='complete',best_admissible_probe=best,sampled_feasible_probe=feasible,candidates_recorded=len(history),candidate_table_size=len(table),history=history,guidance_evaluations=optimized['evaluations'],guidance_stop_reason=optimized['stop_reason'],starting_energy=optimized['starting_energy'],best_guidance_energy=optimized['best_guidance_energy'],geometry_times=len(times),source_assets_and_author_permissions_unchanged=True,source_rebased=False,character_motion_edited=False,original_selected=True,continuous_collision_certified=False,physics_verified=False,quality_approved=False,release_approved=False,scope='Original-relative local prop rotation fitting with all-actor/other-mesh-prop bidirectional sampled surface guidance at the edited key, primitive bounds and prop planes. Guidance is not complete collision detection. ALL declared geometry/contact conditions and native/frame pose budgets govern comparisons; protect original passing identities and metrics, best componentwise improvement. Original selection retained. No global feasibility, full-clock/continuous geometry, grasp, dynamics, engine, semantic or human approval.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['permissions','policy','warm_start','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--maximum-evaluations',type=int,default=96);parser.add_argument('--maximum-iterations',type=int,default=12);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):print(fit(args.permissions,args.policy,args.warm_start,args.output,maximum_evaluations=args.maximum_evaluations,maximum_iterations=args.maximum_iterations))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.policy.resolve()),str(args.warm_start.resolve()),str(args.output/'fit'),'--worker','--maximum-evaluations',str(args.maximum_evaluations),'--maximum-iterations',str(args.maximum_iterations)]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result);raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
