"""Run a new portable generation through character transfer, editing and Godot.

Uses only this installation's paths. Component evidence, not motion-quality approval.
"""
import argparse
import os
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def run(generation):
    from studio_characters import import_bytes, save_profile, validate_job, asset_folder, JOBS
    from action_studio_server import allowed_file
    from rig_studio_job import run as run_rig
    from rig_clip_edit import prepare
    from run_godot_rig_import import run as engine_import
    generation=Path(generation).resolve()
    if not generation.is_relative_to(ROOT/'reports/action-jobs'):
        raise ValueError('Choose a completed generation in this installation')
    if read(generation/'pipeline.json')['status']!='complete':
        raise ValueError('Generation is incomplete')
    trial=read(generation/'summary.json')['trials'][0]
    source=generation/'takes'/trial['id']
    output=ROOT/'reports/offline-workflow-v1'
    output.mkdir(exist_ok=False)
    save(output/'pipeline.json',{'status':'processing','started_at':now()})
    asset_path=ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    asset=import_bytes(asset_path.read_bytes(),asset_path.name)
    profile=save_profile({'asset_id':asset['id'],'profile':asset['profile']})
    request,motion,mapping=validate_job({'asset_id':asset['id'],'profile_id':profile['profile_id'],
        'kind':'transfer','label':'Offline stretch transfer',
        'motion_url':'/files/'+(source/'motion.npz').relative_to(ROOT/'reports').as_posix()},allowed_file)
    folder=JOBS/'offline-transfer-v1';(folder/'source').mkdir(parents=True,exist_ok=False)
    stored=asset_folder(asset['id'])
    shutil.copyfile(stored/'character.glb',folder/'source/character.glb')
    shutil.copyfile(mapping,folder/'source/rig-profile.json')
    shutil.copyfile(motion,folder/'source/motion.npz')
    for name in ['asset.json','LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md','provenance.json']:
        if (stored/name).exists():shutil.copyfile(stored/name,folder/'source'/name)
    save(folder/'request.json',request)
    run_rig(folder)
    assert read(folder/'pipeline.json')['status']=='complete'
    report=read(folder/'transfer/report.json')
    edited=JOBS/'offline-retime-v1'
    prepare({'source_job':folder.name,'variant':'transfer','edit':{
        'schema':'strep-rig-clip-edit-v1','glb_sha256':sha256(folder/'transfer/character.glb'),
        'label':'Offline stretch at 80 percent speed','start_frame':0,
        'last_frame':report['frames']-1,'speed':.8,'poses':[]}},edited)
    run_rig(edited)
    assert read(edited/'pipeline.json')['status']=='complete'
    cases=[]
    for name,path,frames in [('native',source/'soma.glb',trial['frames']),
                             ('transfer',folder/'transfer/character.glb',report['frames']),
                             ('retimed',edited/'transfer/character.glb',read(edited/'transfer/report.json')['frames'])]:
        cases.append({'id':name,'path':os.path.relpath(path,output).replace('\\','/'),
                      'sha256':sha256(path),'frames':frames,'fps':30})
    save(output/'manifest.json',{'cases':cases})
    engine_import(output,output/'engine')
    save(output/'pipeline.json',{'status':'complete','finished_at':now(),
        'generation':str(generation),'transfer':str(folder),'edit':str(edited),
        'scope':'One new prompt, one known licensed target rig and a retime; no independent human or release approval'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('generation',type=Path)
    run(parser.parse_args().generation)
