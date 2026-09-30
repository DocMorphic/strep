"""Separate trust-radius and regularization effects in a bound refined proposal."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from diagnose_scene_pair_limits import load_bound_study,constraint_population,original_checks
from coupled_pair_reserve import tightened_radii
from coupled_pair_proposal import solve


def variants(base_degrees,budget_degrees,scale,regularizer):
    values=np.asarray([base_degrees,budget_degrees,scale,regularizer],float)
    if not np.isfinite(values).all() or min(values)<=0 or base_degrees>budget_degrees:
        raise ValueError('Positive finite trust, budget and objective settings required')
    output=[];seen=set()
    for multiplier in [1.,5.,10.,50.]:
        degrees=min(base_degrees*multiplier,budget_degrees)
        if degrees in seen:continue
        seen.add(degrees)
        for penalty,name in [(1.,'same_physical_penalty'),(1e-4,'weaker_penalty')]:
            # The objective in metres is peak + scale*regularizer/trust^2*||step||^2.
            # Increasing trust with an unchanged solver regularizer also weakens
            # the physical penalty; compensate to measure these effects separately.
            output.append(dict(name=f'trust_{degrees:g}_{name}',trust_degrees=degrees,scale=scale,
                regularizer=regularizer*(degrees/base_degrees)**2*penalty,penalty_multiplier=penalty))
    return output


def objective_terms(step,solver,setting):
    trust=np.deg2rad(setting['trust_degrees'])
    coefficient=setting['scale']*setting['regularizer']/trust**2
    penalty=coefficient*float(np.dot(step,step))
    return dict(physical_penalty_coefficient=coefficient,penalty_m=penalty,
        peak_m=solver['predicted_peak_m'],total_m=solver['predicted_peak_m']+penalty)


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh trust diagnostic required')
    request,linear,files=load_bound_study(study);result=read(study/'result.json')
    if not request.get('curve_actors') or not request.get('angular_motion'):
        raise ValueError('Completed angular refined reserve assembly required')
    margin_path=study/'margins.npz'
    if sha256(margin_path)!=result['margins_sha256']:raise ValueError('Proposal margins changed')
    files[str(margin_path)]=sha256(margin_path)
    with np.load(margin_path,allow_pickle=False) as archive:margins=dict(archive)
    np.testing.assert_array_equal(margins['kinds'],linear['kinds'])
    np.testing.assert_array_equal(margins['original_radii'],linear['radii'])
    radii=tightened_radii(linear['radii'],margins['reserve'],linear['kinds'])
    np.testing.assert_array_equal(radii,margins['tightened_radii'])
    parent=Path(request['assembly']['export_audit'])/'request.json'
    if files.get(str(parent))!=sha256(parent):raise ValueError('Parent objective is unbound')
    scaling=read(parent)['solver_scaling'];base=request['trust_degrees']
    prepared=Path(request['prepared_request'])
    if files.get(str(prepared))!=sha256(prepared):raise ValueError('Original edit budget is unbound')
    budget=read(prepared)['authored']['limit_degrees']
    settings=variants(base,budget,scaling['scale'],scaling['regularizer'])
    population=constraint_population(dict(linear,radii=radii));original_population=constraint_population(linear)
    output.mkdir();(output/'implementation').mkdir()
    methods={}
    for name in ['study_refined_trust_limits.py','diagnose_scene_pair_limits.py','coupled_pair_reserve.py','coupled_pair_proposal.py','conic_root_descent.py','strep.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,variants=settings,
        scope='Affine diagnosis only. Original source-relative motion/surface/edit caps, protected-key layout and empirical margins retained. Numerical trust and quadratic objective penalty varied explicitly. Larger trust is not nonlinear validity, clearance, or export approval.',quality_approved=False))
    records=[];saved_step=np.asarray(read(study/'solver.json')['step'])
    for i,setting in enumerate(settings):
        trust=np.deg2rad(setting['trust_degrees'])
        step,solver=solve(**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},
            **{k:population[k] for k in ['vectors','jacobians','radii']},trust=trust,scale=setting['scale'],
            regularizer=setting['regularizer'],norm_tolerances=population['tolerances'])
        row=dict(setting=setting,solver=solver,step=None if step is None else step.tolist(),quality_approved=False)
        if step is not None:
            row['objective']=objective_terms(step,solver,setting)
            row['original_checks']=original_checks(linear,original_population,step,np.deg2rad(base))
            if i==0:
                np.testing.assert_allclose(step,saved_step,atol=1e-9,rtol=0)
                row['baseline_maximum_control_difference']=float(np.abs(step-saved_step).max())
        records.append(row);save(output/'variants.json',records)
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Diagnostic evidence changed')
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Diagnostic method changed')
        print(dict(name=setting['name'],proposal=step is not None,**solver),flush=True)
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),
        variants_sha256=sha256(output/'variants.json'),exported=False,quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.study,args.output)
