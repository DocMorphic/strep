"""Measure refined constraint restrictions without changing animation acceptance."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from bound_evidence import bind_inputs
from diagnose_scene_pair_limits import load_bound_study,constraint_population,original_checks
from coupled_pair_reserve import tightened_radii
from coupled_pair_proposal import solve,check_step


VARIANTS=['original','planes_only','distances_only','global_peak_only']
MOTION_VARIANTS=['original','without_positional','without_angular','without_motion','edit_and_global_peak_only']


def surface_variant(linear,population,name):
    if name not in VARIANTS:raise ValueError('Explicit surface diagnostic required')
    retain_distance=name in ['original','distances_only']
    retain_planes=name in ['original','planes_only']
    mask=np.ones(len(population['radii']),bool) if retain_distance else population['kinds']!='surface_distance'
    caps=linear['depth_caps'].copy() if retain_planes else np.full_like(linear['depth_caps'],np.maximum(-linear['gaps'],0).max())
    selected={k:population[k][mask] for k in ['vectors','jacobians','radii','tolerances']}
    return caps,selected


def motion_variant(linear,population,name):
    if name not in MOTION_VARIANTS:raise ValueError('Explicit motion diagnostic required')
    positional=['speed','acceleration'];angular=['angular_speed','angular_acceleration']
    omitted={'original':[], 'without_positional':positional, 'without_angular':angular,
        'without_motion':positional+angular, 'edit_and_global_peak_only':positional+angular+['surface_distance']}[name]
    mask=~np.isin(population['kinds'],omitted)
    caps=linear['depth_caps'].copy()
    if name=='edit_and_global_peak_only':caps[:]=np.maximum(-linear['gaps'],0).max()
    return caps,{k:population[k][mask] for k in ['vectors','jacobians','radii','tolerances']}


def verify_reference(step,linear,population,trust):
    step=np.asarray(step,float)
    if step.shape!=(linear['gap_jacobian'].shape[1],) or not np.isfinite(step).all():raise ValueError('Matching finite reference controls required')
    checks=check_step(step,**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},
        **{k:population[k] for k in ['vectors','jacobians','radii']},trust=trust)
    norms=np.linalg.norm(population['vectors']+np.einsum('nid,d->ni',population['jacobians'],step),axis=1)
    if checks['per_frame_cap_excess_m']>1e-8 or checks['trust_excess_radians']>1e-8 or np.any(norms-population['radii']>population['tolerances']):
        raise ValueError('Saved reference fails declared hard conditions')
    return step


def run(parent,output,variant,profile='surface'):
    if profile not in ['surface','motion']:raise ValueError('Explicit diagnostic profile required')
    parent,output=Path(parent).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh surface diagnosis required')
    request,result=read(parent/'request.json'),read(parent/'result.json')
    if result['status']!='complete':raise ValueError('Completed trust diagnosis required')
    files={str(parent/'result.json'):sha256(parent/'result.json')}
    for name in ['request','variants']:
        path=parent/(name+'.json')
        if sha256(path)!=result[name+'_sha256']:raise ValueError('Trust diagnostic changed')
        files[str(path)]=sha256(path)
    for name,digest in request['implementation'].items():
        path=parent/'implementation'/name
        if sha256(path)!=digest:raise ValueError('Trust method snapshot changed')
        files[str(path)]=digest
    matches=[r for r in read(parent/'variants.json') if r['setting']['name']==variant]
    if len(matches)!=1 or matches[0]['step'] is None or matches[0]['solver']['proposal_hard_checks'] is not True:
        raise ValueError('One passing affine reference required')
    reference=matches[0];setting=reference['setting'];trust=np.deg2rad(setting['trust_degrees'])
    study=Path(request['study']);original,linear,required=load_bound_study(study)
    files.update(bind_inputs(required,request['inputs']))
    margin_path=study/'margins.npz'
    if files.get(str(margin_path))!=read(study/'result.json')['margins_sha256']:raise ValueError('Bound reserve margins required')
    with np.load(margin_path,allow_pickle=False) as archive:margins=dict(archive)
    np.testing.assert_array_equal(margins['original_radii'],linear['radii']);np.testing.assert_array_equal(margins['kinds'],linear['kinds'])
    radii=tightened_radii(linear['radii'],margins['reserve'],linear['kinds'])
    np.testing.assert_array_equal(radii,margins['tightened_radii'])
    population=constraint_population(dict(linear,radii=radii));original_population=constraint_population(linear)
    saved_step=verify_reference(reference['step'],linear,population,trust)
    names=VARIANTS if profile=='surface' else MOTION_VARIANTS
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in ['study_refined_surface_limits.py','bound_evidence.py','diagnose_scene_pair_limits.py','coupled_pair_reserve.py','coupled_pair_proposal.py','conic_root_descent.py','strep.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),parent=str(parent),variant=variant,study=str(study),setting=setting,
        inputs=files,implementation=methods,profile=profile,variants=names,
        scope='Affine diagnostic only. Native edit budget, controls and protected-key layout unchanged. Every omitted condition remains required under the existing animation acceptance policy. Motion profile rechecks and reuses the bound passing baseline; its final variant also omits local surface restrictions. No export, full-mesh result or publication.',quality_approved=False))
    records=[]
    for name in names:
        caps,selected=(surface_variant if profile=='surface' else motion_variant)(linear,population,name)
        reused=profile=='motion' and name=='original'
        if reused:step,solver=saved_step,reference['solver']
        else:
            step,solver=solve(gaps=linear['gaps'],gap_jacobian=linear['gap_jacobian'],depth_caps=caps,
                **{k:selected[k] for k in ['vectors','jacobians','radii']},norm_tolerances=selected['tolerances'],
                trust=trust,scale=setting['scale'],regularizer=setting['regularizer'])
        row=dict(name=name,solver=solver,step=None if step is None else step.tolist(),
            reference_reused=reused,original_checks=None if step is None else original_checks(linear,original_population,step,trust),quality_approved=False)
        if name=='original' and step is not None:
            np.testing.assert_allclose(step,reference['step'],atol=1e-9,rtol=0)
            row['baseline_maximum_control_difference']=float(np.abs(step-reference['step']).max())
        records.append(row);save(output/'variants.json',records)
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Diagnostic input changed')
        for file,digest in methods.items():
            if sha256(ROOT/'scripts'/file)!=digest:raise ValueError('Diagnostic method changed')
        print(dict(name=name,proposal=step is not None,**solver),flush=True)
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),
        variants_sha256=sha256(output/'variants.json'),exported=False,quality_approved=False))


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--variant',required=True);parser.add_argument('--profile',choices=['surface','motion'],default='surface');args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.parent,args.output,args.variant,args.profile)
