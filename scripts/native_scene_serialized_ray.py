"""Finite actual-key ray probes, including quaternion tracks; no interval proof."""
import numpy as np


def probe_fractions(edits, origin, direction, *, maximum_probes=64, start_fraction=1.):
    if type(maximum_probes) is not int or not 1<=maximum_probes<=512:
        raise ValueError('Choose 1-512 serialized ray probes')
    if type(start_fraction) not in (int,float) or not np.isfinite(start_fraction) or not 0<start_fraction<=1:
        raise ValueError('Positive bounded serialized ray starting fraction required')
    origin=edits.controls(origin);direction=edits.controls(direction)
    endpoint=origin+start_fraction*direction
    if (np.any(origin<edits.lower) or np.any(origin>edits.upper)
            or np.any(endpoint<edits.lower) or np.any(endpoint>edits.upper)):
        raise ValueError('Serialized ray must stay within original control boxes')
    queries=0;population=None
    def signature(fraction):
        nonlocal queries,population
        if not 0<=fraction<=start_fraction:raise ValueError('Serialized ray query left its bounded interval')
        controls=origin+fraction*direction;parts=[];names=[]
        for name,actor in edits.actors.items():
            values=edits.values(name,controls)
            for entry in actor['tracks']:
                # Keep every key of every editable track, including frozen keys
                # and tracks unchanged along this ray. The exporter uses these
                # same complete arrays; neither anatomy nor small values filter.
                value=np.asarray(values[entry['node'],entry['path']],dtype=np.float32)
                if not np.isfinite(value).all():
                    raise ValueError('Complete finite Float32 track values required')
                names.append((name,entry['node'],entry['path'],value.shape));parts.append(value.tobytes(order='C'))
        if population is None:population=names
        elif names!=population:raise ValueError('Serialized ray key population changed')
        queries+=1;return b''.join(parts)
    initial=signature(0.);cursor=float(start_fraction);result=[];seen=set();reached_original=False
    for _ in range(maximum_probes):
        current=signature(cursor)
        if current==initial:reached_original=True;break
        if current in seen:break
        seen.add(current)
        # Locate a tested lower fraction with different actual keys. Quaternion
        # paths can curve and return to states: this is bounded numerical search,
        # not an analytic cell walk or exhaustive coverage of the interval.
        matching=cursor;distance=64*np.finfo(float).eps*max(1.,cursor);different=None
        for _ in range(52):
            lower=max(0.,cursor-distance)
            if signature(lower)!=current:different=lower;break
            matching=lower
            if lower==0.:break
            distance*=2.
        if different is None:break
        for _ in range(52):
            middle=(different+matching)*.5
            if not different<middle<matching:break
            if signature(middle)==current:matching=middle
            else:different=middle
            if matching-different<=64*np.finfo(float).eps*max(1.,matching):break
        representative=(matching+cursor)*.5
        if not different<representative<=cursor or signature(representative)!=current:
            raise ValueError('Serialized ray representative differs from its measured keys')
        result.append(dict(fraction=float(representative),matched_lower_probe=float(matching),
            matched_upper_probe=float(cursor),different_lower_probe=float(different)))
        if not different<cursor:raise ValueError('Serialized ray probes did not advance')
        cursor=different
    return result,dict(available=True,maximum_probes=maximum_probes,visited_probes=len(result),
        starting_fraction=float(start_fraction),signature_queries=queries,reached_original_keys=reached_original,
        complete_track_population=[dict(actor=n,node=i,path=p,shape=list(s)) for n,i,p,s in population],
        sampling_modified=False,original_caps_unchanged=True,
        interval_certified=False,exhaustive=False,
        scope='Numerically bracketed actual Float32 track signatures; all original decoded constraints decide acceptance.')
