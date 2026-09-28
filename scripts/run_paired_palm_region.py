"""Preserved palm-region experiment on the already-authored reference hands."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from rig_asset import RigAsset
from target_rig_contact import baseline
from paired_palm_region import region,RegionActor,RegionFitter,refine,contact_records


def run(output,initial_state='point_fit',iterations=4,safeguard=False,initial_refinement=None,fingers=False):
    if initial_state not in ('point_fit','input','orientation') or type(iterations)is not int or not 1<=iterations<=12:raise ValueError('Invalid fixed experiment budget')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier region experiment')
    previous=ROOT/'reports/paired-hand-prototype-v6';scene=read(previous/'input-scene.json')['scene']
    initial=read(previous/'parameters.json');skin=dict(np.load(ASSET,allow_pickle=False));patch=region(skin,'LeftHand')
    continuation=None
    if initial_refinement is not None:
        initial_refinement=Path(initial_refinement).resolve()
        prior=read(initial_refinement/'request.json');continuation=read(initial_refinement/'parameters.json')
        if initial_state!='point_fit' or read(initial_refinement/'pipeline.json')['status']!='complete':raise ValueError('Continuation requires a completed fixed seed')
        for key,digest in [('scene_sha256',sha256(previous/'input-scene.json')),('skin_sha256',sha256(ASSET)),('input_manifest_sha256',sha256(previous/'manifest.json'))]:
            if prior[key]!=digest:raise ValueError('Continuation source mismatch')
        for name,digest in prior['implementation'].items():
            if sha256(initial_refinement/'implementation'/name)!=digest:raise ValueError('Continuation implementation changed')
        if read(initial_refinement/'palm-region.json')!=dict(A=patch,B=patch,quality_approved=False):raise ValueError('Continuation patch mismatch')
        if len(continuation['values'])!=24:raise ValueError('Paired comparison requires the same arm-only starting state')
    output.mkdir(parents=True);(output/'implementation').mkdir()
    names=['paired_palm_region.py','run_paired_palm_region.py','paired_hand_fit.py','paired_hand_clearance.py',
        'rig_asset.py','target_rig_contact.py','rig_clearance_fit.py','palm_contacts.py','floor_contact.py']
    if fingers:names.extend(['paired_finger_region.py','paired_finger_fit.py'])
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(created_at=now(),input=str(previous),input_manifest_sha256=sha256(previous/'manifest.json'),
        initial_parameters_sha256=sha256(previous/'parameters.json'),scene_sha256=sha256(previous/'input-scene.json'),skin_sha256=sha256(ASSET),
        implementation={n:sha256(ROOT/'scripts'/n) for n in names},initial_state=initial_state,iterations=iterations,safeguard=safeguard,
        actor_kind='arm_and_fingers' if fingers else 'arms',
        continuation=None if continuation is None else dict(path=str(initial_refinement),parameters_sha256=sha256(initial_refinement/'parameters.json'),request_sha256=sha256(initial_refinement/'request.json')),
        safeguard_trials=8 if safeguard else 0,safeguard_depth_precision_m=1e-6,clearance_margin_m=.001,proximity_selection_m=.003,
        contact_gap_m=.001,contact_weight=100.,contacts_per_direction=3,contact_spacing_m=.006,inner_component_trust_degrees=5,
        screen=dict(max_contact_distance_m=.003,min_triangle_area_m2=.000025,max_event_penetration_m=.005,opposing_normal_max_degrees=20),
        scope='Observed development high-five, authored reference fingers, isolated event. New region contact intent; legacy same-vertex distance is diagnostic only, not the optimized goal. Geometry heuristic is not anatomical review.'))
    save(output/'palm-region.json',dict(A=patch,B=patch,quality_approved=False))
    if continuation is not None:
        shutil.copyfile(initial_refinement/'parameters.json',output/'initial-parameters.json')
        shutil.copyfile(initial_refinement/'request.json',output/'initial-request.json')
    actor_class=RegionActor
    if fingers:
        from paired_finger_region import FingerRegionActor
        actor_class=FingerRegionActor
    actors=[]
    for name in ['A','B']:
        path=previous/'input'/name/'character.glb'
        if sha256(path)!=read(previous/'manifest.json')['assets'][f'input/{name}/character.glb']['sha256']:raise ValueError('Input changed')
        rig=RigAsset.load(path);_,local=baseline(rig,scene['frame_count'])
        actors.append(actor_class(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],scene['actors'][name]['transform'],patch=patch))
    fitter=RegionFitter(*actors,event=75,fade=15)
    def progress(history):
        save(output/'history.json',dict(iterations=history,quality_approved=False))
        save(output/'pipeline.json',dict(status='refining',completed_iterations=len(history)-1))
        print('Iteration',len(history)-1,'depth',max(d['max_depth_m'] for d in history[-1]['collision']),'contact',max(max(d['distances_m']) for d in history[-1]['contact']),flush=True)
    seed=np.array(initial['values']) if initial_state=='point_fit' else np.zeros(len(fitter.bounds))
    if continuation is not None:
        seed=np.asarray(continuation['values'])
        arm_bounds=np.concatenate([fitter.bounds[:12],fitter.bounds[actors[0].dim:actors[0].dim+12]])
        if not np.array_equal(continuation['envelope'],fitter.envelope) or not np.array_equal(continuation['bounds'],arm_bounds):raise ValueError('Continuation budget changed')
    if fingers and seed.shape==(24,):
        from paired_finger_fit import expand_arm_seed
        seed=expand_arm_seed(seed,actors)
    if initial_state=='orientation':
        from paired_hand_clearance import correspondences
        save(output/'pipeline.json',dict(status='orientation_initialization'))
        with threadpool_limits(limits=1):
            seed,fit=fitter.solve()
            _,collision=correspondences(fitter.actors,fitter.event,seed,skin['faces'],margin=.003)
        save(output/'initial-orientation.json',dict(parameters=seed.tolist(),solver=fit,collision=collision))
        if max(d['max_depth_m'] for d in collision)>1e-6:
            save(output/'pipeline.json',dict(status='failed',error='Orientation initialization intersects',quality_approved=False))
            raise ValueError('Preserved intersecting orientation initialization')
    with threadpool_limits(limits=1):values,history=refine(fitter,seed,skin['faces'],progress,iterations=iterations,safeguard=safeguard)
    save(output/'parameters.json',dict(values=values.tolist(),envelope=fitter.envelope.tolist(),bounds=fitter.bounds.tolist(),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--initial-state',choices=['point_fit','input','orientation'],default='point_fit');p.add_argument('--iterations',type=int,default=4)
    p.add_argument('--safeguard',action='store_true');p.add_argument('--initial-refinement',type=Path);p.add_argument('--fingers',action='store_true')
    a=p.parse_args();run(a.output,a.initial_state,a.iterations,a.safeguard,a.initial_refinement,a.fingers)
