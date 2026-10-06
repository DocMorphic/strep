"""Optional compact nonlinear surface proposal model with original native norms.

This is not installed into old jobs or verifiers. Nonsmooth support-gap
differences only guide a local proposal. The caller must independently export,
decode and check every original native condition and complete scene geometry.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows, linearize, rows as native_rows
from native_compact_surface_rows import build, METHODS as ROW_METHODS
from native_surface_model import surface_points
from native_surface_lift import lift

SCHEMA = 'strep-native-compact-surface-model-v1'
METHODS = tuple(dict.fromkeys(ROW_METHODS + ('native_surface_model.py','native_surface_lift.py',
    'native_scene_norms.py','native_scene_conic.py','native_compact_surface_model.py')))


def model(problem,value,decoded_scene,policy,digest,trust,*,step=.001,maximum_rows=100000,
          decoded_worlds=None,clearance=.0005,difference_scheme='central'):
    if (type(step) not in (int,float) or not np.isfinite(step) or not 1e-6 <= step <= .01
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 100000
            or type(clearance) not in (int,float) or not np.isfinite(clearance) or not 0 <= clearance <= .005
            or difference_scheme not in ('forward','central')):
        raise ValueError('Bounded explicit compact proposal settings required')
    value = problem.edits.controls(value)
    original,jac,identity = linearize(problem,value,step=step,difference_source='continuous',difference_scheme=difference_scheme)
    if decoded_worlds is not None:
        anchored = native_rows(problem,value,decoded_worlds)
        if not np.array_equal(original.caps,anchored.caps) or not np.array_equal(original.scales,anchored.scales):
            raise ValueError('Decoded anchoring changed original norm caps or ordering')
        original = anchored
    witnesses = build(decoded_scene,policy,digest,maximum_rows=maximum_rows,clearance=clearance)
    report = dict(schema=SCHEMA,differences=identity,original_norm_rows=len(original.caps),surface_rows=len(witnesses.rows),
        surface_query=witnesses.report,native_acceptance_unchanged=True,affine_nine_pair_equivalence=False,
        quality_approved=False,release_approved=False,
        scope='Complete compact surface guides appended after every unchanged original native norm. '
            'Fixed-axis support gaps are nonsmooth; their finite differences and affine trust model are local approximations. '
            'Every candidate requires independently decoded native and complete geometry audits; no clearance or quality approval.')
    if not witnesses.rows: return original,jac,None,report
    stored = witnesses.gaps()
    np.testing.assert_allclose(stored,witnesses.gaps(surface_points(problem,problem.worlds(value))),atol=2e-10,rtol=0)
    if decoded_worlds is not None:
        anchored = witnesses.gaps(surface_points(problem,decoded_worlds))
        np.testing.assert_allclose(stored,anchored,atol=2e-10,rtol=0); stored = anchored
    smooth = witnesses.gaps(surface_points(problem,problem.worlds(value,quantized=False)))
    columns = []; steps = []
    for i in range(len(value)):
        forward,backward = problem.upper[i]-value[i],value[i]-problem.lower[i]
        if difference_scheme == 'central' and min(forward,backward) > 0:
            h = min(step,forward,backward); plus,minus = value.copy(),value.copy(); plus[i] += h; minus[i] -= h
            a = witnesses.gaps(surface_points(problem,problem.worlds(plus,quantized=False)))
            b = witnesses.gaps(surface_points(problem,problem.worlds(minus,quantized=False)))
            columns.append((a-b)/(2*h)); steps.append(dict(column=i,scheme='central',step=h))
        else:
            room = forward if forward >= backward else -backward
            h = np.copysign(min(step,abs(room)),room)
            if h == 0: raise ValueError('No finite-difference room for compact surface controls')
            other = value.copy(); other[i] += h
            a = witnesses.gaps(surface_points(problem,problem.worlds(other,quantized=False)))
            columns.append((a-smooth)/h); steps.append(dict(column=i,scheme='one-sided',step=h))
    scalar_jac = sparse.csr_matrix(np.stack(columns,axis=1))
    extra,extra_jac,conversion = lift(stored,scalar_jac,value,problem.lower,problem.upper,trust,clearance=clearance)
    combined = NormRows(np.r_[original.vectors,extra.vectors],np.r_[original.caps,extra.caps],np.r_[original.scales,extra.scales])
    report.update(conversion=conversion,surface_differences=steps)
    return combined,sparse.vstack([jac,extra_jac],format='csc'),witnesses,report
