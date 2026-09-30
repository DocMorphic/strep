"""Separate nonlinear motion and serialized export changes in retained proposals."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_problem import PairProblem
from study_paired_guarded_temporal import decoded
from paired_temporal_neighbor import placed_joint_positions
from audit_scene_joint_rates import compare_rates


def run(study,witnesses,output):
    study,output=Path(study).resolve(),Path(output).resolve();problem=PairProblem(witnesses)
    if output.exists():raise ValueError('Preserve prior rounding audit')
    request,result=read(study/'request.json'),read(study/'result.json');solver=read(study/'solver.json');trials=read(study/'trials.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json') or result['solver_sha256']!=sha256(study/'solver.json'):raise ValueError('Completed bound proposal required')
    inputs={**request['inputs']}
    for path in [study/'request.json',study/'result.json',study/'solver.json',study/'trials.json']:inputs[str(path)]=sha256(path)
    for trial in trials:
        for actor in trial['actors']:inputs[str(study/actor['path'])]=actor['sha256']
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['audit_coupled_pair_export_error.py','coupled_pair_problem.py','coupled_pair_proposal.py','paired_approach_basis.py','paired_guarded_temporal.py',
             'paired_temporal_neighbor.py','paired_surface_witness.py','study_paired_guarded_temporal.py','rig_clip_import.py','rig_asset.py','gltf_tools.py','audit_scene_joint_rates.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    protocol=dict(at=now(),inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False)
    save(output/'request.json',protocol);controls=np.array(solver['controls']);rows=[]
    indices=np.round(problem.frames*4).astype(int);windows=dict(whole_clip=[0,149],**problem.windows)
    for number,actor in enumerate(problem.actors):
        model=actor['model'];doc,source_world=decoded(actor['source']);joints=doc['skins'][0]['joints'];names=[doc['nodes'][j]['name'] for j in joints]
        reference=placed_joint_positions(source_world,joints,actor['rotation'],actor['translation']);tracks=dict(source=reference)
        for index,trial in enumerate(trials):
            part=np.split(controls*trial['factor'],[problem.sizes[0]])[number]
            ideal=reference.copy();ideal[indices]=placed_joint_positions(model.world(part),joints,actor['rotation'],actor['translation'])
            entry=next(a for a in trial['actors'] if a['actor']==actor['name']);_,actual_world=decoded(study/entry['path'])
            actual=placed_joint_positions(actual_world,joints,actor['rotation'],actor['translation'])
            ideal_rates=compare_rates(reference,ideal,names,windows);actual_rates=compare_rates(reference,actual,names,windows)
            failures=[];ideal_count=0;actual_count=0;introduced=0;peak_shift=0.
            for metric in ['speed','acceleration']:
                for iw,aw in zip(ideal_rates[metric]['windows'],actual_rates[metric]['windows']):
                    for i,a in zip(iw['joints'],aw['joints']):
                        bad_ideal=i['change']>1e-5;bad_actual=a['change']>1e-5
                        ideal_count+=bad_ideal;actual_count+=bad_actual;introduced+=bad_actual and not bad_ideal
                        if metric=='acceleration':peak_shift=max(peak_shift,abs(a['candidate_peak']-i['candidate_peak']))
                        if bad_ideal or bad_actual:failures.append(dict(metric=metric,window=iw['window'],joint=i['joint'],ideal_change=i['change'],exported_change=a['change'],introduced_by_export=bool(bad_actual and not bad_ideal)))
            if actual_count!=entry['rate_failures']:raise ValueError('Serialized failure replay differs')
            tracks[f'ideal_{index}']=ideal;tracks[f'exported_{index}']=actual
            rows.append(dict(actor=actor['name'],factor=trial['factor'],maximum_position_rounding_m=float(np.linalg.norm(actual-ideal,axis=-1).max()),
                maximum_acceleration_peak_shift_m_s2=peak_shift,ideal_failures=ideal_count,exported_failures=actual_count,
                failures_introduced_by_export=int(introduced),failures=failures))
        np.savez_compressed(output/(actor['name']+'-tracks.npz'),**tracks)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during comparison')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during comparison')
    save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),rows=rows,
        tracks={p.name:sha256(p) for p in output.glob('*-tracks.npz')},quality_approved=False,
        scope='Matched ideal float64 kinematics and actual serialized GLB decoding at the same 120 Hz times. Separates continuous-model failures from exported changes on retained trials; does not estimate a universal quantization bound or change any motion gate.'))
    print([{k:r[k] for k in ['actor','factor','ideal_failures','exported_failures','failures_introduced_by_export','maximum_acceleration_peak_shift_m_s2']} for r in rows],flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.output)
