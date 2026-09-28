"""Convex partner-clearance proposal with individual frame caps and exact edit balls.

Frozen surface planes are local approximations. Fresh mesh queries must decide
whether the proposed motion actually satisfies the caps.
"""
import numpy as np
from scipy import sparse
from conic_root_descent import solver_module


def solve(base,gaps,jacobian,caps,locked,radii,step_matrix,trust,*,scale=.005,regularizer=1e-4,tightening=None):
    base,gaps,jacobian,caps=map(lambda x:np.asarray(x,float),(base,gaps,jacobian,caps))
    locked=np.asarray(locked,bool);radii=np.asarray(radii,float);step_matrix=np.asarray(step_matrix,float)
    n=len(base)
    if base.ndim!=1 or n%3 or gaps.ndim!=1 or not len(gaps) or jacobian.shape!=(len(gaps),n) or caps.shape!=gaps.shape or locked.shape!=(n,) or radii.shape!=(n//3,) or step_matrix.ndim!=2 or step_matrix.shape[1]!=n or step_matrix.shape[0]%3:
        raise ValueError('Matching controls, surface rows, edit balls and edge map required')
    if not np.isfinite(np.r_[base,gaps,jacobian.ravel(),caps,radii,step_matrix.ravel(),trust,scale,regularizer]).all() or min(trust,scale,regularizer)<=0 or np.any(caps<0) or np.any(radii<=0):
        raise ValueError('Finite controls and positive scales required')
    if np.min(gaps+caps)<-1e-8 or np.max(np.linalg.norm(base.reshape(-1,3),axis=1)-radii)>1e-8 or np.max(np.linalg.norm((step_matrix@base).reshape(-1,3),axis=1),initial=0)>np.radians(5)+1e-8:
        raise ValueError('Initial motion must satisfy the retained caps and hard bounds')
    tightening=np.zeros_like(caps) if tightening is None else np.asarray(tightening,float)
    if tightening.shape!=caps.shape or not np.isfinite(tightening).all() or np.any(tightening<0) or np.any(tightening>caps):
        raise ValueError('Finite nonnegative tightening within the original caps required')
    clarabel=solver_module();width=n+1;mats=[];rhs=[];cones=[]
    def linear(matrix,bound):
        mats.append(sparse.csc_matrix(matrix));rhs.append(np.asarray(bound));cones.append(clarabel.NonnegativeConeT(len(bound)))
    # -J*d <= gap+cap preserves each sample's own depth allowance.
    linear(np.c_[-jacobian*trust/scale,np.zeros(len(gaps))],(gaps+caps-tightening)/scale)
    # Epigraph t is maximum remaining penetration in units of distance_scale.
    linear(np.c_[-jacobian*trust/scale,-np.ones(len(gaps))],gaps/scale)
    linear(np.r_[np.zeros(n),-1.][None,:],np.array([0.]))
    if locked.any():
        mats.append(sparse.csc_matrix(np.c_[np.eye(n)[locked],np.zeros(locked.sum())]))
        rhs.append(np.zeros(locked.sum()));cones.append(clarabel.ZeroConeT(int(locked.sum())))
    def ball(vector,matrix,cap):
        block=np.vstack([np.zeros(width),np.c_[-matrix,np.zeros(3)]])/cap
        mats.append(sparse.csc_matrix(block));rhs.append(np.r_[cap,vector]/cap);cones.append(clarabel.SecondOrderConeT(4))
    for i,radius in enumerate(radii):
        select=np.eye(n)[3*i:3*i+3]
        ball(base[3*i:3*i+3],select*trust,radius)
        ball(np.zeros(3),select,1.)
    for i in range(0,len(step_matrix),3):
        block=step_matrix[i:i+3];ball(block@base,block*trust,np.radians(5))
    p=sparse.diags(np.r_[np.full(n,2*regularizer),0.],format='csc');q=np.r_[np.zeros(n),1.]
    settings=clarabel.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-9
    if hasattr(settings,'max_threads'):settings.max_threads=1
    result=clarabel.DefaultSolver(p,q,sparse.vstack(mats,format='csc'),np.concatenate(rhs),cones,settings).solve()
    y=np.asarray(result.x);candidate=base+trust*y[:n];candidate[locked]=base[locked]
    predicted=gaps+jacobian@(candidate-base)
    report=dict(status=str(result.status),iterations=result.iterations,solve_time_s=result.solve_time,
        predicted_peak_m=float(np.maximum(-predicted,0).max()),initial_peak_m=float(np.maximum(-gaps,0).max()),
        per_frame_cap_excess_m=float(np.maximum(-predicted-caps,0).max()),
        tightened_cap_excess_m=float(np.maximum(-predicted-caps+tightening,0).max()),
        maximum_proposal_tightening_m=float(tightening.max()),
        control_ball_excess_radians=float(np.max(np.linalg.norm(candidate.reshape(-1,3),axis=1)-radii)),
        edit_step_max_radians=float(np.max(np.linalg.norm((step_matrix@candidate).reshape(-1,3),axis=1),initial=0)),
        trust_max_radians=float(np.linalg.norm((candidate-base).reshape(-1,3),axis=1).max()),
        event_controls_exact=bool(np.array_equal(candidate[locked],base[locked])),surface_rows=len(gaps),quality_approved=False)
    good=str(result.status) in ('Solved','AlmostSolved') and np.isfinite(candidate).all() and report['tightened_cap_excess_m']<=1e-8 and report['control_ball_excess_radians']<=1e-8 and report['edit_step_max_radians']<=np.radians(5)+1e-8 and report['trust_max_radians']<=trust+1e-8
    report['proposal_hard_checks']=bool(good)
    return candidate if good else None,report
