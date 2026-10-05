"""Explicit Studio grip drafts and source-preserving native prop packages.

No production geometry search, skin sampling, anatomy inference, model or engine
execution. Joint alignment evaluates only a user-selected native joint/event.
"""
import argparse,hashlib,json,os,shutil,sys,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
from scipy.spatial.transform import Rotation
import studio_native_scene_game as game
from studio_native_scene import NAME
from native_scene_contacts import fields
from native_scene_runtime import METHODS as NATIVE_METHODS,configure,package_members
from scene_prop_runtime import compile_request,package,GDS,entry_files,matrix as rigid_offset
from strep import ROOT,now,read,save,sha256

NAMESPACE='scene-prop-runtime-jobs'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(NATIVE_METHODS+game.METHODS+GDS+('scene_prop_runtime.py','scene_prop_ownership.py','studio_scene_prop_runtime.py','studio_native_scene_game.py','primitive_penetration_bounds.py')))
DOWNLOADS=('runtime/prop-runtime-assets.zip','runtime-request.json','runtime/result.json','result.json')


def require(value,message):
    if not value:raise ValueError(message)


def member_digest(archive,name):
    digest=hashlib.sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid prop runtime job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve();require(folder.parent==base,'Prop runtime job escapes namespace');return folder


def source(job):
    manifest=game.manifest(job);require(manifest['status']=='complete','Select a completed game-track package')
    folder=game.folder_for(job);_,values=game.frozen(folder,current_methods=False)
    return folder,manifest,values[3],read(folder/'tracks/events.json')


def metadata(job):
    folder,manifest,scene,events=source(job)
    times=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8')
    roots=read(folder/'tracks/root-motion.json')['actors']
    return dict(game_job=job,source_result_sha256=sha256(folder/'result.json'),source_game_zip_sha256=sha256(folder/'game-assets.zip'),
        actors={n:dict(glb_sha256=roots[n]['character_glb_sha256'],animation_index=a['animation_index'],
            joints=[dict(node=int(node),name=a['rig'].document['nodes'][node].get('name','Unnamed joint')) for node in a['rig'].joints]) for n,a in scene.actors.items()},
        objects={n:dict(geometry=o['geometry'].record()) for n,o in scene.objects.items()},
        confirmed_events=[dict(id=e['id'],name=e['name'],actor=e['actor'],sample_index=e['sample_index'],time_s=float(times[e['sample_index']])) for e in events['events'] if e['runtime_dispatch_allowed']],
        clock=events['clock'],source_scene_conditions_pass=manifest['scene_sampled_conditions_pass'],root_samples_pass=manifest['root_samples_pass'],
        source_contacts_apply_to='unchanged-authored-reference-only',physics_verified=False,quality_approved=False,release_approved=False)


def selected(payload):
    fields(payload,('game_job','source_result_sha256','request'),'selected source-bound prop package')
    folder,manifest,scene,events=source(payload['game_job'])
    require(payload['source_result_sha256']==sha256(folder/'result.json'),'Selected game package result changed')
    return folder,manifest,scene,events


def validate_request(payload):
    folder,manifest,scene,events=selected(payload);request=payload['request']
    require(isinstance(request,dict),'Explicit prop request required')
    modes=request.get('root_modes');require(isinstance(modes,dict) and set(modes)==set(scene.actors) and all(v in ('embedded','extracted') for v in modes.values()),'Choose a root mode for every actor')
    roots=read(folder/'tracks/root-motion.json')['actors']
    config=dict(actors=[dict(id=n,extract=modes[n]=='extracted',asset=dict(sha256=roots[n]['character_glb_sha256'])) for n in scene.actors],objects=dict(names=list(scene.objects)))
    compiled=compile_request(request,config,scene,events,sha256(folder/'game-assets.zip'))
    return folder,manifest,scene,events,compiled


def align(payload):
    folder,_,scene,events=selected(payload);r=payload['request'];fields(r,('actor','joint_node','object','event_id'),'explicit grip alignment')
    require(r['actor'] in scene.actors and r['object'] in scene.objects,'Choose an existing actor and prop')
    a=scene.actors[r['actor']];node=r['joint_node'];require(type(node) is int and node in a['rig'].joints,'Choose an existing source skin joint')
    bone=a['rig'].document['nodes'][node].get('name')
    require(isinstance(bone,str) and bone and ':' not in bone and '/' not in bone and sum(a['rig'].document['nodes'][n].get('name')==bone for n in a['rig'].joints)==1,'Choose a unique plain source bone name')
    event=next((e for e in events['events'] if e['id']==r['event_id']),None)
    require(event is not None and event['runtime_dispatch_allowed'] and event['actor']==r['actor'],'Choose a confirmed event for the selected grip actor')
    times=np.frombuffer(bytes.fromhex(events['clock']['bytes_hex']),dtype='<f8');time=float(times[event['sample_index']])
    p,rot=a['placement'];placement=np.eye(4);placement[:3,:3]=rot;placement[:3,3]=p
    p,rot=scene.object_poses(r['object'],np.array([0.]));prop=np.eye(4);prop[:3,:3]=rot[0];prop[:3,3]=p[0]
    offset=np.linalg.inv(placement@a['sampler'].sample(time)[node])@prop
    rigid_offset(offset.tolist()) # Reject scale/reflection; Euler conversion must not approximate it.
    return dict(game_job=payload['game_job'],source_result_sha256=payload['source_result_sha256'],source_game_zip_sha256=sha256(folder/'game-assets.zip'),
                selection=r,source_time_s=time,source_time_f64le=np.asarray([time],dtype='<f8').tobytes().hex(),prop_offsets={r['object']:offset.tolist()},
                translation_m=offset[:3,3].tolist(),rotation_xyz_degrees=Rotation.from_matrix(offset[:3,:3]).as_euler('xyz',degrees=True).tolist(),
                target='parked-source-prop-center-at-zero',pose_alignment_only=True,physics_verified=False,quality_approved=False,release_approved=False)


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh prop runtime job required')
    source_folder,manifest,_,_,_=validate_request(payload)
    methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};folder.mkdir(parents=True)
    save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        save(folder/'request.json',payload);save(folder/'runtime-request.json',payload['request'])
        implementation=folder/'implementation';implementation.mkdir()
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,implementation/n)
        shutil.copyfile(source_folder/'game-assets.zip',folder/'source-game-assets.zip')
        require(sha256(folder/'source-game-assets.zip')==payload['request']['source_game_zip_sha256'],'Source game ZIP changed during snapshot')
        prepared=dict(schema='strep-studio-prop-runtime-prepared-v1',request_sha256=sha256(folder/'request.json'),runtime_request_sha256=sha256(folder/'runtime-request.json'),
            source_result_sha256=sha256(source_folder/'result.json'),source_game_zip_sha256=sha256(folder/'source-game-assets.zip'),implementation_sha256=methods,
            original_selected=True,quality_approved=False,physics_verified=False,release_approved=False)
        save(folder/'prepared.json',prepared);frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False));return prepared
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound prop job folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json')
    require(p['schema']=='strep-studio-prop-runtime-prepared-v1' and p['request_sha256']==sha256(folder/'request.json') and p['runtime_request_sha256']==sha256(folder/'runtime-request.json'),'Prop preparation/request changed')
    require(p['original_selected'] is True and all(p[k] is False for k in ('physics_verified','quality_approved','release_approved')),'Prop preparation approval changed')
    require(read(folder/'runtime-request.json')==payload['request'],'Prop request snapshot differs')
    values=validate_request(payload)
    require(sha256(values[0]/'result.json')==p['source_result_sha256'] and sha256(values[0]/'game-assets.zip')==sha256(folder/'source-game-assets.zip')==p['source_game_zip_sha256'],'Source game package changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete prop method archive required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n)==h,'Archived prop implementation changed')
        if current_methods:require(sha256(SCRIPT_ROOT/n)==h,'Prop implementation changed during worker')
    return p,values


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Bound prop job folder required')
    require(read(folder/'pipeline.json')['status']=='starting' and not (folder/'worker.json').exists() and not (folder/'runtime').exists() and not (folder/'completion.json').exists(),'Fresh prepared prop worker required')
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        p,values=frozen(folder);save(folder/'pipeline.json',dict(status='processing',stage='source-bound-native-prop-package',original_selected=True,quality_approved=False))
        result=package(folder/'source-game-assets.zip',folder/'runtime-request.json',folder/'runtime');frozen(folder)
        r=dict(schema='strep-studio-prop-runtime-job-v1',status='complete',source_game_job=values[0].name,source_result_sha256=p['source_result_sha256'],
            prepared_sha256=sha256(folder/'prepared.json'),package_sha256=result['package_sha256'],source_bytes_unchanged=True,studio_selection_changed=False,
            source_scene_conditions_pass=values[1]['scene_sampled_conditions_pass'],root_samples_pass=values[1]['root_samples_pass'],
            physics_verified=False,animation_runtime_playback_verified=False,quality_approved=False,release_approved=False,
            files_sha256={n:sha256(folder/n) for n in DOWNLOADS if n!='result.json'})
        save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
        save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return r
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json');data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,physics_verified=False)
    if state['status']!='complete':return data
    p,values=frozen(folder,current_methods=False);r=read(folder/'result.json')
    require(r['schema']=='strep-studio-prop-runtime-job-v1' and r['status']=='complete' and read(folder/'completion.json')['result_sha256']==sha256(folder/'result.json') and r['prepared_sha256']==sha256(folder/'prepared.json'),'Prop completion changed')
    require(r['source_game_job']==values[0].name and r['source_result_sha256']==p['source_result_sha256'] and r['source_bytes_unchanged'] is True and all(r[k] is False for k in ('studio_selection_changed','physics_verified','animation_runtime_playback_verified','quality_approved','release_approved')),'Prop source/approval changed')
    require(r['source_scene_conditions_pass'] is values[1]['scene_sampled_conditions_pass'] and r['root_samples_pass'] is values[1]['root_samples_pass'],'Source failures changed')
    require(set(r['files_sha256'])==set(DOWNLOADS)-{'result.json'},'Complete fixed prop download population required')
    for n,h in r['files_sha256'].items():require(sha256(folder/n)==h,'Prop download changed')
    exported=read(folder/'runtime/result.json')
    require(exported['schema']=='strep-scene-prop-runtime-package-v1' and exported['status']=='complete' and exported['source_game_zip_sha256']==p['source_game_zip_sha256'] and exported['ownership_request_sha256']==p['runtime_request_sha256'],'Exported prop source/request changed')
    require(all(exported[k] is False for k in ('engine_executed','physics_verified','animation_quality_approved','release_approved')) and exported['source_bytes_unchanged'] is True,'Export approval changed')
    methods={n:p['implementation_sha256'][n] for n in GDS}
    require(exported['runtime_methods_sha256']==methods,'Exported runtime method lineage changed')
    require(r['package_sha256']==exported['package_sha256']==sha256(folder/'runtime/prop-runtime-assets.zip'),'Prop ZIP changed')
    with zipfile.ZipFile(folder/'runtime/prop-runtime-assets.zip') as archive:
        names=archive.namelist();stored=json.loads(archive.read('package.json'))
        require(len(names)==len(set(n.casefold() for n in names)) and len(names)<512 and sum(i.file_size for i in archive.infolist())<=1024**3,'Unique bounded complete prop ZIP required')
        require(all(n and not PurePosixPath(n).is_absolute() and '\\' not in n and ':' not in n and all(part not in ('','.','..') for part in n.split('/')) for n in names),'Portable relative prop ZIP paths required')
        require(set(names)==set(stored['files_sha256'])|{'package.json'},'Complete prop ZIP population required')
        require(stored=={k:v for k,v in exported.items() if k!='package_sha256'},'Prop ZIP manifest differs')
        for n,h in stored['files_sha256'].items():
            require(member_digest(archive,n)==h,'Prop ZIP member changed')
            require(sha256(folder/'runtime/project'/n)==h,'Prop project member changed')
        require(archive.read('ownership-v1/ownership-authoring-request.json')==(folder/'runtime-request.json').read_bytes(),'Portable authoring request changed')
        for n,h in methods.items():require(stored['files_sha256']['ownership-v1/'+n]==h,'Portable runtime differs from archived implementation')
        with zipfile.ZipFile(folder/'source-game-assets.zip') as original:
            original_manifest=package_members(original)
            for n in original.namelist():
                target='source-game-package.json' if n=='package.json' else n
                expected=member_digest(original,n)
                require(stored['files_sha256'].get(target)==expected,'Portable original source bytes changed')
        config,scene,_,events=configure(folder/'runtime/project',original_manifest,read(folder/'runtime-request.json')['root_modes'])
        expected=compile_request(read(folder/'runtime-request.json'),config,scene,events,p['source_game_zip_sha256'])
        require(json.loads(archive.read('ownership-v1/prop-runtime.json'))==expected,'Portable grip configuration differs from bound request/source')
        for n,text in entry_files(expected['physics_fps']).items():require(archive.read(n)==text.encode('utf8'),'Portable startup differs from bound physics rate/entry')
    data.update(source_scene_conditions_pass=r['source_scene_conditions_pass'],root_samples_pass=r['root_samples_pass'],source_game_job=r['source_game_job'],source_bytes_unchanged=True)
    data['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in DOWNLOADS];return data


def listing():
    return dict(jobs=[dict(id=p.name,status=read(p/'pipeline.json')['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True) if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        require(target.is_relative_to(folder),'Prop download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
