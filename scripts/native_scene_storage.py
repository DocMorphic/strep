"""Finite translation storage-cell probes; decoded constraints stay authoritative.

Each probe follows one existing bounded control direction. No native key, track,
contact clock or acceptance limit is added or changed. Rotation directions are
explicitly unavailable for this affine Float32 cell calculation.
"""
import numpy as np


def line_data(edits, origin, direction):
    origin = edits.controls(origin); direction = edits.controls(direction)
    bases, slopes = [], []
    for actor in edits.actors.values():
        for entry in actor['tracks']:
            delta = entry['weights'] @ direction[entry['controls']] * entry['unit']
            if entry['path'] != 'translation':
                if np.any(delta): raise ValueError('Storage cells require a translation-only direction')
                continue
            base = entry['source'][entry['ids']].astype(float)
            base += entry['weights'] @ origin[entry['controls']] * entry['unit']
            changed = delta != 0
            bases.append(base[changed]); slopes.append(delta[changed])
    if not bases or not sum(len(b) for b in bases): raise ValueError('A changed translation direction is required')
    return np.concatenate(bases),np.concatenate(slopes)


def cell(base, slope, fraction):
    raw = base+slope*fraction
    stored = raw.astype(np.float32)
    previous = np.nextafter(stored,np.float32(-np.inf)).astype(float)
    following = np.nextafter(stored,np.float32(np.inf)).astype(float)
    if not np.isfinite(np.r_[raw,previous,following]).all(): raise ValueError('Finite neighboring storage cells required')
    low = ((previous+stored.astype(float))*.5-base)/slope
    high = ((following+stored.astype(float))*.5-base)/slope
    lower = max(0.,float(np.minimum(low,high).max()))
    upper = min(1.,float(np.maximum(low,high).min()))
    if lower>fraction or upper<fraction or not lower<upper:
        raise ValueError('A nonempty Float32 translation cell is required')
    return lower,upper,stored


def fractions(edits, origin, direction, *, maximum_cells=64, start_fraction=1.):
    if type(maximum_cells) is not int or not 1<=maximum_cells<=512:
        raise ValueError('Choose 1-512 storage cells')
    if type(start_fraction) not in (int,float) or not np.isfinite(start_fraction) or not 0<start_fraction<=1:
        raise ValueError('Choose a positive bounded starting fraction')
    origin=edits.controls(origin);direction=edits.controls(direction)
    base,slope = line_data(edits,origin,direction)
    cursor=float(start_fraction); result=[]; previous_lower=None
    for _ in range(maximum_cells):
        lower,upper,stored=cell(base,slope,cursor)
        if previous_lower is not None and upper>previous_lower+64*np.finfo(float).eps:
            raise ValueError('Storage cell walk did not advance')
        representative=(lower+min(upper,start_fraction))*.5
        # Independent evaluation order matters at numerical boundaries. Retain
        # only interior representatives whose actual SceneEdits values agree.
        controls=edits.controls(origin)+representative*edits.controls(direction)
        actual=[]
        for name,actor in edits.actors.items():
            values=edits.values(name,controls)
            for entry in actor['tracks']:
                if entry['path']!='translation':continue
                delta=entry['weights'] @ direction[entry['controls']] * entry['unit']
                actual.append(values[entry['node'],entry['path']][entry['ids']][delta!=0].astype(np.float32))
        if not np.array_equal(np.concatenate(actual),stored):
            raise ValueError('Storage-cell interior differs from actual serialized keys')
        result.append(dict(fraction=float(representative),lower_fraction=lower,upper_fraction=upper))
        if lower==0.:break
        # A bounded Float64 reserve steps off the tie; the next cell is again
        # checked against actual key serialization. This is not interval proof.
        reserve=64*np.finfo(float).eps*max(1.,abs(lower),float(np.max((abs(base)+abs(slope*lower))/abs(slope))))
        if lower<=reserve:break
        previous_lower=lower;cursor=lower-reserve
    return result,dict(maximum_cells=maximum_cells,visited_cells=len(result),
        starting_fraction=float(start_fraction),last_lower_fraction=result[-1]['lower_fraction'],
        reached_zero=result[-1]['lower_fraction']==0.,
        scope='Finite neighboring affine translation cells; actual decoded constraints decide acceptance; no exhaustive feasibility proof.')
