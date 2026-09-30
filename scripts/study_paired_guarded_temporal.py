"""Fit the retained first pair with source-relative per-joint temporal guards."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from paired_temporal_neighbor import BODY,placed_joint_positions
from paired_guarded_temporal import GuardedEdit
from rig_clip_import import AnimationSampler
from study_paired_temporal_neighbor import preservation
from audit_scene_joint_rates import compare_rates
from verify_paired_stage_rates import verify_rates


def decoded(path):
    doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0)
    return doc,np.array([sampler.sample(f/120) for f in range(597)])


def motion_guard(rates,tolerance=1e-5):
    failures=[]
    for metric in ['speed','acceleration']:
        for window in rates[metric]['windows']:
            for joint in window['joints']:
                if joint['change']>tolerance:failures.append(dict(metric=metric,window=window['window'],**joint))
    return failures


def run(output,resume=None,restore=False):
    output=Path(output).resolve();prior=ROOT/'reports/paired-temporal-neighbor-v1';protocol=read(prior/'protocol.json')
    evidence=ROOT/'reports/paired-temporal-rates-v4/verification.json';result=read(prior/'result.json')
    inputs={**protocol['inputs'],str(evidence):sha256(evidence),str(prior/'protocol.json'):sha256(prior/'protocol.json'),str(prior/'result.json'):sha256(prior/'result.json')}
    for actors in result['exports'].values():
        for row in actors.values():inputs[str(prior/row['path'])]=row['sha256']
    initial={}
    if restore and resume is None:raise ValueError('Restoration requires a retained fit')
    if resume is not None:
        resume=Path(resume).resolve();previous=read(resume/'request.json');completed=read(resume/'result.json')
        if completed['status']!='complete' or completed['request_sha256']!=sha256(resume/'request.json'):raise ValueError('Completed bound previous fit required')
        if previous['free_frames']!=[74,76] or previous['selected_joints']!=BODY or previous['fit_windows']!={'event':[73,77]} or previous['limit_degrees']!=5.:
            raise ValueError('Continuation must retain parameter layout, bounds and phase caps')
        for file,digest in previous['inputs'].items():
            if sha256(file)!=digest:raise ValueError('Previous fit input changed')
        for actor in ['A','B']:
            fit_path=resume/actor/'fit.json';saved=read(fit_path)['fit']
            matching=[row for row in completed['rows'] if row['actor']==actor]
            if len(matching)!=1 or matching[0]['fit']!=saved:raise ValueError('Retained fit does not match completed result')
            initial[actor]=saved['final_parameters'];inputs[str(fit_path)]=sha256(fit_path)
        inputs[str(resume/'request.json')]=sha256(resume/'request.json');inputs[str(resume/'result.json')]=sha256(resume/'result.json')
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Bound input changed')
    if output.exists():raise ValueError('Preserve earlier trial')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['study_paired_guarded_temporal.py','paired_guarded_temporal.py','paired_temporal_neighbor.py','study_paired_temporal_neighbor.py',
             'audit_scene_joint_rates.py','verify_paired_stage_rates.py','rig_clip_import.py','rig_asset.py','gltf_tools.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    windows=dict(whole_clip=[0,149],edited_interval=[70,80],event=[73,77],entry_join=[68,72],exit_join=[78,82])
    request=dict(at=now(),inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},seed=1301,free_frames=[74,76],
        selected_joints=BODY,windows=windows,fit_windows=dict(event=[73,77]),limit_degrees=5.,
        maximum_iterations=60,maximum_seconds_per_actor=90,line_factors=[1.,.5,.25,.125,.0625,.03125,0.],
        initialization=None if resume is None else resume.relative_to(ROOT).as_posix(),restoration=restore,constraint_form='Each sampled rate bounded by original joint peak; no maximum inside nonlinear inequality.',
        restoration_max_evaluations=80,restoration_reserve_fraction=1e-4,restoration_speed_reserve_m_s=1e-5,restoration_acceleration_reserve_m_s2=1e-3,
        quality_approved=False,scope='Source-relative constrained body edit; fingers, contact key and outer key stencils fixed. Source per-joint peak guards are development nonregression checks, not physical quality thresholds. Full scene geometry and human review still required.')
    save(output/'request.json',request);rows=[];cases=[];scene=read(ROOT/protocol['source_scene'])['scene'];peak_count=0;max_error=0.
    for actor in ['A','B']:
        folder=output/actor;folder.mkdir();source=prior/'input'/(actor+'.glb');doc,binary=read_glb(source)
        problem=GuardedEdit(doc,binary,BODY,[74,76],np.arange(67,83.001,.25),request['fit_windows'],5.)
        parameters,fit=problem.restore(initial[actor],80,90) if restore else problem.fit(60,90,initial.get(actor))
        save(folder/'fit.json',dict(parameters=parameters.tolist(),fit=fit))
        source_doc,source_world=decoded(source);joints=source_doc['skins'][0]['joints'];names=[source_doc['nodes'][j]['name'] for j in joints]
        placement=scene['actors'][actor]['transform'];rotation=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();translation=placement['translation_m']
        source_positions=placed_joint_positions(source_world,joints,rotation,translation);attempts=[];selected=None
        for number,factor in enumerate(request['line_factors']):
            path=folder/f'trial-{number}.glb'
            if factor==0 or not np.any(parameters):shutil.copyfile(source,path)
            else:problem.export(parameters*factor,path)
            _,world=decoded(path);positions=placed_joint_positions(world,joints,rotation,translation)
            locked=(np.arange(597)/4<73)|(np.arange(597)/4>77)|(np.arange(597)/4==75)
            np.testing.assert_allclose(world[locked],source_world[locked],atol=1e-12,rtol=0)
            record=dict(selected_joints=BODY,frames=[74,76]);body=ROOT/'reports/paired-pose-posture-v1'/f'seed-1301/{actor}/body_fit/character.glb'
            proof=preservation(source,path,body,record)
            if not proof['original_finger_limits_passed']:raise ValueError('Original finger bounds changed')
            rates=compare_rates(source_positions,positions,names,windows);count,error=verify_rates(source_positions,positions,rates,names)
            peak_count+=count;max_error=max(max_error,error);failures=motion_guard(rates)
            rate_file=folder/f'trial-{number}-rates.json';save(rate_file,rates)
            row=dict(factor=factor,path=path.relative_to(output).as_posix(),sha256=sha256(path),rates_sha256=sha256(rate_file),
                rate_failure_count=len(failures),largest_failures=sorted(failures,key=lambda x:x['change'],reverse=True)[:10],preservation=proof,
                protected_world_matrix_max_error=float(np.abs(world[locked]-source_world[locked]).max()))
            attempts.append(row);save(folder/'attempts.json',attempts)
            if not failures:selected=row;break
        if selected is None:raise ValueError('Exact unchanged fallback must pass')
        target=folder/'candidate.glb';shutil.copyfile(output/selected['path'],target);shutil.copyfile(source,folder/'input.glb')
        rows.append(dict(actor=actor,fit=fit,selected=selected,motion_changed=bool(selected['factor'] and np.any(parameters)),quality_approved=False))
        for variant in ['input','candidate']:
            path=folder/(variant+'.glb');cases.append(dict(id=variant+'-'+actor,path=path.relative_to(output).as_posix(),sha256=sha256(path),frames=150,fps=30,sample_by_time=True))
        print(dict(actor=actor,selected_factor=selected['factor'],fit=fit['message'],failures=selected['rate_failure_count']),flush=True)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during fitting')
    for name,digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during fitting')
    save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),rows=rows,
        verified_peak_values=peak_count,maximum_peak_replay_error=max_error,quality_approved=False))


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--resume',type=Path);p.add_argument('--restore',action='store_true');a=p.parse_args()
    with threadpool_limits(limits=1):run(a.output,a.resume,a.restore)
