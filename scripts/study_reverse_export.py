"""Verify the reverse-cycle adapter reaches real Studio exports without pose edits."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from urllib.request import urlopen
from strep import ROOT,read,save,sha256,now
from run_event_study import submit


def run(output,prior=None):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'reports/rig-jobs/20260926-222539-831f5a06';variant=source/'transfer'
    original=read(variant/'events.json')
    markers=[dict(id=e['id'],name=e['name'],frame=e['frame'],confirmed=e.get('requires_review') is False) for e in original['events'] if e.get('kind')=='authored']
    payload=dict(schema='strep-rig-events-v1',job=source.name,variant='transfer',glb_sha256=sha256(variant/'character.glb'),label='Authored cycle with reverse runtime support',markers=markers)
    save(output/'pipeline.json',dict(status='submitting',at=now()))
    try:
        if prior is None:
            folder=submit('/api/rig-events',payload,output,'export')
        else:
            # Re-verify the already completed real job; do not submit duplicates
            # when only the external package verifier needed a correction.
            prior=Path(prior).resolve()
            assert read(prior/'export-request.json')==payload
            job=read(prior/'export-job.json');folder=ROOT/'reports/rig-jobs'/job['id']
            assert read(folder/'pipeline.json')['status']=='complete'
            save(output/'export-request.json',payload);save(output/'export-job.json',job)
        result=read(folder/'result.json');target=folder/'transfer';meta=read(target/'runtime-cycle.json')
        assert sha256(target/'character.glb')==payload['glb_sha256']
        assert sha256(target/'root-motion.json')==sha256(variant/'root-motion.json')
        assert sha256(folder/'repeated/character.glb')==sha256(source/'repeated/character.glb')
        assert meta['playback']['reverse_method']=='rewind' and meta['playback']['reverse_default']=='silent'
        assert meta['playback']['reverse_notifications_undo_gameplay'] is False
        assert sha256(target/'godot_cycle_adapter.gd')==sha256(ROOT/'scripts/godot_cycle_adapter.gd')
        assert sha256(target/'GODOT-CYCLES.md')==sha256(ROOT/'integrations/godot/CYCLES.md')
        assert [e['name'] for e in meta['markers']]==[e['name'] for e in read(variant/'runtime-cycle.json')['markers']]
        assert sha256(folder/'character-animation.zip')==result['package_sha256']
        with zipfile.ZipFile(folder/'character-animation.zip') as archive:
            assert archive.testzip() is None
            checked={};generated={}
            for name in archive.namelist():
                if name.endswith('/'):continue
                if name=='README.txt':
                    body=archive.read(name);note=body.decode('utf8')
                    assert 'No independent animator or engine approval.' in note
                    assert 'The source asset retains its own licensing.' in note
                    generated[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
                    (output/'package-README.txt').write_bytes(body)
                    continue
                path=folder/name
                assert path.is_file(),name
                assert archive.read(name)==path.read_bytes(),name
                checked[name]=sha256(path)
            for name in ['transfer/runtime-cycle.json','transfer/godot_cycle_adapter.gd','transfer/GODOT-CYCLES.md']:
                assert name in checked,name
        downloads={}
        for key,path in [('runtime_cycle',target/'runtime-cycle.json'),('runtime_adapter',target/'godot_cycle_adapter.gd'),('runtime_readme',target/'GODOT-CYCLES.md'),('package',folder/'character-animation.zip')]:
            body=urlopen('http://127.0.0.1:8768'+result[key],timeout=30).read();digest=hashlib.sha256(body).hexdigest()
            assert digest==sha256(path);downloads[key]=dict(url=result[key],sha256=digest,bytes=len(body))
        save(output/'verification.json',dict(at=now(),job=folder.name,source_job=source.name,request_sha256=sha256(output/'export-request.json'),result_sha256=sha256(folder/'result.json'),
            unchanged_glb_sha256=payload['glb_sha256'],unchanged_repeated_glb_sha256=sha256(folder/'repeated/character.glb'),
            package_sha256=result['package_sha256'],archive_files=checked,generated_archive_entries=generated,downloads=downloads,quality_approved=False,
            scope='Actual Studio event-only export preserving prior authored timing and both GLBs; updated adapter/contract/metadata, all source-backed archive bytes and HTTP downloads. Generated README is captured with hash and checked caveats. Reverse playback is separately audited in runtime-reverse-v2; no new motion-quality or gameplay reversal claim.'))
        save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False));print(folder.name,len(checked))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--prior',type=Path);a=p.parse_args();run(a.output,a.prior)
