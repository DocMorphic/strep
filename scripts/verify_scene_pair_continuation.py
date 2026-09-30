"""Independently replay every cumulative continuation export, including failures."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from continuation_evidence import load_continuation


def run(study,output):
    from diagnose_scene_pair_limits import load_bound_study
    from bound_evidence import bind_inputs
    from scene_pair_problem import load_actors
    from refined_reserve_inputs import install_refined_models
    from verify_scene_pair_fit import rate_check,trial_controls
    from study_scene_pair_fit import exported_motion
    from scene_pair_relinearization import refreshed_problem
    from scalar_angular_replay import angular_replay,compare_saved
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists(): raise ValueError('Fresh continuation replay required')
    request,solver,trials,files=load_continuation(study)
    parent=Path(request['study']).resolve(); original,_,required=load_bound_study(parent)
    bind_inputs(required,request['inputs']);files.update(required)
    _,actors=load_actors(Path(original['prepared_request']).parent)
    original_models=[a['model'] for a in actors]
    install_refined_models(actors,original['curve_actors'])
    samples=[read(parent/'source'/name) for name in read(parent/'source-index.json')]
    current=[read(study/'current'/name) for name in read(study/'current-index.json')]
    problem,refreshed=refreshed_problem(actors,samples,current)
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'verify_scene_pair_continuation.py','continuation_evidence.py','verify_scene_pair_fit.py','scalar_angular_replay.py'}
    for name in sorted(names):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,
        scope='Exact cumulative export reconstruction, all-joint original-bin positional and independent scalar angular replay of every attempted trial. No fresh decoded full-mesh, engine, visual or release approval.',quality_approved=False))
    reviews=[]
    for index,trial in enumerate(trials):
        controls=trial_controls(trial,actors)
        records,worlds,bounds=exported_motion(problem,controls,output/f'trial-{index}')
        if records!=trial['actors'] or bounds!=trial['bounds']:
            raise ValueError('Reconstructed export or original surface report differs')
        surfaces=refreshed.surface_rows(worlds)
        excess=float(np.maximum(-surfaces['gaps']-surfaces['depth_caps'],0).max(initial=0))
        if excess!=trial['refreshed_plane_excess_m']: raise ValueError('Refreshed plane report differs')
        rows=[]
        for actor,old,world,saved,angular in zip(actors,original_models,worlds,records,trial['angular_rates']):
            joints=actor['rig'].joints
            positions=lambda w: w[:,joints,:,:][:,:,:3,3]@actor['rotation'].T+actor['translation']
            positional=rate_check(positions(old.source_world),positions(world),old.times,old.knots)
            if positional['failures']!=saved['rate_failures']: raise ValueError('Independent positional failure count differs')
            rotations=lambda w:w[:,joints,:,:][:,:,:3,:3]
            rates=angular_replay(rotations(old.source_world),rotations(world),old.times,old.knots)
            compare_saved(rates,angular['rates'])
            rows.append(dict(actor=actor['name'],exact_export_reconstruction=True,positional=positional,angular=rates))
        reasons=[]
        if any(r['positional']['failures'] for r in rows): reasons.append('exported_motion')
        if any(not r['preserved'] for r in records): reasons.append('preservation_or_budget')
        if max(bounds.values())>1e-6: reasons.append('original_surface_bounds')
        if any(v['exceeding_observations'] for r in rows for v in r['angular'].values()): reasons.append('exported_angular_motion')
        if excess>1e-6: reasons.append('refreshed_surface_planes')
        if reasons!=trial['reasons'] or trial['preliminary_pass']!=(not reasons): raise ValueError('Preliminary continuation classification differs')
        reviews.append(dict(trial=index,factor=trial['factor'],actors=rows,reasons=reasons,preliminary_pass=not reasons))
        save(output/'reviews.json',reviews);print(dict(trial=index,reasons=reasons),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest: raise ValueError('Continuation replay input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest: raise ValueError('Continuation replay method changed')
    save(output/'verification.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),
        reviews_sha256=sha256(output/'reviews.json') if reviews else None,reconstructed_exports=2*len(reviews),
        positional_observations=sum(r['positional']['checked'] for t in reviews for r in t['actors']),
        preliminary_passes=sum(r['preliminary_pass'] for r in reviews),accepted_for_publication=False,quality_approved=False))
    print(read(output/'verification.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1): run(a.study,a.output)
