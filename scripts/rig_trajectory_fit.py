"""Experimental contact and trajectory fitting with immutable context and hard bounds.

Supports are explicit mesh vertex groups, intervals and world targets. A caller
may supply unconfirmed drafts, but this solver never upgrades their provenance.
"""
import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation
from rig_clearance_fit import ClearanceFitter, right_jacobian
from rig_periodic_contact import clip_step, neighbor_constraints
from strep import save


DEFAULTS = dict(support_position_weight=20., support_velocity_weight=30.,
                rotation_acceleration_weight=.6, root_acceleration_weight=18.,
                free_horizontal_weight=5., rotation_step_allowance_degrees=.5)


def skew(v):
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


class TrajectoryFitter(ClearanceFitter):
    def __init__(self, rig, spec, local, targets, envelope, supports, settings=None):
        super().__init__(rig,spec,local,targets,envelope)
        self.settings=DEFAULTS.copy()
        if settings is not None:
            if set(settings)-set(DEFAULTS):raise ValueError('Unknown trajectory setting')
            self.settings.update(settings)
        if any(not np.isfinite(v) or v<0 for v in self.settings.values()):
            raise ValueError('Trajectory weights must be finite and nonnegative')
        if not 0<self.settings['rotation_step_allowance_degrees']<=5:
            raise ValueError('Rotation step allowance must lie in (0,5] degrees')
        self.supports=[]
        for entry in supports:
            if set(entry)!={'vertices','start_frame','end_frame_exclusive','target_position_m','provenance','side'}:
                raise ValueError('Invalid trajectory support fields')
            a,b=entry['start_frame'],entry['end_frame_exclusive'];ids=entry['vertices']
            if type(a)is not int or type(b)is not int or not 0<=a<b<=len(local):
                raise ValueError('Invalid support interval')
            if not isinstance(ids,list) or not ids or any(type(i)is not int or not 0<=i<self.skin.count for i in ids) or len(set(ids))!=len(ids):
                raise ValueError('Invalid support vertices')
            target=np.asarray(entry['target_position_m'],float)
            if target.shape!=(3,) or not np.isfinite(target).all():raise ValueError('Invalid support position')
            if entry['side'] not in self.spec['patches'] or not isinstance(entry['provenance'],str) or not entry['provenance'].strip():
                raise ValueError('Support side and provenance required')
            if not set(ids)<=set(self.spec['patches'][entry['side']]['vertices']):
                raise ValueError('Support vertices must belong to declared foot region')
            if any(e['side']==entry['side'] and max(a,e['start_frame'])<min(b,e['end_frame_exclusive']) for e in self.supports):
                raise ValueError('Overlapping support intervals for one side')
            self.supports.append(dict(entry,vertices=ids.copy(),target_position_m=target.copy()))
        self.values=np.zeros((len(local),len(self.bounds)))
        poses=[self.pose(f,x) for f,x in enumerate(self.values)]
        self.world=np.array([p[0] for p in poses]);self.locals=np.array([p[1] for p in poses])
        self.positions=np.array([rig.vertices(w) for w in self.world])
        self.reference_positions=self.positions.copy()
        rotations=local[:,self.nodes,:3,:3]
        steps=Rotation.from_matrix((rotations[:-1].transpose(0,1,3,2)@rotations[1:]).reshape(-1,3,3)).magnitude().reshape(len(local)-1,-1)
        self.rotation_limits=np.minimum(np.pi,steps+np.radians(self.settings['rotation_step_allowance_degrees']))

    def rotation_pair(self,frame,x):
        vectors=x[3:].reshape(-1,3)
        rotation=self.local[frame,self.nodes,:3,:3]@Rotation.from_rotvec(vectors).as_matrix()
        jac=np.zeros((len(self.nodes),3,3,len(x)))
        for j,(r,v) in enumerate(zip(rotation,vectors)):
            jr=right_jacobian(v)
            for axis in range(3):jac[j,:,:,3+3*j+axis]=r@skew(jr[:,axis])
        return rotation,jac

    def constraints(self,frame,x):
        adjacent=[n for n in (frame-1,frame+1) if 0<=n<len(self.values)]
        residual,jac=neighbor_constraints(x,[self.values[n] for n in adjacent],self.spec['limits']['root_step_m'],np.radians(self.spec['limits']['joint_step_degrees']))
        parts=[residual];rows=[jac];r,d=self.rotation_pair(frame,x)
        for n in adjacent:
            reference=self.locals[n,self.nodes,:3,:3]
            limit=self.rotation_limits[min(frame,n)]
            denominator=np.maximum(2*(1-np.cos(limit)),1e-8)
            parts.append((np.einsum('jik,jik->j',reference,r)-1-2*np.cos(limit))/denominator)
            rows.append(np.einsum('jik,jikl->jl',reference,d)/denominator[:,None])
        return np.concatenate(parts),np.vstack(rows)

    def trajectory_pair(self,frame,x):
        # Base residual excludes its old edit-difference prior; actual motion
        # acceleration and support velocities below span neighboring samples.
        positions,jac=self.surface_jacobian(frame,x)
        base,bj=self.objective_from_surface(frame,x,[],positions,jac)
        rotation,rj=self.rotation_pair(frame,x)
        world,_=self.pose(frame,x);root=self.spec['root_node']
        root_position=world[root,:3,3];root_jac=np.zeros((3,len(x)));root_jac[:,:3]=np.eye(3)
        parts=[base];rows=[bj];cfg=self.settings
        active=[s for s in self.supports if s['start_frame']<=frame<s['end_frame_exclusive']]
        for side,patch in self.spec['patches'].items():
            if any(s['side']==side for s in active):continue
            ids=patch['vertices'];weight=cfg['free_horizontal_weight']/np.sqrt(len(ids))
            parts.append(((positions[ids][:,[0,2]]-self.reference_positions[frame,ids][:,[0,2]])*weight).ravel())
            rows.append((jac[ids][:,[0,2]]*weight).reshape(-1,len(x)))
        for s in active:
            ids=s['vertices'];p=positions[ids].mean(axis=0);j=jac[ids].mean(axis=0)
            weight=cfg['support_position_weight'];parts.append((p-s['target_position_m'])*weight);rows.append(j*weight)
            for n in (frame-1,frame+1):
                if s['start_frame']<=n<s['end_frame_exclusive']:
                    weight=cfg['support_velocity_weight'];other=self.positions[n,ids].mean(axis=0)
                    parts.append((p-other)*weight);rows.append(j*weight)
        # Include each acceleration residual affected by this coordinate block,
        # including centers one frame away, so accepted updates decrease a
        # consistent whole-trajectory objective rather than a one-sided proxy.
        for center in (frame-1,frame,frame+1):
            if not 1<=center<len(self.values)-1:continue
            rs=np.zeros_like(rotation);ps=np.zeros(3)
            for n,coefficient in ((center-1,1),(center,-2),(center+1,1)):
                rs+=coefficient*(rotation if n==frame else self.locals[n,self.nodes,:3,:3])
                ps+=coefficient*(root_position if n==frame else self.world[n,root,:3,3])
            coefficient=-2 if center==frame else 1
            weight=cfg['rotation_acceleration_weight']
            parts.append((rs*weight).ravel());rows.append((rj*(coefficient*weight)).reshape(-1,len(x)))
            weight=cfg['root_acceleration_weight'];parts.append(ps*weight);rows.append(root_jac*(coefficient*weight))
        return np.concatenate(parts),np.vstack(rows)

    def accept(self,frame,x):
        self.values[frame]=x
        self.world[frame],self.locals[frame]=self.pose(frame,x)
        self.positions[frame]=self.rig.vertices(self.world[frame])

    def solve(self,output,max_sweeps=6):
        records=[];stopped=False
        for sweep in range(max_sweeps):
            start=self.values.copy()
            order=range(len(start)) if sweep%2==0 else range(len(start)-1,-1,-1)
            for frame in order:
                if self.envelope[frame]==0:continue
                old=self.values[frame].copy();bounds=self.bounds*self.envelope[frame]
                cached=None;result=None
                def pair(x):
                    nonlocal cached,result
                    if cached is None or not np.array_equal(x,cached):
                        cached=x.copy();result=self.trajectory_pair(frame,x)
                    return result
                def objective(x):
                    r=pair(x)[0];return float(r@r)
                fit=least_squares(lambda x:pair(x)[0],np.clip(old,-bounds+1e-12,bounds-1e-12),jac=lambda x:pair(x)[1],bounds=(-bounds,bounds),max_nfev=self.spec['max_nfev'],ftol=1e-5,xtol=1e-5,gtol=1e-5)
                initial_nfev=int(fit.nfev)
                fallback=bool(np.min(self.constraints(frame,fit.x)[0]) < -1e-8)
                if fallback:
                    fit=minimize(objective,old,jac=lambda x:2*pair(x)[1].T@pair(x)[0],method='SLSQP',bounds=list(zip(-bounds,bounds)),constraints={'type':'ineq','fun':lambda x:self.constraints(frame,x)[0],'jac':lambda x:self.constraints(frame,x)[1]},options={'maxiter':self.spec['max_nfev'],'ftol':1e-9})
                adjacent=[self.values[n] for n in (frame-1,frame+1) if 0<=n<len(start)]
                candidate=clip_step(old,np.clip(fit.x,-bounds,bounds),adjacent,self.spec['limits']['root_step_m'],np.radians(self.spec['limits']['joint_step_degrees']))
                cost=objective(old);after=cost;accepted=False
                for backtrack in range(24):
                    trial=old+(candidate-old)*(.5**backtrack)
                    if np.min(self.constraints(frame,trial)[0]) < -1e-8:continue
                    trial_cost=objective(trial)
                    if trial_cost<=cost:
                        self.accept(frame,trial);after=trial_cost;accepted=True;break
                records.append(dict(sweep=sweep,frame=frame,success=bool(fit.success),status=int(fit.status),initial_nfev=initial_nfev,nfev=int(fit.nfev),constrained_fallback=fallback,accepted=accepted,cost_before=cost,cost_after=after))
                if frame%10==0:save(output/'pipeline.json',dict(status='fitting_trajectory',sweep=sweep+1,frame=frame))
            change=float(np.abs(self.values-start).max())
            print(f'{output.name}: trajectory sweep {sweep+1}, change {change:.6g}',flush=True)
            save(output/'pipeline.json',dict(status='fitting_trajectory',sweep=sweep+1,max_parameter_change=change))
            if change<1e-5:stopped=True;break
        return self.values.copy(),records,dict(sweeps=sweep+1,small_update_stopping_rule=stopped,max_parameter_change=change,stationarity_proven=False)
