"""Surface/support refinement with reached joint targets kept as constraints."""
import numpy as np
from scipy.optimize import minimize
from rig_pose_tolerances import PoseTolerances
from strep import save


class TargetPreservingRefiner:
    def __init__(self,coupled,position_m=.005,orientation_degrees=5.):
        self.coupled=coupled;self.targets=PoseTolerances(coupled,position_m,orientation_degrees)
        zero=np.zeros(np.prod(coupled.shape));coupled.synchronize(zero)
        if not all(row['within_tolerances'] for row in self.targets.metrics(zero)) or self.targets.pair(zero)[0].min()<0:
            raise ValueError('Refinement requires an input already meeting target tolerances')
        self.target_margin=min(.001,max(0.,float(self.targets.pair(zero)[0].min())/2))
        f=coupled.fitter;self.floor_caps=np.maximum(0,-f.positions[:,:,1].min(axis=1))+1e-6
        self.support_caps=[]
        for support in f.supports:
            a,b=support['start_frame'],support['end_frame_exclusive']
            track=f.positions[a:b][:,support['vertices']].mean(axis=1)
            self.support_caps.append(dict(position=np.maximum(np.linalg.norm(track-support['target_position_m'],axis=1),1e-4),
                                          edge=np.maximum(np.linalg.norm(np.diff(track,axis=0),axis=1),1e-5)))
        self.surface_cache=None;self.cached_surface=None

    def surface_pair(self,controls):
        if self.surface_cache is not None and np.array_equal(controls,self.surface_cache):return self.cached_surface
        c=self.coupled;f=c.fitter;values=c.parameters(controls);active=set(map(int,c.active))
        parts=[];rows=[];tracks={}
        for frame in range(len(values)):
            if frame in active:
                points,jac=f.surface_jacobian(frame,values[frame])
                lowest=int(np.argmin(points[:,1]))
                parts.append((points[lowest,1]+self.floor_caps[frame])/.01)
                rows.append((c.basis[frame,:,None]*jac[lowest,1][None,:]/.01).ravel())
            else:
                points=f.positions[frame];jac=None
            for index,support in enumerate(f.supports):
                if support['start_frame']<=frame<support['end_frame_exclusive']:
                    ids=support['vertices'];p=points[ids].mean(axis=0)
                    j=np.zeros((3,np.prod(c.shape))) if jac is None else (jac[ids].mean(axis=0)[:,None,:]*c.basis[frame,None,:,None]).reshape(3,-1)
                    tracks[index,frame]=(p,j)
        for index,support in enumerate(f.supports):
            a,b=support['start_frame'],support['end_frame_exclusive'];caps=self.support_caps[index]
            for frame in range(a,b):
                p,j=tracks[index,frame];delta=p-support['target_position_m']
                if frame in active:
                    radius=caps['position'][frame-a]
                    parts.append(1-delta@delta/radius**2);rows.append(-2*delta@j/radius**2)
                if frame+1<b and (frame in active or frame+1 in active):
                    q,qj=tracks[index,frame+1];difference=q-p;radius=caps['edge'][frame-a]
                    parts.append(1-difference@difference/radius**2);rows.append(-2*difference@(qj-j)/radius**2)
        self.surface_cache=np.array(controls,copy=True);self.cached_surface=(np.array(parts),np.vstack(rows))
        return self.cached_surface

    def inequality_pair(self,controls):
        target,jac=self.targets.pair(controls)
        pairs=[self.coupled.inequality_pair(controls),(target-self.target_margin,jac),self.surface_pair(controls)]
        return np.concatenate([p[0] for p in pairs]),np.vstack([p[1] for p in pairs])

    def solve(self,output,max_iterations=60):
        if type(max_iterations)is not int or not 1<=max_iterations<=1000:raise ValueError('Invalid refinement budget')
        c=self.coupled;initial=np.zeros(np.prod(c.shape));best=initial.copy()
        initial_cost=c.objective_pair(initial)[0];best_cost=initial_cost;cache=None;pair=None;trace=[]
        if self.inequality_pair(initial)[0].min() < -1e-7:raise ValueError('Input violates refinement guards')
        def evaluate(x):
            nonlocal cache,pair,best,best_cost
            if cache is None or not np.array_equal(x,cache):
                pair=c.objective_pair(x);cache=x.copy()
                if pair[0]<best_cost and self.inequality_pair(x)[0].min()>=-1e-8 and all(row['within_tolerances'] for row in self.targets.metrics(x)):
                    best=x.copy();best_cost=pair[0]
            return pair
        def progress(x):
            trace.append(dict(iteration=len(trace)+1,cost=evaluate(x)[0],best_feasible_cost=best_cost,
                              constraint_min=float(self.inequality_pair(x)[0].min())))
            save(output/'pipeline.json',dict(status='refining_with_target_guards',**trace[-1]))
        result=minimize(lambda x:evaluate(x)[0],initial,jac=lambda x:evaluate(x)[1],method='SLSQP',
            constraints={'type':'ineq','fun':lambda x:self.inequality_pair(x)[0],'jac':lambda x:self.inequality_pair(x)[1]},
            callback=progress,options={'maxiter':max_iterations,'ftol':1e-9})
        evaluate(result.x);origin=best.copy();direction=result.x-origin
        for exponent in range(1,25):
            trial=origin+direction*.5**exponent
            if self.inequality_pair(trial)[0].min() < -1e-8:continue
            old_cost=best_cost;evaluate(trial)
            if best_cost<old_cost:break
        c.synchronize(best)
        summary=dict(solver_success=bool(result.success),solver_status=int(result.status),iterations=int(result.nit),
            cost_before=initial_cost,cost_after=best_cost,constraint_min=float(self.inequality_pair(best)[0].min()),
            target_metrics=self.targets.metrics(best),targets_reached=True,quality_approved=False,
            target_interior_margin=self.target_margin,
            floor_guard_slack_m=1e-6,support_position_min_radius_m=1e-4,support_edge_min_radius_m=1e-5,
            scope='Integer-frame floor and requested support diagnostics cannot regress beyond recorded guards. Supports may be unconfirmed; half-frame, collision and semantic checks remain independent.')
        return c.fitter.values.copy(),trace,summary
