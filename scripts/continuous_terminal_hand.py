"""Continuous vector wrist controls and a motion-feasible surrogate search."""
import numpy as np
from scipy.optimize import minimize
from continuous_waypoint_motion import ContinuousWaypointMotion


class VectorTerminalMotion(ContinuousWaypointMotion):
    def __init__(self,rig,chain,native,times,protected,placement,actor):
        native=np.asarray(native,float)
        if native.shape!=(3,):raise ValueError('Three native times around one editable key required')
        super().__init__(rig,chain,native,times,protected,placement,np.array([1.,0.,0.]),actor)

    def evaluate_vector(self,controls):
        controls=np.asarray(controls,float)
        if controls.shape!=(5,) or not np.isfinite(controls).all():raise ValueError('Finite XYZ wrist offset and two elbow swivels required')
        amount=float(np.linalg.norm(controls[:3]));self.axis=controls[:3]/amount if amount else np.array([1.,0.,0.])
        parameters=np.zeros((3,3));parameters[1]=np.r_[amount,controls[3:]]
        return self.evaluate(parameters)


class HandWitnessObjective:
    def __init__(self,skins,placements,rows):
        if not rows:raise ValueError('Nonempty hand witness population required')
        self.skins=skins;self.placements=placements;self.rows=rows

    def gaps(self,worlds):
        from paired_surface_witness import moving_gap
        result=[]
        for source,target in [(0,1),(1,0)]:
            rows=[r for r in self.rows if r['source']==source and r['target']==target]
            if not rows:continue
            frames=np.array([r['frame'] for r in rows]);vertices=np.array([r['vertex'] for r in rows])
            triangles=np.array([r['target_vertices'] for r in rows])
            points=self.skins[source].evaluate(worlds[source],frames,vertices)
            other=self.skins[target].evaluate(worlds[target],np.repeat(frames,3),triangles.ravel()).reshape(-1,3,3)
            a,b=self.placements[source],self.placements[target]
            points=points@a['rotation'].T+a['translation'];other=other@b['rotation'].T+b['translation']
            result.extend(moving_gap(points,other,[r['barycentric'] for r in rows],[r['normal'] for r in rows]).tolist())
        if len(result)!=len(self.rows):raise ValueError('Every witness must identify opposite actors')
        return np.array(result)


def solve(evaluate,scale,starts,*,iterations=100,observe=None):
    """Minimize measured witness depth; retain only physically feasible controls.

    The epigraph variable is an optimizer device, never accepted as a measured
    depth. Mesh clearance remains a separate fresh query after this solve.
    """
    scale=np.asarray(scale,float)
    if scale.ndim!=1 or len(scale) not in [5,11] or not np.isfinite(scale).all() or np.any(scale<=0):raise ValueError('Five or eleven positive control scales required')
    dimensions=len(scale)
    if type(iterations) is not int or iterations<1:raise ValueError('Positive iteration budget required')
    cache={};records=[];best=None
    def physical(x):
        nonlocal best
        key=np.asarray(x,float).tobytes()
        if key in cache:return cache[key]
        control=np.asarray(x)*scale;depth,margins=evaluate(control)
        margins=np.asarray(margins,float)
        if not np.isfinite(depth) or depth<0 or margins.ndim!=1 or not len(margins) or not np.isfinite(margins).all():
            raise ValueError('Finite depth and physical margins required')
        feasible=bool(np.all(margins>=0) and np.all(np.abs(x)<=1))
        record=dict(evaluation=len(records),controls=control.tolist(),witness_peak_m=float(depth),
                    minimum_margin=float(margins.min()),motion_domain_feasible=feasible)
        records.append(record);cache[key]=(float(depth),margins)
        if len(cache)>32:del cache[next(iter(cache))]
        if feasible and (best is None or depth<best['witness_peak_m']):best=record.copy()
        if observe:observe(record,best)
        return float(depth),margins
    baseline=physical(np.zeros(dimensions))
    if best is None:raise ValueError('Unchanged source must remain motion feasible')
    reports=[]
    for start in starts:
        normalized=np.asarray(start,float)/scale
        if normalized.shape!=(dimensions,) or not np.isfinite(normalized).all() or np.any(np.abs(normalized)>1):raise ValueError('Matching bounded finite start required')
        depth,_=physical(normalized);initial=np.r_[normalized,min(10.,depth/.02)]
        def constraints(x):
            measured,margins=physical(x[:dimensions])
            return np.r_[margins,x[dimensions]-measured/.02]
        result=minimize(lambda x:x[dimensions]+1e-7*np.dot(x[:dimensions],x[:dimensions]),initial,
            jac=lambda x:np.r_[2e-7*x[:dimensions],1.],method='SLSQP',bounds=[(-1.,1.)]*dimensions+[(0.,10.)],
            constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=iterations,ftol=1e-9,eps=1e-4))
        measured,margins=physical(result.x[:dimensions])
        backoff=None
        if np.any(margins<0):
            # Solver roundoff is not permission to relax a hard gate. Search
            # toward the known feasible source and re-evaluate actual margins.
            for factor in [.999,.99,.9,.75,.5,.25,.1,.01]:
                candidate_depth,candidate_margins=physical(result.x[:dimensions]*factor)
                if np.all(candidate_margins>=0):
                    backoff=dict(factor=factor,witness_peak_m=candidate_depth);break
        reports.append(dict(start=np.asarray(start).tolist(),success=bool(result.success),status=int(result.status),message=str(result.message),
            iterations=int(result.nit),function_evaluations=int(result.nfev),returned_controls=(result.x[:dimensions]*scale).tolist(),
            returned_witness_peak_m=measured,returned_minimum_margin=float(margins.min()),returned_epigraph_m=float(result.x[dimensions]*.02),feasible_backoff=backoff))
    return best,reports,records
