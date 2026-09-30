"""Load cumulative controls without rebasing the original edit/cap reference."""
from pathlib import Path
import numpy as np
from strep import read,sha256


def checkpoint(folder):
    folder=Path(folder).resolve();request=read(folder/'request.json');result=read(folder/'result.json')
    if result['status']!='complete' or result['selected'] is None or result['request_sha256']!=sha256(folder/'request.json'):
        raise ValueError('Completed bound checkpoint required')
    inputs={**request['inputs'],str(folder/'request.json'):sha256(folder/'request.json'),str(folder/'result.json'):sha256(folder/'result.json')}
    if 'total_controls' in result:
        origin=Path(request.get('origin',request['start'])).resolve()
        controls=np.asarray(result['total_controls'],float);reserve=Path(request['reserve']).resolve()
    else:
        origin=folder;solver=read(folder/'solver.json')
        if result['solver_sha256']!=sha256(folder/'solver.json'):raise ValueError('Starting solver changed')
        controls=np.asarray(solver['controls'],float)*result['selected']['factor'];reserve=Path(request['fitting_reserve']).resolve()
        inputs[str(folder/'solver.json')]=sha256(folder/'solver.json')
    op,orr,os=read(origin/'request.json'),read(origin/'result.json'),read(origin/'solver.json')
    if not op.get('penetrating_surface_norms') or orr['status']!='complete' or orr['request_sha256']!=sha256(origin/'request.json') or orr['solver_sha256']!=sha256(origin/'solver.json') or os['linearization_sha256']!=sha256(origin/'linearization.npz'):
        raise ValueError('Unchanged original full-vector reference required')
    if controls.ndim!=1 or not len(controls) or not np.isfinite(controls).all():raise ValueError('Finite cumulative controls required')
    for name in ['request.json','result.json','solver.json','linearization.npz']:inputs[str(origin/name)]=sha256(origin/name)
    inputs.update(op['inputs'])
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Checkpoint input changed')
    return dict(request=request,result=result,origin=origin,controls=controls,reserve=reserve,inputs=inputs)
