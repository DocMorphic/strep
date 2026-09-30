"""Compare bound hand screens at identical times without hiding directional regressions."""
from pathlib import Path
import numpy as np
from strep import read,sha256


def population(rows):
    result={}
    for row in rows:
        sample,time=row['sample'],row['time_s'];directions=row['directions']
        if type(sample) is not int or sample<0 or sample in result or not np.isfinite(time) or len(directions)!=2:
            raise ValueError('Unique sample IDs, finite times and two ordered directions required')
        depths=np.array([d['max_depth_m'] for d in directions],float)
        counts=[(d['vertices_checked'],d['source_full_vertex_count']) for d in directions]
        if not np.isfinite(depths).all() or np.any(depths<0) or any(
                type(c) is not int or type(n) is not int or not 1<=c<=n for c,n in counts):
            raise ValueError('Finite nonnegative depths and positive vertex populations required')
        result[sample]=(float(time),depths,counts)
    if not result:raise ValueError('Nonempty hand geometry required')
    return result


def compare(reference,candidate,tolerance=.005):
    old,new=population(reference),population(candidate)
    if not np.isfinite(tolerance) or tolerance<0:raise ValueError('Finite nonnegative threshold required')
    if not set(old).issubset(new):raise ValueError('Candidate must retain every reference sample')
    rows=[]
    for sample in sorted(old):
        time,a,counts=old[sample];stamp,b,population_counts=new[sample]
        if time!=stamp or counts!=population_counts:raise ValueError('Exact matching times and hand populations required')
        rows.append(dict(sample=sample,time_s=time,reference_depths_m=a.tolist(),candidate_depths_m=b.tolist(),
            directional_increases_m=(b-a).tolist(),reference_peak_m=float(a.max()),candidate_peak_m=float(b.max())))
    return dict(samples=rows,compared_samples=len(rows),uncompared_candidate_samples=sorted(set(new)-set(old)),
        reference_peak_m=max(r['reference_peak_m'] for r in rows),candidate_peak_m=max(r['candidate_peak_m'] for r in rows),
        reference_failed_samples=[r['sample'] for r in rows if r['reference_peak_m']>tolerance],
        candidate_failed_samples=[r['sample'] for r in rows if r['candidate_peak_m']>tolerance],
        new_failed_samples=[r['sample'] for r in rows if r['reference_peak_m']<=tolerance<r['candidate_peak_m']],
        maximum_sample_increase_m=max(r['candidate_peak_m']-r['reference_peak_m'] for r in rows),
        maximum_directional_increase_m=max(max(r['directional_increases_m']) for r in rows),
        direction_observations_worsened=sum(v>1e-8 for r in rows for v in r['directional_increases_m']))


def load_warm_geometry(request,files):
    """The donor result/request must already be declared by the current study."""
    folder=Path(request['warm_start_study']).resolve()
    for name in ['result','request']:
        path=folder/(name+'.json')
        if files.get(str(path))!=sha256(path):raise ValueError('Geometry donor differs from bound warm start')
    result,donor=read(folder/'result.json'),read(folder/'request.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(folder/'request.json'):
        raise ValueError('Completed bound geometry donor required')
    path=folder/'geometry.json'
    if sha256(path)!=result['geometry_sha256']:raise ValueError('Donor geometry changed')
    geometry=read(path)
    if [r['sample'] for r in geometry]!=donor['hand_samples']:raise ValueError('Complete donor hand clock required')
    population(geometry)
    return geometry,{str(path):result['geometry_sha256']}
