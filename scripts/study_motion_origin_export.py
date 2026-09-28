"""Exercise a real Studio transfer and verify original intent in its download."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback
from urllib.request import Request, urlopen
import zipfile
from strep import ROOT, read, save, sha256, now
from motion_origin import describe, verify


def api(path, payload=None):
    request=Request('http://127.0.0.1:8768'+path,data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8768'})
    with urlopen(request,timeout=30) as response:return json.load(response)


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    (output/'implementation').mkdir()
    names=['motion_origin.py','studio_characters.py','action_studio_server.py','rig_studio_job.py','study_motion_origin_export.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    source=ROOT/'reports/action-jobs/profile-response-v1/takes/kick-high-seed-301'
    baseline=ROOT/'reports/profile-transfer-v1'
    asset=read(baseline/'rigs/rig-01/profile.json')['character_sha256']
    profile=sha256(baseline/'rigs/rig-01/profile.json')
    payload=dict(asset_id=asset,profile_id=profile,kind='transfer',label='Mobility profile provenance verification',
        motion_url='/files/action-jobs/profile-response-v1/takes/kick-high-seed-301/motion.npz',correct_contacts=False)
    expected=describe(source/'motion.npz')
    request=dict(at=now(),payload=payload,expected_origin=expected,baseline_results_sha256=sha256(baseline/'results.json'),
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    try:
        response=api('/api/rig-jobs',payload);save(output/'response.json',response)
        folder=ROOT/'reports/rig-jobs'/response['id'];print('Studio job',response['id'],flush=True)
        # Poll this exact newly-created job; a timeout never restarts the job.
        while True:
            state=read(folder/'pipeline.json')
            save(output/'pipeline.json',dict(at=now(),job=response['id'],worker_status=state,status='waiting_for_exact_studio_job',quality_approved=False))
            if state['status']=='failed':raise ValueError('Studio failed: '+str(state))
            if state['status']=='complete':break
            time.sleep(1)
        result=read(folder/'result.json');pinned=read(folder/'request.json')
        if pinned['motion_origin']!=expected:raise ValueError('API request did not pin original intent')
        verify(folder/'source/motion.npz',folder/'source/motion-origin',expected)
        origin=result['source_generation_origin']
        if origin['applies_to']!='original_source_motion' or origin['quality_approved']:raise ValueError('Intent presented as quality evidence')
        rows=read(baseline/'results.json')
        target=next(r for r in rows['rows'] if r['id']=='kick-high-seed-301-rig-01')
        if target['status']!='complete' or sha256(folder/'transfer/character.glb')!=target['files']['character.glb']:
            raise ValueError('Transfer animation bytes changed from the frozen baseline')
        group=next(g for g in rows['engine_groups'] if g['motion']=='kick-high-seed-301')
        proof_path=Path(group['verification']);proof=read(proof_path)
        if group['status']!='complete' or proof['checks']!=group['checks']:raise ValueError('Baseline engine proof differs')
        check=next(c for c in proof['checks'] if c['id']==target['id'])
        if check['source_sha256']!=sha256(folder/'transfer/character.glb') or check['frames']!=120 or check['bones']!=19:
            raise ValueError('Baseline engine proof does not cover these exact animation bytes')
        archived={}
        with zipfile.ZipFile(folder/'character-animation.zip') as archive:
            if archive.testzip() is not None:raise ValueError('Archive CRC failure')
            for name in archive.namelist():
                if name=='README.txt':continue
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Invalid archive path')
                path=folder/name
                if not path.is_file() or hashlib.sha256(archive.read(name)).hexdigest()!=sha256(path):raise ValueError('Archive differs: '+name)
                archived[name]=sha256(path)
            for name in ['manifest.json',*expected['files']]:
                assert 'source/motion-origin/'+name in archived
            for name in expected['files']:
                if archive.read('source/motion-origin/'+name)!=(source/name).read_bytes():raise ValueError('Original metadata was rewritten')
            assert archive.read('source/motion.npz')==(source/'motion.npz').read_bytes()
            assert 'source/implementation/motion_origin.py' in archived
        downloads={}
        for key in ['manifest','generation_record','request','motion_brief']:
            url=origin[key];body=urlopen('http://127.0.0.1:8768'+url,timeout=30).read()
            name='manifest.json' if key=='manifest' else key.replace('_','-')+'.json'
            digest=hashlib.sha256(body).hexdigest()
            if digest!=sha256(folder/'source/motion-origin'/name):raise ValueError('Downloaded metadata differs')
            downloads[key]=dict(url=url,sha256=digest,bytes=len(body))
        body=urlopen('http://127.0.0.1:8768'+result['package'],timeout=30).read()
        if hashlib.sha256(body).hexdigest()!=result['package_sha256']:raise ValueError('Downloaded archive differs')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
        if sha256(baseline/'results.json')!=request['baseline_results_sha256']:raise ValueError('Baseline evidence changed')
        save(output/'verification.json',dict(at=now(),job=response['id'],job_request_sha256=sha256(folder/'request.json'),
            manifest_sha256=sha256(folder/'source/motion-origin/manifest.json'),archive_files=archived,downloads=downloads,
            package_sha256=result['package_sha256'],animation_bytes_unchanged=True,baseline_engine_proof_sha256=sha256(proof_path),
            baseline_engine_check=check,new_engine_run=False,quality_approved=False))
        save(output/'pipeline.json',dict(at=now(),status='complete',quality_approved=False));print('Verified',len(archived),'archive entries',flush=True)
    except BaseException as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
