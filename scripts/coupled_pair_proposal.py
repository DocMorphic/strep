"""A joint clearance proposal with explicit native-edit and motion norm cones.

Surface planes and motion vectors are linearized. Only independent decoded
motion and fresh mesh queries can accept the resulting animation.
"""
import numpy as np
from scipy import sparse


def motion_rows(positions,derivatives,reference,frames,windows,affected,active_positions):
    vectors=[];jacobians=[];caps=[];orders=[]
    for order in [1,2]:
        value=np.diff(positions,n=order,axis=0)*120**order
        jac=np.diff(derivatives,n=order,axis=0)*120**order
        original=np.linalg.norm(np.diff(reference,n=order,axis=0)*120**order,axis=-1)
        clock=frames[:-order]+order/8
        limits=np.full(original.shape,np.inf)
        for start,end in windows.values():
            mask=(clock>=start)&(clock<=end)
            if mask.any():limits[mask]=np.minimum(limits[mask],original[mask].max(0))
        active=np.zeros(len(value),bool)
        for offset in range(order+1):active|=active_positions[offset:offset+len(value)]
        selected=np.flatnonzero(active)
        bound=limits[selected][:,affected]
        if not np.isfinite(bound).all():raise ValueError('Every changed motion stencil needs a declared window')
        vectors.append(value[selected][:,affected].reshape(-1,3));jacobians.append(jac[selected][:,affected].reshape(-1,3,jac.shape[-1]))
        caps.append(bound.ravel());orders.extend([order]*bound.size)
    return np.concatenate(vectors),np.concatenate(jacobians),np.concatenate(caps),np.array(orders)


def check_step(step,gaps,gap_jacobian,depth_caps,vectors,jacobians,radii,trust):
    predicted=gaps+gap_jacobian@step
    norms=np.linalg.norm(vectors+np.einsum('nid,d->ni',jacobians,step),axis=1)
    return dict(predicted_peak_m=float(np.maximum(-predicted,0).max()),
                per_frame_cap_excess_m=float(np.maximum(-predicted-depth_caps,0).max()),
                norm_excess=float(np.maximum(norms-radii,0).max(initial=0)),
                trust_excess_radians=float(max(0.,np.linalg.norm(step.reshape(-1,3),axis=1).max()-trust)))


def solve(gaps,gap_jacobian,depth_caps,vectors,jacobians,radii,trust,scale=.005,regularizer=1e-4,norm_tolerances=None):
    gaps,gap_jacobian,depth_caps,vectors,jacobians,radii=map(lambda x:np.asarray(x,float),[gaps,gap_jacobian,depth_caps,vectors,jacobians,radii])
    if gap_jacobian.ndim!=2 or not len(gaps):raise ValueError('Nonempty surface rows required')
    n=gap_jacobian.shape[1]
    if n==0 or n%3 or gap_jacobian.shape!=(len(gaps),n) or depth_caps.shape!=gaps.shape or vectors.shape!=(len(radii),3) or jacobians.shape!=(len(radii),3,n):
        raise ValueError('Matching surface rows and three-vector norm constraints required')
    if not all(np.isfinite(x).all() for x in [gaps,gap_jacobian,depth_caps,vectors,jacobians,radii,[trust,scale,regularizer]]) or min(trust,scale,regularizer)<=0 or np.any(depth_caps<0) or np.any(radii<0):
        raise ValueError('Finite data and nonnegative caps required')
    tolerances=np.full(len(radii),1e-8) if norm_tolerances is None else np.asarray(norm_tolerances,float)
    if tolerances.shape!=radii.shape or not np.isfinite(tolerances).all() or np.any(tolerances<0):raise ValueError('Matching finite norm tolerances required')
    from conic_root_descent import solver_module
    clarabel=solver_module();width=n+1;matrices=[];rhs=[];cones=[]
    def linear(matrix,bound):
        matrices.append(sparse.csc_matrix(matrix));rhs.append(bound);cones.append(clarabel.NonnegativeConeT(len(bound)))
    linear(np.c_[-gap_jacobian*trust/scale,np.zeros(len(gaps))],(gaps+depth_caps)/scale)
    linear(np.c_[-gap_jacobian*trust/scale,-np.ones(len(gaps))],gaps/scale)
    linear(np.r_[np.zeros(n),-1.][None,:],np.zeros(1))
    def ball(vector,jacobian,radius):
        if radius==0:
            matrices.append(sparse.csc_matrix(np.c_[-jacobian,np.zeros(3)]));rhs.append(vector);cones.append(clarabel.ZeroConeT(3))
        else:
            matrices.append(sparse.csc_matrix(np.vstack([np.zeros(width),np.c_[-jacobian,np.zeros(3)]])/radius))
            rhs.append(np.r_[radius,vector]/radius);cones.append(clarabel.SecondOrderConeT(4))
    for vector,jacobian,radius in zip(vectors,jacobians,radii):ball(vector,jacobian*trust,radius)
    for index in range(0,n,3):ball(np.zeros(3),np.eye(n)[index:index+3],1.)
    settings=clarabel.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-9
    if hasattr(settings,'max_threads'):settings.max_threads=1
    p=sparse.diags(np.r_[np.full(n,2*regularizer),0.],format='csc');q=np.r_[np.zeros(n),1.]
    result=clarabel.DefaultSolver(p,q,sparse.vstack(matrices,format='csc'),np.concatenate(rhs),cones,settings).solve()
    solution=np.asarray(result.x);step=solution[:n]*trust
    if not np.isfinite(step).all():raise ValueError('Nonfinite conic solution')
    checks=check_step(step,gaps,gap_jacobian,depth_caps,vectors,jacobians,radii,trust)
    norms=np.linalg.norm(vectors+np.einsum('nid,d->ni',jacobians,step),axis=1)
    failed_norms=int((norms-radii>tolerances).sum())
    passed=str(result.status) in ['Solved','AlmostSolved'] and checks['per_frame_cap_excess_m']<=1e-8 and failed_norms==0 and checks['trust_excess_radians']<=1e-8
    report=dict(status=str(result.status),iterations=result.iterations,seconds=result.solve_time,surface_rows=len(gaps),norm_rows=len(radii),
                initial_peak_m=float(np.maximum(-gaps,0).max()),failed_norms=failed_norms,proposal_hard_checks=bool(passed),**checks,quality_approved=False)
    return step if passed else None,report
