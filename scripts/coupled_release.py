"""Joint arm fit across a grasp/release boundary with frozen non-arm motion."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from scipy.optimize import least_squares
from scipy.sparse import csr_matrix
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_pose_witness_bounded import inverse_rotation_bound
from grasp_contact_binding import apply_region_binding
from support_contact_v8 import bounded_rotation,rodrigues
from region_grasp_track import arm_columns
from sphere_approach import set_problem_frame


def second_difference_matrix(count):
    if type(count) is not int or count<3: raise ValueError('At least three keys required')
    matrix=np.zeros((count-2,count))
    for i in range(count-2): matrix[i,i:i+3]=[1,-2,1]
    return matrix


class CoupledWindow:
    def __init__(self,problems,fixed,source,frames,protocol,settings):
        self.problems,self.fixed,self.source,self.frames=problems,fixed,source,frames
        self.settings=settings; self.columns,self.limits=arm_columns(problems[0])
        self.arms=[problems[0].names.index(side+n) for side in ['Left','Right'] for n in ['Shoulder','Arm','ForeArm','Hand']]
        self.support=list(range(frames[0]-2,frames[-1]+3)); self.difference=second_difference_matrix(len(self.support))
        self.initial=np.concatenate([inverse_rotation_bound(v[self.columns].reshape(-1,3),self.limits).ravel() for v in fixed])
        self.specs=[]
        self.anchor_support=[]
        for frame in self.support:
            vertices=problems[0].surface.vertices(source['global_rot_mats'][frame],source['posed_joints'][frame])
            self.anchor_support.append(np.concatenate([vertices[b['anchor']] for b in protocol['contact_bindings']]))
        self.anchor_support=np.array(self.anchor_support)
        for frame,p,values in zip(frames,problems,fixed):
            with torch.no_grad(): _,joints,_,vertices=p.fk(p.t(values))
            specs=[]
            for binding,region in zip(protocol['contact_bindings'],protocol['region_protocols']):
                faces=p.skin['faces'][region['patch']['face_ids']]; anchor=binding['anchor']; hand=binding['hand']
                wrist=p.names.index(hand);knuckles=[p.names.index(hand+n+'2') for n in ['Index','Middle','Ring','Pinky']]
                tri=vertices[faces];normal=torch.linalg.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);normal/=torch.linalg.vector_norm(normal)
                tangent=joints[knuckles].mean(0)-joints[wrist];tangent-=normal*(normal@tangent);tangent/=torch.linalg.vector_norm(tangent)
                # Preserve the measured passing hand frame during grasp. After
                # release this is only weak guidance, not a new contact event.
                specs.append((anchor,faces,wrist,knuckles,vertices[anchor].numpy().copy(),normal.numpy().copy(),tangent.numpy().copy()))
            self.specs.append(specs)

    def physical(self,index,raw):
        p=self.problems[index]
        angles=bounded_rotation(raw.reshape(-1,3)/p.t(self.limits)[:,None],p.t(self.limits)[:,None]).ravel()
        return p.t(self.fixed[index]).index_copy(0,torch.as_tensor(self.columns),angles)

    def geometry(self,index,raw):
        p=self.problems[index];_,joints,_,vertices=p.fk(self.physical(index,raw));values=[]
        active=self.frames[index]<=self.settings['release_frame']
        point_scale=self.settings['active_point_scale_m'] if active else self.settings['release_point_scale_m']
        direction_scale=self.settings['active_direction_scale'] if active else self.settings['release_direction_scale']
        for anchor,faces,wrist,knuckles,point,normal,tangent in self.specs[index]:
            tri=vertices[faces];n=torch.linalg.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);n=n/torch.linalg.vector_norm(n)
            t=joints[knuckles].mean(0)-joints[wrist];t=t-n*(n@t);t=t/torch.linalg.vector_norm(t)
            values.extend([(vertices[anchor]-p.t(point))/point_scale,(n-p.t(normal))/direction_scale,(t-p.t(tangent))/direction_scale])
        values.append(torch.relu(p.t(p.config['clearance_m'])-vertices[:,1].min()).reshape(1)/self.settings['geometry_scale_m'])
        for geometry,_,position,_ in p.objects:
            if geometry.shape!='sphere': raise ValueError('This development window requires sphere objects')
            gap=torch.linalg.vector_norm(vertices-position,dim=1).min()-geometry.dimensions[0]
            values.append(torch.relu(p.t(p.config['object_clearance_m']+.00005)-gap).reshape(1)/self.settings['geometry_scale_m'])
        return torch.cat(values)

    def arm_local(self,index,raw):
        p=self.problems[index];values=self.physical(index,raw)
        return (p.initial[self.arms]@rodrigues(values[self.columns].reshape(-1,3))).reshape(-1)

    def pair(self,flat,jacobian=True):
        count=len(self.frames);width=len(self.columns);blocks=flat.reshape(count,width);residual=[];jac=[]
        local=self.source['local_rot_mats'][self.support][:,self.arms].astype(float).reshape(len(self.support),-1).copy();local_jac={}
        anchors=self.anchor_support.copy();anchor_jac={}
        for i,(frame,p) in enumerate(zip(self.frames,self.problems)):
            variable=p.t(blocks[i]).requires_grad_();g=self.geometry(i,variable)
            residual.append(g.detach().numpy())
            if jacobian:
                block=np.array([torch.autograd.grad(v,variable,retain_graph=True)[0].detach().numpy() for v in g])
                full=np.zeros((len(g),len(flat)));full[:,i*width:(i+1)*width]=block;jac.append(full)
                local_jac[i]=torch.autograd.functional.jacobian(lambda x:self.arm_local(i,x),variable,vectorize=True).detach().numpy()
            local[self.support.index(frame)]=self.arm_local(i,variable).detach().numpy()
            point_scale=self.settings['active_point_scale_m'] if frame<=self.settings['release_frame'] else self.settings['release_point_scale_m']
            anchor_rows=np.r_[0:3,9:12]
            anchors[self.support.index(frame)]=np.concatenate([spec[4] for spec in self.specs[i]])+g.detach().numpy()[anchor_rows]*point_scale
            if jacobian: anchor_jac[i]=block[anchor_rows]*point_scale
        scale=self.settings['curvature_scale'];residual.append((self.difference@local/scale).ravel())
        if jacobian:
            smooth=np.zeros(((len(self.support)-2)*local.shape[1],len(flat)))
            for i,frame in enumerate(self.frames):
                smooth[:,i*width:(i+1)*width]=np.kron(self.difference[:,self.support.index(frame),None],local_jac[i])/scale
            jac.append(smooth)
        cartesian_scale=self.settings.get('cartesian_curvature_scale_m')
        if cartesian_scale is not None:
            residual.append((self.difference@anchors/cartesian_scale).ravel())
            if jacobian:
                smooth=np.zeros(((len(self.support)-2)*6,len(flat)))
                for i,frame in enumerate(self.frames):smooth[:,i*width:(i+1)*width]=np.kron(self.difference[:,self.support.index(frame),None],anchor_jac[i])/cartesian_scale
                jac.append(smooth)
        residual.append(self.settings['regularization']*(flat-self.initial))
        if jacobian: jac.append(self.settings['regularization']*np.eye(len(flat)))
        return np.concatenate(residual),np.concatenate(jac) if jacobian else None


def run(spatial_report,output,cartesian_curvature_scale_m=None):
    if cartesian_curvature_scale_m is not None and (not np.isfinite(cartesian_curvature_scale_m) or cartesian_curvature_scale_m<=0): raise ValueError('Positive finite Cartesian curvature scale required')
    torch.set_num_threads(2);spatial_report,output=Path(spatial_report).resolve(),Path(output).resolve()
    sp,sr=read(spatial_report/'protocol.json'),read(spatial_report/'result.json')
    if sr['status']!='complete' or sha256(spatial_report/'motion.npz')!=sr['motion_sha256'] or sha256(spatial_report/'protocol.json')!=sr['protocol_sha256']: raise ValueError('Completed unchanged spatial input required')
    study=ROOT/sp['base_study'];protocol,result=read(study/'protocol.json'),read(study/'result.json')
    inputs=dict(sp['inputs'])
    for name in ['protocol.json','result.json','motion.npz']:inputs[(spatial_report/name).relative_to(ROOT).as_posix()]=sha256(spatial_report/name)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest: raise ValueError('Input changed')
    fit=ROOT/protocol['study']/'fit';folder=fit/'assets'/read(fit/'summary.json')['trials'][0]['id']/'A'
    source=dict(np.load(spatial_report/'motion.npz',allow_pickle=False));skin=dict(np.load(ASSET,allow_pickle=False))
    endpoint=protocol['active_interval'][1];frames=list(range(endpoint-5,endpoint+4))
    parameters={r['frame']:np.array(r['parameters']) for r in result['rows']};parameters.update({r['frame']:np.array(r['parameters']) for r in sr['rows']})
    problems=[]
    for frame in frames:
        p=PoseProblem(folder,skin,min(frame,endpoint));set_problem_frame(p,frame)
        for binding,region in zip(protocol['contact_bindings'],protocol['region_protocols']):apply_region_binding(p,binding['hand'],binding['anchor'],region['patch'])
        problems.append(p)
    settings=dict(release_frame=endpoint,active_point_scale_m=.00002,active_direction_scale=.001,release_point_scale_m=.005,release_direction_scale=.05,
                  geometry_scale_m=.00005,curvature_scale=.02,cartesian_curvature_scale_m=cartesian_curvature_scale_m,regularization=1e-5,maximum_evaluations=20,maximum_seconds=180,maximum_rss_bytes=3*1024**3,minimum_available_bytes=1024**3)
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    methods=['coupled_release.py','grasp_pose_witness.py','grasp_pose_witness_bounded.py','grasp_contact_binding.py','sphere_approach.py','region_grasp_track.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py']
    implementation={n:sha256(ROOT/'scripts'/n) for n in methods}
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    window=CoupledWindow(problems,[parameters[f] for f in frames],source,frames,protocol,settings)
    save(output/'protocol.json',dict(at=now(),spatial_report=spatial_report.relative_to(ROOT).as_posix(),base_study=sp['base_study'],inputs=inputs,implementation=implementation,frames=frames,
         arm_columns=window.columns.tolist(),settings=settings,targets=[[[int(s[0]),s[4].tolist(),s[5].tolist(),s[6].tolist()] for s in specs] for specs in window.specs],
         scope='Joint nine-key arm fit across grasp and release; frozen non-arm edits/root and all outside keys. Chordal local-rotation and optional world-anchor second differences are fitting objectives, not physical acceleration guarantees. Authored contact times/regions/limits unchanged; full dense contact/geometry audit required.',quality_approved=False))
    initial=window.initial;began=time.monotonic();res,jac=window.pair(initial)
    direction=np.random.default_rng(1891).normal(size=len(initial));direction/=np.linalg.norm(direction);h=1e-6
    fd=(window.pair(initial+h*direction,False)[0]-window.pair(initial-h*direction,False)[0])/(2*h)
    derivative_error=float(np.max(np.abs(fd-jac@direction)));np.testing.assert_allclose(fd,jac@direction,atol=2e-4,rtol=2e-4)
    save(output/'derivative-proof.json',dict(at=now(),maximum_error=derivative_error,variables=len(initial),residuals=len(res),initial_squared_residual=float(res@res)))
    cache=(initial.copy(),res,jac);last=initial.copy();evaluations=0
    def pair(x):
        nonlocal cache,last,evaluations
        if np.array_equal(cache[0],x):return cache[1:]
        if time.monotonic()-began>settings['maximum_seconds'] or psutil.Process().memory_info().rss>settings['maximum_rss_bytes'] or psutil.virtual_memory().available<settings['minimum_available_bytes']:raise TimeoutError('Coupled fit resource guard')
        r,j=window.pair(x);cache=(x.copy(),r,j);last=x.copy();evaluations+=1
        save(output/'progress.json',dict(status='running',evaluations=evaluations,squared_residual=float(r@r),seconds=time.monotonic()-began));print(dict(evaluation=evaluations,squared_residual=float(r@r)),flush=True)
        return r,j
    status='complete'
    try:
        fit_result=least_squares(lambda x:pair(x)[0],initial,jac=lambda x:csr_matrix(pair(x)[1]),max_nfev=settings['maximum_evaluations'],ftol=1e-8,xtol=1e-8,gtol=1e-8)
        last=fit_result.x;solver=dict(success=bool(fit_result.success),message=str(fit_result.message),evaluations=int(fit_result.nfev))
    except TimeoutError as exc:status='interrupted_resource_guard';solver=dict(success=False,message=str(exc),evaluations=evaluations)
    candidate={k:v.copy() for k,v in source.items()};rows=[]
    for i,(frame,p) in enumerate(zip(frames,problems)):
        values=window.physical(i,p.t(last.reshape(len(frames),-1)[i])).numpy();audit,motion=p.independent(values)
        for name in candidate:candidate[name][frame]=motion[name][0]
        rows.append(dict(frame=frame,parameters=values.tolist(),candidate=audit))
    protected=np.setdiff1d(np.arange(len(source['root_positions'])),frames)
    for name in source:np.testing.assert_array_equal(source[name][protected],candidate[name][protected])
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed during fit')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed during fit')
    np.savez(output/'motion.npz',**candidate)
    save(output/'result.json',dict(at=now(),status=status,solver=solver,rows=rows,protected_frames_exact=len(protected),motion_sha256=sha256(output/'motion.npz'),protocol_sha256=sha256(output/'protocol.json'),seconds=time.monotonic()-began,quality_approved=False))
    save(output/'progress.json',dict(status=status,solver=solver))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('spatial_report',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--cartesian-curvature-scale-m',type=float);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.spatial_report,args.output,args.cartesian_curvature_scale_m)
