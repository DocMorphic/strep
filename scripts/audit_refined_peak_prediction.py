"""Compare a rejected diagnostic proposal with fresh geometry at the source peak."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now


def selected(parent,name):
    parent=Path(parent).resolve();result=read(parent/'result.json');request=read(parent/'request.json')
    if result['status']!='complete':raise ValueError('Completed diagnostic required')
    files={str(parent/'result.json'):sha256(parent/'result.json')}
    for artifact in ['request','variants']:
        path=parent/(artifact+'.json')
        if sha256(path)!=result[artifact+'_sha256']:raise ValueError('Diagnostic evidence changed')
        files[str(path)]=sha256(path)
    rows=[r for r in read(parent/'variants.json') if r['name']==name]
    if len(rows)!=1 or rows[0]['step'] is None or rows[0]['solver']['proposal_hard_checks'] is not True:
        raise ValueError('One finite proposal passing its declared diagnostic subset required')
    step=np.asarray(rows[0]['step'],float)
    if step.ndim!=1 or not len(step) or len(step)%3 or not np.isfinite(step).all():raise ValueError('Finite control triples required')
    return request,rows[0],files


def run(parent,output,name):
    from bound_evidence import bind_inputs
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors,ScenePairProblem
    from refined_reserve_inputs import install_refined_models
    from study_scene_pair_fit import exported_motion,METHODS
    from joint_angular_rates import compare_angular_rates
    from convex_partner_surface import penetration
    parent,output=Path(parent).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh peak diagnostic required')
    request,trial,files=selected(parent,name);study=Path(request['study'])
    original,linear,required=load_bound_study(study);files.update(bind_inputs(required,request['inputs']))
    for file,digest in request['implementation'].items():
        path=parent/'implementation'/file
        if sha256(path)!=digest:raise ValueError('Diagnostic snapshot changed')
        files[str(path)]=digest
    _,actors=load_actors(Path(original['prepared_request']).parent)
    original_knots=[a['model'].knots.copy() for a in actors]
    install_refined_models(actors,original['curve_actors'])
    samples=[read(study/'source'/n) for n in read(study/'source-index.json')]
    problem=ScenePairProblem(actors,samples);step=np.asarray(trial['step']);problem.split(step)
    sample=max(samples,key=lambda r:max(d['maximum_depth_m'] for d in r['directions']));index=sample['sample']
    output.mkdir();(output/'implementation').mkdir();methods={}
    for file in sorted(set(METHODS)|{'audit_refined_peak_prediction.py','refined_reserve_inputs.py','bound_evidence.py','diagnose_scene_pair_limits.py','diagnose_scene_pair_refinement.py','verify_scene_pair_fit.py'}):
        shutil.copyfile(ROOT/'scripts'/file,output/'implementation'/file);methods[file]=sha256(output/'implementation'/file)
    save(output/'request.json',dict(at=now(),parent=str(parent),variant=name,inputs=files,implementation=methods,
        sample=index,time_s=sample['time_s'],controls=step.tolist(),
        scope='Diagnostic export and fresh full-mesh queries at the single deepest source time. Rejected original-motion/surface conditions stay visible. No full-timeline geometry or engine check, publication or quality approval.',quality_approved=False))
    records,worlds,bound=exported_motion(problem,step,output/'diagnostic-export')
    angular=[]
    for actor,world,knots in zip(actors,worlds,original_knots):
        joints=actor['rig'].joints;model=actor['model']
        names=[actor['rig'].document['nodes'][j]['name'] for j in joints]
        angular.append(dict(actor=actor['name'],rates=compare_angular_rates(model.source_world[:,joints][:,:,:3,:3],
            world[:,joints][:,:,:3,:3],model.times,knots,names,speed_tolerance=1e-5,acceleration_tolerance=1e-5)))
    surface=problem.surface_rows(worlds);mask=np.concatenate([g['frames']==index for g in problem.groups])
    predicted=linear['gaps']+linear['gap_jacobian']@step
    before=dict(actors=records,bound=bound,angular=angular,
        affine_peak_at_sample_m=float(np.maximum(-predicted[mask],0).max()),
        decoded_fixed_witness_peak_at_sample_m=float(np.maximum(-surface['gaps'][mask],0).max()))
    save(output/'decoded.json',before);print(dict(phase='decoded',positional_failures=[r['rate_failures'] for r in records],**bound),flush=True)
    points=[a['rig'].vertices(w[index])@a['rotation'].T+a['translation'] for a,w in zip(actors,worlds)]
    directions=[]
    for s,t in [(0,1),(1,0)]:
        directions.append(dict(source=s,target=t,**penetration(points[s],points[t],actors[t]['faces'])))
        save(output/'geometry.json',directions);print(dict(phase='geometry',directions=len(directions)),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Peak audit input changed')
    for file,digest in methods.items():
        if sha256(ROOT/'scripts'/file)!=digest:raise ValueError('Peak audit method changed')
    save(output/'result.json',dict(at=now(),status='complete',sample=index,time_s=sample['time_s'],
        source_peak_m=max(d['maximum_depth_m'] for d in sample['directions']),fresh_peak_m=max(d['max_depth_m'] for d in directions),
        affine_peak_at_sample_m=before['affine_peak_at_sample_m'],decoded_fixed_witness_peak_at_sample_m=before['decoded_fixed_witness_peak_at_sample_m'],
        request_sha256=sha256(output/'request.json'),decoded_sha256=sha256(output/'decoded.json'),geometry_sha256=sha256(output/'geometry.json'),
        full_timeline_geometry_checked=False,accepted_for_publication=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--variant',required=True);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.parent,args.output,args.variant)
