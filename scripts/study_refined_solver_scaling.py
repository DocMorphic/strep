"""Retry a bound refined system with equivalent physical objective scaling."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_proposal import solve
from diagnose_scene_pair_limits import constraint_population,original_checks


def objective_scalings():
    # min peak/scale + regularizer*||step/trust||^2 has the same physical
    # objective after multiplying through by scale, when scale*regularizer is fixed.
    original_scale,original_regularizer=.005,1e-4
    return [dict(name=name,scale=scale,regularizer=original_scale*original_regularizer/scale)
        for name,scale in [('smaller_distance_scale',.001),('larger_distance_scale',.025)]]


def run(refinement,output):
    refinement,output=Path(refinement).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh solver scaling study required')
    parent,result=read(refinement/'request.json'),read(refinement/'result.json')
    if result['status']!='complete':raise ValueError('Completed refined system required')
    files={str(refinement/'result.json'):sha256(refinement/'result.json')}
    for name in ['request.json','solver.json','linearization.npz']:
        digest=result[name.split('.')[0]+'_sha256']
        if sha256(refinement/name)!=digest:raise ValueError('Refined evidence changed')
        files[str(refinement/name)]=digest
    for path,digest in parent['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Original input changed')
        files[path]=digest
    for name,digest in parent['implementation'].items():
        path=refinement/'implementation'/name
        if sha256(path)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Refined method changed')
        files[str(path)]=digest
    source_request=Path(parent['study'])/'request.json'
    if files.get(str(source_request))!=sha256(source_request):raise ValueError('Original trust policy unbound')
    original=read(source_request);trust=np.deg2rad(original['trust_degrees'])
    with np.load(refinement/'linearization.npz') as f:linear=dict(f)
    population=constraint_population(linear);output.mkdir();summaries=[]
    for setting in objective_scalings():
        folder=output/setting['name'];folder.mkdir();(folder/'implementation').mkdir()
        methods={}
        for name in sorted(set(parent['implementation'])|{'study_refined_solver_scaling.py'}):
            shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name);methods[name]=sha256(folder/'implementation'/name)
        shutil.copyfile(refinement/'linearization.npz',folder/'linearization.npz')
        protocol=dict(parent,at=now(),inputs=files,implementation=methods,parent_refinement=str(refinement),solver_scaling=setting,
            scope='Identical saved refined matrices, physical objective, motion limits, surface caps, edit budget and trust. Only numerical distance scaling changes. No exported animation or approval.')
        save(folder/'request.json',protocol)
        step,solver=solve(**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},
            **{k:population[k] for k in ['vectors','jacobians','radii']},trust=trust,
            scale=setting['scale'],regularizer=setting['regularizer'],norm_tolerances=population['tolerances'])
        save(folder/'solver.json',dict(solver=solver,step=None if step is None else step.tolist(),
            original_checks=None if step is None else original_checks(linear,population,step,trust),parent_solver_sha256=sha256(refinement/'solver.json')))
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Scaling evidence changed during solve')
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Scaling method changed during solve')
        save(folder/'result.json',dict(at=now(),status='complete',request_sha256=sha256(folder/'request.json'),
            solver_sha256=sha256(folder/'solver.json'),linearization_sha256=sha256(folder/'linearization.npz'),
            original_controls=result['original_controls'],refined_controls=result['refined_controls'],quality_approved=False))
        summaries.append(dict(**setting,proposal_available=step is not None,solver=solver,result_sha256=sha256(folder/'result.json')))
        save(output/'variants.json',summaries);print(dict(name=setting['name'],proposed=step is not None,**solver),flush=True)
    save(output/'result.json',dict(at=now(),status='complete',variants_sha256=sha256(output/'variants.json'),quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('refinement',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.refinement,a.output)
