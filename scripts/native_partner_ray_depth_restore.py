"""Recover a rejected initial depth point by explicit bounded affine retreat.

The prior solver failure remains recorded. A recovered point is a separately
verified first-phase candidate, never a solver optimum or export approval.
"""
import numpy as np
from native_partner_accurate_depth_restore import direction as solve_direction
from native_affine_ray_retreat import project


def direction(native,native_jac,gaps,surface_jac,offsets,blocks,value,lower,upper,trust,**kwargs):
    delta,info,reduction=solve_direction(native,native_jac,gaps,surface_jac,offsets,blocks,value,lower,upper,trust,**kwargs)
    info=dict(info,ray_recovery_attempted=False)
    if delta is not None:return delta,info,reduction
    phases=info.get('phase_checks',[])
    if (info.get('status')!='UnverifiedDepthPhase' or len(phases)!=1 or phases[0].get('phase')!='depth'
            or phases[0].get('status') not in ('Solved','AlmostSolved')
            or phases[0].get('rejections')!=['native_conditions'] or 'projected_control_step' not in phases[0]):
        return None,info,reduction
    raw=np.asarray(phases[0]['projected_control_step'],float)
    recovered,ray=project(native,native_jac,raw,value,lower,upper,trust)
    info.update(ray_recovery_attempted=True,ray_recovery=ray,original_solver_validation_status=info['status'])
    if recovered is None:return None,dict(info,status='UnverifiedRayDepthCandidate'),reduction
    if np.any(recovered<reduction.report['proof_delta_lower']) or np.any(recovered>reduction.report['proof_delta_upper']):
        return None,dict(info,status='RayOutsideCertificateBox'),reduction
    gaps=np.asarray(gaps,float);ids=np.asarray(info['guard_scalar_ids'],int);scale=info['scale_m'];preferred=info['guidance_depth_target_m']
    moved=gaps+surface_jac@recovered
    full=(info['clearance_m']-moved)/scale
    np.testing.assert_allclose(full.max(),full[reduction.retained].max(),atol=1e-10,rtol=1e-12)
    depth=float(max(0.,((-moved[ids]-preferred)/scale).max())) if len(ids) else 0.
    anchor_depth=float(max(0.,((-gaps[ids]-preferred)/scale).max())) if len(ids) else 0.
    if not depth<anchor_depth:
        return None,dict(info,status='RayDoesNotImprovePreferredDepth',ray_preferred_depth_deficit=depth,original_anchor_preferred_depth_deficit=anchor_depth),reduction
    return recovered,dict(info,status='VerifiedRayDepthCandidate',selected_phase='depth-ray-recovery',
        recovered_first_phase_candidate_not_solver_optimum=True,original_rejected_solver_point_preserved=True,
        depth_phase_verified_candidate_bound=depth,original_anchor_preferred_depth_deficit=anchor_depth,
        maximum_control_step=float(abs(recovered).max()),predicted_native_excess=ray['selected_native_maximum_excess'],
        full_affine_surface_excess=float(max(0.,full.max())),selected_affine_surface_excess=float(max(0.,full.max())),
        predicted_partner_depth_deficit=depth,predicted_preferred_depth_deficit=depth,
        predicted_original_depth_floor_deficit=float(max(0.,((-moved[ids]-info['depth_limit_m'])/scale).max())) if len(ids) else 0.,
        all_original_affine_surface_rows_evaluated=True,every_guarded_affine_gap_evaluated=True,
        invalid_solution=False,quality_approved=False,release_approved=False),reduction
