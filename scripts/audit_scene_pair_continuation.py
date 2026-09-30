"""Full decoded mesh and engine audit for an independently replayed continuation."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from continuation_evidence import load_continuation,parent_trial
from bound_evidence import bind_inputs


def improvement_reasons(geometry,previous_peak):
    values=[geometry[k] for k in ['candidate_peak_m','maximum_cap_excess_m','maximum_floor_increase_m']]+[previous_peak]
    if not np.isfinite(values).all() or min(values[0],previous_peak)<0:
        raise ValueError('Finite nonnegative measured peak depths required')
    reasons=[]
    if geometry['maximum_cap_excess_m']>1e-6:reasons.append('fresh_surface_caps')
    if geometry['maximum_floor_increase_m']>1e-6:reasons.append('floor_regression')
    if previous_peak-geometry['candidate_peak_m']<1e-6:reasons.append('no_improvement_over_previous_correction')
    return reasons


def reviewed_trial(study,replay,index):
    if type(index) is not int or index<0:raise ValueError('Nonnegative trial index required')
    study,replay=Path(study).resolve(),Path(replay).resolve()
    request,_,trials,files=load_continuation(study);parent=parent_trial(request)
    if index>=len(trials):raise ValueError('Trial outside completed continuation')
    result=read(replay/'verification.json');protocol=read(replay/'request.json')
    if result['status']!='complete' or Path(protocol['study']).resolve()!=study:
        raise ValueError('Completed replay of this continuation required')
    for name,key in [('request.json','request_sha256'),('reviews.json','reviews_sha256')]:
        if sha256(replay/name)!=result[key]:raise ValueError('Replay evidence changed')
    files.update(bind_inputs(files,protocol['inputs']))
    for name,digest in protocol['implementation'].items():
        path=(replay/'implementation'/name).resolve()
        if path.parent!=replay/'implementation' or sha256(path)!=digest:raise ValueError('Replay method snapshot changed')
        files[str(path)]=digest
    for name in ['request.json','reviews.json','verification.json']:files[str(replay/name)]=sha256(replay/name)
    reviews=read(replay/'reviews.json')
    if len(reviews)!=len(trials) or [r['trial'] for r in reviews]!=list(range(len(trials))):
        raise ValueError('Complete ordered replay population required')
    trial,review=trials[index],reviews[index]
    if trial['preliminary_pass'] is not True or trial['reasons'] or review['preliminary_pass'] is not True or review['reasons'] or review['factor']!=trial['factor']:
        raise ValueError('Only an independently passing preliminary trial can enter full geometry')
    if [a['actor'] for a in review['actors']]!=[a['actor'] for a in trial['actors']]:
        raise ValueError('Replay actors differ')
    for actor in review['actors']:
        if actor['exact_export_reconstruction'] is not True or actor['positional']['failures']!=0:
            raise ValueError('Exact reconstructed exports with passing motion required')
        if set(actor['angular'])!={'angular_speed_rad_s','angular_acceleration_rad_s2'} or any(v['exceeding_observations']!=0 or v['tolerance']!=1e-5 for v in actor['angular'].values()):
            raise ValueError('Passing independent angular replay required')
    return request,trial,parent,files


def run(study,replay,index,output):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors,ScenePairProblem
    from refined_reserve_inputs import install_refined_models
    from study_scene_pair_fit import exported_motion,exported_geometry
    from rig_clip_import import AnimationSampler
    from run_godot_rig_import import run as engine_run
    study,replay,output=[Path(p).resolve() for p in [study,replay,output]]
    if output.exists():raise ValueError('Fresh continuation geometry audit required')
    request,trial,baseline,files=reviewed_trial(study,replay,index)
    parent=Path(request['study']);original,_,required=load_bound_study(parent)
    bind_inputs(required,request['inputs']);files.update(required)
    geometry_path=(parent/baseline['folder']/'geometry.json').resolve()
    if not geometry_path.is_relative_to(parent) or sha256(geometry_path)!=baseline['geometry']['geometry_sha256']:
        raise ValueError('Previous full-mesh geometry changed')
    files[str(geometry_path)]=sha256(geometry_path)
    previous=read(geometry_path)
    samples=[read(parent/'source'/n) for n in read(parent/'source-index.json')]
    if [(s['sample'],s['time_s']) for s in previous]!=[(s['sample'],s['time_s']) for s in samples]:
        raise ValueError('Previous mesh clock differs')
    previous_peak=max(r['candidate_depth_m'] for r in previous)
    if previous_peak!=baseline['geometry']['candidate_peak_m']:raise ValueError('Previous geometry peak differs')
    _,actors=load_actors(Path(original['prepared_request']).parent)
    if [a['name'] for a in actors]!=[a['actor'] for a in trial['actors']]:raise ValueError('Actor order differs')
    install_refined_models(actors,original['curve_actors']);problem=ScenePairProblem(actors,samples)
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'audit_scene_pair_continuation.py','continuation_evidence.py',
        'run_godot_rig_import.py','godot_import_audit.gd'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    records,worlds,bounds=exported_motion(problem,trial['controls'],output/'reconstruction')
    if records!=trial['actors'] or bounds!=trial['bounds']:raise ValueError('Audited clips do not reconstruct exactly')
    cases=[]
    for i,actor in enumerate(actors):
        sampler=AnimationSampler(actor['model'].document,actor['model'].binary,0)
        for label,source in [('input',actor['source']),('candidate',output/'reconstruction'/f'actor-{i}.glb')]:
            target=output/f'{label}-actor-{i}.glb';shutil.copyfile(source,target)
            cases.append(dict(id=label+'-'+actor['name'],path=target.name,sha256=sha256(target),frames=int(round(sampler.duration*30))+1,fps=30,sample_by_time=True))
    save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    save(output/'request.json',dict(at=now(),study=str(study),replay=str(replay),trial_index=index,inputs=files,
        implementation=methods,manifest_sha256=sha256(output/'manifest.json'),previous_peak_m=previous_peak,
        scope='Exact decoded reconstruction, native engine import and full local-clock vertex-depth/floor audit. Requires improvement over the previous correction with unchanged original per-time caps. No continuous collision, human or release approval.',quality_approved=False))
    save(output/'pipeline.json',dict(status='processing',stage='Checking engine import'))
    engine_run(output,output/'engine')
    save(output/'pipeline.json',dict(status='processing',stage='Checking full decoded meshes',total=len(samples)))
    geometry=exported_geometry(problem,worlds,output);reasons=improvement_reasons(geometry,previous_peak)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Continuation audit input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Continuation audit method changed')
    save(output/'result.json',dict(at=now(),status='complete',geometry=geometry,previous_peak_m=previous_peak,
        improvement_over_previous_m=previous_peak-geometry['candidate_peak_m'],reasons=reasons,accepted_local_step=not reasons,
        request_sha256=sha256(output/'request.json'),manifest_sha256=sha256(output/'manifest.json'),
        engine_verification_sha256=sha256(output/'engine/verification.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',accepted_local_step=not reasons));print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('replay',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--trial',type=int,required=True);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.study,a.replay,a.trial,a.output)
