"""Bounded contact fitting on a ring of phases, with an exact transformed terminal."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.optimize import minimize,least_squares
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from target_rig_contact import Fitter,RigAsset,baseline,audit,floor_lower_bound
from rig_loop import place,encode


def contract(folder,rig,before):
    timeline=read(Path(folder)/'timeline.json');p=timeline['period_frames'];cycle=np.asarray(timeline['cycle_transform'],float)
    if type(p) is not int or not 4<=p<=900 or len(before)!=p+1:raise ValueError('Periodic contacts require one cycle plus its terminal sample')
    if cycle.shape!=(4,4) or not np.isfinite(cycle).all() or not np.allclose(cycle[3],[0,0,0,1],atol=1e-8):raise ValueError('Invalid cycle placement')
    r=cycle[:3,:3]
    if not np.allclose(r.T@r,np.eye(3),atol=1e-7) or not np.isclose(np.linalg.det(r),1,atol=1e-7) or not np.allclose(r@[0,1,0],[0,1,0],atol=1e-7) or abs(cycle[1,3])>1e-7:raise ValueError('Periodic floor fitting requires rigid yaw and horizontal cycle placement')
    root=read(Path(folder)/'report.json')['root_node']
    expected=place(before[:1],rig.parents,root,cycle)[0]
    if np.max(np.abs(expected-before[-1]))>1e-5:raise ValueError('Input terminal pose does not close under the saved cycle transform')
    descendants=set()
    for node in range(len(rig.parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=rig.parents[ancestor]
        if ancestor==root:descendants.add(node)
    for primitive in rig.primitives:
        if primitive['joints'] is None:raise ValueError('Periodic contacts currently require fully skinned geometry')
        weighted={rig.joints[j] for j in np.unique(primitive['joints'][primitive['weights']>0])}
        if weighted-descendants:raise ValueError('Periodic contact geometry must descend from the mapped pelvis')
    return p,cycle,timeline


def clip_step(current,candidate,neighbors,root_step,joint_step):
    """Largest segment step satisfying every Euclidean neighbor edit bound."""
    direction=candidate-current;alpha=1.
    for neighbor in neighbors:
        for sl,radius in [(slice(0,3),root_step)]+[(slice(i,i+3),joint_step) for i in range(3,len(current),3)]:
            v=current[sl]-neighbor[sl];d=direction[sl];a=float(d@d)
            if a<1e-30:continue
            b=2*float(v@d);c=float(v@v-radius*radius)
            if c>1e-10:raise ValueError('Periodic optimizer lost a feasible edit bound')
            limit=(-b+np.sqrt(max(0.,b*b-4*a*min(c,0.))))/(2*a)
            alpha=min(alpha,max(0.,limit))
    return current+direction*alpha


def neighbor_constraints(x,neighbors,root_step,joint_step):
    residual=[];jacobian=[]
    for neighbor in neighbors:
        for sl,radius in [(slice(0,3),root_step)]+[(slice(i,i+3),joint_step) for i in range(3,len(x),3)]:
            delta=x[sl]-neighbor[sl];row=np.zeros(len(x));row[sl]=-2*delta/radius**2
            residual.append(1-float(delta@delta)/radius**2);jacobian.append(row)
    return np.asarray(residual),np.asarray(jacobian)


def review_targets(active,patches,period,cycle,count):
    """Export the actual phase constraints, including folded endpoint-only targets."""
    groups={}
    for frame in range(count):
        transform=np.linalg.matrix_power(cycle,frame//period)
        for contact in active[frame%period]:
            position=(transform@np.r_[contact['target_position_m'],1])[:3]
            key=(contact['patch'],tuple(position))
            group=groups.setdefault(key,dict(patch=contact['patch'],vertices=patches[contact['patch']]['vertices'],target_position_m=position.tolist(),output_frames=[]))
            if not group['output_frames'] or group['output_frames'][-1]['frame']!=frame:group['output_frames'].append(dict(frame=frame,weight=1.))
    return list(groups.values())


class PeriodicFitter(Fitter):
    def __init__(self,rig,spec,local,period,cycle):
        super().__init__(rig,spec,local);self.period=period;self.cycle=cycle
        # Terminal targets are constraints on phase zero in the previous placement.
        self.active[0]=copy.deepcopy(self.active[0]);inverse=np.linalg.inv(cycle)
        self.target_conflicts=[]
        for contact in self.active[period]:
            folded=copy.deepcopy(contact);target=(inverse@np.r_[contact['target_position_m'],1])[:3];folded['target_position_m']=target.tolist()
            for existing in self.active[0]:
                if existing['patch']==folded['patch']:
                    lower=float(np.linalg.norm(np.asarray(existing['target_position_m'])-target)/2)
                    if lower>spec['screen']['contact_error_m']:
                        self.target_conflicts.append(dict(patch=folded['patch'],unavoidable_endpoint_error_m=lower))
            self.active[0].append(folded)

    def neighbors(self,values,frame):
        previous=values[(frame-1)%self.period].copy();following=values[(frame+1)%self.period].copy()
        if frame==0:previous[:3]=self.cycle[:3,:3].T@previous[:3]
        if frame==self.period-1:following[:3]=self.cycle[:3,:3]@following[:3]
        return previous,following

    def cyclic_residual(self,frame,x,neighbors):
        base=super().residual(frame,x,x);objective=self.spec['objective']
        scale=np.r_[np.ones(3),np.full(len(x)-3,objective['rotation_prior_m_per_radian'])]*objective['temporal_weight']
        return np.concatenate([base]+[(x-n)*scale for n in neighbors])

    def solve(self,output,max_sweeps=6):
        values=np.zeros((self.period,len(self.bounds)));records=[];converged=False
        for sweep in range(max_sweeps):
            start=values.copy();accepted=0
            for frame in (range(self.period) if sweep%2==0 else range(self.period-1,-1,-1)):
                neighbors=self.neighbors(values,frame);old=values[frame].copy()
                residual=lambda x:self.cyclic_residual(frame,x,neighbors)
                constraints=lambda x:neighbor_constraints(x,neighbors,self.spec['limits']['root_step_m'],np.radians(self.spec['limits']['joint_step_degrees']))
                def objective(x):
                    r=residual(x);return float(r@r)
                fit=least_squares(residual,np.clip(old,-self.bounds+1e-12,self.bounds-1e-12),bounds=(-self.bounds,self.bounds),max_nfev=self.spec['max_nfev'],ftol=1e-5,xtol=1e-5,gtol=1e-5)
                projected=clip_step(old,fit.x,neighbors,self.spec['limits']['root_step_m'],np.radians(self.spec['limits']['joint_step_degrees']))
                constrained=np.linalg.norm(projected-old)<.95*np.linalg.norm(fit.x-old)
                initial_nfev=int(fit.nfev)
                if constrained:
                    fit=minimize(objective,projected,method='SLSQP',bounds=list(zip(-self.bounds,self.bounds)),constraints={'type':'ineq','fun':lambda x:constraints(x)[0],'jac':lambda x:constraints(x)[1]},options={'maxiter':self.spec['max_nfev'],'ftol':1e-9})
                candidate=clip_step(old,fit.x,neighbors,self.spec['limits']['root_step_m'],np.radians(self.spec['limits']['joint_step_degrees']))
                cost=float(residual(old)@residual(old));after=cost;step=candidate-old
                for backtrack in range(20):
                    trial=old+step*(.5**backtrack);v=residual(trial);after=float(v@v)
                    if after<=cost:
                        values[frame]=trial;accepted+=int(np.linalg.norm(trial-old)>1e-10);break
                records.append(dict(sweep=sweep,frame=frame,success=bool(fit.success),status=int(fit.status),constrained_fallback=bool(constrained),iterations=int(fit.nit) if constrained else None,initial_least_squares_nfev=initial_nfev,nfev=int(fit.nfev),cost_before=cost,cost_after=min(cost,after)))
                if frame%15==0:save(output/'pipeline.json',dict(status='fitting_periodic',sweep=sweep+1,frame=frame,period_frames=self.period))
            change=float(np.abs(values-start).max());print(f'Periodic sweep {sweep+1}: max parameter change {change:.6g}, accepted {accepted}',flush=True)
            if change<1e-5:converged=True;break
        return values,records,dict(sweeps=sweep+1,converged=converged,final_max_parameter_change=change,per_frame_iteration_cap=self.spec['max_nfev'],method='Alternating bounded least squares, SLSQP fallback for neighbor-limited steps, exact edit-norm constraints and feasible segment safeguard. max_nfev also sets fallback iteration cap; actual evaluations logged. Small update is a stopping rule, not a stationary/global optimum certificate.')


def run(folder,spec_path,output):
    folder,spec_path,output=map(lambda p:Path(p).resolve(),(folder,spec_path,output));spec=read(spec_path);report=read(folder/'report.json')
    if sha256(folder/'character.glb')!=spec['glb_sha256'] or spec['frames']!=report['frames']:raise ValueError('Periodic contact snapshot changed')
    rig=RigAsset.load(folder/'character.glb');before,local=baseline(rig,spec['frames']);p,cycle,timeline=contract(folder,rig,before)
    fitter=PeriodicFitter(rig,spec,local,p,cycle);output.mkdir(parents=True,exist_ok=False)
    snapshot=output/'source-snapshot';snapshot.mkdir()
    for name in ('rig_periodic_contact.py','target_rig_contact.py','rig_loop.py','rig_asset.py','gltf_tools.py'):shutil.copyfile(Path(__file__).with_name(name),snapshot/name)
    shutil.copyfile(spec_path,output/'contact-spec.json');save(output/'feasibility.json',floor_lower_bound(rig,spec,before))
    with threadpool_limits(limits=1):values,solver,convergence=fitter.solve(output)
    world=np.array([fitter.pose(f,x)[0] for f,x in enumerate(values)]);after=np.concatenate([world,place(world[:1],rig.parents,spec['root_node'],cycle)])
    terminal=values[0].copy();terminal[:3]=cycle[:3,:3]@terminal[:3];parameters=np.vstack([values,terminal])
    evidence=audit(rig,spec,before,after,parameters,solver)
    if fitter.target_conflicts:evidence['flags'].append('incompatible_periodic_endpoint_targets')
    if not convergence['converged']:evidence['flags'].append('periodic_sweep_limit')
    evidence['numerical_screen_passed']=not evidence['flags']
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    repeated=np.concatenate([place(world,rig.parents,spec['root_node'],np.linalg.matrix_power(cycle,c)) for c in range(3)]+[place(world[:1],rig.parents,spec['root_node'],np.linalg.matrix_power(cycle,3))])
    from rig_events import load as load_events,remap as remap_events
    contacts=read(folder/'contacts.json');source_events=load_events(folder)
    exports={}
    for target,matrices in [(output,after),(output/'repeated',repeated)]:
        target.mkdir(exist_ok=True);count=len(matrices)
        times,roundtrip=encode(rig,matrices,animated,spec['root_node'],target/'character.glb','Periodic contact candidate')
        exports[target.name]=roundtrip
        for name in ('inventory.json','rig-profile.json'):shutil.copyfile(folder/name,target/name)
        rep=copy.deepcopy(report);rep.update(frames=count,glb_sha256=sha256(target/'character.glb'),last_key_time_s=float(times[-1]),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'],contact_annotations_file=str(target/'contacts.json'))
        if target==output:
            save(target/'contacts.json',contacts);save(target/'events.json',source_events);save(target/'timeline.json',timeline)
        else:
            intervals=[]
            for c in range(3):
                for entry in contacts.get('intervals',[]):
                    a,b=entry['start_frame'],min(p,entry['end_frame_exclusive'])
                    if a<b:intervals.append({**entry,'start_frame':a+c*p,'end_frame_exclusive':b+c*p,'start_seconds':(a+c*p)/30,'end_seconds_exclusive':(b+c*p)/30})
            for entry in contacts.get('intervals',[]):
                if entry['start_frame']==0:intervals.append({**entry,'start_frame':3*p,'end_frame_exclusive':3*p+1,'start_seconds':p/10,'end_seconds_exclusive':(3*p+1)/30})
            ambiguous=[{**e,'frame':e['frame']+c*p} for c in range(3) for e in contacts.get('ambiguous_support_frames',[]) if e['frame']<p]
            ambiguous += [{**e,'frame':3*p} for e in contacts.get('ambiguous_support_frames',[]) if e['frame']==0]
            save(target/'contacts.json',{**contacts,'intervals':intervals,'ambiguous_support_frames':ambiguous})
            clock=[[{**entry,'cycle_offset':entry.get('cycle_offset',0)+f//p} for entry in timeline['contributors'][f%p]] for f in range(count)]
            save(target/'timeline.json',{**timeline,'frames':count,'contributors':clock})
            save(target/'events.json',remap_events([source_events],[[dict(frame=f%p,weight=1.,cycle_offset=f//p)] for f in range(count)],[dict(name='cycle_boundary',frame=f,time_s=f/30) for f in range(p,count,p)]))
        authored=review_targets(fitter.active,spec['patches'],p,cycle,count)
        save(target/'contact-review.json',dict(authored_targets=authored,input_intervals=spec['contacts'],requires_review=True,scope='Actual periodic phase constraints, including endpoint targets folded to phase zero and accumulated at every wrap. Original input intervals retained separately. No independently confirmed support.'))
        rep['contact_annotations_sha256']=sha256(target/'contacts.json');save(target/'report.json',rep)
        save(target/'root-motion.json',dict(node=spec['root_node'],space='Periodic corrected pelvis world transform; accumulate cycle_transform at each wrap',times_s=times.tolist(),positions_m=matrices[:,spec['root_node'],:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(matrices[:,spec['root_node'],:3,:3]).as_quat().tolist(),cycle_transform=cycle.tolist()))
    evidence.update(created_at=now(),source_glb_sha256=spec['glb_sha256'],contact_spec_sha256=sha256(spec_path),glb_sha256=sha256(output/'character.glb'),period_frames=p,cycle_transform=cycle.tolist(),periodic_solver=convergence,endpoint_target_conflicts=fitter.target_conflicts,exports=exports,frames=p+1,fps=30,scope=evidence['scope']+' Periodic closure and correction-step bounds include the seam; contact targets may be infeasible.')
    save(output/'audit.json',evidence);save(output/'solver.json',solver);np.savez_compressed(output/'target-transforms.npz',global_matrices=after,parameters=parameters,times_s=np.arange(p+1)/30)
    from rig_runtime_cycle import write
    write(output)
    save(output/'pipeline.json',dict(status='complete',numerical_screen_passed=evidence['numerical_screen_passed']))
    print(evidence['after'],evidence['flags'],flush=True);return evidence
