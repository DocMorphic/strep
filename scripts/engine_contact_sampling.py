"""Predeclared game-frame contact populations, separate from exact event points.

No rate/phase selection after observing a result; no legacy failure override.
"""
import hashlib
import json
import numpy as np


RATES_HZ = (30, 60, 120)
PHASES_FRAMES = (0., .25, .5, .75)


def contract():
    return dict(schema='strep-engine-frame-contact-sampling-v1',
        rates_hz=list(RATES_HZ), phase_offsets_frames=list(PHASES_FRAMES),
        clock='Absolute clip time (integer_tick + phase_offset_frames) / rate_hz',
        velocity='Adjacent ticks within the same authored stance and clock population',
        geometry='All requested stance points, including exact boundaries and native keys',
        missing_velocity_population='Unavailable and not passed; never substitute boundaries or another clock',
        legacy_population='Retained independently; frame results cannot override legacy failures',
        continuous_contact_certified=False, physics_playback_verified=False)


def contract_sha256():
    raw=json.dumps(contract(),sort_keys=True,separators=(',',':')).encode('utf8')
    return hashlib.sha256(raw).hexdigest()


def frame_populations(stance):
    a=np.asarray(stance,float)
    if a.shape!=(2,) or not np.isfinite(a).all() or not 0<=a[0]<a[1]<=30:
        raise ValueError('Finite increasing stance seconds within 30-second clip required')
    start,end=a; result=[]
    for rate in RATES_HZ:
        for phase in PHASES_FRAMES:
            # Overshoot by a tick before checking membership numerically. The
            # clock is declared independently of floating native key positions.
            ticks=np.arange(int(np.floor(start*rate-phase))-1,int(np.ceil(end*rate-phase))+2)
            times=(ticks.astype(float)+phase)/rate
            selected=(times>=start)&(times<=end)
            result.append(dict(id=f'{rate}hz-phase-{phase:g}',rate_hz=rate,phase_offset_frames=phase,
                               tick_indices=ticks[selected],times_s=times[selected]))
    return result


def point_limits(points,anchor,normal,offset,patch,limits):
    """Exact points retain anchor and height requirements without derivatives."""
    points,anchor,normal=map(lambda x:np.asarray(x,float),(points,anchor,normal))
    patch=np.asarray(patch)
    if (points.ndim!=3 or points.shape[2]!=3 or not len(points) or points.shape[1]==0
            or anchor.shape!=points.shape[1:] or normal.shape!=(3,)
            or not np.isfinite(points).all() or not np.isfinite(anchor).all()
            or not np.isfinite(normal).all() or abs(np.linalg.norm(normal)-1)>1e-8
            or not np.isfinite(offset) or patch.ndim!=1 or patch.dtype.kind not in 'iu'
            or len(patch)==0 or len(np.unique(patch))!=len(patch)
            or patch.min()<0 or patch.max()>=points.shape[1]):
        raise ValueError('Finite point population and fixed patch identities required')
    required={'anchor_m','clearance_m','maximum_gap_m'}
    if (set(limits)!=required or any(type(v) not in (int,float) or not np.isfinite(v) or v<0 for v in limits.values())
            or limits['maximum_gap_m']<limits['clearance_m']):
        raise ValueError('Explicit finite point limits required')
    delta=points[:,patch]-anchor[patch]
    delta-=(delta@normal)[...,None]*normal
    heights=points@normal+offset
    error=float(np.linalg.norm(delta,axis=2).max())
    low=float(heights.min());gap=float(heights.min(axis=1).max())
    return dict(samples=len(points),maximum_patch_anchor_error_m=error,minimum_region_height_m=low,
        maximum_lowest_region_height_m=gap,limits=dict(limits),
        passed=bool(error<=limits['anchor_m'] and low>=limits['clearance_m']-1e-8 and gap<=limits['maximum_gap_m']))


def frame_speed(points,normal,patch,population,limit):
    points=np.asarray(points,float);normal=np.asarray(normal,float);patch=np.asarray(patch)
    times=np.asarray(population['times_s'],float);ticks=np.asarray(population['tick_indices'])
    rate=population['rate_hz'];phase=population['phase_offset_frames']
    if (type(rate) is not int or rate not in RATES_HZ or type(phase) is not float or phase not in PHASES_FRAMES
            or times.ndim!=1 or ticks.shape!=times.shape or ticks.dtype.kind not in 'iu'
            or not np.isfinite(times).all() or np.any(np.diff(ticks)!=1)
            or not np.array_equal(times,(ticks.astype(float)+phase)/rate)
            or points.ndim!=3 or points.shape!=(len(times),points.shape[1],3) or points.shape[1]==0
            or not np.isfinite(points).all() or normal.shape!=(3,) or not np.isfinite(normal).all()
            or abs(np.linalg.norm(normal)-1)>1e-8 or patch.ndim!=1 or patch.dtype.kind not in 'iu'
            or not len(patch) or len(np.unique(patch))!=len(patch) or patch.min()<0 or patch.max()>=points.shape[1]
            or type(limit) not in (int,float) or not np.isfinite(limit) or limit<0):
        raise ValueError('Declared consecutive game-frame population and finite patch data required')
    result=dict(frames=len(times),pairs=max(0,len(times)-1),rate_hz=rate,phase_offset_frames=phase,
                maximum_speed_m_s=None,peak_pair=None,limit_m_s=float(limit),available=len(times)>=2,passed=False)
    if len(times)<2:return result
    movement=np.diff(points[:,patch],axis=0)
    movement-=(movement@normal)[...,None]*normal
    speed=np.linalg.norm(movement,axis=2)*rate
    pair,vertex=np.unravel_index(speed.argmax(),speed.shape)
    maximum=float(speed[pair,vertex])
    result.update(maximum_speed_m_s=maximum,passed=bool(maximum<=limit),peak_pair=dict(
        tick_indices=ticks[pair:pair+2].tolist(),times_s=times[pair:pair+2].tolist(),
        interval_s=1./rate,patch_vertex_index=int(patch[vertex]),tangential_distance_m=float(np.linalg.norm(movement[pair,vertex]))))
    return result


def evaluate(points,anchor,normal,offset,patch,point_indices,populations,all_times,limits):
    """Never differentiate the union of event, native-key and game clocks."""
    all_times=np.asarray(all_times,float);points=np.asarray(points,float)
    if (all_times.ndim!=1 or len(all_times)<2 or not np.isfinite(all_times).all()
            or np.any(np.diff(all_times)<=0) or points.ndim!=3 or len(points)!=len(all_times)):
        raise ValueError('Complete increasing engine point clock required')
    ids=np.asarray(point_indices)
    if (ids.ndim!=1 or ids.dtype.kind not in 'iu' or not len(ids) or ids.min()<0 or ids.max()>=len(all_times)
            or len(np.unique(ids))!=len(ids)):
        raise ValueError('Distinct stance geometry sample indices required')
    point=point_limits(points[ids],anchor,normal,offset,patch,
        {k:limits[k] for k in ('anchor_m','clearance_m','maximum_gap_m')})
    expected=[(rate,phase) for rate in RATES_HZ for phase in PHASES_FRAMES]
    if [(p['rate_hz'],p['phase_offset_frames']) for p in populations]!=expected:
        raise ValueError('All fixed rate/phase populations required in declared order')
    measured=[]
    for population in populations:
        clock=np.asarray(population['times_s'],float)
        index=np.searchsorted(all_times,clock)
        if np.any(index>=len(all_times)) or not np.array_equal(all_times[index],clock):
            raise ValueError('Missing game-frame engine samples')
        if not np.isin(index,ids).all():
            raise ValueError('Game-frame points omitted from geometry population')
        speed=frame_speed(points[index],normal,patch,population,limits['speed_m_s'])
        measured.append(dict(id=population['id'],times_s=clock.tolist(),tick_indices=population['tick_indices'].tolist(),**speed))
    return dict(points=point,populations=measured,
        passed=bool(point['passed'] and all(p['available'] and p['passed'] for p in measured)),
        continuous_contact_certified=False,quality_approved=False)
