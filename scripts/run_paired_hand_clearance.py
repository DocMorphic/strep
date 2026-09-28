"""Fixed four-iteration exploratory refinement of the preserved point fit."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from rig_asset import RigAsset
from target_rig_contact import baseline
from paired_hand_fit import HandActor,PairFitter
from paired_hand_clearance import refine


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier refinement')
    previous=ROOT/'reports/paired-hand-prototype-v3';scene=read(previous/'input-scene.json')['scene']
    initial=read(previous/'parameters.json');skin=dict(np.load(ASSET,allow_pickle=False));actors=[]
    output.mkdir(parents=True);(output/'implementation').mkdir()
    names=['paired_hand_clearance.py','run_paired_hand_clearance.py','paired_hand_fit.py',
        'rig_asset.py','target_rig_contact.py','rig_clearance_fit.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(created_at=now(),input=str(previous),input_manifest_sha256=sha256(previous/'manifest.json'),
        initial_parameters_sha256=sha256(previous/'parameters.json'),scene_sha256=sha256(previous/'input-scene.json'),skin_sha256=sha256(ASSET),
        implementation={n:sha256(ROOT/'scripts'/n) for n in names},iterations=4,margin_m=.002,weight=1000.,inner_component_trust_degrees=5,
        scope='Observed development seed, isolated event refinement. Frozen correspondences updated each outer iteration. No release, whole-window or semantic approval.'))
    for name in ['A','B']:
        path=previous/'input'/name/'character.glb'
        if sha256(path)!=read(previous/'manifest.json')['assets'][f'input/{name}/character.glb']['sha256']:raise ValueError('Input changed')
        rig=RigAsset.load(path);_,local=baseline(rig,scene['frame_count'])
        actors.append(HandActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],scene['actors'][name]['transform']))
    fitter=PairFitter(*actors,event=75,fade=15)
    def progress(history):
        save(output/'history.json',dict(iterations=history,quality_approved=False))
        save(output/'pipeline.json',dict(status='refining',completed_iterations=len(history)-1))
        print('Iteration',len(history)-1,'maximum depth',max(d['max_depth_m'] for d in history[-1]['collision']),flush=True)
    with threadpool_limits(limits=1):values,history=refine(fitter,np.array(initial['values']),skin['faces'],progress)
    save(output/'parameters.json',dict(values=values.tolist(),envelope=fitter.envelope.tolist(),bounds=fitter.bounds.tolist(),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
