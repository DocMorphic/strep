"""Frozen rig/action transfer matrix, executed through the actual local Studio API."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from strep import ROOT,read,save,sha256,now

HOST='http://127.0.0.1:8768'


def api(path,data=None):
    request=Request(HOST+path,data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type':'application/json','Origin':HOST})
    with urlopen(request,timeout=60) as response:return json.load(response)


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(exist_ok=False)
    from studio_characters import import_bytes,save_profile
    rigs=[]
    catalog=read(ROOT/'assets/characters/catalog.json')['characters']
    for fixture in catalog:
        character=ROOT/fixture['file'];profile=ROOT/fixture['profile']
        imported=import_bytes(character.read_bytes(),character.name)
        saved=save_profile(dict(asset_id=imported['id'],profile=read(profile)))
        rigs.append(dict(name=character.stem,family='cesium' if 'cesium-man' in fixture['file'] else 'quaternius-base',
            asset_id=imported['id'],profile_id=saved['profile_id']))
    actions=['jump-land','crawl','dance','wave','kick','get-up','run-roll-stand']
    requests=[]
    for rig in rigs:
        for action in actions:
            motion_url='/files/action-jobs/body-holdout-seed77/takes/'+action+'-seed-77/motion.npz'
            source=ROOT/'reports'/motion_url.removeprefix('/files/')
            requests.append(dict(rig=rig['name'],family=rig['family'],action=action,seed=77,source_sha256=sha256(source),
                payload=dict(asset_id=rig['asset_id'],profile_id=rig['profile_id'],kind='transfer',motion_url=motion_url,
                    label=rig['name']+' · '+action+' · seed 77',correct_contacts=False)))
    save(folder/'request.json',dict(created_at=now(),rigs=rigs,cases=requests,
        scope='Development transfer-only matrix. Same 7 existing raw SOMA clips, 3 assets, 2 rig families. No contact fitting or per-motion profile tuning; no independent animator approval.',
        script_sha256=sha256(__file__)))
    manifest=dict(cases=[],jobs=[],failures=[],request_sha256=sha256(folder/'request.json'))
    save(folder/'pipeline.json',dict(status='processing',total=len(requests)))
    for i,item in enumerate(requests):
        # Waiting observes the server's live worker; a previous completed job can
        # have a brief process-exit tail. Never retry a submitted/unknown POST.
        while api('/api/studies')['busy']:time.sleep(1)
        job=api('/api/rig-jobs',item['payload']);identifier=job['id']
        manifest['jobs'].append(dict(id=identifier,**item));save(folder/'manifest.json',manifest)
        while True:
            current=next(j for j in api('/api/rig-jobs')['jobs'] if j['id']==identifier)
            if current['status'] in ('complete','failed'):break
            time.sleep(1)
        if current['status']=='failed':
            manifest['failures'].append(dict(job=identifier,error=current.get('error'),**item))
        else:
            result=current['result'];variant=result['variants']['transfer']
            output=ROOT/'reports'/variant['glb'].removeprefix('/files/')
            if sha256(output)!=variant['sha256']:raise ValueError('Served job output changed')
            report=read(output.parent/'report.json')
            manifest['cases'].append(dict(id=identifier,path='../rig-jobs/'+identifier+'/transfer/character.glb',
                sha256=variant['sha256'],frames=result['frames'],fps=result['fps'],rig=item['rig'],family=item['family'],
                action=item['action'],floor_depth_m=report['target_mesh_floor_depth_max_m'],
                floor_frames_over_1cm=report['target_mesh_floor_frames_above_1cm'],
                predicted_contact_foot_speed=report['predicted_contact_foot_speed'],
                package_sha256=result['package_sha256'],source_sha256=result['source_motion_sha256']))
        save(folder/'manifest.json',manifest)
        save(folder/'pipeline.json',dict(status='processing',finished=i+1,total=len(requests)))
        print(f"{i+1}/{len(requests)} {item['rig']} {item['action']} {current['status']}",flush=True)
    save(folder/'pipeline.json',dict(status='complete',finished=len(requests),failed=len(manifest['failures']),finished_at=now()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output)
