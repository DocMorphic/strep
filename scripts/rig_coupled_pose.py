"""Coordinated temporal controls around an existing bounded pose fitter.

The original objective and hard limits remain in force. Cubic controls reduce
the search dimension; they do not guarantee convergence or target feasibility.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from strep import save


class CoupledPoseFitter:
    def __init__(self, fitter, basis):
        self.fitter=fitter
        basis=np.asarray(basis,float)
        if basis.ndim!=2 or basis.shape[0]!=len(fitter.values) or not 1<=basis.shape[1]<=64 or not np.isfinite(basis).all():
            raise ValueError('Finite temporal control matrix required')
        if np.any(basis[fitter.envelope==0]):
            raise ValueError('Temporal controls must preserve fixed frames')
        if np.any(np.linalg.norm(basis,axis=0)==0):
            raise ValueError('Empty temporal control column')
        self.basis=basis.copy();self.initial=fitter.values.copy()
        self.active=np.flatnonzero(np.any(basis!=0,axis=1))
        self.dim=len(fitter.bounds);self.shape=(basis.shape[1],self.dim)
        self.mapping=np.kron(basis[self.active],np.eye(self.dim))
        self.limits=(fitter.envelope[self.active,None]*fitter.bounds).ravel()
        self.cached=None
        if self.inequality_pair(np.zeros(np.prod(self.shape)))[0].min() < -1e-7:
            raise ValueError('Initial trajectory violates hard constraints')

    def parameters(self, controls):
        return self.initial+self.basis@np.asarray(controls).reshape(self.shape)

    def synchronize(self, controls):
        if self.cached is None or not np.array_equal(controls,self.cached):
            values=self.parameters(controls)
            for frame in self.active:self.fitter.accept(frame,values[frame])
            self.cached=np.array(controls,copy=True)

    def energy(self):
        f=self.fitter;cfg=f.settings;obj=f.spec['objective'];p=f.positions
        value=float(np.sum((np.minimum(p[:,:,1],0)*obj['floor_weight'])**2))
        for side,patch in f.spec['patches'].items():
            ids=patch['vertices']
            value+=float(np.sum(((p[:,ids,1].min(axis=1)-f.targets[side])*12)**2))
            free=np.ones(len(p),bool)
            for s in f.supports:
                if s['side']==side:free[s['start_frame']:s['end_frame_exclusive']]=False
            difference=p[free][:,ids][:,:,[0,2]]-f.reference_positions[free][:,ids][:,:,[0,2]]
            value+=float(np.sum(difference**2)*cfg['free_horizontal_weight']**2/len(ids))
        value+=float(np.sum((f.values[:,:3]*obj['root_prior'])**2)+np.sum((f.values[:,3:]*obj['rotation_prior_m_per_radian'])**2))
        for s in f.supports:
            track=p[s['start_frame']:s['end_frame_exclusive']][:,s['vertices']].mean(axis=1)
            value+=float(np.sum((track-s['target_position_m'])**2)*cfg['support_position_weight']**2)
            value+=float(np.sum(np.diff(track,axis=0)**2)*cfg['support_velocity_weight']**2)
        value+=float(np.sum(np.diff(f.locals[:,f.nodes,:3,:3],n=2,axis=0)**2)*cfg['rotation_acceleration_weight']**2)
        value+=float(np.sum(np.diff(f.world[:,f.spec['root_node'],:3,3],n=2,axis=0)**2)*cfg['root_acceleration_weight']**2)
        for frame in {g['frame'] for g in f.goals}:
            residual=f.goal_pair(frame,f.values[frame])[0];value+=float(residual@residual)
        return value

    def objective_pair(self, controls):
        self.synchronize(controls);gradient=np.zeros(self.shape)
        for frame in self.active:
            residual,jac=self.fitter.trajectory_pair(frame,self.fitter.values[frame])
            gradient+=self.basis[frame,:,None]*(2*jac.T@residual)[None,:]
        return self.energy(),gradient.ravel()

    def inequality_pair(self, controls):
        f=self.fitter;values=self.parameters(controls);x=values[self.active].ravel()
        rows=[self.mapping/-self.limits[:,None],self.mapping/self.limits[:,None]]
        parts=[1-x/self.limits,1+x/self.limits]
        rotations=[];derivatives=[]
        for frame,value in enumerate(values):
            r,j=f.rotation_pair(frame,value);rotations.append(r);derivatives.append(j)
        for frame in range(len(values)-1):
            if not (np.any(self.basis[frame]) or np.any(self.basis[frame+1])):continue
            db=self.basis[frame+1]-self.basis[frame];d=values[frame+1]-values[frame]
            for sl,radius in [(slice(0,3),f.spec['limits']['root_step_m'])]+[(slice(i,i+3),np.radians(f.spec['limits']['joint_step_degrees'])) for i in range(3,self.dim,3)]:
                row=np.zeros(self.shape);row[:,sl]=-2*db[:,None]*d[sl]/radius**2
                parts.append(np.array([1-d[sl]@d[sl]/radius**2]));rows.append(row.reshape(1,-1))
            a,b=rotations[frame:frame+2];da,dbrot=derivatives[frame:frame+2]
            limit=f.rotation_limits[frame];denom=np.maximum(2*(1-np.cos(limit)),1e-8)
            parts.append((np.einsum('jik,jik->j',a,b)-1-2*np.cos(limit))/denom)
            ga=np.einsum('jik,jikl->jl',b,da);gb=np.einsum('jik,jikl->jl',a,dbrot)
            derivative=(ga[:,None,:]*self.basis[frame,None,:,None]+gb[:,None,:]*self.basis[frame+1,None,:,None])/denom[:,None,None]
            rows.append(derivative.reshape(len(f.nodes),-1))
        return np.concatenate(parts),np.vstack(rows)

    def inequality_values(self, controls):
        """The same complete limits without allocating their dense Jacobian."""
        f=self.fitter;values=self.parameters(controls);x=values[self.active].ravel()
        parts=[1-x/self.limits,1+x/self.limits]
        edges=np.any(self.basis[:-1]!=0,axis=1)|np.any(self.basis[1:]!=0,axis=1)
        delta=np.diff(values,axis=0)
        root=1-np.sum(delta[:,:3]**2,axis=1)/f.spec['limits']['root_step_m']**2
        joint=1-np.sum(delta[:,3:].reshape(len(delta),-1,3)**2,axis=2)/np.radians(f.spec['limits']['joint_step_degrees'])**2
        rotations=f.local[:,f.nodes,:3,:3]@Rotation.from_rotvec(values[:,3:].reshape(-1,3)).as_matrix().reshape(len(values),len(f.nodes),3,3)
        limits=f.rotation_limits;denom=np.maximum(2*(1-np.cos(limits)),1e-8)
        actual=(np.sum(rotations[:-1]*rotations[1:],axis=(2,3))-1-2*np.cos(limits))/denom
        parts.append(np.c_[root,joint,actual][edges].ravel())
        return np.concatenate(parts)

    def solve(self, output, max_iterations=100):
        if type(max_iterations)is not int or not 1<=max_iterations<=1000:
            raise ValueError('Iteration budget must be between 1 and 1000')
        initial=np.zeros(np.prod(self.shape));cache=None;pair=None
        best=initial.copy();best_cost=self.objective_pair(initial)[0];initial_cost=best_cost;records=[]
        def evaluate(x):
            nonlocal cache,pair,best,best_cost
            if cache is None or not np.array_equal(x,cache):
                pair=self.objective_pair(x);cache=x.copy()
                if np.isfinite(pair[0]) and pair[0]<best_cost and self.inequality_pair(x)[0].min()>=-1e-8:
                    best=x.copy();best_cost=pair[0]
            return pair
        def progress(x):
            records.append(dict(iteration=len(records)+1,cost=evaluate(x)[0],best_feasible_cost=best_cost,
                                constraint_min=float(self.inequality_pair(x)[0].min())))
            save(output/'pipeline.json',dict(status='fitting_coupled',**records[-1]))
        result=minimize(lambda x:evaluate(x)[0],initial,jac=lambda x:evaluate(x)[1],method='SLSQP',
            constraints={'type':'ineq','fun':lambda x:self.inequality_pair(x)[0],'jac':lambda x:self.inequality_pair(x)[1]},
            callback=progress,options={'maxiter':max_iterations,'ftol':1e-9})
        evaluate(result.x)
        # SLSQP may exhaust its budget with a useful but infeasible direction.
        # Keep a tested feasible segment step instead of trusting that endpoint.
        origin=best.copy();direction=result.x-origin;backtracked=False
        for exponent in range(1,25):
            trial=origin+direction*(.5**exponent)
            if self.inequality_pair(trial)[0].min() < -1e-8:continue
            old_cost=best_cost;evaluate(trial)
            if best_cost<old_cost:backtracked=True;break
        self.synchronize(best)
        summary=dict(solver_success=bool(result.success),solver_status=int(result.status),iterations=int(result.nit),
                     cost_before=initial_cost,cost_after=best_cost,constraint_min=float(self.inequality_pair(best)[0].min()),
                     returned_best_feasible=True,endpoint_backtracked=backtracked,convergence_or_feasibility_proven=False)
        return self.fitter.values.copy(),records,summary


def window_basis(envelope, spacing=10):
    # Reuse the existing cubic interpolation controls, with an explicit fixed
    # context envelope and per-frame hard bounds to contain spline overshoot.
    from temporal_basis import correction_basis
    envelope=np.asarray(envelope,float)
    if envelope.ndim!=1 or not np.isfinite(envelope).all() or np.any((envelope<0)|(envelope>1)):
        raise ValueError('Finite unit edit envelope required')
    active=np.flatnonzero(envelope>0)
    if len(active)<3:raise ValueError('At least three editable frames required')
    start,end=int(active[0]),int(active[-1]+1)
    basis,_=correction_basis(end-start,spacing)
    result=np.zeros((len(envelope),basis.shape[1]));result[start:end]=basis*envelope[start:end,None]
    return result
