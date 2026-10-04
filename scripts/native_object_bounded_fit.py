"""Original-relative translation/rotation balls inside explicit multi-point fits.

Pointwise local optimization proposes object motion only. All saved contact,
pose-budget and complete sampled geometry conditions remain separate gates.
"""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from engine_contact_sampling import contract_sha256
from native_scene_contacts import SceneContacts,fields,scalar
from native_scene_geometry import evaluate_to_archive as geometry_archive,policy_for
from native_object_hold_fit import audit_bounds
import native_object_correspondence_fit as unbounded
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-object-bounded-fit-v1'
METHODS=unbounded.METHODS+('native_object_bounded_fit.py',)
BASE_FIELDS=('schema','contacts_sha256','object','contact_ids','edit_window_s','maximum_translation_m',
    'maximum_rotation_degrees','maximum_keys','maximum_correspondences')


def settings(value):
    fields(value,('schema','maximum_iterations','ftol','bound_reserve_fraction'),'bounded pose solver')
    if value['schema']!='strep-object-pose-solver-v1':raise ValueError('Explicit bounded pose solver schema required')
    if type(value['maximum_iterations']) is not int or not 1<=value['maximum_iterations']<=1000:raise ValueError('Explicit solver iteration budget required')
    scalar(value['ftol'],1e-14,1e-4,'solver ftol');scalar(value['bound_reserve_fraction'],1e-8,1e-3,'internal bound reserve')
    return value


def base_request(value):
    fields(value,BASE_FIELDS+('initial_scene','solver'),'bounded multi-point object fit')
    if value['schema']!=SCHEMA:raise ValueError('Bounded object fit schema required')
    settings(value['solver']);initial=value['initial_scene']
    if initial is not None:
        fields(initial,('path','sha256'),'initial scene binding')
        if not isinstance(initial['path'],str) or not initial['path'] or not isinstance(initial['sha256'],str):raise ValueError('Bound initial scene path and SHA-256 required')
    result={k:copy.deepcopy(value[k]) for k in BASE_FIELDS};result['schema']=unbounded.SCHEMA;return result


def initial_for(authored,scene,value,base):
    if value['initial_scene'] is None:return scene,None
    binding=value['initial_scene'];path=(Path(base)/binding['path']).resolve()
    if sha256(path)!=binding['sha256']:raise ValueError('Initial scene binding changed')
    spec=read(path);initial=SceneContacts(spec,path.parent)
    if spec['duration_s']!=authored['duration_s'] or spec['contacts']!=authored['contacts'] or set(spec['actors'])!=set(authored['actors']) or set(spec['objects'])!=set(authored['objects']):
        raise ValueError('Initial scene must preserve source actors, duration, objects and complete contact intent')
    for name in spec['actors']:
        if {k:v for k,v in spec['actors'][name].items() if k!='glb'}!={k:v for k,v in authored['actors'][name].items() if k!='glb'}:
            raise ValueError('Initial scene changed actor identity, animation or placement')
    for name in spec['objects']:
        if (spec['objects'][name]['geometry']!=authored['objects'][name]['geometry'] or
                name!=value['object'] and spec['objects'][name]!=authored['objects'][name]):raise ValueError('Initial scene changed undeclared object geometry or paths')
    if sha256(path)!=binding['sha256']:raise ValueError('Initial scene changed during validation')
    return initial,path


def skew(v):
    x,y,z=np.asarray(v,float);return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def residual_jacobian(x,local,observed,p0,r0,translation_scale,rotation_scale):
    omega=np.asarray(x[3:])*rotation_scale;theta=np.linalg.norm(omega);s=skew(omega)
    if theta<1e-5:
        a=.5-theta**2/24+theta**4/720;b=1/6-theta**2/120+theta**4/5040
    else:a=(1-np.cos(theta))/theta**2;b=(theta-np.sin(theta))/theta**3
    right=np.eye(3)-a*s+b*s@s;delta=Rotation.from_rotvec(omega).as_matrix()
    points=local@r0.T;residual=points@delta.T+p0+np.asarray(x[:3])*translation_scale-observed
    jac=np.empty((len(local),3,6));jac[:,:,:3]=np.eye(3)*translation_scale
    jac[:,:,3:]=np.array([-delta@skew(p)@right*rotation_scale for p in points])
    return residual,jac


def unit_balls(x):
    x=np.asarray(x,float).copy()
    for part in (slice(0,3),slice(3,6)):
        length=np.linalg.norm(x[part])
        if length>1:x[part]/=length
    return x


def proper_pose(p,r):
    p=np.asarray(p,float);r=np.asarray(r,float)
    if p.shape!=(3,) or r.shape!=(3,3) or not np.isfinite(p).all() or not np.isfinite(r).all() or not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-10) or abs(np.linalg.det(r)-1)>1e-10:
        raise ValueError('Finite proper rigid pose required')
    return p,r


def fit_bounded(local,observed,p0,r0,translation_m,rotation_degrees,solver,*,initial_pose=None):
    settings(solver);p0,r0=proper_pose(p0,r0)
    scalar(translation_m,1e-6,.1,'translation budget');scalar(rotation_degrees,1e-6,45,'rotation budget')
    p,r,error=unbounded.fit_points(local,observed);local=np.asarray(local,float);observed=np.asarray(observed,float)
    reserve=1-solver['bound_reserve_fraction'];ts=float(translation_m)*reserve;rs=np.deg2rad(rotation_degrees)*reserve
    scale=max(ts,rs*float(np.linalg.norm(local,axis=1).max()),1e-6)
    def parameters(p,r):return np.r_[(p-p0)/ts,Rotation.from_matrix(r@r0.T).as_rotvec()/rs]
    initial_p,initial_r=proper_pose(*(initial_pose if initial_pose is not None else (p0,r0)))
    raw_initial=parameters(initial_p,initial_r);start=unit_balls(raw_initial)
    def objective(x):
        e,j=residual_jacobian(x,local,observed,p0,r0,ts,rs)
        return float(np.sum(e*e)/len(local)/scale**2),2*np.einsum('ni,nij->j',e,j)/len(local)/scale**2
    initial_cost=objective(start)[0];unconstrained=parameters(p,r)
    if np.linalg.norm(unconstrained[:3])<=1 and np.linalg.norm(unconstrained[3:])<=1:
        x=unconstrained;record=dict(method='proper-unconstrained-fit-within-reserved-bounds',solver_success=True,status=0,iterations=0,message='Closed form is feasible')
    else:
        def constraints(x):return np.array([1-x[:3]@x[:3],1-x[3:]@x[3:]])
        def constraint_jac(x):
            j=np.zeros((2,6));j[0,:3]=-2*x[:3];j[1,3:]=-2*x[3:];return j
        # Component bounds are implied by the balls; they also prevent axis-aligned
        # boundary iterates from drifting outside the representable unit interval.
        solved=minimize(objective,start,jac=True,method='SLSQP',bounds=[(-1.,1.)]*6,constraints=dict(type='ineq',fun=constraints,jac=constraint_jac),
            options=dict(maxiter=solver['maximum_iterations'],ftol=solver['ftol'],disp=False))
        if not np.isfinite(solved.x).all():raise ValueError('Bounded solver returned nonfinite parameters')
        x=solved.x;record=dict(method='SLSQP-normalized-original-relative-balls',solver_success=bool(solved.success),
            status=int(solved.status),iterations=int(solved.nit),message=str(solved.message))
    projected=unit_balls(x);record['final_projection_change']=float(np.linalg.norm(projected-x));x=projected
    cost=objective(x)[0];record['initial_retained']=bool(cost>initial_cost+1e-14)
    if record['initial_retained']:x=start;cost=initial_cost
    p=p0+x[:3]*ts;r=Rotation.from_rotvec(x[3:]*rs).as_matrix()@r0
    error=np.linalg.norm(local@r.T+p-observed,axis=1)
    record.update(initial_projection_change=float(np.linalg.norm(start-raw_initial)),initial_scaled_cost=initial_cost,
        final_scaled_cost=cost,translation_m=float(np.linalg.norm(p-p0)),rotation_degrees=float(np.rad2deg(Rotation.from_matrix(r@r0.T).magnitude())))
    if record['translation_m']>translation_m or record['rotation_degrees']>rotation_degrees:raise ValueError('Saved bounded pose exceeds the original budget')
    return p,r,error,x,record


def proposal(scene,value,digest,initial=None,progress=None):
    base=base_request(value);_,raw,layout=unbounded.proposal(scene,base,digest)
    hold_times=raw['hold_times_s'];times=raw['times_s'];grips=raw['object_local_points'];observed=raw['observed_world_points']
    selected,hold,window,_,_=unbounded.request_for(scene,base,digest);name=value['object']
    reference_p,reference_r=scene.object_poses(name,hold_times);initial_p,initial_r=(initial or scene).object_poses(name,hold_times)
    fitted=[]
    for i,points in enumerate(observed):
        try:fitted.append(fit_bounded(grips,points,reference_p[i],reference_r[i],value['maximum_translation_m'],value['maximum_rotation_degrees'],value['solver'],initial_pose=(initial_p[i],initial_r[i])))
        except ValueError as exc:raise ValueError('Bounded object fit at '+repr(float(hold_times[i]))+': '+str(exc)) from exc
        if progress and (i+1)%100==0:progress(dict(status='fitting',completed_hold_times=i+1,total_hold_times=len(hold_times)))
    fitted_p=np.array([f[0] for f in fitted]);fitted_r=np.array([f[1] for f in fitted]);errors=np.array([f[2] for f in fitted])
    positions=raw['source_positions'].copy();rotations=raw['source_rotations'].copy();inside=(times>=hold[0])&(times<=hold[1]);ids=np.searchsorted(hold_times,times[inside])
    if not np.array_equal(hold_times[ids],times[inside]):raise ValueError('Complete bounded fit clock required')
    positions[inside]=fitted_p[ids];rotations[inside]=fitted_r[ids]
    for begin,end,endpoint,reverse in [(window[0],hold[0],0,False),(hold[1],window[1],-1,True)]:
        mask=(times>begin)&(times<end);u=(times[mask]-begin)/(end-begin);w=u*u*u*(10+u*(-15+6*u));w=1-w if reverse else w
        positions[mask]+=w[:,None]*(fitted_p[endpoint]-reference_p[endpoint])
        delta=Rotation.from_matrix(fitted_r[endpoint]@reference_r[endpoint].T).as_rotvec()
        rotations[mask]=Rotation.from_rotvec(w[:,None]*delta).as_matrix()@raw['source_rotations'][mask]
    keys=[dict(time_s=float(t),translation_m=p.tolist(),rotation_xyzw=q.tolist()) for t,p,q in zip(times,positions,Rotation.from_matrix(rotations).as_quat())]
    arrays=dict(times_s=times,hold_times_s=hold_times,source_positions=raw['source_positions'],source_rotations=raw['source_rotations'],
        proposed_positions=positions,proposed_rotations=rotations,observed_world_points=observed,object_local_points=grips,
        initial_hold_positions=initial_p,initial_hold_rotations=initial_r,bounded_point_errors_m=errors,
        bounded_rms_point_error_m=np.sqrt(np.mean(errors**2,axis=1)),normalized_pose_parameters=np.array([f[3] for f in fitted]),
        unconstrained_positions=raw['proposed_positions'],unconstrained_rotations=raw['proposed_rotations'],
        unconstrained_point_errors_m=raw['least_squares_point_errors_m'])
    records=[dict(time_s=float(t),**f[4]) for t,f in zip(hold_times,fitted)]
    return keys,arrays,layout,records


def run(contacts_path,request_path,policy_path,output):
    contacts_path,request_path,policy_path,output=[Path(p).resolve() for p in (contacts_path,request_path,policy_path,output)]
    if output.exists():raise ValueError('Fresh bounded object output required')
    with worker_lock(),threadpool_limits(limits=1):
        inputs={str(p):sha256(p) for p in (contacts_path,request_path,policy_path)}
        authored=read(contacts_path);scene=SceneContacts(authored,contacts_path.parent);value=read(request_path);policy=read(policy_path)
        base=base_request(value);unbounded.request_for(scene,base,inputs[str(contacts_path)]);policy_for(policy,scene,inputs[str(contacts_path)])
        initial,initial_path=initial_for(authored,scene,value,contacts_path.parent)
        if initial_path is not None:
            inputs[str(initial_path)]=value['initial_scene']['sha256']
            if sha256(initial_path)!=inputs[str(initial_path)]:raise ValueError('Initial scene changed after validation')
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        copies=[(contacts_path,'source-contacts.json'),(request_path,'fit-request.json'),(policy_path,'source-policy.json')]
        if initial_path is not None:copies.append((initial_path,'initial-contacts.json'))
        for path,name in copies:shutil.copyfile(path,output/name)
        snapshots={};derived=copy.deepcopy(authored)
        for i,(name,a) in enumerate(scene.actors.items()):
            src=(contacts_path.parent/authored['actors'][name]['glb']).resolve();dest=output/'input'/f'actor-{i}.glb';dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(src,dest)
            if sha256(dest)!=authored['actors'][name]['sha256']:raise ValueError('Actor snapshot changed')
            snapshots[name]=dict(path=dest.relative_to(output).as_posix(),sha256=sha256(dest));derived['actors'][name]['glb']=str(dest)
        save(output/'pipeline.json',dict(status='fitting',original_selected=True))
        try:
            keys,arrays,layout,records=proposal(scene,value,inputs[str(contacts_path)],initial,
                lambda p:save(output/'pipeline.json',dict(**p,original_selected=True)))
            derived['objects'][value['object']]['keyframes']=unbounded.saved_keys(keys,authored,base)
            save(output/'proposal-contacts.json',derived);digest=sha256(output/'proposal-contacts.json');candidate=SceneContacts(derived,output)
            derived_policy=copy.deepcopy(policy);derived_policy['contacts_sha256']=digest
            derived_policy['clock']=dict(mode=policy['clock']['mode'],times_s=np.unique(np.r_[policy['clock']['times_s'],arrays['times_s']]).tolist())
            clocks,_,_=policy_for(derived_policy,candidate,digest);bounds=audit_bounds(scene,candidate,base,clocks)
            initial_bounds=audit_bounds(scene,initial,base,clocks);initial_contacts,initial_observations=initial.evaluate()
            contacts,observations=candidate.evaluate();save(output/'contact-audit.json',contacts);save(output/'initial-contact-audit.json',initial_contacts)
            np.savez_compressed(output/'initial-contact-observations.npz',**initial_observations)
            save(output/'solver-records.json',dict(settings=value['solver'],records=records,global_optimum_certified=False))
            np.savez_compressed(output/'proposal-observations.npz',**arrays);np.savez_compressed(output/'contact-observations.npz',**observations)
            geometry,transport=geometry_archive(candidate,derived_policy,digest,output/'geometry-observations.npz',
                lambda p:save(output/'pipeline.json',dict(**p,original_selected=True)))
            geometry.update(**transport);save(output/'geometry-policy.json',derived_policy);save(output/'geometry-audit.json',geometry)
            scene.check_inputs();initial.check_inputs();candidate.check_inputs()
            if any(sha256(Path(p))!=h for p,h in inputs.items()):raise ValueError('Bounded fit input changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Bounded fit implementation changed')
            for path,name in copies:
                if sha256(path)!=sha256(output/name):raise ValueError('Authored snapshot changed')
            converged=all(r['solver_success'] for r in records)
            result=dict(schema=SCHEMA,at=now(),status='complete',object=value['object'],contact_ids=value['contact_ids'],
                correspondence_layout=layout,correspondences=len(layout),keys=len(keys),bounds=bounds,initial_bounds=initial_bounds,
                initial_contact_conditions_pass=initial_contacts['passed'],initial_geometry_rechecked=False,
                all_solver_frames_converged=converged,all_contact_conditions_pass=contacts['passed'],sampled_geometry_conditions_pass=geometry['sampled_conditions_pass'],
                sampled_constraints_pass=bool(converged and bounds['passed'] and contacts['passed'] and geometry['sampled_conditions_pass']),
                actor_bytes_unchanged=True,actor_snapshots=snapshots,input_sha256=inputs,actor_inputs_sha256=scene.inputs,
                initial_actor_inputs_sha256=initial.inputs,implementation_sha256=methods,frame_contract_sha256=contract_sha256(),proposal_contacts_sha256=digest,
                geometry_samples=len(clocks),original_selected=True,quality_approved=False,release_approved=False,training_admitted=False,
                scope='Equal-point proper rigid proposals inside original-relative pose balls, with explicit numerical reserve. Pointwise SLSQP is local, with projection and non-improving initial retention recorded. Closed-form fits are used only inside the reserved bounds. Complete saved contacts, source-relative budgets, geometry and solver convergence remain separate gates. No minimax, continuous/global optimum, character edits, anatomy, forces, engine or human-quality approval.')
            files=[n for _,n in copies]+['proposal-contacts.json','geometry-policy.json','solver-records.json','contact-audit.json','initial-contact-audit.json',
                'proposal-observations.npz','contact-observations.npz','initial-contact-observations.npz','geometry-audit.json','geometry-observations.npz','geometry-observations.npz.receipt.json']
            result['files_sha256']={n:sha256(output/n) for n in files}
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','request','policy','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();result=run(args.contacts,args.request,args.policy,args.output)
    print(dict(correspondences=result['correspondences'],keys=result['keys'],sampled_constraints_pass=result['sampled_constraints_pass'],quality_approved=False),flush=True)
