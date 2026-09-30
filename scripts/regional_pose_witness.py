"""Single-pose feasibility search for a completed native regional scene fit.

Keeps source-relative edit bounds, authored patches and full skin clearance.
Temporal coupling is relaxed. Success is only a pose witness; local solver
failure cannot establish infeasibility. No saved scene or clip is overwritten.
"""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
import torch
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from floor_contact import Surface,reconstruct
from inspect_motion import skeleton_metadata
from grasp_pose_witness import PoseProblem,BODY,norm_slack_and_jacobian
from support_contact_v8 import finger_rotation_budgets,torch_primitive_clearance_violation
from scene_solver_context import compile_context,context_primitives
from compile_scene_regions import compile_regions
from region_contact_objective import violations,choose_triangle
from scene_region_contact import measure_frame


def reduced_region_residual(values,count):
    """Max preserves the entire patch-clearance feasible set; other rows stay separate."""
    if type(count) is not int or count<3 or values.ndim!=1 or len(values)!=count+13:
        raise ValueError('Invalid regional constraint layout')
    return torch.cat([values[:count].amax().reshape(1),values[count:]])


class RegionalPoseProblem(PoseProblem):
    # Reuse only the established full-skin FK, not its legacy point-only audit.
    def __init__(self,fit,frame):
        fit=Path(fit).resolve();protocol=read(fit/'protocol.json');result=read(fit/'result.json')
        if protocol['solver_version']!=14 or result['status']!='complete':raise ValueError('Completed v14 fit required')
        if result['protocol_sha256']!=sha256(fit/'protocol.json'):raise ValueError('Fit protocol changed')
        for file,key in [('motion.npz','candidate_sha256'),('authored-scene.json','authored_scene_sha256'),('recipe.json','recipe_sha256')]:
            if sha256(fit/file)!=result[key]:raise ValueError('Fit artifact changed: '+file)
        for path,digest in protocol['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Fit input changed: '+path)
        for name,digest in protocol['implementation'].items():
            if sha256(fit/'implementation'/name)!=digest:raise ValueError('Fit method snapshot changed: '+name)
        scene=read(fit/'authored-scene.json');actor=protocol['actor']
        if set(scene['actors'])!={actor} or scene.get('partner_cut_file'):raise ValueError('Single actor without partner cuts required')
        if type(frame) is not int or not 0<=frame<scene['frame_count']:raise ValueError('Native integer frame required')
        self.frame=frame;self.skin=dict(np.load(ASSET,allow_pickle=False));self.surface=Surface(self.skin)
        self.names,self.parents,_=skeleton_metadata(77)
        self.base=dict(np.load(fit/'source-motion.npz',allow_pickle=False));self.previous=self.base
        if sha256(fit/'source-motion.npz')!=sha256(ROOT/scene['actors'][actor]['motion']):raise ValueError('Native source changed')
        self.candidate=dict(np.load(fit/'motion.npz',allow_pickle=False));self.config=protocol['config']
        package=compile_regions(scene,actor,protocol['contact_ids'],self.skin)
        # compile_context supplies the same actor-native object frames and also
        # enforces yaw-only, ground-level actor placement.
        import copy
        plain=copy.deepcopy(scene)
        for c in plain['contacts']:c.pop('region_contact',None)
        self.context=compile_context(plain,actor,protocol['contact_ids'],self.skin)
        fingers=finger_rotation_budgets(self.names)
        self.editable=[self.names.index(n) for n in BODY]+list(fingers)
        self.limits=np.deg2rad([self.config['max_rotation_degrees']]*len(BODY)+list(fingers.values()))
        self.lookup={j:i for i,j in enumerate(self.editable)};self.dim=3*len(self.editable)+1
        self.t=lambda value:torch.as_tensor(np.asarray(value),dtype=torch.float64)
        self.initial=self.t(self.base['local_rot_mats'][frame]);self.root=self.t(self.base['root_positions'][frame])
        offsets=np.zeros((77,3))
        for j,parent in enumerate(self.parents):
            if parent>=0:offsets[j]=self.base['global_rot_mats'][frame,parent].T@(self.base['posed_joints'][frame,j]-self.base['posed_joints'][frame,parent])
        self.offsets=self.t(offsets);self.indices=self.skin['lbs_indices'];self.weights=self.t(self.skin['lbs_weights'])
        self.bind=self.t(np.einsum('vwij,vj->vwi',self.surface.inverse[self.indices],self.surface.points)[:,:,:3])
        relative=self.base['local_rot_mats'][frame].transpose(0,2,1)@self.candidate['local_rot_mats'][frame]
        self.seed=np.r_[Rotation.from_matrix(relative[self.editable]).as_rotvec().ravel(),
                       float(self.candidate['root_positions'][frame,1])-float(self.base['root_positions'][frame,1])]
        if norm_slack_and_jacobian(self.seed,self.limits)[0].min() < -1e-6 or not 0<=self.seed[-1]<=self.config['max_root_lift_m']:
            raise ValueError('Seed violates original pose budgets')
        self.objects=[(g,o['id'],self.t(o['positions_m'][frame])[None],self.t(o['rotations'][frame])[None]) for g,o in context_primitives(self.context)]
        seed_vertices=self.surface.vertices(self.candidate['global_rot_mats'][frame],self.candidate['posed_joints'][frame])
        self.regions=[];self.selections=[]
        from object_geometry import Geometry
        for record in package['regions']:
            if not record['start_frame']<=frame<=record['end_frame']:continue
            ids=np.array(record['vertex_ids']);mapping={v:i for i,v in enumerate(ids)}
            binding=record['binding'];limits=binding['limits'];geometry=Geometry.parse(record['geometry'])
            position=np.array(record['object_positions_m'][frame]);rotation=np.array(record['object_rotations'][frame])
            contact=next(c for c in scene['contacts'] if c['id']==record['contact_id'])
            target=position+rotation@contact['target']['point_m']
            points=seed_vertices[ids];gaps=geometry.distance_gradient(points,position,rotation)[0]
            chosen,method=choose_triangle(points,ids,target,gaps,limits)
            faces=self.skin['faces'][binding['face_ids']]
            self.regions.append(dict(id=record['contact_id'],ids=ids,faces=faces,
                local_faces=np.array([[mapping[v] for v in face] for face in faces]),triple=np.array([mapping[v] for v in chosen]),
                anchor=contact['effector']['surface_vertex'],local_anchor=mapping[contact['effector']['surface_vertex']],
                target=target,normal=np.array(record['desired_normals'][frame]),geometry=geometry,position=position,rotation=rotation,
                limits=limits,anchor_tolerance=record['anchor_tolerance_m']))
            self.selections.append(dict(contact_id=record['contact_id'],vertices=chosen,method=method))
        if not self.regions:raise ValueError('No declared regional contacts at the requested frame')
        self.cache=None;self.guard=None
        self.labels=['floor']+['object:'+name for _,name,_,_ in self.objects]
        for region in self.regions:
            self.labels.extend(region['id']+':'+suffix for suffix in ['patch_clearance',*[f'gap_{i}' for i in range(3)],*[f'radius_{i}' for i in range(3)],*[f'spacing_{i}' for i in range(3)],'area','centroid','normal','anchor'])

    def geometry_slack(self,x):
        _,_,_,vertices=self.fk(x)
        values=[(vertices[:,1].amin()-self.config['clearance_m'])/.001]
        for geometry,_,position,rotation in self.objects:
            values.append(-torch_primitive_clearance_violation(vertices[None],position,rotation,geometry,self.config['object_clearance_m']).amax()/.001)
        result=[torch.stack(values)]
        for r in self.regions:
            g=violations(vertices[r['ids']],r['local_faces'],r['triple'],r['local_anchor'],self.t(r['target']),self.t(r['normal']),
                r['geometry'],self.t(r['position']),self.t(r['rotation']),r['limits'],r['anchor_tolerance'])
            result.append(-reduced_region_residual(g,len(r['ids'])))
        return torch.cat(result)

    def pair(self,x):
        if self.guard is not None:self.guard()
        return super().pair(x)

    def independent(self,x):
        local=self.base['local_rot_mats'][self.frame:self.frame+1].astype(float).copy()
        local[0,self.editable]=local[0,self.editable]@Rotation.from_rotvec(np.asarray(x[:-1]).reshape(-1,3)).as_matrix()
        source={k:v[self.frame:self.frame+1].copy() for k,v in self.base.items()}
        moved={k:v.copy() for k,v in source.items()};moved['root_positions']=moved['root_positions'].astype(float)
        moved['root_positions'][0,1]+=x[-1]
        motion=reconstruct(moved,local,self.parents)
        vertices=self.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        from audit_scene_region_fit import edit_bounds
        bounds,angles,lift=edit_bounds(source,motion,self.names,self.config)
        rows=[]
        for r in self.regions:
            row=measure_frame(vertices,r['ids'],r['faces'],r['target'],r['normal'],r['geometry'],r['position'],r['rotation'],r['limits'])
            error=float(np.linalg.norm(vertices[r['anchor']]-r['target']))
            rows.append(dict(id=r['id'],anchor_error_m=error,anchor_tolerance_m=r['anchor_tolerance'],all_conditions_passed=row['passed'] and error<=r['anchor_tolerance'],**row))
        objects=[dict(id=name,minimum_clearance_m=float(g.distance_gradient(vertices,p.numpy()[0],r.numpy()[0])[0].min())) for g,name,p,r in self.objects]
        floor=float(vertices[:,1].min())
        passed=bounds and all(row['all_conditions_passed'] for row in rows) and floor>=self.config['clearance_m']-1e-6 and all(o['minimum_clearance_m']>=self.config['object_clearance_m']-1e-6 for o in objects)
        return dict(pose_witness_passed=bool(passed),bounds_passed=bounds,maximum_rotation_edit_degrees=float(angles.max()),root_lift_m=float(lift[0]),
            minimum_floor_m=floor,objects=objects,contacts=rows),motion


def run(fit,output,frame=96,iterations=150,seconds=180):
    if type(iterations) is not int or not 1<=iterations<=500 or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('Bounded positive solve budget required')
    torch.set_num_threads(2);fit=Path(fit).resolve();output=Path(output).resolve()
    problem=RegionalPoseProblem(fit,frame);output.mkdir(parents=True,exist_ok=False)
    snapshot=output/'implementation';snapshot.mkdir()
    for pattern in ['*.py','*.gd']:
        for p in (ROOT/'scripts').glob(pattern):shutil.copyfile(p,snapshot/p.name)
    inputs=[fit/n for n in ['protocol.json','result.json','source-motion.npz','motion.npz','authored-scene.json','recipe.json']]+[ASSET]
    protocol=dict(at=now(),fit=fit.relative_to(ROOT).as_posix(),frame=frame,iterations=iterations,seconds_budget=seconds,
        inputs={str(p):sha256(p) for p in inputs},methods={p.name:sha256(p) for p in snapshot.iterdir()},selections=problem.selections,
        rotation_limits_degrees=dict(zip([problem.names[j] for j in problem.editable],np.rad2deg(problem.limits))),max_root_lift_m=problem.config['max_root_lift_m'],
        scope='One native pose; original regions/anchors/full skin/floor and edit bounds. Temporal spline/rate/support constraints are relaxed. Fixed triangle witnesses may miss feasible correspondences. A failed local solve is not an infeasibility certificate; success is not a usable clip.',quality_approved=False)
    save(output/'protocol.json',protocol)
    seed_audit,_=problem.independent(problem.seed)
    with torch.no_grad():r,p,_,_=problem.fk(problem.t(problem.seed))
    seed_error=max(float(abs(r.numpy()-problem.candidate['global_rot_mats'][frame]).max()),float(abs(p.numpy()-problem.candidate['posed_joints'][frame]).max()))
    if seed_error>2e-6:raise ValueError('Seed FK does not reproduce the saved regional fit')
    # Away from changing maxima, every regional row and the full-skin extrema
    # must agree with a directional central difference, not only the anchors.
    direction=np.random.default_rng(716).normal(size=problem.dim);direction/=np.linalg.norm(direction);h=1e-7
    values,jac=problem.pair(problem.seed)
    with torch.no_grad():fd=((problem.geometry_slack(problem.t(problem.seed+h*direction))-problem.geometry_slack(problem.t(problem.seed-h*direction)))/(2*h)).numpy()
    np.testing.assert_allclose(jac[:len(problem.labels)]@direction,fd,atol=2e-4,rtol=2e-4)
    save(output/'preflight.json',dict(seed=seed_audit,seed_fk_error=seed_error,directional_max_error=float(abs(jac[:len(fd)]@direction-fd).max()),constraint_count=len(values),labels=problem.labels))
    started=time.monotonic();history=[];current=problem.seed.copy();peak=0
    scale=np.r_[np.repeat(problem.limits,3),problem.config['max_root_lift_m']]
    def guard():
        nonlocal peak
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-started>seconds or rss>2*1024**3 or psutil.virtual_memory().available<1.25*1024**3:raise TimeoutError('Pose diagnostic resource guard')
    problem.guard=guard
    def objective(x):
        guard();delta=(x-problem.seed)/scale
        return .5*float(delta@delta),delta/scale
    def callback(x):
        nonlocal current
        current=x.copy();slack=problem.pair(x)[0]
        row=dict(iteration=len(history)+1,seconds=time.monotonic()-started,minimum_slack=float(slack.min()),failed_constraints=int((slack<0).sum()))
        history.append(row);save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created_at=psutil.Process().create_time(),history=history))
        if len(history)%10==0:print(row,flush=True)
    lower=np.r_[-np.repeat(problem.limits,3),0.];upper=np.r_[np.repeat(problem.limits,3),problem.config['max_root_lift_m']]
    try:
        result=minimize(objective,problem.seed,method='SLSQP',jac=True,bounds=list(zip(lower,upper)),
            constraints=[dict(type='ineq',fun=lambda x:problem.pair(x)[0],jac=lambda x:problem.pair(x)[1])],callback=callback,
            options=dict(maxiter=iterations,ftol=1e-10))
        current=result.x;solver=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev));status='complete'
    except TimeoutError as exc:solver=dict(success=False,message=str(exc));status='interrupted_resource_guard'
    problem.guard=None
    audit,motion=problem.independent(current);np.savez(output/'pose.npz',**motion)
    with torch.no_grad():_,_,_,v=problem.fk(problem.t(current))
    vertices=problem.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);error=float(abs(vertices-v.numpy()).max())
    if error>2e-6:raise ValueError('Independent serialized skin mismatch')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Pose input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Pose method changed')
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-started,peak_rss_bytes=peak,seed=seed_audit,candidate=audit,
        parameters=current.tolist(),independent_skin_error_m=error,pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False))
    print(dict(status=status,solver=solver,candidate=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fit',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--frame',type=int,default=96);parser.add_argument('--iterations',type=int,default=150);parser.add_argument('--seconds',type=float,default=180.)
    a=parser.parse_args()
    with threadpool_limits(limits=2):run(a.fit,a.output,a.frame,a.iterations,a.seconds)
