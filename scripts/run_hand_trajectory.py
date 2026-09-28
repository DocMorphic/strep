"""Preserved timed-correction development experiment on the observed high-five."""
import argparse
import os
import shutil
from pathlib import Path
import psutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from rig_asset import RigAsset
from target_rig_contact import baseline
from paired_palm_region import RegionActor
from paired_hand_trajectory import TrajectoryFitter
from refine_hand_trajectory import refine


def run(output,restoration=False):
    output=Path(output).resolve();seed_study=ROOT/'reports/paired-palm-region-v5'
    prior=read(seed_study/'request.json');parameters=read(seed_study/'parameters.json');source=Path(prior['input'])
    if output.exists():raise ValueError('Preserve earlier trajectory trial')
    if read(seed_study/'pipeline.json')['status']!='complete':raise ValueError('Seed incomplete')
    for path,key in [(source/'manifest.json','input_manifest_sha256'),(source/'input-scene.json','scene_sha256'),(ASSET,'skin_sha256')]:
        if sha256(path)!=prior[key]:raise ValueError('Seed source changed')
    for name,digest in prior['implementation'].items():
        if sha256(seed_study/'implementation'/name)!=digest:raise ValueError('Seed snapshot changed')
    skin=dict(np.load(ASSET,allow_pickle=False));scene=read(source/'input-scene.json')['scene'];patches=read(seed_study/'palm-region.json');actors=[]
    for name in ['A','B']:
        path=source/'input'/name/'character.glb'
        if sha256(path)!=read(source/'manifest.json')['assets'][f'input/{name}/character.glb']['sha256']:raise ValueError('Source actor changed')
        rig=RigAsset.load(path);_,local=baseline(rig,150)
        actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],scene['actors'][name]['transform'],patch=patches[name]))
    fitter=TrajectoryFitter(actors);initial=fitter.expand(parameters['values'])
    if not np.array_equal(parameters['bounds'],fitter.base.bounds) or not np.array_equal(parameters['envelope'],fitter.base.envelope):raise ValueError('Seed limits differ')
    output.mkdir();(output/'implementation').mkdir()
    names=['run_hand_trajectory.py','refine_hand_trajectory.py','paired_hand_trajectory.py','paired_palm_region.py','paired_hand_fit.py','paired_hand_clearance.py','rig_asset.py','target_rig_contact.py','rig_clearance_fit.py']
    if restoration:names.append('elastic_hand_step.py')
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    frames=[72.,74.,74.5,75.,75.5,76.,78.]
    save(output/'request.json',dict(created_at=now(),input=str(source),input_manifest_sha256=sha256(source/'manifest.json'),scene_sha256=sha256(source/'input-scene.json'),skin_sha256=sha256(ASSET),
        implementation={n:sha256(output/'implementation'/n) for n in names},actor_kind='arms',seed_study=str(seed_study),initial_parameters_sha256=sha256(seed_study/'parameters.json'),
        knots=fitter.knots,frames=frames,iterations=3,inner_max_iterations=60,component_trust_degrees=5,safeguard_trials=8,
        restoration=restoration,restoration_settings=dict(slack_scale_m=.03,slack_max_m=.12,slack_weight=30.,slack_is_not_acceptance_tolerance=True) if restoration else None,
        clearance_margin_m=.001,proximity_selection_m=.003,contact_gap_m=.001,contact_weight=100.,surface_violation_weight=100.,change_prior=.1,
        screen=prior['screen'],pid=os.getpid(),process_created=psutil.Process().create_time(),
        scope='Observed development event, three timed arm-control vectors per actor. Finite-difference derivatives of local-rotation interpolation matching exported keys. Same global/envelope/adjacent edit limits. No anatomical, self-collision, full-window or continuous certificate.'))
    shutil.copyfile(seed_study/'parameters.json',output/'initial-parameters.json');save(output/'palm-region.json',patches)
    save(output/'pipeline.json',dict(status='initial_surface_samples'))
    def progress(history):
        save(output/'history.json',dict(iterations=history,quality_approved=False))
        save(output/'pipeline.json',dict(status='refining',completed_iterations=len(history)-1))
        print('Iteration',len(history)-1,'depths',[max(c['max_depth_m'] for c in s['collision']) for s in history[-1]['window']],'gap',max(max(d['distances_m']) for d in history[-1]['contact']),flush=True)
    with threadpool_limits(limits=1):controls,history=refine(fitter,initial,skin['faces'],frames,iterations=3,progress=progress,restoration=restoration)
    trajectory=fitter.values(controls)
    save(output/'parameters.json',dict(values=trajectory[fitter.event].tolist(),envelope=fitter.base.envelope.tolist(),bounds=fitter.base.bounds.tolist(),
        trajectory_values=trajectory.tolist(),controls=controls.tolist(),control_bounds=fitter.bounds.tolist(),basis=fitter.matrix.tolist(),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--restoration',action='store_true');a=p.parse_args();run(a.output,a.restoration)
