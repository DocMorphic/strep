"""Target-feasibility stage over coordinated controls, with explicit rejection.

Position and orientation are separate acceptance conditions. Surface/support
quality is not certified by reaching a joint target.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from strep import save


class PoseTolerances:
    def __init__(self,coupled,position_m=.005,orientation_degrees=5.):
        for value,upper in [(position_m,.5),(orientation_degrees,90)]:
            if type(value)not in (int,float) or not np.isfinite(value) or not 0<value<=upper:
                raise ValueError('Positive finite target tolerances required')
        self.coupled=coupled;self.position_m=position_m;self.orientation_degrees=orientation_degrees
        self.rotation_denominator=2*(1-np.cos(np.radians(orientation_degrees)))
        if self.rotation_denominator<1e-12:raise ValueError('Orientation tolerance is numerically too small')

    def pair(self,controls):
        c=self.coupled;f=c.fitter;values=c.parameters(controls);parts=[];rows=[]
        for goal in f.goals:
            frame=goal['frame'];p,r,jp,jr=f.joint_pair(frame,values[frame],goal['node'])
            delta=p-goal['position_m'];target=goal['rotation_matrix']
            parts.extend([1-delta@delta/self.position_m**2,
                          (np.sum(target*r)-1-2*np.cos(np.radians(self.orientation_degrees)))/self.rotation_denominator])
            position=-2*delta@jp/self.position_m**2
            rotation=np.einsum('ij,ijk->k',target,jr)/self.rotation_denominator
            for derivative in [position,rotation]:rows.append((c.basis[frame,:,None]*derivative[None,:]).ravel())
        return np.asarray(parts),np.asarray(rows)

    def metrics(self,controls):
        c=self.coupled;f=c.fitter;values=c.parameters(controls);rows=[]
        for goal in f.goals:
            w=f.pose(goal['frame'],values[goal['frame']])[0][goal['node']]
            position=float(np.linalg.norm(w[:3,3]-goal['position_m']))
            rotation=float(np.degrees(Rotation.from_matrix(np.linalg.solve(goal['rotation_matrix'],w[:3,:3])).magnitude()))
            rows.append(dict(frame=goal['frame'],node=goal['node'],position_error_m=position,
                orientation_error_degrees=rotation,within_tolerances=position<=self.position_m and rotation<=self.orientation_degrees))
        return rows

    def solve(self,output,max_iterations=100):
        if type(max_iterations)is not int or not 1<=max_iterations<=1000:raise ValueError('Invalid iteration budget')
        c=self.coupled;zero=np.zeros(np.prod(c.shape));margin=.01
        initial_goals=self.pair(zero)[0];best=zero.copy()
        best_violation=max(0.,float(margin-initial_goals.min()));trace=[]
        def consider(controls):
            nonlocal best,best_violation
            if not np.isfinite(controls).all() or c.inequality_pair(controls)[0].min() < -1e-8:return
            violation=max(0.,float(margin-self.pair(controls)[0].min()))
            if violation<best_violation:best=controls.copy();best_violation=violation
        def constraints(z):
            motion,mj=c.inequality_pair(z[:-1]);goals,gj=self.pair(z[:-1])
            return np.r_[motion,goals+z[-1]-margin,z[-1]],np.vstack([
                np.c_[mj,np.zeros(len(motion))],np.c_[gj,np.ones(len(goals))],
                np.r_[np.zeros(len(z)-1),1][None,:]])
        def progress(z):
            consider(z[:-1]);row=dict(iteration=len(trace)+1,slack=float(z[-1]),
                best_target_violation=best_violation,motion_constraint_min=float(c.inequality_pair(z[:-1])[0].min()))
            trace.append(row);save(output/'pipeline.json',dict(status='fitting_target_feasibility',**row))
        z=np.r_[zero,best_violation]
        result=minimize(lambda z:float(z[-1]),z,jac=lambda z:np.r_[np.zeros(len(z)-1),1.],
            method='SLSQP',constraints={'type':'ineq','fun':lambda z:constraints(z)[0],'jac':lambda z:constraints(z)[1]},
            callback=progress,options={'maxiter':max_iterations,'ftol':1e-10})
        consider(result.x[:-1]);origin=best.copy();direction=result.x[:-1]-origin
        for exponent in range(1,25):consider(origin+direction*.5**exponent)
        c.synchronize(best);metrics=self.metrics(best)
        reached=all(row['within_tolerances'] for row in metrics)
        summary=dict(solver_success=bool(result.success),solver_status=int(result.status),iterations=int(result.nit),
            position_tolerance_m=self.position_m,orientation_tolerance_degrees=self.orientation_degrees,
            target_interior_margin=margin,initial_target_violation=max(0.,float(margin-initial_goals.min())),
            final_target_violation=best_violation,motion_constraint_min=float(c.inequality_pair(best)[0].min()),
            targets_reached=reached,target_metrics=metrics,
            result='target_tolerances_met' if reached else 'target_tolerances_not_met',
            infeasibility_proven=False,quality_approved=False)
        return c.fitter.values.copy(),trace,summary
