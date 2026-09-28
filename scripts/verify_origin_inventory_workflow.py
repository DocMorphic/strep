"""Exercise new transfer, two-donor transition and descendant packages via Studio."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import time
import traceback
import urllib.request
import zipfile
import psutil
from strep import ROOT,read,save,sha256,now
from motion_origin_inventory import collect
from audit_paired_guides import await_owner
from run_godot_rig_import import run as engine


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);base='http://127.0.0.1:8768';jobs=ROOT/'reports/rig-jobs'
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),base=base,primary_job='20260928-015236-7ba359be',
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['motion_origin_inventory.py','motion_origin.py','rig_studio_job.py','rig_transition.py','rig_clip_edit.py','verify_origin_inventory_workflow.py']},quality_approved=False)
    save(output/'request.json',request)
    (output/'implementation').mkdir()
    for name in request['implementation']:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def get(path):return urllib.request.urlopen(base+path,timeout=30).read()
    submissions=[]
    def submit(route,payload,label):
        body=json.dumps(payload).encode();response=json.loads(urllib.request.urlopen(urllib.request.Request(base+route,data=body,headers={'Content-Type':'application/json','Origin':base},method='POST'),timeout=30).read())
        identifier=response['id'];folder=jobs/identifier;submissions.append(dict(label=label,route=route,payload=payload,response=response));save(output/'submissions.json',submissions)
        phase('waiting_for_job',label=label,job=identifier)
        for _ in range(30):
            if (folder/'worker.json').exists():break
            time.sleep(1)
        owner=read(folder/'worker.json');await_owner(owner,'pid','created_at',folder,{'complete'})
        return identifier,folder,read(folder/'result.json')
    def verify_package(identifier,folder,result,expected_sources):
        link=result['generation_sources'];raw=get(link['manifest']);index=json.loads(raw)
        if hashlib.sha256(raw).hexdigest()!=link['manifest_sha256'] or index!=collect(folder):raise ValueError('Downloaded generation index differs')
        if index['distinct_source_records']!=expected_sources or index['recorded_sources']!=expected_sources or index['quality_approved']:
            raise ValueError('Unexpected generation source population')
        if index['applies_to']!='retained_source_snapshots':raise ValueError('Generation history mislabelled')
        blob=get(result['package'])
        if hashlib.sha256(blob).hexdigest()!=result['package_sha256']:raise ValueError('Downloaded package changed')
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            if z.testzip() is not None or z.read('generation-sources.json')!=raw:raise ValueError('Archived generation index differs')
            for entry in index['entries']:
                for location in entry['locations']:
                    for path,digest in {location['motion']:location['motion_sha256'],**location['metadata_files']}.items():
                        if hashlib.sha256(z.read(path)).hexdigest()!=digest:raise ValueError('Archived origin changed: '+path)
                        if hashlib.sha256(get('/files/rig-jobs/'+identifier+'/'+path)).hexdigest()!=digest:raise ValueError('HTTP origin changed: '+path)
                    if 'manifest' in location and hashlib.sha256(z.read(location['manifest'])).hexdigest()!=location['manifest_sha256']:raise ValueError('Archived source manifest changed')
        return dict(job=identifier,index_sha256=link['manifest_sha256'],package_sha256=result['package_sha256'],distinct_sources=expected_sources,retained_locations=index['retained_locations'],source_ids=[e['id'] for e in index['entries']],quality_approved=False)
    try:
        primary=jobs/request['primary_job'];original=read(primary/'request.json');parent=read(primary/'result.json');results=[]
        identifier,folder,result=submit('/api/rig-jobs',dict(asset_id=original['asset_id'],profile_id=original['profile_id'],kind='transfer',
            label='Generation history low-profile source',motion_url='/files/action-jobs/profile-response-v1/takes/kick-low-seed-301/motion.npz',correct_contacts=False),'low-profile transfer')
        results.append(verify_package(identifier,folder,result,1));low_id=identifier;low_folder=folder;low_result=result
        payload=dict(schema='strep-rig-transition-v1',label='Two-profile generation history transition',clips=[
            dict(job=request['primary_job'],variant='transfer',glb_sha256=parent['variants']['transfer']['sha256'],first_frame=10,last_frame=80),
            dict(job=low_id,variant='transfer',glb_sha256=low_result['variants']['transfer']['sha256'],first_frame=10,last_frame=80)],blend_frames=8,yaw_degrees=0)
        transition_id,transition_folder,transition_result=submit('/api/rig-transitions',payload,'two-source transition')
        results.append(verify_package(transition_id,transition_folder,transition_result,2))
        index=read(transition_folder/'generation-sources.json')
        if {e['motion_sha256'] for e in index['entries']}!={original['source_motion_sha256'],read(low_folder/'request.json')['source_motion_sha256']}:raise ValueError('Transition donor identity differs')
        edit=dict(source_job=transition_id,variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',glb_sha256=transition_result['variants']['transfer']['sha256'],
            label='Retimed descendant retains both source histories',start_frame=10,last_frame=110,speed=1.25,poses=[]))
        edit_id,edit_folder,edit_result=submit('/api/rig-clip-edits',edit,'retimed transition')
        results.append(verify_package(edit_id,edit_folder,edit_result,2))
        if results[-1]['source_ids']!=results[-2]['source_ids']:raise ValueError('Descendant lost donor history')
        cases=[]
        for label,p in [('original',primary),('low',low_folder),('transition',transition_folder),('retimed',edit_folder)]:
            report=read(p/'transfer/report.json');path=p/'transfer/character.glb';cases.append(dict(id=label,path=str(path),sha256=sha256(path),frames=report['frames'],fps=30))
        save(output/'manifest.json',dict(cases=cases));phase('engine');engine(output,output/'engine')
        proof=read(output/'engine/verification.json')
        if len(proof['checks'])!=len(cases):raise ValueError('Engine population missing')
        for got,want in zip(proof['checks'],cases):
            if got['id']!=want['id'] or got['frames']!=want['frames'] or got['source_sha256']!=want['sha256']:raise ValueError('Engine input or clock differs')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed: '+name)
        save(output/'verification.json',dict(at=now(),jobs=results,engine_actor_frames=sum(c['frames'] for c in cases),engine_verification_sha256=sha256(output/'engine/verification.json'),
            request_sha256=sha256(output/'request.json'),submissions_sha256=sha256(output/'submissions.json'),quality_approved=False,
            scope='Actual Studio submission, downloaded manifests/archive/source hashes, two donor profiles retained through transition and retiming, all-frame Godot playback. No animation-quality or style-following approval.'))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
