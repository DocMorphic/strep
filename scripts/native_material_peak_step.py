"""Worst declared material depth before complete aggregate guide deficit.

Fixed face/normal witnesses provide local guidance, never collision approval.
Every original native norm remains hard; actual decoded checks remain required.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_conic import solver_module
from native_affine_ray_retreat import project


def direction(native, native_jacobian, gaps_m, gap_jacobian, witnesses,
              value, lower, upper, trust, *, parameter_rows=None,
              clearance_m=.0001, scale_m=.005, solver_sink=None):
    """Caller binds all witness provenance and the complete same-point model.

    The first phase reduces maximum containment depth. The second reduces all
    guide deficits without exceeding the first verified depth ceiling. A
    finite stalled iterate can be inspected, but its status is never changed.
    """
    value,lower,upper,gaps=[np.asarray(a,float) for a in (value,lower,upper,gaps_m)]
    vectors,caps,scales=[np.asarray(a,float) for a in (native.vectors,native.caps,native.scales)]
    n=len(value) if value.ndim==1 else 0
    nj,gj=[sparse.csr_matrix(a,copy=True) for a in (native_jacobian,gap_jacobian)]
    eq=sparse.csr_matrix((0,n)) if parameter_rows is None else sparse.csr_matrix(parameter_rows,copy=True)
    if (not 1<=n<=96 or lower.shape!=value.shape or upper.shape!=value.shape
        or vectors.ndim!=2 or vectors.shape[1:]!=(3,) or not len(vectors)
        or caps.shape!=(len(vectors),) or scales.shape!=caps.shape or nj.shape!=(vectors.size,n)
        or gaps.ndim!=1 or not 1<=len(gaps)<=4096 or gj.shape!=(len(gaps),n)
        or eq.shape[1]!=n or eq.shape[0]>96 or nj.nnz+gj.nnz>60_000_000
        or not isinstance(witnesses,list) or len(witnesses)!=len(gaps)
        or any(not isinstance(w,dict) or w.get('kind') not in ('triangle-separation','penetrating-vertex') for w in witnesses)
        or any(not np.isfinite(a).all() for a in (value,lower,upper,vectors,caps,scales,gaps,nj.data,gj.data,eq.data))
        or np.any(caps<0) or np.any(scales<=0) or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
        or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02
        or type(clearance_m) not in (int,float) or not np.isfinite(clearance_m) or not 0<=clearance_m<=.1
        or type(scale_m) not in (int,float) or not np.isfinite(scale_m) or not 1e-6<=scale_m<=1.
        or solver_sink is not None and not callable(solver_sink)):
        raise ValueError('Complete original native/material model, witness population, bounds and finite settings required')
    ids=np.array([i for i,w in enumerate(witnesses) if w['kind']=='penetrating-vertex'],int)
    if len(ids) and np.any(gaps[ids]>0):raise ValueError('Every declared containment witness needs a nonpositive anchor gap')
    nj.eliminate_zeros()
    anchor=float(((np.linalg.norm(vectors,axis=1)-caps)/scales).max())
    depth_before=float(max(0.,(-gaps[ids]).max())) if len(ids) else 0.
    before=np.minimum((gaps-clearance_m)/scale_m,0.)
    info=dict(schema='strep-native-material-peak-step-v1',status='not-solved',phases=[],selected_phase=None,
        original_norm_rows=len(caps),controls=n,complete_guide_rows=len(gaps),parameter_rows=eq.shape[0],
        containment_rows=ids.tolist(),witnesses=copy.deepcopy(witnesses),
        original_anchor_maximum_excess=anchor,initial_material_peak_depth_m=depth_before,
        initial_complete_guide_squared_deficit=float(before@before),clearance_m=clearance_m,scale_m=scale_m,
        original_caps_scales_clocks_unchanged=True,all_original_native_rows_columns_retained=True,
        all_guide_rows_retained=True,solver_statuses_preserved=True,solver_optimality_verified=False,
        strict_native_acceptance_tolerance=0.,parameter_proposal_tolerance=1e-9,
        priority='Worst declared containment depth, then complete squared negative guide deficit.',
        quality_approved=False,release_approved=False,
        scope='Complete indexed material witness population and original hard native norms. '
            'Second-phase priority ceiling is a strictly checked first-phase candidate, not a claimed optimum. '
            'Fixed normals/faces/barycentric points do not prove signed distance or nonlinear nonregression. '
            'Actual decoded motion, contacts, references and complete scene geometry remain required.')
    if anchor>0:return None,dict(info,status='OriginalAnchorNotStrictlyPassing')
    if not len(ids) or depth_before==0:return None,dict(info,status='NoPositiveContainmentDepth')
    solver=solver_module()
    count=np.diff(nj.indptr).reshape(-1,3).sum(axis=1);active=np.flatnonzero(count!=0)
    info.update(active_original_norm_cones=len(active),omitted_exactly_fixed_passing_norms=int((count==0).sum()),solver_version=solver.__version__)
    lo,hi=np.maximum(-1.,(lower-value)/trust),np.minimum(1.,(upper-value)/trust)
    def solve(phase,ceiling=None):
        # First phase has controls and peak; second also has every guide slack.
        extra=1 if ceiling is None else 1+len(gaps);total=n+extra
        box=sparse.hstack([sparse.eye(n),sparse.csc_matrix((n,extra))],format='csc')
        mats=[box,-box];rhs=[hi,-lo];cones=[solver.NonnegativeConeT(2*n)]
        if eq.shape[0]:
            mats.append(sparse.hstack([eq*trust,sparse.csc_matrix((eq.shape[0],extra))],format='csc'))
            rhs.append(np.zeros(eq.shape[0]));cones.append(solver.ZeroConeT(eq.shape[0]))
        selected=nj[(3*active[:,None]+np.arange(3)).ravel()].multiply((-trust/np.repeat(scales[active],3))[:,None]).tocoo()
        mats.append(sparse.csc_matrix((selected.data,(4*(selected.row//3)+1+selected.row%3,selected.col)),shape=(4*len(active),total)))
        rhs.append((np.c_[caps[active],vectors[active]]/scales[active,None]).ravel())
        cones.extend(solver.SecondOrderConeT(4) for _ in active)
        rest=sparse.csc_matrix((len(ids),extra-1))
        mats.append(sparse.hstack([-trust/scale_m*gj[ids],-np.ones((len(ids),1)),rest],format='csc'))
        rhs.append(gaps[ids]/scale_m);cones.append(solver.NonnegativeConeT(len(ids)))
        peak=np.r_[np.zeros(n),-1.,np.zeros(extra-1)][None]
        mats.append(sparse.csc_matrix(peak));rhs.append(np.zeros(1));cones.append(solver.NonnegativeConeT(1))
        if ceiling is None:
            P=sparse.csc_matrix((total,total));q=np.r_[np.zeros(n),1.]
        else:
            mats.append(sparse.csc_matrix(-peak));rhs.append(np.array([ceiling/scale_m]));cones.append(solver.NonnegativeConeT(1))
            mats.append(sparse.hstack([-trust/scale_m*gj,sparse.csc_matrix((len(gaps),1)),-sparse.eye(len(gaps))],format='csc'))
            rhs.append((gaps-clearance_m)/scale_m);cones.append(solver.NonnegativeConeT(len(gaps)))
            mats.append(sparse.hstack([sparse.csc_matrix((len(gaps),n+1)),-sparse.eye(len(gaps))],format='csc'))
            rhs.append(np.zeros(len(gaps)));cones.append(solver.NonnegativeConeT(len(gaps)))
            P=sparse.diags(np.r_[np.full(n,1e-12),0.,np.ones(len(gaps))],format='csc');q=np.zeros(total)
        settings=solver.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
        settings.tol_feas=settings.tol_gap_abs=settings.tol_gap_rel=1e-11
        if hasattr(settings,'max_threads'):settings.max_threads=1
        A,b=sparse.vstack(mats,format='csc'),np.concatenate(rhs)
        solution=solver.DefaultSolver(P,q,A,b,cones,settings).solve()
        point=np.asarray(solution.x,float)
        record=dict(phase=phase,solver_status=str(solution.status),iterations=solution.iterations,
            returned_point=point.tolist(),priority_ceiling_m=ceiling,selected=False)
        info['phases'].append(record)
        if solver_sink is not None:
            solver_sink(phase,dict(quadratic=P.copy(),linear=q.copy(),matrix=A.copy(),rhs=b.copy(),
                cones=[str(c) for c in cones],record=copy.deepcopy(record)))
        if str(solution.status) not in ('Solved','AlmostSolved','InsufficientProgress','MaxIterations','MaxTime'):
            record['status']='NotMotionIterateStatus';return None
        if point.shape!=(total,) or not np.isfinite(point).all():record['status']='InvalidReturnedPoint';return None
        raw=point[:n]*trust;record['raw_control_step']=raw.tolist()
        if np.any(raw<lo*trust-1e-9) or np.any(raw>hi*trust+1e-9):record['status']='IterateOutsideOriginalBox';return None
        delta,ray=project(native,nj,raw,value,lower,upper,trust);record['strict_original_norm_ray']=ray
        if delta is None:record['status']='NoStrictPositiveRay';return None
        moved=gaps+gj@delta
        depth=float(max(0.,(-moved[ids]).max()));neg=np.minimum((moved-clearance_m)/scale_m,0.)
        parameter_error=float(abs(eq@delta).max()) if eq.shape[0] else 0.
        record.update(selected_control_step=delta.tolist(),material_peak_depth_m=depth,
            complete_guide_squared_deficit=float(neg@neg),parameter_maximum_absolute_residual=parameter_error)
        if parameter_error>1e-9:record['status']='UnverifiedParameterRows';return None
        if not depth<depth_before:record['status']='NoStrictPeakImprovement';return None
        if ceiling is not None and depth>ceiling:record['status']='DepthPriorityExceeded';return None
        if ceiling is not None and not float(neg@neg)<info['phases'][0]['complete_guide_squared_deficit']:
            record['status']='NoSecondaryImprovement';return None
        record['status']='ProvisionalStrictPeakCandidate';return delta
    first=solve('peak')
    if first is None:return None,dict(info,status='NoVerifiedPeakCandidate')
    first_depth=info['phases'][0]['material_peak_depth_m']
    second=solve('complete-guide-deficit',first_depth)
    selected=0 if second is None else 1
    info['phases'][selected]['selected']=True
    chosen=info['phases'][selected]
    info.update(selected_phase=chosen['phase'],selected_material_peak_depth_m=chosen['material_peak_depth_m'],
        selected_complete_guide_squared_deficit=chosen['complete_guide_squared_deficit'],
        selected_control_step=chosen['selected_control_step'],verified_first_phase_depth_ceiling_m=first_depth)
    return first if second is None else second,dict(info,status='ProvisionalStrictPeakCandidate')
