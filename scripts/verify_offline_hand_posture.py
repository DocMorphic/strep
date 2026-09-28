"""Use a relocated installation's own runtime to import, edit and export a hand.

The external GLB is an explicit test input, not fresh model generation. No
development modules or historical job results are copied into the runtime.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now


def run(source,license_folder):
    if not (ROOT/'installation.json').is_file() or not Path(sys.executable).resolve().is_relative_to(ROOT):raise ValueError('Run with the relocated installation Python')
    from studio_characters import import_bytes,save_profile,validate_job,asset_folder,JOBS
    from rig_studio_job import run as run_job
    from rig_posture_edit import metadata,prepare
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from verify_rig_clearance import localize
    from run_godot_rig_import import run as engine
    output=ROOT/'reports/offline-hand-posture-v1';output.mkdir(exist_ok=False)
    source=Path(source).resolve();license_folder=Path(license_folder).resolve()
    shutil.copyfile(source,output/'input-character.glb')
    save(output/'request.json',dict(at=now(),source_input=str(source),source_sha256=sha256(source),runtime=sys.executable,
        installation_manifest_sha256=sha256(ROOT/'installation.json'),driver_sha256=sha256(__file__),
        scope='Relocated import and authored finger edit of a previously generated GLB. No new inference, learned grasp, anatomy or quality approval.'))
    asset=import_bytes((output/'input-character.glb').read_bytes(),'Previously-generated-wave.glb')
    proposed=asset['profile']
    saved_profile=license_folder/'rig-profile.json'
    if saved_profile.is_file():
        proposed=read(saved_profile);original_rig=RigAsset.load(license_folder/'character.glb');incoming=RigAsset.load(output/'input-character.glb')
        if original_rig.parents!=incoming.parents or [n.get('name') for n in original_rig.document['nodes']]!=[n.get('name') for n in incoming.document['nodes']]:raise ValueError('Saved mapping topology differs from imported clip')
        proposed['character_sha256']=asset['id']
    profile=save_profile(dict(asset_id=asset['id'],profile=proposed))
    request,_,mapping=validate_job(dict(asset_id=asset['id'],profile_id=profile['profile_id'],kind='rough_import',animation_index=0,label='Offline imported wave'),lambda _:None)
    imported=JOBS/'offline-hand-import-v1';(imported/'source').mkdir(parents=True,exist_ok=False)
    shutil.copyfile(asset_folder(asset['id'])/'character.glb',imported/'source/character.glb');shutil.copyfile(mapping,imported/'source/rig-profile.json')
    licenses=[p for p in license_folder.iterdir() if p.is_file() and ('license' in p.name.lower() or p.name=='provenance.json')]
    if not licenses:raise ValueError('Retain source character license/provenance')
    for p in licenses:shutil.copyfile(p,imported/'source'/p.name)
    save(imported/'request.json',request);run_job(imported)
    if read(imported/'pipeline.json')['status']!='complete':raise RuntimeError(read(imported/'pipeline.json'))
    meta=metadata(imported.name,'transfer');rig=RigAsset.load(imported/'transfer/character.glb')
    if meta['frames']<=90 or not meta['hands']:raise ValueError('Expected a mapped hand and at least 91 frames')
    hand=meta['hands'][0];joint=next(j for j in hand['joints'] if j['node'] in rig.parents)
    world=AnimationSampler(rig.document,rig.binary,0).sample(float(np.float32(40/30)))
    local=localize(world[None],rig.parents)[0];target=Rotation.from_matrix(local[joint['node'],:3,:3])*Rotation.from_euler('z',10,degrees=True)
    recipe=dict(schema='strep-hand-posture-v1',source_glb_sha256=meta['glb_sha256'],frames=meta['frames'],fps=30,hand_roots=[hand['node']],
        poses=[dict(id='captured-finger-z10',hand_root=hand['node'],targets=[dict(node=joint['node'],rotation_xyzw=target.as_quat().tolist())],
            start_frame=10,full_start_frame=30,full_end_frame=60,end_frame=90,strength=1.)],
        limits=dict(rotation_degrees=30,correction_step_degrees=5),provenance='Explicit ten-degree local Z edit relative to captured frame 40, one finger joint. Not a semantic hand preset or generated grasp.')
    edited=JOBS/'offline-hand-edit-v1';prepare(dict(source_job=imported.name,variant='transfer',label='Offline timed finger edit',posture=recipe),edited);run_job(edited)
    if read(edited/'pipeline.json')['status']!='complete':raise RuntimeError(read(edited/'pipeline.json'))
    cases=[]
    for variant in ['input','transfer']:
        path=edited/variant/'character.glb';cases.append(dict(id=variant,path=os.path.relpath(path,output).replace('\\','/'),sha256=sha256(path),frames=meta['frames'],fps=30))
    save(output/'manifest.json',dict(cases=cases));engine(output,output/'engine')
    package=edited/'character-animation.zip';members={}
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            digest=hashlib.sha256(archive.read(name)).hexdigest();members[name]=digest
            if name!='README.txt' and digest!=sha256(edited/name):raise ValueError('Package member mismatch')
    modules={name:str(sys.modules[name].__file__) for name in ['strep','rig_posture_edit','hand_posture','rig_studio_job','rig_asset','numpy','scipy']}
    if any(not Path(p).resolve().is_relative_to(ROOT) for p in modules.values()):raise ValueError('Module escaped relocated installation')
    save(output/'completion.json',dict(at=now(),import_job=imported.name,edit_job=edited.name,modules=modules,selected_joint=joint,
        package_sha256=sha256(package),package_members=members,verification_sha256=sha256(edited/'transfer/verification.json'),engine_proof_sha256=sha256(output/'engine/verification.json'),
        engine_frames=2*meta['frames'],quality_approved=False,new_model_inference=False))
    print(output,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('license_folder',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.source,a.license_folder)
