"""Measure the exhausted continuation direction against its frozen fitting margins."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_problem import PairProblem
from coupled_pair_proposal import motion_rows
from study_paired_guarded_temporal import decoded,motion_guard
from paired_temporal_neighbor import placed_joint_positions
from audit_scene_joint_rates import compare_rates


def run(study,witnesses,output):
    study,output=Path(study).resolve(),Path(output).resolve();problem=PairProblem(witnesses)
    if output.exists():raise ValueError('Preserve previous limit audit')
    request,result=read(study/'request.json'),read(study/'result.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json') or result['termination']!='exported_line_search_exhausted':
        raise ValueError('Completed exhausted line search required')
    folder=sorted(study.glob('iteration-*'))[-1];solver=read(folder/'solver.json');trials=read(folder/'trials.json')
    with np.load(folder/'linearization.npz',allow_pickle=False) as archive:linear=dict(archive)
    reserve=Path(request['reserve'])
    with np.load(reserve/'reserve.npz',allow_pickle=False) as archive:margins=archive['reserve'].copy()
    inputs={**problem.inputs,**request['inputs']}
    for file in [study/'request.json',study/'result.json',folder/'solver.json',folder/'trials.json',folder/'linearization.npz',reserve/'reserve.npz']:
        inputs[str(file)]=sha256(file)
    if inputs[str(folder/'linearization.npz')]!=solver['linearization_sha256']:raise ValueError('Stored linearization changed')
    for trial in trials:
        for actor in trial['actors']:inputs[str(study/actor['path'])]=actor['sha256']
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Audit input changed')
    output.mkdir();shutil.copyfile(__file__,output/'implementation.py')
    step=np.array(solver['step']);base=np.array(solver['base_controls']);indices=np.round(problem.frames*4).astype(int)
    predicted=np.array([np.linalg.norm(linear['vectors']+linear['jacobians']@(step*t['factor']),axis=1) for t in trials])
    actual=predicted.copy();ideal=predicted.copy();rows=[];cursor=0
    for number,actor in enumerate(problem.actors):
        model=actor['model'];cursor+=model.original_vectors.reshape(-1,3).shape[0]
        doc,source_world=decoded(actor['source']);names=[doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
        reference=placed_joint_positions(source_world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
        clock=model.base.channels[model.base.nodes[0]][1];active=(problem.frames/30>float(clock[63]))&(problem.frames/30<float(clock[75]))
        dummy=np.zeros(reference[indices].shape+(1,));tracks=dict(source=reference)
        for index,trial in enumerate(trials):
            controls=base+step*trial['factor'];np.testing.assert_array_equal(controls,trial['controls'])
            part=np.split(controls,[problem.sizes[0]])[number];continuous=reference.copy()
            continuous[indices]=placed_joint_positions(model.world(part),doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
            entry=next(a for a in trial['actors'] if a['actor']==actor['name']);_,world=decoded(study/entry['path'])
            exported=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
            for positions,destination in [(continuous,ideal),(exported,actual)]:
                vectors,_,caps,orders=motion_rows(positions[indices],dummy,reference[indices],problem.frames,problem.windows,model.base.affected,active)
                end=cursor+len(caps);np.testing.assert_array_equal(caps,linear['radii'][cursor:end])
                np.testing.assert_array_equal(linear['kinds'][cursor:end],np.where(orders==1,'speed','acceleration'))
                destination[index,cursor:end]=np.linalg.norm(vectors,axis=1)
            windows=dict(whole_clip=[0,149],**problem.windows)
            ideal_fail=motion_guard(compare_rates(reference,continuous,names,windows));export_fail=motion_guard(compare_rates(reference,exported,names,windows))
            if len(export_fail)!=entry['rate_failures']:raise ValueError('Exported failure replay differs')
            lookup={(r['metric'],r['window'],r['joint']):r['change'] for r in ideal_fail}
            details=[dict(metric=r['metric'],window=r['window'],joint=r['joint'],exported_change=r['change'],ideal_fails=(r['metric'],r['window'],r['joint']) in lookup) for r in export_fail]
            rows.append(dict(actor=actor['name'],factor=trial['factor'],ideal_failures=len(ideal_fail),exported_failures=len(export_fail),failures=details))
            tracks[f'ideal_{index}']=continuous;tracks[f'exported_{index}']=exported
        cursor=end;np.savez_compressed(output/(actor['name']+'-tracks.npz'),**tracks)
    if cursor!=len(linear['radii']):raise ValueError('Unaccounted norm rows')
    np.savez_compressed(output/'norms.npz',predicted=predicted,ideal=ideal,exported=actual,previous_reserve=margins,kinds=linear['kinds'])
    observed_error=np.maximum(actual-predicted,0);stats={}
    for kind in ['speed','acceleration']:
        mask=linear['kinds']==kind;excess=observed_error[:,mask]-margins[mask]
        stats[kind]=dict(maximum_exported_prediction_error=float(observed_error[:,mask].max()),maximum_reserve_excess=float(max(0.,excess.max())),
            reserve_exceedances_over_1e_8=int((excess>1e-8).sum()),maximum_serialization_norm_difference=float(np.abs(actual[:,mask]-ideal[:,mask]).max()))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during limit audit')
    save(output/'verification.json',dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),iteration=int(folder.name.split('-')[-1]),
        statistics=stats,rows=rows,artifacts={p.name:sha256(p) for p in output.glob('*.npz')},quality_approved=False,
        scope='Matched ideal nonlinear and exported motion versus the local affine model for the exhausted direction. The first-step empirical margins are measured, not assumed valid for subsequent directions. No final acceptance gate is changed.'))
    print(dict(statistics=stats,rows=[{k:v for k,v in row.items() if k!='failures'} for row in rows]),flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.output)
