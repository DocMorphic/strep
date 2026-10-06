"""Source-preserving root/contact/gameplay packages from completed scene jobs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now,offline_environment
import studio_native_scene as scenes
from native_scene_contacts import SceneContacts,fields
from native_engine_clock import check_clock_wire
from native_scene_game_tracks import validate as validate_tracks,export as export_tracks,crossed,event_plan
from native_object_scene_engine import load
from action_worker_lock import worker_lock

NAMESPACE='native-scene-game-jobs'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(scenes.METHODS+('native_scene_game_tracks.py','studio_native_scene_game.py',
    'godot_scene_game_events.gd','godot_scene_game_event_audit.gd')))
DOWNLOADS=('game-assets.zip','tracks/root-motion.json','tracks/root-observations.npz','tracks/contacts.json',
    'tracks/events.json','tracks/result.json','runtime-events/result.json','result.json')


def require(condition,message):
    if not condition:raise ValueError(message)


def folder_for(job):
    require(isinstance(job,str) and scenes.NAME.fullmatch(job),'Invalid native game asset job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Game job escapes namespace');return folder


def source(job):
    manifest=scenes.manifest(job);require(manifest['status']=='complete','Select a complete native scene job')
    folder=scenes.folder_for(job);result=read(folder/'authoring/result.json')
    contacts=Path(result['artifacts']['active_contacts']).resolve()
    require(contacts.is_relative_to(folder),'Source contacts escape scene job')
    spec=read(contacts)
    policy=folder/'authoring/objects-common/common-policy.json' if spec['objects'] else folder/'geometry-policy.json'
    scene=SceneContacts(spec,contacts.parent);request=read(folder/'authoring/actors-engine/request.json')
    times=np.asarray(request['sample_times_s'],dtype='<f8');check_clock_wire(request['sample_clock'],times)
    receipt=read(folder/'authoring/actors-engine/raw-engine-receipt.json')
    require(sha256(folder/'authoring/actors-engine/request.json')==receipt['request_sha256'],'Source actor clock request changed')
    require(times[0]==0 and times[-1]==scene.duration and len(times)==manifest['samples'],'Complete source scene clock required')
    return folder,manifest,spec,scene,contacts,policy,times


def method_names(scene,*,corrections=False,transitions=False):
    result=METHODS if scene.objects else METHODS+('verify_native_actor_scene_engine.py',)
    if corrections:
        from studio_native_scene_fit import METHODS as CORRECTION_METHODS
        result=tuple(dict.fromkeys(result+CORRECTION_METHODS+('native_correction_lineage.py',)))
    if transitions:
        from studio_native_scene_transition import METHODS as TRANSITION_METHODS
        result=tuple(dict.fromkeys(result+TRANSITION_METHODS+('native_transition_lineage.py',)))
    return result


def measured_contacts(folder, scene):
    path=folder/'authoring/combined-engine/native-authoring-contacts.json' if scene.objects else folder/'authoring/actors-engine/result.json'
    value=read(path)
    return (value if scene.objects else value['imported_contacts']),path


def metadata(job):
    folder,manifest,spec,scene,contacts,policy,times=source(job)
    return dict(scene_job=job,source_result_sha256=manifest['result_sha256'],times_s=times.tolist(),
        actors={name:dict(glb_sha256=spec['actors'][name]['sha256'],animation_index=actor['animation_index'],
            joints=[dict(node=n,name=actor['rig'].document['nodes'][n].get('name','Joint '+str(n))) for n in actor['rig'].joints])
            for name,actor in scene.actors.items()},quality_approved=False,
        root_application_mode='reference-only-motion-remains-embedded')


def validate_request(payload):
    fields(payload,('scene_job','source_result_sha256','request'),'selected native game package')
    values=source(payload['scene_job']);require(values[1]['result_sha256']==payload['source_result_sha256'],'Selected scene result changed')
    validate_tracks(payload['request'],values[3],values[6]);return values


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh native game package job required')
    values=validate_request(payload);source_folder,manifest,spec,scene,contacts,policy,times=values
    engine=Path(read(source_folder/'prepared.json')['engine_path']).resolve()
    methods={n:sha256(SCRIPT_ROOT/n) for n in method_names(scene,corrections=read(source_folder/'prepared.json').get('correction_lineage') is not None,transitions=read(source_folder/'prepared.json').get('transition_lineage') is not None)}
    folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        save(folder/'request.json',payload);archive=folder/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,archive/n)
        shutil.copyfile(source_folder/'assets.zip',folder/'source-assets.zip')
        require(sha256(folder/'source-assets.zip')==sha256(source_folder/'assets.zip'),'Scene package changed during snapshot')
        prepared=dict(schema='strep-native-scene-game-prepared-v1',request_sha256=sha256(folder/'request.json'),
            correction_lineage_included=read(source_folder/'prepared.json').get('correction_lineage') is not None,
            source_completion_sha256=sha256(source_folder/'completion.json'),source_assets_sha256=sha256(folder/'source-assets.zip'),
            engine_path=str(engine),engine_sha256=sha256(engine),implementation_sha256=methods,
            original_selected=True,quality_approved=False,training_admitted=False,release_approved=False)
        save(folder/'prepared.json',prepared);frozen(folder)
        save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False));return prepared
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Native game asset folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json')
    require(p['schema']=='strep-native-scene-game-prepared-v1' and p['request_sha256']==sha256(folder/'request.json')
        and p['original_selected'] is True and all(p[k] is False for k in ('quality_approved','training_admitted','release_approved')),'Game package preparation changed')
    values=validate_request(payload);source_folder=values[0]
    require(sha256(source_folder/'completion.json')==p['source_completion_sha256'] and
        sha256(source_folder/'assets.zip')==sha256(folder/'source-assets.zip')==p['source_assets_sha256'],'Game package source changed')
    expected_methods=set(method_names(values[3],corrections=read(source_folder/'prepared.json').get('correction_lineage') is not None,transitions=read(source_folder/'prepared.json').get('transition_lineage') is not None))
    require(p.get('correction_lineage_included',False) is (read(source_folder/'prepared.json').get('correction_lineage') is not None),
        'Game correction lineage selection changed')
    legacy=not current_methods and 'native_contact_revision.py' not in p['implementation_sha256'] and 'contact_revision' not in read(source_folder/'draft.json')
    if legacy:expected_methods.remove('native_contact_revision.py')
    if not current_methods and 'correction_lineage_included' not in p and 'native_correction_lineage.py' not in p['implementation_sha256']:
        expected_methods.remove('native_correction_lineage.py')
    require(set(p['implementation_sha256'])==expected_methods,'Complete game package method population required')
    for name,digest in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/name)==digest,'Game package method archive changed')
        if current_methods:require(sha256(SCRIPT_ROOT/name)==digest,'Game package implementation changed')
    require(Path(p['engine_path'])==Path(read(source_folder/'prepared.json')['engine_path'])
        and sha256(p['engine_path'])==p['engine_sha256'],'Game package engine changed')
    return p,values


def engine_audit(events_path,folder,engine):
    folder.mkdir();project=folder/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep game event audit"\n',encoding='utf8')
    for n in ('godot_scene_game_event_audit.gd','godot_scene_game_events.gd','native_engine_clock.gd'):
        shutil.copyfile(SCRIPT_ROOT/n,project/('audit.gd' if n=='godot_scene_game_event_audit.gd' else n))
    events=read(events_path);count=events['clock']['count'];indices=list(range(count))
    scenarios=[dict(id='whole-clip',indices=[0,count-1]),dict(id='every-sample',indices=indices),
        dict(id='skipped-samples',indices=sorted(set([0,count//4,count//2,3*count//4,count-1]))),
        dict(id='repeated-seeks',indices=[i for i in indices for _ in range(2)])]
    request=dict(events_path=str(events_path.resolve()),scenarios=scenarios);save(folder/'request.json',request)
    command=[str(engine),'--headless','--path',str(project),'--script','res://audit.gd','--',str((folder/'request.json').resolve()),str((folder/'engine-output.json').resolve())]
    with (folder/'engine.log').open('w',encoding='utf8') as log:
        process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=offline_environment(),timeout=120,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    require(process.returncode==0,'Game event engine audit failed; logs retained')
    actual=read(folder/'engine-output.json');times=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    require(set(actual['traces'])=={s['id'] for s in scenarios} and actual['invalid_rejected'] is True
        and actual['malformed_configs_rejected'] is True and actual['malformed_config_cases']==6,'Complete event audit traces and rejection cases required')
    for scenario in scenarios:
        expected=[];previous=None
        for index in scenario['indices']:
            current=float(times[index]);expected.extend(crossed(events,previous,current));previous=current
        require(actual['traces'][scenario['id']]==expected,'Godot event trace differs from declared timing/confirmation')
    result=dict(status='complete',engine=actual['engine'],traces_exact=True,scenarios=len(scenarios),
        invalid_clock_changes_rejected=True,malformed_event_cases_rejected=6,
        gameplay_event_dispatch_verified=True,animation_runtime_playback_verified=False,physics_verified=False,
        quality_approved=False,release_approved=False,events_sha256=sha256(events_path),engine_sha256=sha256(engine),
        files_sha256={n:sha256(folder/n) for n in ('request.json','engine-output.json','engine.log')},
        executed_scripts_sha256={n:sha256(project/('audit.gd' if n=='godot_scene_game_event_audit.gd' else n))
            for n in ('godot_scene_game_event_audit.gd','godot_scene_game_events.gd','native_engine_clock.gd')},
        scope='Actual finite event-helper dispatch for confirmed gameplay intent across full/skipped/repeated seeks; no motion, attachment, rendering or gameplay semantics approval.')
    save(folder/'result.json',result);return result


def combine_package(folder,tracks,event_result,source_result):
    extra={n:folder/'tracks'/n for n in ('root-motion.json','root-observations.npz','contacts.json','events.json')}
    extra['game-tracks-request.json']=folder/'tracks/request.json'
    extra['runtime/godot_scene_game_events.gd']=folder/'implementation/godot_scene_game_events.gd'
    extra['runtime/native_engine_clock.gd']=folder/'implementation/native_engine_clock.gd'
    receipts={n:sha256(path) for n,path in extra.items()}
    with zipfile.ZipFile(folder/'source-assets.zip') as source,zipfile.ZipFile(folder/'game-assets.zip','x',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as output:
        original=json.loads(source.read('package.json'))
        require(original['schema']=='strep-native-scene-asset-package-v1' and original['root_event_tracks_included'] is False,'Original scene package required')
        require(len(source.namelist())==len(set(source.namelist())) and set(source.namelist())==set(original['files_sha256'])|{'package.json'},'Complete original package population required')
        require(not set(original['files_sha256']).intersection(set(extra)|{'source-package.json'}),'Game package file collision')
        for name in source.namelist():
            destination='source-package.json' if name=='package.json' else name;digest=hashlib.sha256()
            with source.open(name) as src,output.open(destination,'w',force_zip64=True) as dst:
                for chunk in iter(lambda:src.read(1024*1024),b''):digest.update(chunk);dst.write(chunk)
            value=digest.hexdigest()
            if name!='package.json':require(value==original['files_sha256'][name],'Original package entry changed')
            receipts[destination]=value
        for name,path in extra.items():output.write(path,name)
        manifest=dict(schema='strep-native-scene-game-package-v1',files_sha256=receipts,
            selected_animations=original['selected_animations'],root_event_tracks_included=True,root_removed_from_character_clips=False,
            root_application_mode='reference-only-motion-remains-embedded',sampled_scene_conditions_pass=source_result['sampled_conditions_pass'],
            root_samples_pass=tracks['all_root_samples_pass'],event_helper_dispatch_verified=event_result['gameplay_event_dispatch_verified'],
            animation_runtime_playback_verified=False,original_selected=True,quality_approved=False,physics_verified=False,release_approved=False,
            scope='Original scene assets plus complete root references, declared contact intent, explicit gameplay timing and tested finite Godot dispatcher. Apply no second root track to clips with embedded motion; no automatic physical interaction or human-quality approval.')
        save(folder/'package.json',manifest);output.write(folder/'package.json','package.json')
    with zipfile.ZipFile(folder/'game-assets.zip') as stored:
        require(set(stored.namelist())==set(receipts)|{'package.json'},'Complete game ZIP population required')
        for name in stored.namelist():
            expected=sha256(folder/'package.json') if name=='package.json' else receipts[name]
            digest=hashlib.sha256()
            with stored.open(name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            require(digest.hexdigest()==expected,'Game ZIP bytes differ')
    return manifest


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Native game asset folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not (folder/'worker.json').exists()
        and not (folder/'tracks').exists() and not (folder/'runtime-events').exists() and not (folder/'completion.json').exists(),'Fresh prepared game worker required')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        p,values=frozen(folder);source_folder,manifest,spec,scene,contacts,policy,times=values
        with worker_lock(),threadpool_limits(limits=1):
            save(folder/'pipeline.json',dict(status='processing',stage='root-contact-tracks',original_selected=True,quality_approved=False))
            if scene.objects:
                scene,policy_value,actor,providers,loaded_times,bindings=load(contacts,policy,source_folder/'authoring/actors-engine',source_folder/'authoring/objects-engine')
            else:
                from verify_native_actor_scene_engine import load as actor_load
                scene,policy_value,actor,loaded_times,bindings=actor_load(contacts,policy,source_folder/'authoring/actors-engine')
            require(np.array_equal(times,loaded_times),'Complete unchanged source clock required')
            contact_value,contact_report=measured_contacts(source_folder,scene)
            with zipfile.ZipFile(folder/'source-assets.zip') as package:
                portable_digest=hashlib.sha256(package.read('scene.json')).hexdigest()
            tracks=export_tracks(scene,read(folder/'request.json')['request'],times,actor.worlds,contact_value,folder/'tracks',
                source_spec=spec,portable_scene_sha256=portable_digest,contact_report_sha256=sha256(contact_report))
            frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='runtime-event-helper',original_selected=True,quality_approved=False))
            events=engine_audit(folder/'tracks/events.json',folder/'runtime-events',Path(p['engine_path']))
            frozen(folder);combine_package(folder,tracks,events,read(source_folder/'authoring/result.json'))
            frozen(folder)
        result=dict(schema='strep-native-scene-game-job-v1',status='complete',source_scene_job=source_folder.name,
            source_result_sha256=manifest['result_sha256'],prepared_sha256=sha256(folder/'prepared.json'),
            samples=tracks['samples'],root_samples_pass=tracks['all_root_samples_pass'],scene_sampled_conditions_pass=manifest['sampled_conditions_pass'],
            event_helper_dispatch_verified=events['gameplay_event_dispatch_verified'],original_selected=True,studio_selection_changed=False,
            quality_approved=False,physics_verified=False,animation_runtime_playback_verified=False,training_admitted=False,release_approved=False,
            files_sha256={n:sha256(folder/n) for n in DOWNLOADS if n!='result.json'})
        save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json'),package_sha256=sha256(folder/'package.json')))
        save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return result
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json')
    data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,original_selected=True)
    if state['status']!='complete':return data
    p,values=frozen(folder,current_methods=False);r=read(folder/'result.json');completion=read(folder/'completion.json')
    require(r['schema']=='strep-native-scene-game-job-v1' and r['status']=='complete' and r['prepared_sha256']==sha256(folder/'prepared.json')
        and sha256(folder/'result.json')==completion['result_sha256'] and sha256(folder/'package.json')==completion['package_sha256'],'Game completion changed')
    require(r['source_scene_job']==values[0].name and r['source_result_sha256']==values[1]['result_sha256']
        and r['original_selected'] is True and all(r[k] is False for k in ('studio_selection_changed','quality_approved','physics_verified',
        'animation_runtime_playback_verified','training_admitted','release_approved')),'Game approval/source choice changed')
    require(set(r['files_sha256'])==set(DOWNLOADS)-{'result.json'},'Complete fixed game download population required')
    for name,digest in r['files_sha256'].items():require(sha256(folder/name)==digest,'Game download changed')
    for stage in ('tracks','runtime-events'):
        record=read(folder/stage/'result.json');require(record['status']=='complete','Complete game stages required')
        require(all(record[k] is False for k in ('quality_approved','physics_verified','release_approved')),'Game stage approval changed')
        for name,digest in record['files_sha256'].items():
            path=(folder/stage/name).resolve();require(path.is_relative_to(folder/stage) and sha256(path)==digest,'Game stage artifact changed')
    runtime=read(folder/'runtime-events/result.json')
    require(set(runtime['executed_scripts_sha256'])=={'godot_scene_game_event_audit.gd','godot_scene_game_events.gd','native_engine_clock.gd'}
        and runtime['events_sha256']==sha256(folder/'tracks/events.json') and runtime['engine_sha256']==p['engine_sha256'],'Complete bound game event execution required')
    for name,digest in runtime['executed_scripts_sha256'].items():
        require(digest==p['implementation_sha256'][name] and sha256(folder/'runtime-events/project'/('audit.gd' if name=='godot_scene_game_event_audit.gd' else name))==digest,'Executed game event helper changed')
    require(r['samples']==len(values[6]) and r['root_samples_pass'] is read(folder/'tracks/result.json')['all_root_samples_pass']
        and r['scene_sampled_conditions_pass'] is values[1]['sampled_conditions_pass']
        and r['event_helper_dispatch_verified'] is runtime['gameplay_event_dispatch_verified'],'Game stage decisions differ')
    require(read(folder/'tracks/request.json')==read(folder/'request.json')['request'],'Game track choices changed')
    with zipfile.ZipFile(folder/'source-assets.zip') as archive:
        portable_digest=hashlib.sha256(archive.read('scene.json')).hexdigest()
    expected_events,expected_contacts=event_plan(values[3],read(folder/'tracks/request.json'),values[6],measured_contacts(values[0],values[3])[0])
    expected_events['portable_scene_sha256']=portable_digest
    expected_contacts.update(portable_scene_sha256=portable_digest,
        contact_report_sha256=sha256(measured_contacts(values[0],values[3])[1]))
    require(read(folder/'tracks/events.json')==expected_events and read(folder/'tracks/contacts.json')==expected_contacts,'Game contact/marker intent differs from original choices')
    roots=read(folder/'tracks/root-motion.json');request=read(folder/'tracks/request.json')
    require(roots['times_s']==values[6].tolist() and set(roots['actors'])==set(request['actors'])
        and roots['portable_scene_sha256']==portable_digest and roots['application_mode']=='reference-only-motion-remains-embedded'
        and roots['quality_approved'] is False and roots['release_approved'] is False,'Root reference clock/application mode changed')
    with np.load(folder/'tracks/root-observations.npz',allow_pickle=False) as arrays:
        require(arrays['times_s'].dtype==np.dtype('<f8') and arrays['times_s'].tobytes()==values[6].tobytes(),'Root binary clock changed')
        expected_keys={'times_s'}
        for i,name in enumerate(values[2]['actors']):
            choice=request['actors'][name]
            entry=roots['actors'][name];prefix=f'actor_{i}';expected_keys.update(prefix+'_'+suffix for suffix in ('world_matrices','initial_local_deltas','imported_world_matrices'))
            require(entry['root_node']==choice['root_node'] and entry['animation_index']==values[2]['actors'][name]['animation_index']
                and entry['character_glb_sha256']==values[2]['actors'][name]['sha256'] and entry['array_prefix']==prefix,'Root joint/clip selection changed')
            for key,suffix in [('world_matrices','world_matrices'),('initial_local_deltas','initial_local_deltas')]:
                data_array=arrays[prefix+'_'+suffix]
                require(data_array.dtype==np.dtype('<f8') and data_array.shape==(len(values[6]),4,4)
                    and np.asarray(entry[key],dtype='<f8').tobytes()==data_array.tobytes(),'Root reference JSON/array transport differs')
        require(set(arrays.files)==expected_keys,'Complete root array population required')
    package=read(folder/'package.json')
    require(package['root_event_tracks_included'] is True and package['root_removed_from_character_clips'] is False
        and package['root_application_mode']=='reference-only-motion-remains-embedded' and package['original_selected'] is True
        and all(package[k] is False for k in ('animation_runtime_playback_verified','quality_approved','physics_verified','release_approved')),'Game package application/approval changed')
    require(package['sampled_scene_conditions_pass'] is r['scene_sampled_conditions_pass'] and package['root_samples_pass'] is r['root_samples_pass']
        and package['event_helper_dispatch_verified'] is r['event_helper_dispatch_verified'],'Game package measured decisions differ')
    with zipfile.ZipFile(folder/'game-assets.zip') as archive:
        require(archive.read('package.json')==(folder/'package.json').read_bytes(),'Game package manifest differs from ZIP')
    for name in DOWNLOADS:data['downloads'].append(dict(label=name,url=f'/files/{NAMESPACE}/{job}/{name}',sha256=sha256(folder/name)))
    data.update(samples=r['samples'],root_samples_pass=r['root_samples_pass'],scene_sampled_conditions_pass=r['scene_sampled_conditions_pass'],event_helper_dispatch_verified=r['event_helper_dispatch_verified'])
    return data


def listing():
    jobs=[]
    for folder in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True):
        if folder.is_dir() and scenes.NAME.fullmatch(folder.name) and (folder/'pipeline.json').is_file():
            state=read(folder/'pipeline.json');jobs.append(dict(id=folder.name,status=state['status']))
    return dict(jobs=jobs)


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        if not target.is_relative_to(folder):return None
        return target if any(e['url']=='/files/'+relative for e in manifest(parts[1])['downloads']) else None
    except (ValueError,KeyError,TypeError,OSError):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
