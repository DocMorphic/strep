"""Compare a neutral-only height calibration against a frozen transfer matrix."""
import argparse
import shutil
from pathlib import Path
from calibrate_rig_height import calibrate
from rig_studio_job import run as worker
from strep import ROOT,read,save,sha256,now


def run(baseline,output):
    baseline,output=Path(baseline).resolve(),Path(output).resolve();output.mkdir(exist_ok=False)
    before=read(baseline/'manifest.json');profiles={};calibrations={};requests=[]
    for item in before['jobs']:
        if item['rig'] not in profiles:
            source=ROOT/'reports/rig-jobs'/item['id']/'source';profile=output/'profiles'/(item['rig']+'.json')
            calibrations[item['rig']]=calibrate(source/'character.glb',source/'rig-profile.json',profile);profiles[item['rig']]=profile
        requests.append(dict(**item,calibrated_profile_sha256=sha256(profiles[item['rig']])))
    save(output/'request.json',dict(created_at=now(),baseline_manifest_sha256=sha256(baseline/'manifest.json'),cases=requests,calibrations=calibrations,
        scope='Same clips reused for a diagnostic comparison; not a new held-out study. Profiles calibrated from neutral source/target meshes only. No default promotion.'))
    manifest=dict(cases=[],jobs=[],failures=[],request_sha256=sha256(output/'request.json'))
    save(output/'pipeline.json',dict(status='processing',total=len(requests)))
    for number,item in enumerate(requests):
        identifier=output.name+'-'+str(number+1).zfill(2);folder=ROOT/'reports/rig-jobs'/identifier
        folder.mkdir(exist_ok=False);source=folder/'source';shutil.copytree(ROOT/'reports/rig-jobs'/item['id']/'source',source,
            ignore=shutil.ignore_patterns('implementation'))
        shutil.copyfile(profiles[item['rig']],source/'rig-profile.json')
        shutil.copyfile(profiles[item['rig']].with_suffix('.calibration.json'),source/'height-calibration.json')
        request=read(ROOT/'reports/rig-jobs'/item['id']/'request.json')
        request.update(profile_id=sha256(source/'rig-profile.json'),label=item['rig']+' · '+item['action']+' · neutral height')
        save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'))
        manifest['jobs'].append(dict(id=identifier,baseline_id=item['id'],rig=item['rig'],family=item['family'],action=item['action']))
        try:
            worker(folder);result=read(folder/'result.json');report=read(folder/'transfer/report.json')
            manifest['cases'].append(dict(id=identifier,baseline_id=item['id'],rig=item['rig'],family=item['family'],action=item['action'],
                path='../rig-jobs/'+identifier+'/transfer/character.glb',sha256=result['variants']['transfer']['sha256'],frames=result['frames'],fps=result['fps'],
                floor_depth_m=report['target_mesh_floor_depth_max_m'],floor_frames_over_1cm=report['target_mesh_floor_frames_above_1cm'],
                predicted_contact_foot_speed=report['predicted_contact_foot_speed'],package_sha256=result['package_sha256'],source_sha256=result['source_motion_sha256']))
        except Exception as exc:manifest['failures'].append(dict(id=identifier,error=str(exc)))
        save(output/'manifest.json',manifest);save(output/'pipeline.json',dict(status='processing',finished=number+1,total=len(requests)))
        print(identifier,item['rig'],item['action'],read(folder/'pipeline.json')['status'],flush=True)
    save(output/'pipeline.json',dict(status='complete',finished=len(requests),failed=len(manifest['failures']),finished_at=now()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('baseline',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.baseline,args.output)
