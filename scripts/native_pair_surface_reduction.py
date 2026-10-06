"""Certified affine dominance inside complete nine-row triangle blocks.

An omitted row is implied by a retained row on the entire declared control
box, with the same surface clearance/scale/epigraph. This is an equivalent
local affine representation, not a reduced geometry benchmark or collision
certificate. Every original row remains available for full candidate checks.
"""
from dataclasses import dataclass
import hashlib
import numpy as np
from scipy import sparse

SCHEMA = 'strep-native-pair-surface-reduction-v1'


def _inputs(gaps, jacobian, offsets, value, lower, upper, trust):
    gaps, value, lower, upper = [np.asarray(a, float) for a in (gaps, value, lower, upper)]
    offsets = np.asarray(offsets)
    jacobian = sparse.csr_matrix(jacobian)
    if (gaps.ndim != 1 or not len(gaps) or len(gaps) > 400000
            or value.ndim != 1 or not 1 <= len(value) <= 96
            or len(gaps)*len(value) > 40000000
            or lower.shape != value.shape or upper.shape != value.shape
            or jacobian.shape != (len(gaps), len(value)) or not jacobian.has_canonical_format
            or offsets.ndim != 1 or offsets.dtype.kind not in 'iu' or len(offsets) < 2
            or offsets[0] != 0 or offsets[-1] != len(gaps) or not np.isin(np.diff(offsets), [1, 9]).all()
            or any(not np.isfinite(a).all() for a in (gaps, value, lower, upper, jacobian.data))
            or np.any(lower >= upper) or np.any(value < lower) or np.any(value > upper)
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 1e-6 <= trust <= .02):
        raise ValueError('Complete canonical affine pair rows, block order and bounded controls required')
    # Enclose normalized-box conversion and final subtraction roundoff. This
    # wider proof box does not change any authored or solver acceptance cap.
    pad = 64*np.finfo(float).eps*(1+abs(value)+trust)
    lo = np.nextafter(np.maximum(-trust, lower-value)-pad, -np.inf)
    hi = np.nextafter(np.minimum(trust, upper-value)+pad, np.inf)
    digest = hashlib.sha256()
    for a in (gaps, jacobian.data, jacobian.indices.astype(np.int64), jacobian.indptr.astype(np.int64),
              offsets.astype(np.int64), value, lower, upper, np.array([trust]), lo, hi):
        a = np.ascontiguousarray(a)
        digest.update(np.asarray(a.shape, np.int64).tobytes()); digest.update(a.dtype.str.encode()); digest.update(a.tobytes())
    return gaps, jacobian, offsets.astype(np.int64), lo, hi, digest.hexdigest()


def dominance_bounds(gaps, jacobian, lower, upper):
    """Outward upper bound of every q_i-q_j; batched blocks of scalar rows.

All arithmetic encloses exact real operations on the represented Float64
inputs. Each coefficient difference, endpoint product and accumulated sum is
rounded outward. Overflow/nonfinite intermediates disable a certificate.
"""
    gaps, jacobian = np.asarray(gaps, float), np.asarray(jacobian, float)
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    if (gaps.ndim != 2 or jacobian.shape[:2] != gaps.shape or jacobian.ndim != 3
            or lower.shape != (jacobian.shape[2],) or upper.shape != lower.shape
            or any(not np.isfinite(a).all() for a in (gaps, jacobian, lower, upper)) or np.any(lower > upper)):
        raise ValueError('Finite batched scalar rows and proof interval required')
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        same = gaps[:, :, None] == gaps[:, None, :]
        raw = gaps[:, :, None]-gaps[:, None, :]
        total = np.where(same, 0., np.nextafter(raw, np.inf))
        valid = np.isfinite(total)
        for k in range(jacobian.shape[2]):
            a, b = jacobian[:, :, None, k], jacobian[:, None, :, k]
            same = a == b; raw = a-b
            lo = np.where(same, 0., np.nextafter(raw, -np.inf))
            hi = np.where(same, 0., np.nextafter(raw, np.inf))
            products = [np.where(same, 0., np.nextafter(c*end, np.inf))
                for c in (lo, hi) for end in (lower[k], upper[k])]
            bound = np.maximum.reduce(products)
            valid &= np.isfinite(lo) & np.isfinite(hi) & np.isfinite(bound)
            total = np.where(bound == 0., total, np.nextafter(total+bound, np.inf))
            valid &= np.isfinite(total)
    return np.where(valid, total, np.inf)


@dataclass
class Reduction:
    roots: np.ndarray
    kinds: np.ndarray
    upper_bounds: np.ndarray
    report: dict

    @property
    def retained(self):
        return np.flatnonzero(self.roots == np.arange(len(self.roots)))


def reduce(gaps, jacobian, offsets, value, lower, upper, trust):
    gaps, jacobian, offsets, lo, hi, digest = _inputs(gaps, jacobian, offsets, value, lower, upper, trust)
    dense = jacobian.toarray(); roots = np.arange(len(gaps)); kinds = np.zeros(len(gaps), np.uint8)
    bounds = np.zeros(len(gaps)); starts = offsets[:-1][np.diff(offsets) == 9]
    for first in range(0, len(starts), 32):
        ids = starts[first:first+32, None]+np.arange(9)
        block_gaps, block_jac = gaps[ids], dense[ids]
        limits = dominance_bounds(block_gaps, block_jac, lo, hi)
        for block, rows in enumerate(ids):
            leaders = []
            for row in np.argsort(block_gaps[block], kind='stable'):
                for leader in leaders:
                    duplicate = block_gaps[block, leader] == block_gaps[block, row] and np.array_equal(block_jac[block, leader], block_jac[block, row])
                    if duplicate or limits[block, leader, row] <= 0:
                        roots[rows[row]] = rows[leader]; kinds[rows[row]] = 1 if duplicate else 2
                        bounds[rows[row]] = 0. if duplicate else limits[block, leader, row]
                        break
                else:
                    leaders.append(row)
    report = dict(schema=SCHEMA, affine_inputs_sha256=digest, original_rows=len(gaps),
        retained_rows=int((kinds == 0).sum()), duplicate_rows=int((kinds == 1).sum()),
        dominated_rows=int((kinds == 2).sum()), triangle_blocks=len(starts),
        other_rows=int((np.diff(offsets) == 1).sum()), proof_delta_lower=lo.tolist(), proof_delta_upper=hi.tolist(),
        all_original_rows_represented=True, affine_equivalence_only=True, quality_approved=False, release_approved=False,
        scope='Every removed affine row maps directly to a retained row of its own triangle block. '
            'Exact equality or outward whole-box upper bound proves q_root <= q_row. '
            'Same epigraph, clearance and scale required. Original nonlinear geometry acceptance unchanged.')
    return Reduction(roots, kinds, bounds, report)


def verify(reduction, gaps, jacobian, offsets, value, lower, upper, trust):
    gaps, jacobian, offsets, lo, hi, digest = _inputs(gaps, jacobian, offsets, value, lower, upper, trust)
    roots, kinds, bounds = reduction.roots, reduction.kinds, reduction.upper_bounds
    if (reduction.report.get('schema') != SCHEMA or reduction.report.get('affine_inputs_sha256') != digest
            or roots.shape != gaps.shape or roots.dtype.kind not in 'iu' or kinds.shape != gaps.shape
            or kinds.dtype != np.dtype('uint8') or not np.isin(kinds, [0, 1, 2]).all()
            or bounds.shape != gaps.shape or not np.isfinite(bounds).all()
            or np.any(roots < 0) or np.any(roots >= len(gaps)) or np.any(roots[roots] != roots)
            or not np.array_equal(kinds == 0, roots == np.arange(len(roots)))
            or np.any(bounds[kinds == 0] != 0)):
        raise ValueError('Bound complete reduction with direct retained roots required')
    expected = {'original_rows':len(gaps), 'retained_rows':int((kinds == 0).sum()),
        'duplicate_rows':int((kinds == 1).sum()), 'dominated_rows':int((kinds == 2).sum()),
        'proof_delta_lower':lo.tolist(), 'proof_delta_upper':hi.tolist(),
        'all_original_rows_represented':True, 'affine_equivalence_only':True,
        'quality_approved':False, 'release_approved':False}
    if (any(reduction.report.get(k) != v for k, v in expected.items())
            or any(reduction.report.get(k) is not v for k, v in expected.items() if type(v) is bool)
            or reduction.report.get('triangle_blocks') != int((np.diff(offsets) == 9).sum())
            or reduction.report.get('other_rows') != int((np.diff(offsets) == 1).sum())):
        raise ValueError('Reduction decisions or proof box changed')
    dense = jacobian.toarray(); starts = offsets[:-1][np.diff(offsets) == 9]
    singleton = offsets[:-1][np.diff(offsets) == 1]
    if np.any(kinds[singleton] != 0):
        raise ValueError('Other surface witnesses must be retained')
    for first in range(0, len(starts), 32):
        ids = starts[first:first+32, None]+np.arange(9)
        limits = dominance_bounds(gaps[ids], dense[ids], lo, hi)
        for block, rows in enumerate(ids):
            for row, identity in enumerate(rows):
                root = roots[identity]
                if not rows[0] <= root <= rows[-1]:
                    raise ValueError('Cross-block dominance is not certified')
                leader = int(root-rows[0])
                if kinds[identity] == 1:
                    if gaps[root] != gaps[identity] or not np.array_equal(dense[root], dense[identity]) or bounds[identity] != 0:
                        raise ValueError('Duplicate certificate is not exact')
                elif kinds[identity] == 2:
                    if not limits[block, leader, row] <= bounds[identity] <= 0:
                        raise ValueError('Whole-box dominance upper bound does not prove implication')
    return dict(original_rows=len(gaps), retained_rows=len(reduction.retained),
        all_certificate_rows_checked=True, affine_equivalent=True, quality_approved=False, release_approved=False)
