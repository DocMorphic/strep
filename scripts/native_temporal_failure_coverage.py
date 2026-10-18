"""Plan explicit native-key blocks from complete sampled failure stencils.

Coverage means a supplied stencil can depend on a proposed one-key temporal
block. It is not a nonzero spatial derivative, a repair, or a feasible motion.
The caller owns original rig permissions, row semantics and physical checks.
"""
import numpy as np

MAXIMUM_ROWS = 65536
MAXIMUM_KEYS = 4096
MAXIMUM_CANDIDATES = 512
MAXIMUM_CELLS = 8 * 1024**2


def temporal_failure_coverage(clock, frozen_keys, stencils, *, initial_peaks=(),
                              maximum_cells=MAXIMUM_CELLS):
    """Retain all rows/candidates and greedily cover their weighted stencils.

    A candidate changes one existing native key and anchors its two neighbours.
    Original frozen keys remain unavailable. Exact stored LINEAR interpolation
    weights decide dependency, including exact keys and rounded-zero weights.
    Initial peaks are explicit scheduling context, never successful repairs.
    The returned matrix includes every candidate, also those not selected.
    """
    raw = np.asarray(clock)
    if (raw.dtype.kind not in 'fiu' or raw.dtype.itemsize > 8 or raw.ndim != 1
            or not 3 <= len(raw) <= MAXIMUM_KEYS or not np.isfinite(raw).all()):
        raise ValueError('Complete finite native clock required')
    times = raw.astype(float, copy=True)
    with np.errstate(over='ignore',invalid='ignore'):
        delta=np.diff(times);span=times[-1]-times[0]
    if np.any(delta <= 0) or not np.isfinite(delta).all() or not np.isfinite(span):
        raise ValueError('Strictly increasing finite-span native clock required')
    if (not isinstance(frozen_keys, list) or not frozen_keys
            or any(type(k) is not int or not 0 <= k < len(times) for k in frozen_keys)
            or frozen_keys != sorted(set(frozen_keys))
            or not {0, len(times) - 1}.issubset(frozen_keys)):
        raise ValueError('Explicit sorted original frozen keys including endpoints required')
    if (not isinstance(stencils, list) or not 1 <= len(stencils) <= MAXIMUM_ROWS
            or type(maximum_cells) is not int or not 1 <= maximum_cells <= MAXIMUM_CELLS):
        raise ValueError('Complete bounded stencil population and cell budget required')
    keys = [k for k in range(len(times)) if k not in frozen_keys]
    if len(keys) > MAXIMUM_CANDIDATES or len(keys) * len(stencils) > maximum_cells:
        raise ValueError('Complete candidate/row budget exceeded; no keys or rows dropped')
    if (not isinstance(initial_peaks, (list, tuple))
            or any(type(k) is not int or k not in keys for k in initial_peaks)
            or len(set(initial_peaks)) != len(initial_peaks)):
        raise ValueError('Explicit distinct available initial peaks required')
    ids=[];weights=[];samples=[]
    for row in stencils:
        if (not isinstance(row, dict) or set(row) != {'row', 'times_s', 'weight'}
                or type(row['row']) is not int or row['row'] < 0
                or not isinstance(row['times_s'], list) or not 1 <= len(row['times_s']) <= 3
                or any(type(t) not in (int, float) or not np.isfinite(t) for t in row['times_s'])
                or type(row['weight']) not in (int, float) or not np.isfinite(row['weight'])
                or not 0 < row['weight'] <= 1e12):
            raise ValueError('Explicit row identity, one/three finite sample times and positive weight required')
        stamps=np.asarray(row['times_s'], float)
        if np.any(np.diff(stamps) <= 0) or np.any(stamps < times[0]) or np.any(stamps > times[-1]):
            raise ValueError('Ordered stencil samples must belong to the native clock interval')
        ids.append(row['row']);weights.append(row['weight']);samples.append(stamps)
    if len(set(ids)) != len(ids):
        raise ValueError('Every supplied failure must have a distinct stable row identity')
    coverage=np.zeros((len(keys),len(ids)),bool);lookup={key:i for i,key in enumerate(keys)}
    for column,stamps in enumerate(samples):
        for stamp in stamps:
            right=int(np.searchsorted(times,stamp,side='left'))
            if times[right] == stamp:
                endpoints=[(right,1.)]
            else:
                fraction=(stamp-times[right-1])/(times[right]-times[right-1])
                endpoints=[(right-1,1-fraction),(right,fraction)]
            for key,weight in endpoints:
                if weight != 0 and key in lookup:coverage[lookup[key],column]=True
    weight_array=np.asarray(weights,float);covered=np.zeros(len(ids),bool);selected=[];steps=[]
    def select(key,initial):
        nonlocal covered
        newly=coverage[lookup[key]] & ~covered
        steps.append(dict(peak_key=key,initial=initial,newly_covered_rows=int(newly.sum()),
                          newly_covered_weight=float(np.sum(weight_array[newly]))))
        covered |= coverage[lookup[key]];selected.append(key)
    for key in initial_peaks:select(key,True)
    initially_covered=covered.copy()
    while not np.all(covered):
        scores=[float(np.sum(weight_array[mask & ~covered])) for mask in coverage]
        if not scores or max(scores) == 0:break
        select(keys[int(np.argmax(scores))],False)
    row_ids=np.asarray(ids,dtype=object)
    return dict(candidate_keys=keys,coverage=coverage,row_ids=ids,weights=weight_array,
                selected_peaks=selected,steps=steps,
                initially_covered_rows=row_ids[initially_covered].tolist(),
                covered_rows=row_ids[covered].tolist(),uncovered_rows=row_ids[~covered].tolist(),
                report=dict(schema='strep-native-temporal-failure-coverage-v1',rows=len(ids),
                    candidates=len(keys),complete_cells=coverage.size,maximum_cells=maximum_cells,
                    selected_blocks=len(selected),initially_covered=int(initially_covered.sum()),
                    covered=int(covered.sum()),uncovered=int((~covered).sum()),
                    all_rows_and_candidates_retained=True,original_frozen_keys=frozen_keys.copy(),
                    tie_rule='lowest native key among equal complete weighted marginal sums',
                    source_caps_and_row_semantics_owned_by_caller=True,
                    quality_approved=False,release_approved=False,
                    scope='Complete sampled temporal dependency coverage for explicitly declared single-key blocks only. '
                          'Weighted greedy scheduling is not an optimality, controllability, repair or feasibility claim. '
                          'Uncovered rows are invariant for this candidate family, not proof that the rig/action is impossible. '
                          'No source rebasing, motion fitting, geometry, continuous-time, engine or human approval.'))
