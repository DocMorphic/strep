"""Bind a completed lattice guide and independently recompute its path search."""
from pathlib import Path
import numpy as np
from strep import read,sha256
from bound_evidence import bind_inputs
from waypoint_lattice import shortest_path,LinearGuide


def load_path(folder,source_plan,window,required,*,native_clocks=None,protected=None):
    folder=Path(folder).resolve();result=read(folder/'result.json')
    if result['status']!='complete' or not result['selected']:raise ValueError('Completed selected waypoint path required')
    files={str(folder/'result.json'):sha256(folder/'result.json')}
    for name,key in [('request.json','request_sha256'),('routes.json','routes_sha256'),('lattice.npz','lattice_sha256')]:
        if sha256(folder/name)!=result[key]:raise ValueError('Waypoint path artifact changed')
        files[str(folder/name)]=result[key]
    request=read(folder/'request.json')
    if Path(request['source_plan']).resolve()!=Path(source_plan).resolve():raise ValueError('Path uses a different source plan')
    np.testing.assert_array_equal(request['window_s'],window)
    files.update(bind_inputs(required,request['inputs']))
    for name,digest in request['implementation'].items():
        path=(folder/'implementation'/name).resolve()
        if path.parent!=folder/'implementation' or sha256(path)!=digest:raise ValueError('Path snapshot changed')
        files[str(path)]=digest
    with np.load(folder/'lattice.npz',allow_pickle=False) as archive:data=dict(archive)
    np.testing.assert_array_equal(data['states'],request['states']);np.testing.assert_array_equal(data['times'],request['times_s'])
    axes=request['axes'];routes=read(folder/'routes.json')
    if [r['axis_name'] for r in routes]!=list(axes) or data['costs'].shape!=(len(axes),len(data['times']),len(data['states'])):
        raise ValueError('Complete ordered path population required')
    feasible=[]
    for index,route in enumerate(routes):
        np.testing.assert_array_equal(route['axis'],axes[route['axis_name']])
        parameters,report=shortest_path(data['times'],data['states'],data['costs'][index],request['guide_rate_limits'],request['transition_weight'])
        if report!=route['solver']:raise ValueError('Independent path replay differs')
        if parameters is None:
            if route['parameters'] is not None:raise ValueError('Infeasible path has controls')
        else:
            np.testing.assert_array_equal(parameters,route['parameters']);feasible.append(route)
    if not feasible:raise ValueError('No independently feasible path')
    selected=min(feasible,key=lambda r:(r['solver']['total_cost'],r['axis_name']))
    if selected['axis_name']!=result['selected']:raise ValueError('Selected path is not the declared optimum')
    axis=np.asarray(selected['axis'],float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1)>1e-12:raise ValueError('Finite unit route axis required')
    guide=LinearGuide(data['times'],selected['parameters'],request['guide_rate_limits'])
    mode=request.get('clock_mode','uniform_with_failure_times')
    if mode=='native_shared':
        from native_waypoint_clock import guide_clock
        if native_clocks is None or protected is None:raise ValueError('Bound native clocks and guards required')
        np.testing.assert_array_equal(guide.times,guide_clock(native_clocks,window,protected))
    elif mode=='uniform_with_failure_times':
        if not np.array_equal(guide.times[[0,-1]],np.asarray(window)[[0,-1]]):raise ValueError('Guide window differs')
    else:raise ValueError('Unknown waypoint clock mode')
    return guide,axis,selected,files
