"""Conditional rigid-body wrench feasibility for declared sticking contacts.

Contacts are unilateral point forces, with circular Coulomb friction cones and
explicit total-force caps. No contact discovery, human strength, impulses,
articulated balance, collision or animation-quality approval is inferred.
"""
import numpy as np
from scipy import sparse

VERSION='0.11.1'
SCHEMA='strep-contact-force-balance-v1'
FIELDS={'id','lever_from_com_world_m','normal_into_body_world','friction_coefficient','max_force_N'}


def finite(value,shape,label):
    try:array=np.asarray(value,dtype=float)
    except (TypeError,ValueError) as exc:raise ValueError('Invalid '+label) from exc
    if array.shape!=shape or not np.isfinite(array).all():raise ValueError('Invalid '+label)
    return array


def validate(force,torque,contacts,force_tolerance_N,torque_tolerance_Nm):
    force=finite(force,(3,),'required world force')
    torque=finite(torque,(3,),'required torque about COM')
    if np.max(np.abs(np.r_[force,torque]))>1e8:raise ValueError('Bounded wrench required')
    for tolerance in (force_tolerance_N,torque_tolerance_Nm):
        if type(tolerance) not in (int,float) or not np.isfinite(tolerance) or not 0<tolerance<=.01:
            raise ValueError('Explicit finite numerical force/torque tolerances required')
    if not isinstance(contacts,list) or len(contacts)>16:raise ValueError('At most sixteen explicit contacts required')
    seen=set();parsed=[]
    for contact in contacts:
        if not isinstance(contact,dict) or set(contact)!=FIELDS:raise ValueError('Complete explicit contact fields required')
        name=contact['id'];mu=contact['friction_coefficient'];cap=contact['max_force_N']
        if not isinstance(name,str) or not 1<=len(name)<=100 or name in seen:raise ValueError('Distinct contact identities required')
        if type(mu) not in (int,float) or not np.isfinite(mu) or not 0<=mu<=10:raise ValueError('Explicit bounded friction required')
        if type(cap) not in (int,float) or not np.isfinite(cap) or not 0<cap<=1e8:raise ValueError('Explicit positive total-force cap required')
        lever=finite(contact['lever_from_com_world_m'],(3,),'contact lever')
        normal=finite(contact['normal_into_body_world'],(3,),'inward contact normal')
        if np.max(np.abs(lever))>1000 or not np.isclose(np.linalg.norm(normal),1,rtol=0,atol=1e-10):
            raise ValueError('Bounded COM lever and explicit unit inward normal required')
        normal=normal/np.linalg.norm(normal)
        seen.add(name);parsed.append((name,lever,normal,float(mu),float(cap)))
    return force,torque,parsed


def skew(r):
    x,y,z=r
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def support(direction,normal,mu,cap):
    """Exact support of a capped circular friction cone, including zero force."""
    length=float(np.linalg.norm(direction))
    if length==0:return 0.
    axial=float(np.clip(normal@(direction/length),-1.,1.))
    cosine=1/np.hypot(1.,mu);sine=mu*cosine
    projection=1. if axial>=cosine else max(0.,axial*cosine+np.sqrt(max(0.,1-axial**2))*sine)
    return float(cap*length*projection)


def axis_bounds(parsed):
    # a . (r x f) = (a x r) . f. Each range is necessary; their
    # simultaneous satisfaction is not a force-allocation certificate.
    lower=np.zeros(6);upper=np.zeros(6)
    for _,lever,normal,mu,cap in parsed:
        for i in range(6):
            axis=np.eye(3)[i%3]
            direction=axis if i<3 else np.cross(axis,lever)
            upper[i]+=support(direction,normal,mu,cap)
            lower[i]-=support(-direction,normal,mu,cap)
    # Outward rounding margin for this finite, bounded double-precision model.
    scale=np.r_[np.full(3,max(1.,sum(c[4] for c in parsed))),
        np.full(3,max(1.,sum(np.linalg.norm(c[1])*c[4] for c in parsed)))]
    padding=128*np.finfo(float).eps*scale
    lower-=padding;upper+=padding
    return lower,upper


def projection_exclusion(wrench,parsed,covector,force_tolerance_N,torque_tolerance_Nm):
    """Check a necessary original-model wrench projection, not solver status.

    Torque coefficients use an explicit one-metre reference length, giving a
    force-equivalent scalar. Any finite covector is valid for this support test.
    """
    covector=finite(covector,(6,),'wrench covector');length=np.linalg.norm(covector)
    if length==0:return None
    covector=covector/length;demand=float(covector@wrench);low=0.;high=0.
    for _,lever,normal,mu,cap in parsed:
        direction=covector[:3]+np.cross(covector[3:],lever)
        high+=support(direction,normal,mu,cap);low-=support(-direction,normal,mu,cap)
    rounding=128*np.finfo(float).eps*max(1.,sum(c[4]*(np.linalg.norm(covector[:3])+np.linalg.norm(covector[3:])*np.linalg.norm(c[1])) for c in parsed),float(np.sum(np.abs(covector*wrench))))
    tolerance=float(np.sum(np.abs(covector[:3]))*force_tolerance_N+np.sum(np.abs(covector[3:]))*torque_tolerance_Nm)
    excess=float(max(0.,low-rounding-demand,demand-high-rounding))
    if excess<=tolerance:return None
    return dict(covector=covector.tolist(),reference_length_m=1.,required_projection_N=demand,
        lower_projection_N=float(low-rounding),upper_projection_N=float(high+rounding),
        excess_N=excess,numerical_tolerance_N=tolerance,
        scope='Original bounded sticking point-contact model exclusion in one wrench direction; no human capability or global animation claim.')


def inspect(force,torque,contacts,forces_world_N,*,force_tolerance_N=1e-6,torque_tolerance_Nm=1e-6):
    """Remeasure a complete candidate in original units without a solver."""
    force,torque,parsed=validate(force,torque,contacts,force_tolerance_N,torque_tolerance_Nm)
    if not parsed and isinstance(forces_world_N,list) and not forces_world_N:
        forces_world_N=np.empty((0,3))
    forces=finite(forces_world_N,(len(parsed),3),'complete contact forces')
    if forces.size and np.max(np.abs(forces))>1e150:raise ValueError('Bounded candidate forces required')
    supplied_force=forces.sum(axis=0);supplied_torque=np.zeros(3);rows=[]
    for (name,lever,normal,mu,cap),f in zip(parsed,forces):
        normal_force=float(normal@f);tangent=float(np.linalg.norm(f-normal_force*normal));magnitude=float(np.linalg.norm(f))
        passed=normal_force>=-force_tolerance_N and tangent<=mu*normal_force+force_tolerance_N and magnitude<=cap+force_tolerance_N
        supplied_torque+=np.cross(lever,f)
        rows.append(dict(id=name,force_world_N=f.tolist(),normal_force_N=normal_force,tangential_force_N=tangent,
            total_force_N=magnitude,friction_slack_N=float(mu*normal_force-tangent),capacity_slack_N=float(cap-magnitude),passed=bool(passed)))
    force_error=float(np.max(np.abs(supplied_force-force)));torque_error=float(np.max(np.abs(supplied_torque-torque)))
    return dict(conditional_force_balance_passed=bool(force_error<=force_tolerance_N and torque_error<=torque_tolerance_Nm and all(r['passed'] for r in rows)),
        maximum_force_component_error_N=force_error,maximum_torque_component_error_Nm=torque_error,
        supplied_force_world_N=supplied_force.tolist(),supplied_torque_about_com_world_Nm=supplied_torque.tolist(),contacts=rows)


def solver_module():
    try:import clarabel
    except ImportError as exc:raise RuntimeError('Install requirements-scene-proposals.txt for contact force allocation') from exc
    if clarabel.__version__!=VERSION:raise ValueError('Contact force allocation requires Clarabel '+VERSION)
    return clarabel


def solve(force,torque,contacts,*,force_tolerance_N=1e-6,torque_tolerance_Nm=1e-6,seconds=.25):
    force,torque,parsed=validate(force,torque,contacts,force_tolerance_N,torque_tolerance_Nm)
    if type(seconds) not in (int,float) or not np.isfinite(seconds) or not .01<=seconds<=2:
        raise ValueError('Bounded per-sample solve budget required')
    lower,upper=axis_bounds(parsed);wrench=np.r_[force,torque];tolerance=np.r_[np.full(3,force_tolerance_N),np.full(3,torque_tolerance_Nm)]
    excess=np.maximum.reduce([lower-wrench,wrench-upper,np.zeros(6)])
    report=dict(schema=SCHEMA,required_force_world_N=force.tolist(),required_torque_about_com_world_Nm=torque.tolist(),
        contacts=[dict(id=name,lever_from_com_world_m=lever.tolist(),normal_into_body_world=normal.tolist(),friction_coefficient=mu,max_force_N=cap) for name,lever,normal,mu,cap in parsed],
        force_tolerance_N=float(force_tolerance_N),torque_tolerance_Nm=float(torque_tolerance_Nm),
        axis_lower=np.asarray(lower).tolist(),axis_upper=np.asarray(upper).tolist(),axis_excess=np.asarray(excess).tolist(),
        axis_units=['N']*3+['Nm']*3,conditional_force_balance_passed=False,forces_world_N=None,
        quality_approved=False,release_approved=False,
        scope='One sampled rigid-body wrench under declared sticking, unilateral point-contact/friction/force-cap assumptions. No measured strength, actual contact geometry, between-key/impact, articulated-body balance, dynamics or animation-quality approval.')
    if np.any(excess>tolerance):return dict(report,status='infeasible_axis_bound',violating_axes=np.flatnonzero(excess>tolerance).tolist())
    if not parsed:
        verified=inspect(force,torque,contacts,np.empty((0,3)),force_tolerance_N=force_tolerance_N,torque_tolerance_Nm=torque_tolerance_Nm)
        return dict(report,status='checked_zero_contact_wrench' if verified['conditional_force_balance_passed'] else 'not_certified',forces_world_N=[],replay=verified,conditional_force_balance_passed=verified['conditional_force_balance_passed'])
    original_map=np.hstack([np.vstack([np.eye(3),skew(c[1])]) for c in parsed])
    directions=np.linalg.svd(original_map,full_matrices=True)[0]
    for covector in directions.T:
        excluded=projection_exclusion(wrench,parsed,covector,force_tolerance_N,torque_tolerance_Nm)
        if excluded is not None:return dict(report,status='infeasible_wrench_projection',projection_exclusion=excluded)
    backend=solver_module();n=3*len(parsed)
    cap=np.repeat([c[4] for c in parsed],3)
    mapping=np.hstack([np.vstack([np.eye(3),skew(c[1])])*c[4] for c in parsed])
    scales=np.r_[np.full(3,max(1.,sum(c[4] for c in parsed),float(np.max(abs(force))))),
        np.full(3,max(1.,sum(np.linalg.norm(c[1])*c[4] for c in parsed),float(np.max(abs(torque)))))]
    pieces=[sparse.csc_matrix(mapping/scales[:,None])];bounds=[wrench/scales];cones=[backend.ZeroConeT(6)]
    for i,(_,lever,normal,mu,capacity) in enumerate(parsed):
        block=np.zeros((1,n));block[0,3*i:3*i+3]=-normal
        pieces.append(sparse.csc_matrix(block));bounds.append(np.zeros(1));cones.append(backend.NonnegativeConeT(1))
        block=np.zeros((4,n));block[0,3*i:3*i+3]=-mu*normal;block[1:,3*i:3*i+3]=-(np.eye(3)-np.outer(normal,normal))
        pieces.append(sparse.csc_matrix(block));bounds.append(np.zeros(4));cones.append(backend.SecondOrderConeT(4))
        block=np.zeros((4,n));block[1:,3*i:3*i+3]=-np.eye(3)
        pieces.append(sparse.csc_matrix(block));bounds.append(np.array([1.,0.,0.,0.]));cones.append(backend.SecondOrderConeT(4))
    settings=backend.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=float(seconds)
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-10
    if hasattr(settings,'max_threads'):settings.max_threads=1
    answer=backend.DefaultSolver(sparse.eye(n,format='csc'),np.zeros(n),sparse.vstack(pieces,format='csc'),np.concatenate(bounds),cones,settings).solve()
    report.update(solver_version=backend.__version__,solver_status=str(answer.status),solver_iterations=int(answer.iterations))
    dual=getattr(answer,'z',None)
    if dual is not None:
        dual=np.asarray(dual,dtype=float)
        if dual.ndim==1 and len(dual)>=6 and np.isfinite(dual[:6]).all():
            excluded=projection_exclusion(wrench,parsed,dual[:6]/scales,force_tolerance_N,torque_tolerance_Nm)
            if excluded is not None:return dict(report,status='infeasible_wrench_projection',projection_exclusion=excluded)
    point=np.asarray(answer.x,dtype=float)
    if point.shape!=(n,) or not np.isfinite(point).all():return dict(report,status='invalid_solver_point')
    with np.errstate(over='ignore',invalid='ignore'):actual=(point*cap).reshape(-1,3)
    if not np.isfinite(actual).all() or np.max(np.abs(actual))>1e150:return dict(report,status='invalid_solver_point')
    verified=inspect(force,torque,contacts,actual,force_tolerance_N=force_tolerance_N,torque_tolerance_Nm=torque_tolerance_Nm)
    usable=answer.status is not None and str(answer.status) in ('Solved','AlmostSolved') and verified['conditional_force_balance_passed']
    return dict(report,status='checked_feasible' if usable else 'not_certified',forces_world_N=actual.tolist(),
        replay=verified,conditional_force_balance_passed=bool(usable))
