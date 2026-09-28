"""Verify source intent survives a real timed edit and its engine import."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import zipfile
import numpy as np
from strep import ROOT, read, save, sha256, now
from motion_origin import verify
from study_motion_origin_export import api
from contact_edit_job import observed_state
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_rig_import import run as engine


def run(parent_proof, output):
    parent_proof,output=Path(parent_proof).resolve(),Path(output).resolve()
    proof=read(parent_proof/'verification.json');parent=ROOT/'reports/rig-jobs'/proof['job']
    origin=read(parent/'source/motion-origin/manifest.json');result=read(parent/'result.json')
    if sha256(parent/'source/motion-origin/manifest.json')!=proof['manifest_sha256']:raise ValueError('Parent proof changed')
    payload=dict(source_job=parent.name,variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',
        glb_sha256=result['variants']['transfer']['sha256'],label='Retimed profile provenance check',start_frame=10,last_frame=100,speed=1.5,poses=[]))
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=['study_motion_origin_edit.py','study_motion_origin_export.py','motion_origin.py','rig_clip_edit.py','rig_studio_job.py','run_godot_rig_import.py','godot_import_audit.gd']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),parent_proof=str(parent_proof),parent_proof_sha256=sha256(parent_proof/'verification.json'),payload=payload,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    try:
        response=api('/api/rig-clip-edits',payload);save(output/'response.json',response)
        folder=ROOT/'reports/rig-jobs'/response['id'];print('Edit job',folder.name,flush=True)
        while True:
            state=observed_state(folder)
            save(output/'pipeline.json',dict(at=now(),status='waiting_for_exact_edit_job',job=folder.name,worker_status=state,quality_approved=False))
            if state['status']=='failed':raise ValueError('Edit failed: '+str(state))
            if state['status']=='complete':break
            time.sleep(1)
        edited=read(folder/'result.json');manifest=verify(folder/'source/motion.npz',folder/'source/motion-origin',origin)
        if edited['source_generation_origin']['applies_to']!='original_source_motion' or edited['source_generation_origin']['quality_approved']:
            raise ValueError('Historical intent misrepresented as edited output quality')
        before=RigAsset.load(parent/'transfer/character.glb');after=RigAsset.load(folder/'transfer/character.glb')
        donor=AnimationSampler(before.document,before.binary,0);receiver=AnimationSampler(after.document,after.binary,0)
        if edited['frames']!=61:raise ValueError('Wrong edited frame count')
        errors=[]
        for i,frame in enumerate(np.linspace(10,100,61)):
            expected=donor.sample(float(np.float32(frame/30)))
            actual=receiver.sample(float(np.float32(i/30)))
            errors.append(float(np.abs(expected-actual).max()))
        if max(errors)>1e-5:raise ValueError('Edited poses differ from requested source-frame mapping')
        archive=folder/'character-animation.zip'
        with zipfile.ZipFile(archive) as zipped:
            for name in ['manifest.json',*manifest['files']]:
                path='source/motion-origin/'+name
                if zipped.read(path)!=(parent/path).read_bytes():raise ValueError('Original intent changed across edit')
            if zipped.read('clip-edit.json')!=(folder/'clip-edit.json').read_bytes():raise ValueError('Edit recipe missing from package')
        cases=[]
        for label,path,frames in [('original',parent/'transfer/character.glb',120),('retimed',folder/'transfer/character.glb',61)]:
            cases.append(dict(id=label,path=str(path),sha256=sha256(path),frames=frames,fps=30))
        save(output/'manifest.json',dict(cases=cases));save(output/'pipeline.json',dict(at=now(),status='engine',quality_approved=False))
        engine(output,output/'engine');eproof=read(output/'engine/verification.json')
        if len(eproof['checks'])!=2:raise ValueError('Incomplete engine population')
        for case,check in zip(cases,eproof['checks']):
            if check['id']!=case['id'] or check['source_sha256']!=case['sha256'] or check['frames']!=case['frames']:raise ValueError('Wrong engine source/clock')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
        save(output/'verification.json',dict(at=now(),job=folder.name,parent_job=parent.name,frames=61,
            max_matrix_error=max(errors),original_intent_bytes_preserved=True,manifest_sha256=sha256(folder/'source/motion-origin/manifest.json'),
            package_sha256=sha256(archive),engine_proof_sha256=sha256(output/'engine/verification.json'),engine_actor_frames=181,quality_approved=False))
        save(output/'pipeline.json',dict(at=now(),status='complete',quality_approved=False));print('Verified edited provenance and 181 engine actor-frames',flush=True)
    except BaseException as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.parent,a.output)
