"""Exercise retained generation intent using only a relocated installation.

External fixtures are explicit data inputs copied locally before any job runs.
"""
import argparse
from pathlib import Path
import shutil
import sys
import zipfile
import hashlib
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now


def run(fixtures):
    if not (ROOT/'installation.json').is_file() or not Path(sys.executable).resolve().is_relative_to(ROOT):
        raise ValueError('Use the relocated installation runtime')
    from studio_characters import import_bytes, save_profile, validate_job, asset_folder, JOBS
    from action_studio_server import allowed_file
    from motion_origin import describe, snapshot
    from motion_origin_inventory import collect
    from rig_studio_job import run as run_job
    from rig_transition import prepare as transition
    from rig_clip_edit import prepare as edit
    from run_godot_rig_import import run as engine
    from build_desktop import render
    fixtures=Path(fixtures).resolve();inputs=read(fixtures)
    if set(inputs['sources'])!={'high','low'}:raise ValueError('Exact high/low fixture population required')
    output=ROOT/'reports/offline-generation-history-v1';output.mkdir(parents=True,exist_ok=False)
    save(output/'request.json',dict(at=now(),fixture_manifest_sha256=sha256(fixtures),fixtures=inputs,
        runtime=sys.executable,driver_sha256=sha256(__file__),installation_sha256=sha256(ROOT/'installation.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status='copying_inputs',at=now(),quality_approved=False))
    local={}
    for key, files in inputs['sources'].items():
        if set(files)!={'motion.npz','generation-record.json','request.json','motion-brief.json'}:
            raise ValueError('Unexpected generation fixture file set')
        folder=ROOT/'reports/action-jobs/offline-origin-fixtures/takes'/key;folder.mkdir(parents=True,exist_ok=False)
        for name,item in files.items():
            if sha256(item['path'])!=item['sha256']:raise ValueError('Fixture changed: '+name)
            shutil.copyfile(item['path'],folder/name)
            if sha256(folder/name)!=item['sha256']:raise ValueError('Copied fixture differs')
        local[key]=folder/'motion.npz'
        if describe(local[key])['status']!='recorded':raise ValueError('Fixture origin unavailable')
    asset_path=ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    asset=import_bytes(asset_path.read_bytes(),asset_path.name)
    profile=save_profile(dict(asset_id=asset['id'],profile=asset['profile']))
    packages=[];cases=[];source_ids=[]

    def check(folder, expected):
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Portable job incomplete')
        result=read(folder/'result.json');index=collect(folder)
        if index!=read(folder/'generation-sources.json') or index['recorded_sources']!=expected or index['distinct_source_records']!=expected:
            raise ValueError('Generation-source population differs')
        if sha256(folder/'generation-sources.json')!=result['generation_sources']['manifest_sha256']:
            raise ValueError('Result/index checksum differs')
        with zipfile.ZipFile(folder/'character-animation.zip') as z:
            if z.testzip() or z.read('generation-sources.json')!=(folder/'generation-sources.json').read_bytes():
                raise ValueError('Package index differs')
            for entry in index['entries']:
                for loc in entry['locations']:
                    files={loc['motion']:loc['motion_sha256'],**loc['metadata_files']}
                    if 'manifest' in loc:files[loc['manifest']]=loc['manifest_sha256']
                    for name,digest in files.items():
                        if not (folder/name).resolve().is_relative_to(folder):raise ValueError('Package path escapes installation')
                        if hashlib.sha256(z.read(name)).hexdigest()!=digest or sha256(folder/name)!=digest:
                            raise ValueError('Package origin bytes differ')
        ids=sorted(e['id'] for e in index['entries']);source_ids.append(ids)
        packages.append(dict(job=folder.name,distinct_sources=expected,retained_locations=index['retained_locations'],source_ids=ids,
            index_sha256=sha256(folder/'generation-sources.json'),package_sha256=sha256(folder/'character-animation.zip')))
        report=read(folder/'transfer/report.json');glb=folder/'transfer/character.glb'
        cases.append(dict(id=folder.name,path=str(glb),sha256=sha256(glb),frames=report['frames'],fps=30))
        return result

    parents={}
    for key,motion in local.items():
        request,source,mapping=validate_job(dict(asset_id=asset['id'],profile_id=profile['profile_id'],kind='transfer',
            label='Portable original profile '+key,motion_url='/files/'+motion.relative_to(ROOT/'reports').as_posix(),correct_contacts=False),allowed_file)
        folder=JOBS/('offline-origin-'+key+'-v1');(folder/'source').mkdir(parents=True,exist_ok=False)
        stored=asset_folder(asset['id'])
        shutil.copyfile(stored/'character.glb',folder/'source/character.glb');shutil.copyfile(mapping,folder/'source/rig-profile.json')
        shutil.copyfile(source,folder/'source/motion.npz');snapshot(source,folder/'source/motion-origin',describe(source))
        for name in ['asset.json','LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md','provenance.json']:
            if (stored/name).exists():shutil.copyfile(stored/name,folder/'source'/name)
        save(folder/'request.json',request);run_job(folder);parents[key]=(folder,check(folder,1))
    joined=JOBS/'offline-origin-transition-v1'
    payload=dict(schema='strep-rig-transition-v1',label='Portable two-profile join',clips=[dict(job=parents[k][0].name,
        variant='transfer',glb_sha256=parents[k][1]['variants']['transfer']['sha256'],first_frame=10,last_frame=80) for k in ['high','low']],blend_frames=8,yaw_degrees=0)
    transition(payload,joined);run_job(joined);joined_result=check(joined,2)
    if set(source_ids[-1])!=set(source_ids[0]+source_ids[1]):raise ValueError('Joined record identities changed')
    edited=JOBS/'offline-origin-retimed-v1'
    edit(dict(source_job=joined.name,variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',
        glb_sha256=joined_result['variants']['transfer']['sha256'],label='Portable retained history',start_frame=10,last_frame=110,speed=1.25,poses=[])),edited)
    run_job(edited);check(edited,2)
    if source_ids[-1]!=source_ids[-2]:raise ValueError('Descendant lost generation history')
    save(output/'manifest.json',dict(cases=cases));engine(output,output/'engine')
    checks=read(output/'engine/verification.json')['checks']
    if len(checks)!=4:raise ValueError('Incomplete engine population')
    for got,want in zip(checks,cases):
        if got['id']!=want['id'] or got['frames']!=want['frames'] or got['source_sha256']!=want['sha256']:
            raise ValueError('Engine input differs')
    modules={n:str(sys.modules[n].__file__) for n in ['strep','motion_origin','motion_origin_inventory','rig_studio_job','rig_transition','rig_clip_edit','numpy']}
    if any(not Path(p).resolve().is_relative_to(ROOT) for p in modules.values()):raise ValueError('Workflow imported external code')
    if render()!=(ROOT/'scripts/action-studio.html').read_text(encoding='utf8'):raise ValueError('Installed UI bundle differs from its sources')
    save(output/'completion.json',dict(at=now(),packages=packages,modules=modules,engine_actor_frames=sum(c['frames'] for c in cases),
        engine_sha256=sha256(output/'engine/verification.json'),ui_bundle_sha256=sha256(ROOT/'scripts/action-studio.html'),
        quality_approved=False,new_model_inference=False,scope='Same-laptop offline relocation, original source metadata carried through2transfers/join/retime and actual engine import. Explicit copied fixtures; no new generation, UI interaction, second-machine or animation-quality approval.'))
    save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('fixtures',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.fixtures)
