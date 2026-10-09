"""Isolated pose witness for a saved grasp; not a clip or infeasibility proof."""
import argparse
import shutil
import time
from pathlib import Path
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
from support_contact_v8 import rodrigues,finger_rotation_budgets,torch_primitive_clearance_violation
from scene_solver_context import context_primitives

BODY=['Spine1','Spine2','Chest','Neck1','Neck2','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand','LeftLeg','LeftShin','LeftFoot','RightLeg','RightShin','RightFoot']


def norm_slack_and_jacobian(x,limits):
    angles=np.asarray(x[:-1]).reshape(-1,3);limits=np.asarray(limits)
    slack=1-np.sum(angles**2,axis=1)/limits**2
    jac=np.zeros((len(limits),len(x)))
    for i in range(len(limits)):jac[i,3*i:3*i+3]=-2*angles[i]/limits[i]**2
    return slack,jac


def conservative_max(values,temperature=0.):
    if not np.isfinite(temperature) or temperature<0:raise ValueError('Nonnegative finite smoothing temperature required')
    values=values.reshape(-1)
    return values.max() if temperature==0 else temperature*torch.logsumexp(values/temperature,dim=0)


class PoseProblem:
    def __init__(self,folder,skin,frame):
        self.frame=frame;self.skin=skin;self.surface=Surface(skin);self.names,self.parents,_=skeleton_metadata(77)
        self.base=dict(np.load(folder/'limb-motion.npz',allow_pickle=False));self.previous=dict(np.load(folder/'previous-motion.npz',allow_pickle=False));self.candidate=dict(np.load(folder/'motion.npz',allow_pickle=False))
        self.recipe=read(folder/'recipe.json')['contact'];self.config=self.recipe['config'];self.context=self.recipe['scene_context']
        if not 0<=frame<len(self.base['root_positions']):raise ValueError('Frame outside clip')
        if self.context.get('partner_cuts') or any('tangent_directions' in c for c in self.context['normals']):raise ValueError('This diagnostic does not support partner cuts or tangents')
        fingers=finger_rotation_budgets(self.names)
        self.editable=[self.names.index(n) for n in BODY]+list(fingers)
        self.limits=np.deg2rad([self.config['max_rotation_degrees']]*len(BODY)+list(fingers.values()))
        self.lookup={j:i for i,j in enumerate(self.editable)};self.dim=3*len(self.editable)+1
        self.t=lambda a:torch.as_tensor(np.asarray(a),dtype=torch.float64)
        self.initial=self.t(self.previous['local_rot_mats'][frame]);self.root=self.t(self.base['root_positions'][frame])
        offsets=np.zeros((77,3))
        for j,p in enumerate(self.parents):
            if p>=0:offsets[j]=self.base['global_rot_mats'][frame,p].T@(self.base['posed_joints'][frame,j]-self.base['posed_joints'][frame,p])
        self.offsets=self.t(offsets);self.indices=skin['lbs_indices'];self.weights=self.t(skin['lbs_weights'])
        self.bind=self.t(np.einsum('vwij,vj->vwi',self.surface.inverse[self.indices],self.surface.points)[:,:,:3])
        spec=self.recipe['release_endpoint_guards']['solver_contact_spec'];self.contacts=[]
        for region,entry in spec['regions'].items():
            for seg in entry.get('segments',[]):
                if seg['start_frame']<=frame<=seg['end_frame']:
                    if seg['space']!='track':raise ValueError('Expected compiled target tracks')
                    self.contacts.append(dict(region=region,vertex=seg['vertex_id'],target=seg['positions_m'][frame-seg['start_frame']]))
        if not self.contacts:raise ValueError('No authored contacts at diagnostic frame')
        active_ids={c['vertex'] for c in self.contacts};self.normals=[]
        for c in self.context['normals']:
            if c['surface_vertex'] in active_ids:
                faces=skin['faces'][np.any(skin['faces']==c['surface_vertex'],axis=1)]
                self.normals.append((c['id'],faces,self.t(c['directions'][frame])))
        self.objects=[(g,o['id'],self.t(o['positions_m'][frame])[None],self.t(o['rotations'][frame])[None]) for g,o in context_primitives(self.context)]
        relative=self.previous['local_rot_mats'][frame].transpose(0,2,1)@self.candidate['local_rot_mats'][frame]
        theta=Rotation.from_matrix(relative[self.editable]).as_rotvec()
        self.seed=np.r_[theta.ravel(),self.recipe['root_lift_m'][frame]]
        if norm_slack_and_jacobian(self.seed,self.limits)[0].min() < -1e-6:raise ValueError('Seed violates rotation norm budgets')
        self.labels=['point:'+c['region'] for c in self.contacts]+['normal:'+c[0] for c in self.normals]+['floor']+['object:'+o[1] for o in self.objects]
        self.cache=None

    def fk(self,x,*,vertices=True):
        """Native pose; omit mesh skinning only for joint-only consumers."""
        change=rodrigues(x[:-1].reshape(-1,3));rot=[];pos=[];local=[]
        for j,parent in enumerate(self.parents):
            r=self.initial[j] if j not in self.lookup else self.initial[j]@change[self.lookup[j]]
            local.append(r)
            if parent<0:rot.append(r);pos.append(self.root+torch.stack([x[-1]*0,x[-1],x[-1]*0]))
            else:rot.append(rot[parent]@r);pos.append(pos[parent]+rot[parent]@self.offsets[j])
        r=torch.stack(rot);p=torch.stack(pos)
        vertices=(((r[self.indices]@self.bind[:,:,:,None]).squeeze(-1)+p[self.indices])*self.weights[:,:,None]).sum(1) if vertices else None
        return r,p,torch.stack(local),vertices

    def geometry_slack(self,x,smooth_max_m=0.):
        _,_,_,v=self.fk(x);values=[]
        for c in self.contacts:values.append((self.config['point_tolerance_m']-torch.linalg.vector_norm(v[c['vertex']]-self.t(c['target'])))/.01)
        chord=2*np.sin(np.deg2rad(self.config['normal_tolerance_degrees'])/2)
        for _,faces,target in self.normals:
            tri=v[faces];n=torch.linalg.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);n=n/torch.linalg.vector_norm(n).clamp_min(1e-12)
            values.append((chord-torch.linalg.vector_norm(n-target))/chord)
        values.append(-conservative_max(self.config['clearance_m']-v[:,1],smooth_max_m)/.01)
        for geometry,_,position,rotation in self.objects:values.append(-conservative_max(torch_primitive_clearance_violation(v[None],position,rotation,geometry,self.config['object_clearance_m']),smooth_max_m)/.01)
        return torch.stack(values)

    def pair(self,x):
        if self.cache is not None and np.array_equal(x,self.cache[0]):return self.cache[1:]
        variable=self.t(x).requires_grad_();values=self.geometry_slack(variable)
        jac=np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() for value in values])
        slack=values.detach().numpy();bounds,bjac=norm_slack_and_jacobian(x,self.limits)
        self.cache=(np.array(x).copy(),np.r_[slack,bounds],np.concatenate([jac,bjac]))
        return self.cache[1:]

    def independent(self,x):
        frame=self.frame;theta=np.asarray(x[:-1]).reshape(-1,3)
        local=self.previous['local_rot_mats'][frame:frame+1].astype(float).copy()
        local[0,self.editable]=local[0,self.editable]@Rotation.from_rotvec(theta).as_matrix()
        source={k:v[frame:frame+1].copy() for k,v in self.base.items()}
        source['root_positions']=source['root_positions'].astype(float);source['root_positions'][0,1]+=x[-1]
        motion=reconstruct(source,local,self.parents);v=self.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);contacts=[]
        for c in self.contacts:contacts.append(dict(region=c['region'],error_m=float(np.linalg.norm(v[c['vertex']]-c['target']))))
        normals=[]
        for name,faces,target in self.normals:
            tri=v[faces];n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);n/=np.linalg.norm(n)
            normals.append(dict(id=name,error_degrees=float(np.rad2deg(np.arccos(np.clip(n@target.numpy(),-1,1))))))
        objects=[]
        for geometry,name,position,rotation in self.objects:
            # Same face-inflation semantics for boxes; radial clearance for spheres.
            if geometry.shape=='cylinder':clearance=geometry.distance_gradient(v,position.numpy()[0],rotation.numpy()[0])[0].min()
            elif geometry.shape=='sphere':clearance=np.linalg.norm(v-position.numpy()[0],axis=1).min()-geometry.dimensions[0]
            else:clearance=(np.abs((v-position.numpy()[0])@rotation.numpy()[0])-np.array(geometry.dimensions)/2).max(-1).min()
            objects.append(dict(id=name,minimum_clearance_m=float(clearance),maximum_penetration_m=float(geometry.penetration_depth(v,position.numpy()[0],rotation.numpy()[0]).max())))
        actual=Rotation.from_matrix(self.previous['local_rot_mats'][frame].transpose(0,2,1)@motion['local_rot_mats'][0]).magnitude()
        fixed=[j for j in range(77) if j not in self.editable];bounds_ok=bool(np.all(actual[self.editable]<=self.limits+1e-6) and np.max(actual[fixed])<1e-6 and 0<=x[-1]<=self.config['max_root_lift_m'])
        passed=bounds_ok and min(v[:,1])>=self.config['clearance_m']-1e-6 and all(c['error_m']<=self.config['point_tolerance_m']+1e-6 for c in contacts) and all(n['error_degrees']<=self.config['normal_tolerance_degrees']+1e-4 for n in normals) and all(o['minimum_clearance_m']>=self.config['object_clearance_m']-1e-6 for o in objects)
        return dict(contacts=contacts,normals=normals,objects=objects,minimum_floor_height_m=float(v[:,1].min()),rotation_norm_bounds_passed=bounds_ok,maximum_rotation_edit_degrees=float(np.rad2deg(actual).max()),root_lift_m=float(x[-1]),pose_witness_passed=bool(passed)),motion


def run(study,output,frame=60):
    torch.set_num_threads(2);study=Path(study).resolve();output=Path(output).resolve();fit=study/'fit';summary=read(fit/'summary.json')
    if summary['solver_version']!=13 or read(study/'pipeline.json')['status']!='complete':raise ValueError('Completed V13 study required')
    if sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Mesh changed')
    trial=summary['trials'][0]['id'];folder=fit/'assets'/trial/'A';skin=dict(np.load(ASSET,allow_pickle=False));problem=PoseProblem(folder,skin,frame)
    output.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__).resolve(),ROOT/'scripts/support_contact_v8.py',ROOT/'scripts/support_contact_v5.py',ROOT/'scripts/floor_contact.py',ROOT/'scripts/scene_solver_context.py',ROOT/'scripts/object_geometry.py',ROOT/'scripts/inspect_motion.py']
    inputs=[folder/n for n in ['limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]+[ASSET]
    limits=dict(iterations=300,seconds=240,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3))
    save(output/'protocol.json',dict(at=now(),frame=frame,study=study.relative_to(ROOT).as_posix(),fit_summary_sha256=sha256(fit/'summary.json'),limits=limits,inputs={p.relative_to(ROOT).as_posix():sha256(p) for p in inputs},implementation={p.name:sha256(p) for p in files},control_budgets=dict(rotation_limits_degrees=dict(zip([problem.names[j] for j in problem.editable],np.rad2deg(problem.limits))),max_root_lift_m=problem.config['max_root_lift_m']),point_tolerance_m=problem.config['point_tolerance_m'],normal_tolerance_degrees=problem.config['normal_tolerance_degrees'],full_skin_clearance_m=problem.config['object_clearance_m'],scope='Single-frame necessary-condition relaxation: no temporal basis, velocity, acceleration, inferred support tracking, balance, self-collision or anatomy. Full skin replaces frozen collision samples. Same norm/root edit bounds; a success is only a pose witness, a failed local solve does not prove infeasibility.',quality_approved=False))
    snap=output/'implementation';snap.mkdir()
    for p in files:shutil.copyfile(p,snap/p.name)
    seed_audit,seed_motion=problem.independent(problem.seed)
    with torch.no_grad():r,p,_,v=problem.fk(problem.t(problem.seed))
    seed_error=max(float(np.abs(p.numpy()-problem.candidate['posed_joints'][frame]).max()),float(np.abs(r.numpy()-problem.candidate['global_rot_mats'][frame]).max()))
    if seed_error>2e-6:raise ValueError('Seed FK does not reproduce V13')
    # Smooth point/normal constraints have directional finite-difference checks.
    direction=np.random.default_rng(716).normal(size=problem.dim);direction/=np.linalg.norm(direction);h=1e-6
    values,jac=problem.pair(problem.seed);count=len(problem.contacts)+len(problem.normals)
    with torch.no_grad():fd=((problem.geometry_slack(problem.t(problem.seed+h*direction))-problem.geometry_slack(problem.t(problem.seed-h*direction)))/(2*h)).numpy()
    np.testing.assert_allclose(jac[:count]@direction,fd[:count],atol=2e-5,rtol=2e-4)
    save(output/'preflight.json',dict(seed=seed_audit,seed_fk_max_error=seed_error,smooth_constraint_directional_error=float(np.max(np.abs(jac[:count]@direction-fd[:count]))),full_skin_vertices=len(skin['bind_vertices'])))
    start=time.monotonic();history=[];current=problem.seed.copy();peak=0
    scale=np.r_[np.repeat(problem.limits,3),problem.config['max_root_lift_m']]
    def objective(x):
        delta=(x-problem.seed)/scale
        return .5*float(delta@delta),delta/scale
    def callback(x):
        nonlocal current,peak
        current=x.copy();slack=problem.pair(x)[0];rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        history.append(dict(iteration=len(history)+1,seconds=time.monotonic()-start,minimum_scaled_slack=float(slack.min()),geometry_slack=dict(zip(problem.labels,slack[:len(problem.labels)].tolist())),norm_min_slack=float(slack[len(problem.labels):].min())))
        save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,created=psutil.Process().create_time(),history=history,peak_rss_bytes=peak))
        if len(history)%10==0:print(history[-1],flush=True)
        if time.monotonic()-start>limits['seconds'] or rss>limits['maximum_rss_bytes'] or psutil.virtual_memory().available<limits['minimum_available_bytes']:raise TimeoutError('Diagnostic resource guard')
    lower=np.r_[-np.repeat(problem.limits,3),0.];upper=np.r_[np.repeat(problem.limits,3),problem.config['max_root_lift_m']]
    try:
        result=minimize(objective,problem.seed,method='SLSQP',jac=True,bounds=list(zip(lower,upper)),constraints=[dict(type='ineq',fun=lambda x:problem.pair(x)[0],jac=lambda x:problem.pair(x)[1])],callback=callback,options=dict(maxiter=limits['iterations'],ftol=1e-10))
        current=result.x;solver=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev));status='complete'
    except TimeoutError as e:solver=dict(success=False,message=str(e));status='interrupted_resource_guard'
    audit,motion=problem.independent(current);np.savez(output/'pose.npz',**motion)
    with torch.no_grad():_,_,_,tv=problem.fk(problem.t(current))
    numpy_vertices=problem.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);error=float(np.max(np.abs(tv.numpy()-numpy_vertices)))
    if error>2e-6:raise ValueError('Independent full-skin mismatch')
    for p in files:
        if sha256(p)!=sha256(snap/p.name):raise ValueError('Implementation changed during solve')
    save(output/'result.json',dict(at=now(),status=status,solver=solver,seconds=time.monotonic()-start,peak_rss_bytes=peak,seed=seed_audit,candidate=audit,parameters=current.tolist(),history=history,independent_skin_max_error_m=error,pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False));print(dict(status=status,solver=solver,audit=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--frame',type=int,default=60);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.frame)
