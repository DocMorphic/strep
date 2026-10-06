"""Complete fixed-axis vertex-pair affine guides, separate from acceptance.

All nine scalar inequalities are retained for every recorded triangle pair.
This avoids differentiating a nonsmooth minimum. Axes and witnesses are local;
decoded original native and whole-scene geometry checks remain authoritative.
"""
import numpy as np
from scipy import sparse
from native_compact_surface_rows import build, METHODS as ROW_METHODS
from native_scene_norms import linearize, rows as native_rows
from native_surface_model import surface_points

SCHEMA = 'strep-native-pair-surface-model-v1'
METHODS = tuple(dict.fromkeys(ROW_METHODS + ('native_scene_norms.py',
    'native_surface_model.py', 'native_pair_surface_model.py')))


class PairSurfaceRows:
    """Block metadata with complete expanded scalar order, without nine dicts."""
    def __init__(self, compact, maximum_rows):
        if type(maximum_rows) is not int or not 1 <= maximum_rows <= 400000:
            raise ValueError('Finite explicit expanded surface-row budget required')
        self.compact = compact
        self.sizes = np.array([9 if r['kind'] == 'triangle-support-separation' else 1
            for r in compact.rows], int)
        self.offsets = np.r_[0, np.cumsum(self.sizes)]
        self.count = int(self.offsets[-1])
        if self.count > maximum_rows:
            raise ValueError('Complete expanded surface rows exceed resource budget; no subset returned')
        self.report = dict(compact.report, expanded_scalar_rows=self.count,
            maximum_expanded_rows=maximum_rows, affine_linearization_equivalence=True,
            scalar_order='Block order; triangle left vertex then right vertex, all 3 by 3 pairs',
            scope='Every compact witness retained; each triangle block expanded to nine fixed-axis '
                'scalar functions before differentiation. Local affine proposal only; no geometry approval.')

    def gaps(self, vertices=None):
        cache = {}
        def query(actor, time):
            key = actor, time
            if key not in cache:
                source = self.compact.scene.actors[actor]
                if vertices is None:
                    p, r = source['placement']
                    value = source['rig'].vertices(source['sampler'].sample(time)) @ r.T+p
                else:
                    value = np.asarray(vertices(actor, time), float)
                if value.shape != (len(source['skin'].nodes), 3) or not np.isfinite(value).all():
                    raise ValueError('Complete finite posed surface population required')
                cache[key] = value
            return cache[key]
        result = np.empty(self.count)
        for i, row in enumerate(self.compact.rows):
            normal = np.asarray(row['normal_world'])
            left = query(row['left']['actor'], row['time_s'])[row['left']['vertices']]
            if row['kind'] == 'triangle-support-separation':
                right = query(row['right']['actor'], row['time_s'])[row['right']['vertices']]
                gap = ((left @ normal)[:, None]-(right @ normal)[None, :]).ravel()
            else:
                gap = float(np.asarray(row['left']['weights']) @ left @ normal)
                if row['right'] is None:
                    gap -= row['constant_m']
                else:
                    right = query(row['right']['actor'], row['time_s'])[row['right']['vertices']]
                    gap -= float(np.asarray(row['right']['weights']) @ right @ normal)
            result[self.offsets[i]:self.offsets[i+1]] = gap
        self.compact.scene.check_inputs()
        return result


def model(problem, value, decoded_scene, policy, digest, trust, *, step=.001,
          maximum_rows=400000, maximum_nonzeros=60000000, decoded_worlds=None,
          clearance=.0005, difference_scheme='central'):
    if (type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .01
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 400000
            or type(maximum_nonzeros) is not int or not 1 <= maximum_nonzeros <= 60000000
            or type(clearance) not in (int, float) or not np.isfinite(clearance) or not 0 <= clearance <= .005
            or difference_scheme not in ('forward', 'central')):
        raise ValueError('Bounded explicit pair proposal settings required')
    value = problem.edits.controls(value)
    original, jac, identity = linearize(problem, value, step=step,
        difference_source='continuous', difference_scheme=difference_scheme)
    if decoded_worlds is not None:
        anchored = native_rows(problem, value, decoded_worlds)
        if not np.array_equal(original.caps, anchored.caps) or not np.array_equal(original.scales, anchored.scales):
            raise ValueError('Decoded anchoring changed original norm caps or ordering')
        original = anchored
    compact = build(decoded_scene, policy, digest, maximum_rows=min(maximum_rows, 100000), clearance=clearance)
    guides = PairSurfaceRows(compact, maximum_rows)
    stored = guides.gaps()
    np.testing.assert_allclose(stored, guides.gaps(surface_points(problem, problem.worlds(value))), atol=2e-10, rtol=0)
    if decoded_worlds is not None:
        anchor = guides.gaps(surface_points(problem, decoded_worlds))
        np.testing.assert_allclose(stored, anchor, atol=2e-10, rtol=0)
        stored = anchor
    columns, steps, nonzeros = [], [], 0
    if guides.count:
        smooth = guides.gaps(surface_points(problem, problem.worlds(value, quantized=False)))
        for i in range(len(value)):
            forward, backward = problem.upper[i]-value[i], value[i]-problem.lower[i]
            if difference_scheme == 'central' and min(forward, backward) > 0:
                h = min(step, forward, backward)
                plus, minus = value.copy(), value.copy(); plus[i] += h; minus[i] -= h
                a = guides.gaps(surface_points(problem, problem.worlds(plus, quantized=False)))
                b = guides.gaps(surface_points(problem, problem.worlds(minus, quantized=False)))
                column = (a-b)/(2*h); scheme = 'central'
            else:
                room = forward if forward >= backward else -backward
                h = np.copysign(min(step, abs(room)), room)
                if h == 0:
                    raise ValueError('No finite-difference room for pair surface controls')
                other = value.copy(); other[i] += h
                a = guides.gaps(surface_points(problem, problem.worlds(other, quantized=False)))
                column = (a-smooth)/h; scheme = 'one-sided'
            if not np.isfinite(column).all():
                raise ValueError('Nonfinite complete pair derivative')
            entry = sparse.csc_matrix(column[:, None]); nonzeros += entry.nnz
            if nonzeros > maximum_nonzeros:
                raise ValueError('Complete pair Jacobian exceeds resource budget; no subset returned')
            columns.append(entry); steps.append(dict(column=i, scheme=scheme, step=float(h)))
    scalar_jac = sparse.hstack(columns, format='csc') if columns else sparse.csc_matrix((guides.count, len(value)))
    report = dict(schema=SCHEMA, differences=identity, original_norm_rows=len(original.caps),
        surface_rows=guides.count, surface_query=guides.report, surface_differences=steps,
        surface_nonzeros=nonzeros, maximum_nonzeros=maximum_nonzeros,
        clearance_m=float(clearance), trust=float(trust), native_acceptance_unchanged=True,
        affine_nine_pair_equivalence=True, quality_approved=False, release_approved=False,
        scope='Every original native norm and cap retained separately from complete scalar surface '
            'guides. No selected extrema or derivative threshold; sparse columns omit exact zeros only. '
            'Decoded original native/reference and complete geometry audits decide acceptance.')
    return original, jac, guides, stored, scalar_jac, report
