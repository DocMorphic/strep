"""Experimental source-surface clearance transfer; never infers planted support."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_transition import localize
from rig_loop import encode
from target_rig_contact import Fitter
from rig_periodic_contact import clip_step, neighbor_constraints


def right_jacobian(vector):
    x,y,z=vector;hat=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
    angle=np.linalg.norm(vector)
    if angle<1e-6:
        return np.eye(3)-.5*hat+(1/6)*hat@hat
    return np.eye(3)-(1-np.cos(angle))/angle**2*hat+(angle-np.sin(angle))/angle**3*hat@hat


def foot_regions(rig, mapping):
    """All surface vertices with >=65% weight on the mapped foot and toe."""
    regions = {}
    for side in ('Left', 'Right'):
        roles = [side+'Foot', side+'ToeBase']
        nodes = {mapping[r] for r in roles if r in mapping}
        membership = []
        for p in rig.primitives:
            membership.extend(np.zeros(len(p['positions'])) if p['joints'] is None else
                np.sum(p['weights']*np.isin(np.asarray(rig.joints)[p['joints']], list(nodes)), axis=1))
        ids = np.flatnonzero(np.asarray(membership) >= .65)
        if len(ids) < 12:
            raise ValueError('Insufficient weighted foot geometry for '+side)
        regions[side] = ids
    return regions


def native_heights(motion, skin):
    names = list(map(str, skin['rig_joint_names']))
    points = np.c_[skin['bind_vertices'], np.ones(len(skin['bind_vertices']))]
    inverse = np.linalg.inv(skin['bind_rig_transform'])
    indices, weights = skin['lbs_indices'], skin['lbs_weights']
    result = {}
    for side in ('Left', 'Right'):
        nodes = [names.index(side+r) for r in ('Foot', 'ToeBase')]
        ids = np.flatnonzero(np.sum(weights*np.isin(indices, nodes), axis=1) >= .65)
        if len(ids) < 12:
            raise ValueError('Insufficient native foot geometry')
        heights = []
        for rotations, positions in zip(motion['global_rot_mats'], motion['posed_joints']):
            world = np.broadcast_to(np.eye(4), (len(names),4,4)).copy()
            world[:,:3,:3] = rotations; world[:,:3,3] = positions
            transforms = world@inverse
            y = np.sum(np.einsum('vki,vi->vk', transforms[indices[ids],1,:], points[ids])*weights[ids],axis=1)
            heights.append(float(y.min()))
        result[side] = np.asarray(heights)
    return result


class ClearanceFitter(Fitter):
    def __init__(self, rig, spec, local, targets, envelope, horizontal_reference=None):
        super().__init__(rig, spec, local)
        self.targets = targets
        self.horizontal_reference=horizontal_reference
        self.envelope = np.asarray(envelope, float)
        if self.envelope.shape != (len(local),) or not np.isfinite(self.envelope).all() or np.any((self.envelope<0)|(self.envelope>1)):
            raise ValueError('Invalid editable frame envelope')
        chains=[]
        for n in range(len(rig.parents)):
            chain=set()
            while n>=0:chain.add(n);n=rig.parents[n]
            chains.append(chain)
        self.descendants={node:np.array([node in chain for chain in chains]) for node in [spec['root_node']]+self.nodes}

    def surface_jacobian(self, frame, values):
        world,_=self.pose(frame,values);positions=[];rows=[]
        axes=[world[node,:3,:3]@right_jacobian(v) for node,v in zip(self.nodes,values[3:].reshape(-1,3))]
        for nodes,points,weights in self.skin.parts:
            components=np.einsum('vkij,vkj->vki',world[nodes,:3,:],points)
            positions.append(np.sum(components*weights[:,:,None],axis=1))
            jac=np.zeros((len(nodes),3,len(values)))
            root_weight=np.sum(weights*self.descendants[self.spec['root_node']][nodes],axis=1)
            for axis in range(3):jac[:,axis,axis]=root_weight
            for j,(node,axis) in enumerate(zip(self.nodes,axes)):
                weighted=weights*self.descendants[node][nodes]
                delta=np.sum((components-world[node,:3,3])*weighted[:,:,None],axis=1)
                sl=slice(3+j*3,6+j*3)
                jac[:,0,sl]=delta[:,2,None]*axis[1]-delta[:,1,None]*axis[2]
                jac[:,1,sl]=delta[:,0,None]*axis[2]-delta[:,2,None]*axis[0]
                jac[:,2,sl]=delta[:,1,None]*axis[0]-delta[:,0,None]*axis[1]
            rows.append(jac)
        return np.concatenate(positions),np.concatenate(rows)

    def height_jacobian(self,frame,values):
        positions,jac=self.surface_jacobian(frame,values)
        return positions[:,1],jac[:,1]

    def objective_pair(self, frame, values, neighbors):
        positions,full_jac=self.surface_jacobian(frame,values)
        return self.objective_from_surface(frame,values,neighbors,positions,full_jac)

    def objective_from_surface(self,frame,values,neighbors,positions,full_jac):
        """Reuse a caller's exact surface evaluation for composite objectives."""
        heights=positions[:,1];jac=full_jac[:,1]
        obj = self.spec['objective']
        selected=[p['vertices'][int(np.argmin(heights[p['vertices']]))] for p in self.spec['patches'].values()]
        parts = [np.array([(heights[idx]-self.targets[name][frame])*12.
                  for idx,name in zip(selected,self.spec['patches'])]),
                 np.minimum(heights,0)*obj['floor_weight'],
                 values[:3]*obj['root_prior'], values[3:]*obj['rotation_prior_m_per_radian']]
        identity=np.eye(len(values))
        derivatives=[jac[selected]*12.,jac*(heights<0)[:,None]*obj['floor_weight'],identity[:3]*obj['root_prior'],identity[3:]*obj['rotation_prior_m_per_radian']]
        if self.horizontal_reference is not None:
            for p in self.spec['patches'].values():
                ids=p['vertices'];weight=30./np.sqrt(len(ids))
                parts.append(((positions[ids][:,[0,2]]-self.horizontal_reference[frame,ids][:,[0,2]])*weight).ravel())
                derivatives.append((full_jac[ids][:,[0,2]]*weight).reshape(-1,len(values)))
        scale = np.r_[np.ones(3), np.full(len(values)-3,obj['rotation_prior_m_per_radian'])]*obj['temporal_weight']
        return np.concatenate(parts+[(values-neighbor)*scale for neighbor in neighbors]),np.vstack(derivatives+[identity*scale for _ in neighbors])

    def objective_residual(self,frame,values,neighbors):
        return self.objective_pair(frame,values,neighbors)[0]

    def solve(self, output, max_sweeps=6):
        values = np.zeros((len(self.local),len(self.bounds))); records=[]; converged=False
        root_step = self.spec['limits']['root_step_m']; joint_step = np.radians(self.spec['limits']['joint_step_degrees'])
        for sweep in range(max_sweeps):
            start = values.copy()
            order = range(len(values)) if sweep%2==0 else range(len(values)-1,-1,-1)
            for frame in order:
                if self.envelope[frame] == 0:
                    continue
                neighbors = [values[n].copy() for n in (frame-1,frame+1) if 0<=n<len(values)]
                old=values[frame].copy(); bounds=self.bounds*self.envelope[frame]
                cached_x=None;cached_value=None
                def pair(x):
                    nonlocal cached_x,cached_value
                    if cached_x is None or not np.array_equal(x,cached_x):
                        cached_x=x.copy();cached_value=self.objective_pair(frame,x,neighbors)
                    return cached_value
                residual=lambda x:pair(x)[0]
                constraint=lambda x:neighbor_constraints(x,neighbors,root_step,joint_step)
                objective=lambda x:float(residual(x)@residual(x))
                fit=least_squares(residual,np.clip(old,-bounds+1e-12,bounds-1e-12),jac=lambda x:pair(x)[1],bounds=(-bounds,bounds),max_nfev=self.spec['max_nfev'],ftol=1e-5,xtol=1e-5,gtol=1e-5)
                projected=clip_step(old,fit.x,neighbors,root_step,joint_step)
                fallback=np.linalg.norm(projected-old)<.95*np.linalg.norm(fit.x-old)
                initial_nfev=int(fit.nfev)
                if fallback:
                    fit=minimize(objective,projected,jac=lambda x:2*pair(x)[1].T@pair(x)[0],method='SLSQP',bounds=list(zip(-bounds,bounds)),constraints={'type':'ineq','fun':lambda x:constraint(x)[0],'jac':lambda x:constraint(x)[1]},options={'maxiter':self.spec['max_nfev'],'ftol':1e-9})
                candidate=clip_step(old,np.clip(fit.x,-bounds,bounds),neighbors,root_step,joint_step)
                cost=objective(old); after=cost
                for backtrack in range(20):
                    trial=old+(candidate-old)*(.5**backtrack); trial_cost=objective(trial)
                    if trial_cost<=cost:
                        values[frame]=trial;after=trial_cost;break
                records.append(dict(sweep=sweep,frame=frame,success=bool(fit.success),status=int(fit.status),nfev=int(fit.nfev),initial_nfev=initial_nfev,constrained_fallback=bool(fallback),cost_before=cost,cost_after=after))
                if frame%10==0:save(output/'pipeline.json',dict(status='fitting',sweep=sweep+1,frame=frame))
            change=float(np.abs(values-start).max())
            save(output/'pipeline.json',dict(status='fitting',sweep=sweep+1,max_parameter_change=change))
            print(f'{output.name}: sweep {sweep+1}, change {change:.6g}',flush=True)
            if change<1e-5:
                converged=True;break
        return values,records,dict(sweeps=sweep+1,small_update_stopping_rule=converged,max_parameter_change=change,stationarity_proven=False)


def prepare(job, output):
    """Freeze one complete prompt-edit job; no new inference or original mutations."""
    from rig_contact_authoring import source, empty_spec
    from rig_clip_import import AnimationSampler
    from retarget_rig import calibration, resolve_profile
    from kimodo.skeleton import SOMASkeleton77
    from build_soma_preview import ASSET
    folder, result, request, report, glb = source(job,'transfer')
    if request['kind']!='prompt_edit':
        raise ValueError('This experiment requires a finite prompt-edit result')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    rig=RigAsset.load(glb);reference=RigAsset.load(folder/'source/character.glb')
    profile=read(folder/'source/rig-profile.json');mapping,offset=resolve_profile(reference,profile)
    _,scale,_=calibration(reference,mapping,SOMASkeleton77(),profile.get('axis_alignment_xyzw'))
    sampler=AnimationSampler(rig.document,rig.binary,0)
    before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])])
    regions=foot_regions(rig,mapping)
    source_rig=RigAsset.load(folder/'input/character.glb');source_sampler=AnimationSampler(source_rig.document,source_rig.binary,0)
    original=np.array([source_sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])])
    motion=dict(np.load(folder/'generation/aligned-generated.npz',allow_pickle=False))
    native=native_heights(motion,dict(np.load(ASSET,allow_pickle=False)))
    timeline=read(folder/'transfer/timeline.json');a=timeline['regeneration']['start_frame'];b=timeline['regeneration']['last_frame']
    envelope=np.zeros(len(before));envelope[a:b+1]=timeline['regeneration']['weights']
    # Source penetration is not deliberately transferred. Neither clamping nor
    # this height correspondence is a contact or flight label.
    targets={}; original_heights={}
    for name,ids in regions.items():
        h=np.array([source_rig.vertices(w)[ids,1].min() for w in original]);original_heights[name]=h
        targets[name]=h.copy();targets[name][a:b+1]=(1-envelope[a:b+1])*h[a:b+1]+envelope[a:b+1]*np.maximum(0,native[name]*scale+offset[1])
    spec=empty_spec(report);spec['patches']={name:dict(vertices=ids.tolist()) for name,ids in regions.items()};spec['contacts']=[]
    spec['max_nfev']=80
    spec['provenance']='Surface height correspondences, not support contacts. Native foot clearance scaled by leg length; zero-clamped inside regeneration, input geometry at fixed boundaries.'
    save(output/'spec.json',spec)
    save(output/'request.json',dict(job=job,source_glb_sha256=sha256(glb),source_profile_sha256=sha256(folder/'source/rig-profile.json'),native_motion_sha256=sha256(folder/'generation/aligned-generated.npz'),skin_sha256=sha256(ASSET),leg_scale=scale,world_offset_m=offset.tolist(),envelope=envelope.tolist(),targets_m={k:v.tolist() for k,v in targets.items()},raw_native_heights_m={k:v.tolist() for k,v in native.items()},original_heights_m={k:v.tolist() for k,v in original_heights.items()},source_model_guides_passed=read(folder/'transfer/prompt-edit-audit.json')['raw_anchor_audit']['numerical_screen_passed'],human_approved=False))
    shutil.copytree(folder/'transfer',output/'input')
    return rig,before,report,spec,targets,envelope


def run(job, output):
    output=Path(output);rig,before,report,spec,targets,envelope=prepare(job,output)
    snapshot=output/'implementation';snapshot.mkdir()
    for name in ('rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py','rig_loop.py','rig_asset.py'):
        shutil.copyfile(Path(__file__).with_name(name),snapshot/name)
    horizontal_reference=np.array([rig.vertices(world) for world in before])
    fitter=ClearanceFitter(rig,spec,localize(before,rig.parents),targets,envelope,horizontal_reference)
    save(output/'pipeline.json',dict(status='fitting',sweep=0))
    with threadpool_limits(limits=1):
        parameters,solver,convergence=fitter.solve(output)
    after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
    out=output/'candidate';out.mkdir()
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times,roundtrip=encode(rig,after,animated,report['root_node'],out/'character.glb','Surface clearance candidate')
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (output/'input'/name).exists():shutil.copyfile(output/'input'/name,out/name)
    root=report['root_node']
    save(out/'root-motion.json',dict(node=root,space='Pelvis world transform after bounded source-surface correction; no root extraction',times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
    report=copy.deepcopy(report);report.update(glb_sha256=sha256(out/'character.glb'),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'],contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),human_approved=False)
    save(out/'report.json',report)
    np.savez_compressed(output/'fit.npz',before=before,after=after,parameters=parameters)
    save(output/'solver.json',solver)
    save(output/'fit-summary.json',dict(convergence=convergence,export=roundtrip,scope='Experimental surface-height transfer, not planted-support, dynamics, collision or semantic approval. Source/raw model untouched; independent verification required.'))
    save(output/'pipeline.json',dict(status='complete',quality_approved=False))
    return output


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job');p.add_argument('output',type=Path)
    args=p.parse_args();run(args.job,args.output)
