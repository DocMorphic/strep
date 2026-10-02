"""Restore sampled floor feasibility, then pursue contacts with floor held hard.

Uses explicit authored limits. The active lowest vertex is a nonsmooth exact
floor constraint, not a smooth collision approximation or feasibility proof.
"""
import numpy as np
from scipy.optimize import minimize
from strep import save
from mesh_contact_clock import validate_clock


class MeshContactFeasibility:
    def __init__(self, coupled, guarded_trials=False, playback_guards=False, _protected=None, contact_clock='authored-keys'):
        if type(guarded_trials) is not bool:raise ValueError('Explicit guarded trial choice required')
        if type(playback_guards) is not bool or playback_guards and not guarded_trials:raise ValueError('Playback guards require guarded trials')
        self.contact_clock=validate_clock(contact_clock)
        if contact_clock!='authored-keys' and not playback_guards:raise ValueError('Frame-hold contacts require playback guards')
        self.coupled=coupled
        if not coupled.fitter.spec['contacts']:raise ValueError('Explicit contact targets required')
        self.margin=.01
        self.guarded_trials=guarded_trials
        self.playback_guards=playback_guards;self.playback=None;self.protected=np.array([],dtype=int)
        self.cached=None;self.cached_pair=None
        if playback_guards:
            from mesh_contact_playback import MeshPlaybackFloor
            self.playback=MeshPlaybackFloor(coupled,contact_clock=self.contact_clock)
            contacts=self.pair(np.zeros(np.prod(coupled.shape)))[2]
            groups=np.array([coupled.fitter.spec['contacts'].index(target) for active in coupled.fitter.active for target in active])
            groups=np.r_[groups,self.playback.contact_groups]
            self.protected=(np.flatnonzero(np.isin(groups,[i for i in np.unique(groups) if np.all(contacts[groups==i]>=0)]))
                            if _protected is None else np.asarray(_protected,dtype=int).copy())
            if self.protected.ndim!=1 or np.any(self.protected<0) or np.any(self.protected>=len(contacts)) or len(set(self.protected))!=len(self.protected):
                raise ValueError('Invalid protected contact layout')
            if np.any(contacts[self.protected]<0):raise ValueError('Starting protected contacts must pass')

    def pair(self, controls):
        if self.cached is not None and np.array_equal(controls,self.cached):return self.cached_pair
        c=self.coupled;f=c.fitter;values=c.parameters(controls)
        floors=[];floor_rows=[];contacts=[];contact_rows=[]
        depth=f.spec['screen']['floor_depth_m'];radius=f.spec['screen']['contact_error_m']
        for frame,x in enumerate(values):
            points,jac=f.surface_jacobian(frame,x)
            index=int(np.argmin(points[:,1]))
            floors.append(1+points[index,1]/depth)
            floor_rows.append((c.basis[frame,:,None]*(jac[index,1]/depth)[None,:]).ravel())
            for target in f.active[frame]:
                ids=f.spec['patches'][target['patch']]['vertices']
                delta=points[ids].mean(axis=0)-target['target_position_m'];length=float(np.linalg.norm(delta))
                contacts.append(1-length/radius)
                derivative=-delta@jac[ids].mean(axis=0)/(radius*length) if length>1e-12 else np.zeros(len(x))
                contact_rows.append((c.basis[frame,:,None]*derivative[None,:]).ravel())
        if self.playback is not None:
            playback_floor,playback_rows=self.playback.pair(controls)
            floors.extend(playback_floor.tolist());floor_rows.extend(playback_rows)
            playback_contact,playback_contact_rows=self.playback.contact_pair(controls)
            contacts.extend(playback_contact.tolist());contact_rows.extend(playback_contact_rows)
        self.cached_pair=(np.asarray(floors),np.asarray(floor_rows),np.asarray(contacts),np.asarray(contact_rows))
        self.cached=np.array(controls,copy=True)
        return self.cached_pair

    def metrics(self, controls):
        floor,_,contact,_=self.pair(controls)
        return dict(floor_constraint_min=float(floor.min()),contact_constraint_min=float(contact.min()),
                    floor_reached=bool(floor.min()>=0),contacts_reached=bool(contact.min()>=0),
                    protected_contacts_reached=bool(np.all(contact[self.protected]>=0)))

    def phase(self, output, name, budget):
        if type(budget)is not int or not 1<=budget<=200:raise ValueError('Feasibility budget must be 1–200')
        c=self.coupled;zero=np.zeros(np.prod(c.shape));margin=self.margin
        best=zero.copy();floors,_,contacts,_=self.pair(zero)
        target=floors if name=='floor' else contacts
        if name not in ('floor','contacts'):raise ValueError('Unknown feasibility phase')
        if name=='contacts' and floors.min()<margin-1e-8:
            raise ValueError('Restore floor before pursuing contact targets')
        initial_violation=max(0.,float(margin-target.min()));best_violation=initial_violation;trace=[]
        probes=[];probe_records=[];retained=0;guard=None
        if self.guarded_trials:
            from mesh_contact_guarded_trials import GuardedMeshTrials
            guard=GuardedMeshTrials(c,margin,self.playback)
        def archive_trials(summary):
            if not self.guarded_trials:return summary
            np.savez_compressed(output/(name+'-trials.npz'),warm_parameters=c.initial,basis=c.basis,
                                controls=np.asarray(probes).reshape(-1,len(zero)),selected_controls=best,
                                protected_contact_indices=self.protected)
            save(output/(name+'-trials.json'),dict(phase=name,contact_clock=self.contact_clock,records=probe_records,quality_approved=False,
                aborted=bool(summary.get('aborted',False)),error_type=summary.get('error_type'),error=summary.get('error')))
            summary['guarded_trials']=dict(probes=len(probes),retained_updates=retained,
                controls_file=name+'-trials.npz',records_file=name+'-trials.json')
            return summary
        if initial_violation==0:
            c.synchronize(best)
            return c.fitter.values.copy(),trace,archive_trials(dict(phase=name,attempted=False,solver_success=True,
                solver_status=None,iterations=0,initial_violation=0.,final_violation=0.,
                motion_constraint_min=float(c.inequality_pair(best)[0].min()),**self.metrics(best)))
        def consider(x,observed=None,info=None):
            nonlocal best,best_violation,retained
            if not np.isfinite(x).all():return
            record=None
            if self.guarded_trials:
                record=dict(index=len(probes),source=(info or {}).get('kind','evaluated'),**(info or {}),status='rejected')
                probes.append(np.array(x,copy=True));probe_records.append(record)
            motion=float((c.inequality_values(x) if self.guarded_trials else c.inequality_pair(x)[0]).min())
            if not np.isfinite(x).all() or motion < -1e-8:
                if record is not None:record['reason']='motion_limits';record['motion_min']=motion
                return
            if observed is None:floor,_,contact,_=self.pair(x)
            else:floor,contact=observed
            if record is not None:record.update(floor_min=float(floor.min()),contact_min=float(contact.min()),motion_min=motion)
            if np.any(contact[self.protected]<0):
                if record is not None:record['reason']='protected_contact'
                return
            if name=='contacts' and floor.min()<margin-1e-8:
                if record is not None:record['reason']='hard_floor'
                return
            violation=max(0.,float(margin-(floor if name=='floor' else contact).min()))
            if record is not None:record['violation']=violation
            if violation<best_violation:
                if self.guarded_trials and c.inequality_pair(x)[0].min() < -1e-8:
                    record['reason']='exact_motion_limits';return
                best=x.copy();best_violation=violation;retained+=1
                if record is not None:record['status']='retained';record['reason']='improved_feasibility'
            elif record is not None:record['reason']='no_improvement'
        if self.playback_guards and name=='floor':
            # A bounded deterministic lift can reach the exact feasible set even
            # when continuous derivatives stall at a float32 channel plateau.
            for point,info,observation in guard.candidates(zero,zero):
                consider(point,observation,info)
                if best_violation==0:break
            if best_violation==0:
                c.synchronize(best)
                metrics=self.metrics(best)
                save(output/'pipeline.json',dict(status='fitting_mesh_feasibility',phase=name,
                    restoration='bounded_root_lift',**metrics))
                return c.fitter.values.copy(),trace,archive_trials(dict(phase=name,attempted=False,
                    deterministic_floor_restoration=True,solver_success=True,solver_status=None,iterations=0,
                    initial_violation=initial_violation,final_violation=0.,
                    motion_constraint_min=float(c.inequality_pair(best)[0].min()),**metrics))
        def constraints(z):
            motion,mj=c.inequality_pair(z[:-1]);floor,fj,contact,cj=self.pair(z[:-1])
            if self.guarded_trials:consider(z[:-1],(floor,contact),dict(kind='constraint_evaluation'))
            target,tj=(floor,fj) if name=='floor' else (contact,cj)
            parts=[motion,target+z[-1]-margin,np.array([z[-1]])]
            rows=[np.c_[mj,np.zeros(len(motion))],np.c_[tj,np.ones(len(target))],
                  np.r_[np.zeros(len(z)-1),1][None,:]]
            if name=='contacts':parts.append(floor-margin);rows.append(np.c_[fj,np.zeros(len(floor))])
            if len(self.protected):parts.append(contact[self.protected]);rows.append(np.c_[cj[self.protected],np.zeros(len(self.protected))])
            return np.concatenate(parts),np.vstack(rows)
        def progress(z):
            consider(z[:-1])
            if self.guarded_trials and (name=='contacts' or self.playback_guards):
                origin=best.copy()
                for point,info,observation in guard.candidates(origin,z[:-1]):consider(point,observation,info)
            row=dict(phase=name,iteration=len(trace)+1,slack=float(z[-1]),
                best_violation=best_violation,motion_constraint_min=float(c.inequality_pair(z[:-1])[0].min()),
                **self.metrics(z[:-1]))
            trace.append(row);save(output/'pipeline.json',dict(status='fitting_mesh_feasibility',**row))
        z=np.r_[zero,initial_violation]
        try:
            result=minimize(lambda z:float(z[-1]),z,jac=lambda z:np.r_[np.zeros(len(z)-1),1.],
                method='SLSQP',constraints={'type':'ineq','fun':lambda z:constraints(z)[0],'jac':lambda z:constraints(z)[1]},
                callback=progress,options={'maxiter':budget,'ftol':1e-10})
        except Exception as exc:
            archive_trials(dict(phase=name,aborted=True,error_type=type(exc).__name__,error=str(exc),
                solver_success=False,initial_violation=initial_violation,final_violation=best_violation))
            raise
        consider(result.x[:-1]);origin=best.copy();direction=result.x[:-1]-origin
        for exponent in range(1,25):consider(origin+direction*.5**exponent)
        c.synchronize(best)
        summary=dict(phase=name,attempted=True,solver_success=bool(result.success),solver_status=int(result.status),
            iterations=int(result.nit),initial_violation=initial_violation,final_violation=best_violation,
            motion_constraint_min=float(c.inequality_pair(best)[0].min()),**self.metrics(best))
        return c.fitter.values.copy(),trace,archive_trials(summary)

    def solve(self, output, floor_iterations=30, contact_iterations=60):
        for budget in (floor_iterations,contact_iterations):
            if type(budget)is not int or not 1<=budget<=200:raise ValueError('Feasibility budget must be 1–200')
        c=self.coupled;f=c.fitter;initial_energy=f.total_energy()
        _,trace,floor=self.phase(output,'floor',floor_iterations)
        contact=None
        # Interior margin is 50 micrometres for the fixed Studio floor screen.
        # It is stricter than the authored cap, to leave export roundoff room.
        if floor['floor_constraint_min']>=self.margin-1e-8:
            from rig_mesh_trajectory import CoupledMeshContactFitter
            next_coupled=CoupledMeshContactFitter(f,c.basis)
            next_stage=MeshContactFeasibility(next_coupled,self.guarded_trials,self.playback_guards,self.protected,self.contact_clock)
            _,contact_trace,contact=next_stage.phase(output,'contacts',contact_iterations)
            trace.extend(contact_trace)
        final=MeshContactFeasibility(type(c)(f,c.basis),self.guarded_trials,self.playback_guards,self.protected,self.contact_clock)
        zero=np.zeros(np.prod(final.coupled.shape));metrics=final.metrics(zero)
        summary=dict(method='floor_restoration_then_floor_guarded_contact_feasibility',
            solver_success=bool(floor['solver_success'] and contact is not None and contact['solver_success']),
            iterations=floor['iterations']+(contact['iterations'] if contact else 0),
            cost_before=initial_energy,cost_after=f.total_energy(),cost_is_selection_metric=False,
            constraint_min=float(final.coupled.inequality_pair(zero)[0].min()),
            phases=dict(floor=floor,contacts=contact),target_interior_margin=self.margin,
            guarded_trials=self.guarded_trials,
            playback_guards=self.playback_guards,protected_contact_indices=self.protected.tolist(),
            contact_clock=self.contact_clock,
            contact_phase_skipped=contact is None,**metrics,
            sampled_constraints_reached=metrics['floor_reached'] and metrics['contacts_reached'],
            infeasibility_proven=False,quality_approved=False)
        save(output/'feasibility-summary.json',summary)
        return f.values.copy(),trace,summary
