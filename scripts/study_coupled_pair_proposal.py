"""Run and independently decode one motion-constrained moving-partner proposal."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from paired_temporal_neighbor import rotation_channels,placed_joint_positions
from coupled_pair_problem import PairProblem
from coupled_pair_proposal import solve
from coupled_pair_reserve import tightened_radii
from coupled_surface_norms import penetrating_rows
from study_paired_guarded_temporal import decoded,motion_guard
from study_paired_temporal_neighbor import preservation
from audit_scene_joint_rates import compare_rates
from verify_paired_stage_rates import verify_rates


def run(witnesses,output,reserve=None,surface_norms=False):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous proposal')
    problem=PairProblem(witnesses);output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    names=['study_coupled_pair_proposal.py','coupled_pair_problem.py','coupled_pair_proposal.py','paired_approach_basis.py','paired_surface_witness.py',
           'paired_guarded_temporal.py','paired_temporal_neighbor.py','study_paired_guarded_temporal.py','study_paired_temporal_neighbor.py',
           'audit_scene_joint_rates.py','verify_paired_stage_rates.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','conic_root_descent.py','coupled_pair_reserve.py','coupled_surface_norms.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    bootstrap=ROOT/'reports/conic-solver-bootstrap-v1.json';inputs={**problem.inputs,str(bootstrap):sha256(bootstrap)}
    reserve_result=None
    if reserve is not None:
        reserve=Path(reserve).resolve();reserve_result=read(reserve/'result.json');reserve_request=read(reserve/'request.json')
        if reserve_result['status']!='complete' or reserve_result['request_sha256']!=sha256(reserve/'request.json') or reserve_result['reserve_sha256']!=sha256(reserve/'reserve.npz'):
            raise ValueError('Completed bound fitting reserve required')
        inputs.update(reserve_request['inputs'])
        for path in [reserve/'request.json',reserve/'result.json',reserve/'reserve.npz']:inputs[str(path)]=sha256(path)
        for file,digest in inputs.items():
            if sha256(file)!=digest:raise ValueError('Fitting reserve input changed')
    request=dict(at=now(),inputs=inputs,implementation={n:sha256(snapshot/n) for n in names},trust_degrees=.2,line_factors=[1.,.5,.25,.125,.0625],
        windows=problem.windows,free_frames=list(range(64,75)),selected_joints=['LeftShoulder','LeftArm','LeftForeArm','LeftHand'],
        original_edit_limit_degrees=5.,export_edit_tolerance_degrees=1e-4,fit_edit_limit_degrees=5.00005,
        motion_tolerance=1e-5,fitting_reserve=None if reserve is None else str(reserve),penetrating_surface_norms=bool(surface_norms),surface_norm_tolerance_m=1e-8,quality_approved=False,
        scope='One simultaneous two-actor conic step. Existing per-time depths or 5 mm, whichever larger, are local nonregression allowances; 5 mm remains the clearance screen. Original-reference edit balls and current candidate per-joint phase peaks constrain the proposal. Export and fresh complete meshes must decide acceptance.')
    save(output/'request.json',request);save(output/'progress.json',dict(status='linearizing'))
    started=time.monotonic();linear=problem.linearize(np.zeros(problem.size),include_surface_vectors=surface_norms)
    surfaces=None
    if surface_norms:
        surfaces=penetrating_rows(linear.pop('surface_vectors'),linear.pop('surface_jacobians'),linear['gaps'],linear['depth_caps'])
        np.savez_compressed(output/'surface-norms.npz',**surfaces)
    np.savez_compressed(output/'linearization.npz',**linear)
    fitting_radii=linear['radii']
    if reserve_result is not None:
        path=Path(reserve_result['linearization_path'])
        if sha256(path)!=reserve_result['linearization_sha256']:raise ValueError('Reserve linearization changed')
        with np.load(path,allow_pickle=False) as previous:
            if set(previous.files)!=set(linear):raise ValueError('Reserve linearization schema differs')
            for key,value in linear.items():np.testing.assert_array_equal(value,previous[key],err_msg='Reserve belongs to another linearization: '+key)
        with np.load(reserve/'reserve.npz',allow_pickle=False) as calibration:
            fitting_radii=tightened_radii(linear['radii'],calibration['reserve'],linear['kinds'])
            np.testing.assert_array_equal(fitting_radii,calibration['tightened_radii'])
        np.savez_compressed(output/'fitting-radii.npz',radii=fitting_radii)
    fitting_vectors=linear['vectors'];fitting_jacobians=linear['jacobians'];norm_tolerances=np.where(linear['kinds']=='edit',1e-8,1e-6)
    if surfaces is not None:
        fitting_vectors=np.concatenate([fitting_vectors,surfaces['vectors']]);fitting_jacobians=np.concatenate([fitting_jacobians,surfaces['jacobians']])
        fitting_radii=np.r_[fitting_radii,surfaces['radii']];norm_tolerances=np.r_[norm_tolerances,np.full(len(surfaces['radii']),request['surface_norm_tolerance_m'])]
    controls,solver=solve(**{k:linear[k] for k in ['gaps','gap_jacobian','depth_caps']},vectors=fitting_vectors,jacobians=fitting_jacobians,radii=fitting_radii,trust=np.deg2rad(.2),
        norm_tolerances=norm_tolerances)
    save(output/'solver.json',dict(at=now(),linearization_sha256=sha256(output/'linearization.npz'),elapsed_seconds=time.monotonic()-started,
        surface_norms_sha256=None if surfaces is None else sha256(output/'surface-norms.npz'),
        controls=None if controls is None else controls.tolist(),solver=solver));print(solver,flush=True)
    trials=[];cases=[];selected=None;verified=0;replay_error=0.
    if controls is not None:
        originals={};reference_channels={}
        for actor in problem.actors:
            doc,world=decoded(actor['source']);positions=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
            originals[actor['name']]=(doc,world,positions)
            ref,binary=read_glb(actor['reference']);reference_channels[actor['name']]=rotation_channels(ref,binary)
        for index,factor in enumerate(request['line_factors']):
            folder=output/f'trial-{index}';folder.mkdir();parts=np.split(controls*factor,[problem.sizes[0]]);checks=[]
            for actor,part in zip(problem.actors,parts):
                path=folder/(actor['name']+'.glb');actor['model'].export(part,path);doc,world=decoded(path)
                source_doc,source_world,source_positions=originals[actor['name']];joint_names=[doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
                positions=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
                windows=dict(whole_clip=[0,149],**problem.windows);rates=compare_rates(source_positions,positions,joint_names,windows)
                count,error=verify_rates(source_positions,positions,rates,joint_names);verified+=count;replay_error=max(replay_error,error)
                rate_path=folder/(actor['name']+'-rates.json');save(rate_path,rates);failures=motion_guard(rates)
                body=ROOT/'reports/paired-pose-posture-v1'/f"seed-1301/{actor['name']}/body_fit/character.glb"
                proof=preservation(actor['source'],path,body,dict(selected_joints=request['selected_joints'],frames=request['free_frames']))
                actual_doc,binary=read_glb(path);channels=rotation_channels(actual_doc,binary)
                maximum=max(float(np.rad2deg((Rotation.from_quat(reference_channels[actor['name']][node][2]).inv()*Rotation.from_quat(q)).magnitude()).max()) for node,(_,_,q) in channels.items())
                locked=(np.arange(597)/4<63)|(np.arange(597)/4>=75)
                drift=float(np.abs(world[locked]-source_world[locked]).max());np.testing.assert_allclose(world[locked],source_world[locked],atol=1e-12,rtol=0)
                checks.append(dict(actor=actor['name'],path=path.relative_to(output).as_posix(),sha256=sha256(path),rates_sha256=sha256(rate_path),
                    rate_failures=len(failures),largest_failures=sorted(failures,key=lambda x:x['change'],reverse=True)[:8],maximum_original_edit_degrees=maximum,
                    edit_passed=maximum<=5.0001,protected_world_error=drift,preservation=proof))
            trial=dict(factor=factor,actors=checks,motion_and_edit_passed=all(c['rate_failures']==0 and c['edit_passed'] and c['preservation']['original_finger_limits_passed'] for c in checks))
            trials.append(trial);save(output/'trials.json',trials);print(dict(factor=factor,failures=[c['rate_failures'] for c in checks],edit=[c['maximum_original_edit_degrees'] for c in checks]),flush=True)
            if trial['motion_and_edit_passed']:selected=trial;break
        if selected is not None:
            folder=output/'candidate';folder.mkdir();source_folder=output/'input';source_folder.mkdir()
            for actor,check in zip(problem.actors,selected['actors']):
                for variant,source in [('input',actor['source']),('candidate',output/check['path'])]:
                    target=output/variant/(actor['name']+'.glb');shutil.copyfile(source,target)
                    cases.append(dict(id=variant+'-'+actor['name'],path=target.relative_to(output).as_posix(),sha256=sha256(target),frames=150,fps=30,sample_by_time=True))
            save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during proposal')
    for name,digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during proposal')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),solver_sha256=sha256(output/'solver.json'),
        selected=selected,trial_count=len(trials),verified_peak_values=verified,maximum_replay_error=replay_error,geometry_checked=False,quality_approved=False))
    save(output/'progress.json',dict(status='complete'))


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('witnesses',type=Path);p.add_argument('output',type=Path);p.add_argument('--reserve',type=Path);p.add_argument('--surface-norms',action='store_true');a=p.parse_args()
    with threadpool_limits(limits=1):run(a.witnesses,a.output,a.reserve,a.surface_norms)
