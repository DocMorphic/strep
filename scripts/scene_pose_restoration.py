"""Direct-inequality pose restoration inside a saved native scene clip.

This is a local solver experiment, not a clip feasibility or quality certificate.
It retains original control budgets and checks every original skin vertex.
Neighboring candidate keys stay fixed during each solve.
"""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from scipy.optimize import minimize,least_squares
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from grasp_pose_witness import PoseProblem,norm_slack_and_jacobian
from support_contact_v8 import torch_primitive_clearance_violation
from intentional_object_clearance import validate_constraints,margin_tracks
from scene_solver_context import context_primitives
from point_numerical_headroom import working_limits
from action_worker_lock import worker_lock
from inequality_restoration import restoration_residual

METHODS=['scene_pose_restoration.py','grasp_pose_witness.py','support_contact_v8.py',
    'support_contact_v5.py','floor_contact.py','inspect_motion.py','scene_solver_context.py',
    'intentional_object_clearance.py','point_numerical_headroom.py','object_geometry.py',
    'build_soma_preview.py','gltf_tools.py','scene_constraints.py','audit_scene_orientation.py',
    'action_worker_lock.py','inequality_restoration.py','strep.py']


def reference_slacks(positions,references,neighbors,frame,position_limit=.22,speed_limit=1.5,grouped=False):
    """Intersection of all reference balls; maxima remove duplicate solver rows."""
    if (not isinstance(positions,torch.Tensor) or positions.ndim!=2 or positions.shape[-1]!=3
            or len(positions)==0 or positions.dtype!=torch.float64
            or not torch.isfinite(positions).all() or not isinstance(references,dict)
            or set(references)!={'raw','limb','previous'} or type(frame) is not int or type(grouped) is not bool):
        raise ValueError('Complete finite native positions and all three references required')
    if any(type(x) not in (int,float) or not np.isfinite(x) or x<=0 for x in [position_limit,speed_limit]):
        raise ValueError('Positive reference limits required')
    shape=None
    for ref in references.values():
        if (not isinstance(ref,torch.Tensor) or ref.dtype!=positions.dtype or ref.device!=positions.device
                or ref.ndim!=3 or ref.shape[1:]!=positions.shape or len(ref)<2 or not torch.isfinite(ref).all()):
            raise ValueError('Finite matching complete reference clocks required')
        if shape is not None and ref.shape!=shape:raise ValueError('Reference clocks differ')
        shape=ref.shape
    if not 0<=frame<shape[0] or not isinstance(neighbors,dict) or set(neighbors)!={f for f in [frame-1,frame+1] if 0<=f<shape[0]}:
        raise ValueError('Every available adjacent candidate key required')
    displacement=torch.stack([((positions-ref[frame])**2).sum(-1) for ref in references.values()])
    maximum=lambda v:v.amax(0) if grouped else v.amax()
    values=[1-maximum(displacement)/position_limit**2]
    for neighbor,point in sorted(neighbors.items()):
        if (not isinstance(point,torch.Tensor) or point.shape!=positions.shape or point.dtype!=positions.dtype
                or point.device!=positions.device or not torch.isfinite(point).all()):
            raise ValueError('Finite matching adjacent candidate poses required')
        speeds=torch.stack([(((positions-ref[frame])-(point-ref[neighbor]))*30)**2 for ref in references.values()]).sum(-1)
        values.append(1-maximum(speeds)/speed_limit**2)
    return torch.cat(values) if grouped else torch.stack(values)


class RestorationProblem(PoseProblem):
    def __init__(self,folder,skin,frame,grouping='global'):
        super().__init__(folder,skin,frame)
        if grouping not in ['global','native-joint']:raise ValueError('Explicit constraint grouping required')
        self.grouping=grouping
        self.config=copy.deepcopy(self.config)
        if self.config['fps']!=30:raise ValueError('Saved 30 Hz native clock required')
        frames=len(self.base['posed_joints'])
        self.references={name:self.t(dict(np.load(folder/file,allow_pickle=False))['posed_joints'])
            for name,file in [('raw','raw-motion.npz'),('limb','limb-motion.npz'),('previous','previous-motion.npz')]}
        self.neighbors={f:self.t(self.candidate['posed_joints'][f]) for f in [frame-1,frame+1] if 0<=f<frames}
        spec=self.recipe['release_endpoint_guards']['solver_contact_spec']
        limits=[]
        for contact in self.contacts:
            matches=[seg for seg in spec['regions'][contact['region']]['segments']
                if seg['start_frame']<=frame<=seg['end_frame'] and seg.get('vertex_id')==contact['vertex']]
            if len(matches)!=1:raise ValueError('Unique active authored anchor interval required')
            limits.append(min(self.config['point_tolerance_m'],matches[0].get('tolerance_m',.005)))
        self.point_limits=working_limits(np.asarray(limits)[None],np.ones((1,len(limits)),dtype=bool),
                                        self.config['point_numerical_margin_m'])[0][0]
        self.margins={}
        policy=self.context.get('intentional_object_clearance')
        if policy is None:raise ValueError('Saved explicit intentional-contact policy required')
        validate_constraints(policy,spec,context_primitives(self.context))
        selected=np.arange(len(skin['bind_vertices']))
        for _,name,_,_ in self.objects:
            self.margins[name]=margin_tracks(policy,name,selected,self.config['object_clearance_m'])[frame]+self.config['object_sample_margin_m']
        dominant=skin['lbs_indices'][np.arange(len(selected)),skin['lbs_weights'].argmax(1)]
        self.vertex_groups=[(self.names[j],np.flatnonzero(dominant==j)) for j in sorted(set(dominant))]
        object_labels=['object:'+o[1]+':'+name for o in self.objects for name,_ in self.vertex_groups] if grouping=='native-joint' else ['object:'+o[1] for o in self.objects]
        body_labels=['all-reference-position']+['all-reference-speed:'+str(f) for f in sorted(self.neighbors)]
        if grouping=='native-joint':body_labels=[label+':'+name for label in body_labels for name in self.names]
        self.labels=['point:'+c['region'] for c in self.contacts]+['normal:'+n[0] for n in self.normals]+['floor']+object_labels+body_labels
        self.headroom_m=1e-6

    def geometry_slack(self,x,smooth_max_m=0.,*,neighbors=None):
        if smooth_max_m:raise ValueError('This restoration uses exact population maxima')
        _,positions,_,vertices=self.fk(x);values=[]
        for contact,limit in zip(self.contacts,self.point_limits):
            values.append((limit-self.headroom_m-torch.linalg.vector_norm(vertices[contact['vertex']]-self.t(contact['target'])))/.01)
        chord=2*np.sin(np.deg2rad(self.config['normal_tolerance_degrees']-.001)/2)
        for _,faces,target in self.normals:
            triangle=vertices[faces];normal=torch.linalg.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0]).sum(0)
            normal=normal/torch.linalg.vector_norm(normal).clamp_min(1e-12)
            values.append((chord-torch.linalg.vector_norm(normal-target))/chord)
        values.append((vertices[:,1].amin()-self.config['clearance_m']-self.headroom_m)/.01)
        for geometry,name,position,rotation in self.objects:
            violation=torch_primitive_clearance_violation(vertices[None],position,rotation,geometry,self.t(self.margins[name][None]))
            if self.grouping=='native-joint':
                values.extend((-violation[0,indices].amax()-self.headroom_m)/.01 for _,indices in self.vertex_groups)
            else:values.append((-violation.amax()-self.headroom_m)/.01)
        values.extend(reference_slacks(positions,self.references,self.neighbors if neighbors is None else neighbors,self.frame,.22-self.headroom_m,1.5-30*self.headroom_m,
            grouped=self.grouping=='native-joint'))
        return torch.stack(values)

    def independent(self,x,*,neighbors=None):
        neighbors=self.neighbors if neighbors is None else neighbors
        _,motion=super().independent(x)
        vertices=self.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        point=[];normal=[];objects=[]
        for contact,limit in zip(self.contacts,self.point_limits):
            error=float(np.linalg.norm(vertices[contact['vertex']]-np.asarray(contact['target'])))
            point.append(dict(region=contact['region'],error_m=error,working_tolerance_m=float(limit),passed=bool(error<=limit)))
        for name,faces,target in self.normals:
            triangle=vertices[faces];n=np.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0]).sum(0);length=np.linalg.norm(n)
            error=float(np.rad2deg(np.arccos(np.clip(n@target.numpy()/length,-1,1)))) if length>1e-12 else None
            normal.append(dict(id=name,error_degrees=error,passed=error is not None and error<=self.config['normal_tolerance_degrees']))
        for geometry,name,position,rotation in self.objects:
            local=(vertices-position.numpy()[0])@rotation.numpy()[0];margin=self.margins[name]
            if geometry.shape=='box':violation=(np.array(geometry.dimensions)/2+margin[:,None]-np.abs(local)).min(-1)
            else:violation=margin-geometry.distance_gradient(vertices,position.numpy()[0],rotation.numpy()[0])[0]
            objects.append(dict(id=name,maximum_clearance_violation_m=float(violation.max()),
                maximum_physical_vertex_depth_m=float(geometry.penetration_depth(vertices,position.numpy()[0],rotation.numpy()[0]).max()),passed=bool((violation<=0).all())))
        positions=motion['posed_joints'][0];body={}
        reference_slacks(torch.as_tensor(positions,dtype=torch.float64),self.references,neighbors,self.frame)
        for name,reference in self.references.items():
            ref=reference.numpy();delta=positions-ref[self.frame];peak=float(np.linalg.norm(delta,axis=1).max())
            speeds=[float(np.linalg.norm((delta-(p.numpy()-ref[f]))*30,axis=1).max()) for f,p in sorted(neighbors.items())]
            body[name]=dict(max_displacement_m=peak,neighbor_max_added_speeds_m_s=speeds,passed=peak<=.22 and all(v<=1.5 for v in speeds))
        angle=Rotation.from_matrix(self.previous['local_rot_mats'][self.frame].transpose(0,2,1)@motion['local_rot_mats'][0]).magnitude()
        fixed=[j for j in range(77) if j not in self.editable]
        rotations_pass=bool(np.all(angle[self.editable]<=self.limits+1e-8) and np.max(angle[fixed])<1e-6)
        floor=float(vertices[:,1].min());root=bool(0<=x[-1]<=self.config['max_root_lift_m'])
        passed=rotations_pass and root and floor>=self.config['clearance_m'] and all(r['passed'] for r in point+normal+objects+list(body.values()))
        return dict(points=point,normals=normal,objects=objects,body=body,minimum_floor_y_m=floor,
            rotation_budgets_passed=rotations_pass,root_budget_passed=root,pose_checks_passed=bool(passed),vertices_checked=len(vertices),
            scope='One native pose and its fixed adjacent keys. No full-clip, between-key, support-slide, self-collision, anatomy, import, dynamics or human certificate.'),motion


def _run(study,output,frame,iterations=100,seconds=300,strategy='slsqp',grouping='global'):
    study=Path(study).resolve();output=Path(output).resolve();fit=study/'fit'
    if (type(frame) is not int or type(iterations) is not int or not 1<=iterations<=300
            or type(seconds) not in (int,float) or not 1<=seconds<=1800
            or strategy not in ['slsqp','restore_then_slsqp'] or grouping not in ['global','native-joint']):
        raise ValueError('Explicit frame and bounded solve budgets required')
    summary=read(fit/'summary.json')
    if summary['solver_version']!=17 or read(study/'pipeline.json')['status']!='complete' or len(summary['trials'])!=1:
        raise ValueError('One completed V17 source trial required')
    from build_soma_preview import ASSET
    if sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Skin changed')
    folder=fit/'assets'/summary['trials'][0]['id']/'A'
    inputs=[folder/n for n in ['raw-motion.npz','limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]+[ASSET,fit/'summary.json']
    bindings={str(p):sha256(p) for p in inputs};skin=dict(np.load(ASSET,allow_pickle=False))
    torch.set_num_threads(2)
    problem=RestorationProblem(folder,skin,frame,grouping)
    seed_audit,_=problem.independent(problem.seed)
    with torch.no_grad():rot,pos,_,_=problem.fk(problem.t(problem.seed))
    error=max(float(np.abs(pos.numpy()-problem.candidate['posed_joints'][frame]).max()),float(np.abs(rot.numpy()-problem.candidate['global_rot_mats'][frame]).max()))
    if error>2e-6:raise ValueError('Pose model does not reproduce the saved source')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    protocol=dict(at=now(),frame=frame,study=study.relative_to(ROOT).as_posix(),inputs_sha256=bindings,
        methods_sha256={n:sha256(ROOT/'scripts'/n) for n in METHODS},iterations=iterations,seconds=seconds,
        solver='SLSQP direct inequalities',strategy=strategy,constraint_grouping=grouping,
        geometry_constraint_rows=len(problem.labels),restoration_max_evaluations=iterations if strategy=='restore_then_slsqp' else 0,
        restoration_seed_regularization=1e-5 if strategy=='restore_then_slsqp' else None,position_limit_m=.22,added_speed_limit_m_s=1.5,
        working_point_tolerances_m=problem.point_limits.tolist(),normal_limit_degrees=problem.config['normal_tolerance_degrees'],
        extra_solver_position_headroom_m=problem.headroom_m,vertices_checked=len(skin['bind_vertices']),influences_per_vertex=8,
        scope='Bounded local restoration; solver status does not certify feasibility. Original motion is preserved. Fixed adjacent candidate keys; no clip or quality approval.')
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing'))
    direction=np.random.default_rng(716).normal(size=problem.dim);direction/=np.linalg.norm(direction);step=1e-6
    values,jac=problem.pair(problem.seed);smooth_count=len(problem.contacts)+len(problem.normals)
    with torch.no_grad():
        fd=((problem.geometry_slack(problem.t(problem.seed+step*direction))-
             problem.geometry_slack(problem.t(problem.seed-step*direction)))/(2*step)).numpy()
    np.testing.assert_allclose(jac[:smooth_count]@direction,fd[:smooth_count],atol=2e-5,rtol=2e-4)
    save(output/'preflight.json',dict(seed=seed_audit,seed_fk_max_error_m=error,
        smooth_constraint_directional_error=float(np.abs(jac[:smooth_count]@direction-fd[:smooth_count]).max()),
        seed_solver_slacks=dict(zip(problem.labels,values[:len(problem.labels)].tolist())),
        seed_minimum_rotation_norm_slack=float(values[len(problem.labels):].min())))
    start=time.monotonic();history=[];current=problem.seed.copy();scale=np.r_[np.repeat(problem.limits,3),.22]
    initial=problem.seed/scale;last=initial.copy();restoration_stage=None;solve_initial=initial.copy()
    def pair(z):
        nonlocal last
        if time.monotonic()-start>seconds:raise TimeoutError('Pose restoration time guard')
        last=np.asarray(z).copy();slack,jac=problem.pair(last*scale)
        if not np.isfinite(slack).all() or not np.isfinite(jac).all():raise ValueError('Nonfinite restoration constraint')
        return slack,jac*scale[None]
    def objective(z):
        delta=z-initial;return float(delta@delta),2*delta
    def callback(z):
        history.append(dict(iteration=len(history)+1,seconds=time.monotonic()-start,minimum_solver_slack=float(pair(z)[0].min())))
        save(output/'progress.json',dict(status='processing',history=history))
        if len(history)%10==0:print(history[-1],flush=True)
    lower=np.r_[np.full(problem.dim-1,-1.),0.];upper=np.ones(problem.dim)
    try:
        with threadpool_limits(limits=2):
            if strategy=='restore_then_slsqp':
                def residual_pair(z):
                    values,jac=pair(z)
                    return restoration_residual(z,initial,values,jac)
                restored=least_squares(lambda z:residual_pair(z)[0],initial,jac=lambda z:residual_pair(z)[1],
                    bounds=(lower,upper),method='trf',max_nfev=iterations,ftol=1e-12,xtol=1e-12,gtol=1e-12)
                solve_initial=restored.x
                restored_audit,restored_motion=problem.independent(solve_initial*scale)
                np.savez(output/'restoration-pose.npz',**restored_motion)
                restoration_stage=dict(success=bool(restored.success),message=str(restored.message),evaluations=int(restored.nfev),
                    seconds=time.monotonic()-start,cost=float(restored.cost),candidate=restored_audit,parameters=(solve_initial*scale).tolist(),
                    pose_sha256=sha256(output/'restoration-pose.npz'),quality_approved=False,release_approved=False)
                save(output/'restoration-stage.json',restoration_stage)
                print(dict(stage='inequality_restoration',seconds=restoration_stage['seconds'],cost=restored.cost,
                    minimum_solver_slack=float(pair(solve_initial)[0].min()),pose_checks_passed=restored_audit['pose_checks_passed']),flush=True)
            result=minimize(objective,solve_initial,method='SLSQP',jac=True,bounds=list(zip(lower,upper)),
                constraints=[dict(type='ineq',fun=lambda z:pair(z)[0],jac=lambda z:pair(z)[1])],callback=callback,
                options=dict(maxiter=iterations,ftol=1e-12))
        current=result.x*scale;status='complete';solver=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev))
    except TimeoutError as exc:
        current=last*scale;status='interrupted_resource_guard';solver=dict(success=False,message=str(exc))
    audit,motion=problem.independent(current)
    with torch.no_grad():_,_,_,vertices=problem.fk(problem.t(current))
    numeric_error=float(np.abs(vertices.numpy()-problem.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])).max())
    if numeric_error>2e-6:raise ValueError('Independent skin mismatch')
    if any(sha256(path)!=digest for path,digest in bindings.items()) or any(sha256(ROOT/'scripts'/n)!=h for n,h in protocol['methods_sha256'].items()):
        raise ValueError('Source or implementation changed during restoration')
    np.savez(output/'pose.npz',**motion)
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,seed=seed_audit,candidate=audit,
        history=history,restoration_stage=restoration_stage,parameters=current.tolist(),seed_fk_max_error_m=error,independent_skin_max_error_m=numeric_error,
        protocol_sha256=sha256(output/'protocol.json'),pose_sha256=sha256(output/'pose.npz'),quality_approved=False,release_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_checks_passed=audit['pose_checks_passed'],quality_approved=False,release_approved=False))
    print(dict(status=status,solver=solver,candidate=audit),flush=True)


def run(study,output,frame,iterations=100,seconds=300,strategy='slsqp',grouping='global'):
    output=Path(output).resolve()
    existed=output.exists()
    with worker_lock():
        try:return _run(study,output,frame,iterations,seconds,strategy,grouping)
        except Exception as exc:
            if not existed and output.exists():
                save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),
                    quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output');parser.add_argument('--frame',type=int,required=True)
    parser.add_argument('--iterations',type=int,default=100);parser.add_argument('--seconds',type=float,default=300)
    parser.add_argument('--strategy',choices=['slsqp','restore_then_slsqp'],default='slsqp')
    parser.add_argument('--grouping',choices=['global','native-joint'],default='global')
    args=parser.parse_args();run(args.study,args.output,args.frame,args.iterations,args.seconds,args.strategy,args.grouping)
