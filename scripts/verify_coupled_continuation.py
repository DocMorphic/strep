"""Replay total-control history and independently check the retained final pair."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_problem import PairProblem
from coupled_continuation_policy import acceptance
from study_paired_guarded_temporal import decoded
from paired_temporal_neighbor import placed_joint_positions
from rig_asset import RigAsset
from verify_paired_stage_rates import verify_rates
from coupled_continuation_checkpoint import checkpoint


def run(study,witnesses,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous continuation review')
    request,result=read(study/'request.json'),read(study/'result.json');problem=PairProblem(witnesses)
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json'):raise ValueError('Completed bound continuation required')
    start=Path(request['start']);initial=read(study/'start-review.json');accepted=read(study/'accepted.json') if (study/'accepted.json').exists() else []
    state=checkpoint(start)
    with np.load(state['origin']/'linearization.npz',allow_pickle=False) as archive:original=dict(archive)
    inside=original['gaps']<0;caps=original['depth_caps'];normals=np.concatenate([g['normals'] for g in problem.groups])
    inputs={**request['inputs'],**problem.inputs}
    for name in ['request.json','result.json','start-review.json','manifest.json']:
        inputs[str(study/name)]=sha256(study/name)
    if accepted:inputs[str(study/'accepted.json')]=sha256(study/'accepted.json')
    controls=state['controls'].copy()
    previous=initial['surface']['peak_m'];accepted_count=0;trials_count=0;peak_values=initial['verified_peak_values'];decisions=[]
    for folder in sorted(study.glob('iteration-*')):
        solver=read(folder/'solver.json');inputs[str(folder/'solver.json')]=sha256(folder/'solver.json')
        inputs[str(folder/'linearization.npz')]=solver['linearization_sha256']
        np.testing.assert_array_equal(solver['base_controls'],controls)
        with np.load(folder/'linearization.npz',allow_pickle=False) as linear:
            for key in ['radii','kinds','depth_caps']:np.testing.assert_array_equal(linear[key],original[key])
        if solver['step'] is None:continue
        step=np.array(solver['step'])
        if np.rad2deg(np.linalg.norm(step.reshape(-1,3),axis=1)).max()>.2+1e-7:raise ValueError('Step trust radius exceeded')
        trials=read(folder/'trials.json');inputs[str(folder/'trials.json')]=sha256(folder/'trials.json')
        for index,trial in enumerate(trials):
            if trial['factor']!=request['line_factors'][index]:raise ValueError('Line search order changed')
            np.testing.assert_array_equal(trial['controls'],controls+step*trial['factor'])
            parent=Path(trial['actors'][0]['path']).parent
            vector_path=study/parent/'witness-vectors.npz';inputs[str(vector_path)]=trial['witness_vectors_sha256']
            with np.load(vector_path,allow_pickle=False) as archive:vectors=archive['vectors']
            distances=np.linalg.norm(vectors,axis=1);gaps=np.sum(vectors*normals,axis=1)
            peak=float(distances[inside].max());cap_excess=float(max(0.,np.r_[distances[inside]-caps[inside],-gaps-caps].max()))
            np.testing.assert_allclose([peak,cap_excess],[trial['surface']['peak_m'],trial['surface']['maximum_cap_excess_m']],atol=1e-12,rtol=0)
            decision=acceptance(previous,peak,cap_excess,[a['rate_failures'] for a in trial['actors']],
                [a['maximum_original_edit_degrees'] for a in trial['actors']],[a['preservation']['original_finger_limits_passed'] for a in trial['actors']])
            if decision!=trial['decision']:raise ValueError('Acceptance decision differs')
            for actor in trial['actors']:
                inputs[str(study/actor['path'])]=actor['sha256']
                inputs[str(study/parent/(actor['actor']+'-rates.json'))]=actor['rates_sha256']
            trials_count+=1;peak_values+=trial['verified_peak_values'];decisions.append(dict(iteration=trial['iteration'],factor=trial['factor'],**decision))
            if decision['accepted']:
                if index!=len(trials)-1 or trial!=accepted[accepted_count]:raise ValueError('Accepted history order differs')
                controls=np.array(trial['controls']);previous=peak;accepted_count+=1
        if trials and not trials[-1]['decision']['accepted'] and folder!=sorted(study.glob('iteration-*'))[-1]:raise ValueError('Continued after exhausted line search')
    if accepted_count!=result['accepted_steps'] or trials_count!=result['trial_count'] or peak_values!=result['verified_peak_values']:raise ValueError('Population count differs')
    np.testing.assert_array_equal(controls,result['total_controls']);np.testing.assert_allclose(previous,result['final_retained_peak_m'],atol=1e-12,rtol=0)
    if result['selected']!=(accepted[-1] if accepted else initial):raise ValueError('Final selection differs')
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Review input changed')
    output.mkdir();shutil.copyfile(__file__,output/'implementation.py');reconstructed=output/'reconstructed';reconstructed.mkdir()
    worlds=[];rigs=[];motion_count=0;motion_error=0.
    for actor,part,selected in zip(problem.actors,np.split(controls,[problem.sizes[0]]),result['selected']['actors']):
        file=study/'candidate'/(actor['name']+'.glb');inputs[str(file)]=selected['sha256']
        actor['model'].export(part,reconstructed/file.name)
        if sha256(file)!=selected['sha256'] or sha256(reconstructed/file.name)!=selected['sha256']:raise ValueError('Total controls do not reproduce final GLB')
        original_doc,source_world=decoded(actor['source']);doc,world=decoded(file);worlds.append(world);rigs.append(RigAsset.load(file))
        names=[doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
        source=placed_joint_positions(source_world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
        candidate=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
        path=study/Path(selected['path']).parent/(actor['name']+'-rates.json');rates=read(path)
        count,error=verify_rates(source,candidate,rates,names);motion_count+=count;motion_error=max(motion_error,error)
        for metric in ['speed','acceleration']:
            for window in rates[metric]['windows']:
                if any(row['change']>1e-5 for row in window['joints']):raise ValueError('Final exported joint rate fails')
    records=[row for group in problem.groups for row in group['rows']];values=np.empty((len(records),3))
    by_time={frame:[] for frame in problem.request['frames']}
    for index,row in enumerate(records):by_time[row['frame']].append((index,row))
    for frame,rows in by_time.items():
        points=[rig.vertices(world[int(round(frame*4))])@actor['rotation'].T+actor['translation'] for rig,world,actor in zip(rigs,worlds,problem.actors)]
        for index,row in rows:
            weights=np.maximum(row['barycentric'],0);weights=weights/weights.sum()
            target=sum(w*points[row['target']][v] for w,v in zip(weights,row['target_vertices']))
            values[index]=points[row['source']][row['vertex']]-target
    parent=study/Path(result['selected']['actors'][0]['path']).parent
    with np.load(parent/'witness-vectors.npz',allow_pickle=False) as saved:vector_error=float(np.abs(values-saved['vectors']).max());np.testing.assert_allclose(values,saved['vectors'],atol=1e-10,rtol=0)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during replay')
    save(output/'verification.json',dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),accepted_steps=accepted_count,trials=trials_count,
        verified_history_peak_values=peak_values,final_peak_values_replayed=motion_count,final_rate_replay_error=motion_error,final_full_skin_vectors=len(values),
        final_skin_vector_error_m=vector_error,decisions=decisions,quality_approved=False,
        scope='Exact cumulative controls and unchanged source-cap layouts across all proposals. Retained trial vectors/decisions replayed from stored arrays; final native reconstruction, decoded motion and full CPU-skin vectors checked independently. Complete partner signed-distance queries remain separate.'))
    print(dict(accepted_steps=accepted_count,trials=trials_count,history_peak_values=peak_values,final_rate_error=motion_error,full_skin_vector_error=vector_error),flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.output)
