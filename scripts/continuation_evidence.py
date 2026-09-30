"""Validate completed continuation evidence without accepting its animation."""
from pathlib import Path
import numpy as np
from strep import read, sha256


def cumulative_controls(request, solver, trial):
    base=np.asarray(request['cumulative_controls'],float)
    step=np.asarray(solver['increment'],float)
    controls=np.asarray(trial['controls'],float)
    factor=trial['factor']
    if base.ndim!=1 or not len(base) or len(base)%3 or step.shape!=base.shape or controls.shape!=base.shape:
        raise ValueError('Matching cumulative control triples required')
    if not all(np.isfinite(v).all() for v in [base,step,controls]) or type(factor) not in [int,float] or not np.isfinite(factor) or not 0<factor<=1:
        raise ValueError('Finite controls and a positive bounded step fraction required')
    if solver['solver']['proposal_hard_checks'] is not True:
        raise ValueError('Declared incremental proposal failed its hard checks')
    np.testing.assert_array_equal(controls,base+factor*step)
    return controls


def load_continuation(folder):
    folder=Path(folder).resolve(); result=read(folder/'result.json')
    if result['status']!='complete': raise ValueError('Completed continuation required')
    files={str(folder/'result.json'):sha256(folder/'result.json')}
    def bind(path,digest):
        if sha256(path)!=digest: raise ValueError('Continuation evidence changed: '+str(path))
        files[str(path)]=digest
    for name in ['request.json','current-index.json','linearization.npz','solver.json']:
        key=name.split('.')[0].replace('-','_')+'_sha256'
        bind(folder/name,result[key])
    request=read(folder/'request.json');solver=read(folder/'solver.json')
    for path,digest in request['inputs'].items(): bind(Path(path),digest)
    for name,digest in request['implementation'].items():
        path=(folder/'implementation'/name).resolve()
        if path.parent!=folder/'implementation': raise ValueError('Snapshot path escapes evidence')
        bind(path,digest)
    for name,digest in read(folder/'current-index.json').items():
        path=(folder/'current'/name).resolve()
        if path.parent!=folder/'current': raise ValueError('Witness path escapes evidence')
        bind(path,digest)
    trials=[]
    if result['trials_sha256'] is not None:
        bind(folder/'trials.json',result['trials_sha256']);trials=read(folder/'trials.json')
        if not trials: raise ValueError('Nonempty declared continuation trials required')
    elif solver['increment'] is not None:
        raise ValueError('Proposed continuation is missing decoded trials')
    factors=[]
    for index,trial in enumerate(trials):
        cumulative_controls(request,solver,trial); factors.append(trial['factor'])
        directory=folder/f'trial-{index}';review=directory/'review.json'
        if read(review)!=trial: raise ValueError('Continuation trial record differs')
        files[str(review)]=sha256(review)
        names=[a['actor'] for a in trial['actors']]
        if len(names)!=2 or len(set(names))!=2 or [a['actor'] for a in trial['angular_rates']]!=names:
            raise ValueError('Two distinct ordered actor reviews required')
        for actor in trial['actors']:
            path=(directory/actor['path']).resolve()
            if path.parent!=directory: raise ValueError('Clip path escapes continuation trial')
            bind(path,actor['sha256'])
    if len(set(factors))!=len(factors): raise ValueError('Distinct continuation fractions required')
    return request,solver,trials,files
