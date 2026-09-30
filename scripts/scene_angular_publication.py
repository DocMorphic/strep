"""Check selected-motion angular evidence before offering a corrected Studio asset."""
import math
from pathlib import Path
from strep import read, sha256


def require_angular_replay(folder, result, trial, prepared):
    folder = Path(folder); evidence = folder/'angular-replay'
    if not (evidence/'request.json').is_file() or not (evidence/'verification.json').is_file():
        raise ValueError('Independent angular replay required before candidate publication')
    protocol, proof = read(evidence/'request.json'), read(evidence/'verification.json')
    if proof['status'] != 'complete' or proof['request_sha256'] != sha256(evidence/'request.json') or proof.get('passed') is not True:
        raise ValueError('Completed passing angular replay required')
    if protocol['study_request_sha256'] != sha256(folder/'fit/request.json') or protocol['study_result_sha256'] != sha256(folder/'fit/result.json'):
        raise ValueError('Angular replay belongs to another fit')
    if protocol['selected'] != result['selected'] or proof['selected'] != result['selected'] or protocol['tolerance'] != 1e-5:
        raise ValueError('Angular replay selection or tolerance differs')
    for path,digest in protocol['inputs'].items():
        if sha256(path) != digest: raise ValueError('Angular replay input changed')
    for name,digest in protocol['implementation'].items():
        path = (evidence/'implementation'/name).resolve()
        if path.parent != (evidence/'implementation').resolve() or sha256(path) != digest:
            raise ValueError('Angular method snapshot changed')
    if [a['actor'] for a in proof['actors']] != list(prepared['actors']): raise ValueError('Angular replay participants differ')
    candidates = {a['actor']:a for a in trial['actors']}; samples = len(prepared['sample_times_seconds'])
    for actor in proof['actors']:
        name = actor['actor']
        if actor['source_sha256'] != prepared['actors'][name]['sha256'] or actor['candidate_sha256'] != candidates[name]['sha256']:
            raise ValueError('Angular replay clip identity differs')
        if actor['samples'] != samples or samples < 3 or actor['joints'] != 77:
            raise ValueError('Angular replay does not cover the complete supported rig and clock')
        if set(actor['rates']) != {'angular_speed_rad_s', 'angular_acceleration_rad_s2'}: raise ValueError('Both angular metrics required')
        for order,kind in enumerate(['angular_speed_rad_s', 'angular_acceleration_rad_s2'], start=1):
            metric = actor['rates'][kind]
            if metric['observations'] != (samples-order)*actor['joints'] or metric['exceeding_observations'] != 0 or metric['tolerance'] != 1e-5:
                raise ValueError('Incomplete or failing angular observations')
            maximum = metric['maximum_increase']
            if not math.isfinite(maximum) or not 0 <= maximum <= 1e-5:
                raise ValueError('Angular limit exceeded')
