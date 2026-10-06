"""Bound authored surface conditions to completed scene/game engine packages.

No engine is rerun. Imported CPU skin and saved object resources are replayed;
passing samples permit a separate checked package, never quality approval.
"""
import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import zipfile

from action_worker_lock import _lock
import native_imported_surface_contact as imported
from native_surface_contact import policy_for
from native_scene_contacts import SceneContacts,fields
import studio_native_scene as scenes
import studio_native_scene_game as games
import studio_native_scene_transfer as transfers
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-studio-surface-export-v1';NAMESPACE='surface-export-jobs'
SCRIPT_ROOT=Path(__file__).resolve().parent
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
METHODS=tuple(sorted(set(imported.METHODS+games.METHODS+transfers.METHODS+('studio_surface_export.py',))))
FALSE_FLAGS=('quality_approved','release_approved','training_admitted','human_reviewed','anatomical_reviewed',
    'physics_verified','continuous_collision_certified','real_time_playback_verified','gpu_render_checked','studio_selection_changed')
ADDED=('surface-policy.json','surface-audit.json','surface-gate.json')
_VERIFIED={}


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid surface export job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Surface export escapes namespace');return folder


def intent(spec):
    result=copy.deepcopy(spec)
    for actor in result['actors'].values():actor.pop('glb')
    return result


def zip_members(path):
    with zipfile.ZipFile(path) as z:
        entries=z.infolist();require(1<=len(entries)<=2048 and sum(e.file_size for e in entries)<=1024**3,
            'Complete source package exceeds fixed population/size budget; no truncation')
        names=[e.filename for e in entries]
        require(len(names)==len(set(names)) and not set(names)&set(ADDED),'Distinct source members; surface outputs cannot overwrite existing files')
        for e in entries:
            parts=PurePosixPath(e.filename).parts
            require(e.filename==e.orig_filename and not e.is_dir() and not e.flag_bits&1 and not PurePosixPath(e.filename).is_absolute()
                and e.filename==PurePosixPath(e.filename).as_posix() and all(p not in ('.','..') for p in parts)
                and not any(c in e.filename for c in ('\\',':','\0')),'Safe exact source package members required')
        return {n:hashlib.sha256(z.read(n)).hexdigest() for n in names}


def origins(scene_folder,spec):
    found={};prefix='/files/'+transfers.NAMESPACE+'/'
    for name,s in read(scene_folder/'prepared.json')['sources'].items():
        url=s['url']
        if not url.startswith(prefix):continue
        parts=url[len(prefix):].split('/')
        require(len(parts)==3 and parts[1]=='actors' and re.fullmatch(r'actor-[0-7]\.glb',parts[2]),'Exact transferred scene actor URL required')
        job=parts[0];m=transfers.manifest(job)
        require(m['status']=='complete' and m['staging_conditions_pass'] is True,'Completed passing scene transfer origin required')
        index=int(parts[2][6:-4]);names=list(m['authoring_request']['draft']['scene']['actors'])
        require(index<len(names),'Transfer actor selection changed');original_name=names[index];bound=m['actors'][original_name]
        require(bound['candidate_url']==url and bound['candidate_sha256']==spec['actors'][name]['sha256']
            and bound['animation_index']==spec['actors'][name]['animation_index'],'Transferred clip or original surface lineage changed')
        if job not in found:
            found[job]=dict(job=job,result_sha256=m['result_sha256'],actor_assignments={},
                original_scene=intent(m['stage_draft']['scene']),original_surface=m['authoring_request']['calibration']['surface'])
        found[job]['actor_assignments'][name]=original_name
    rows=[found[n] for n in sorted(found)];inherited=None
    if len(rows)==1 and rows[0]['original_scene']==intent(spec):inherited=copy.deepcopy(rows[0]['original_surface'])
    return rows,inherited


def source(kind,job):
    require(kind in ('scene','game') and isinstance(job,str) and NAME.fullmatch(job),'Choose an exact scene or game package')
    if kind=='game':
        game_folder=games.folder_for(job);gm=games.manifest(job)
        require(gm['status']=='complete','Complete game package required')
        game_result=read(game_folder/'result.json');scene_job=game_result['source_scene_job']
        package=game_folder/'game-assets.zip';selected_result=game_folder/'result.json'
    else:game_folder=None;game_result=None;scene_job=job
    scene_folder=scenes.folder_for(scene_job);m=scenes.manifest(scene_job)
    require(m['status']=='complete','Complete saved-resource scene package required')
    result=read(scene_folder/'authoring/result.json');contacts=Path(result['artifacts']['active_contacts']).resolve()
    require(contacts.is_relative_to(scene_folder),'Active source contacts escape scene job')
    spec=read(contacts);scene=SceneContacts(spec,contacts.parent)
    geometry=scene_folder/'authoring/objects-common/common-policy.json' if scene.objects else scene_folder/'geometry-policy.json'
    if kind=='scene':package=scene_folder/'assets.zip';selected_result=scene_folder/'authoring/result.json'
    members=zip_members(package)
    with zipfile.ZipFile(package) as z:
        portable=json.loads(z.read('scene.json'));portable_hash=hashlib.sha256(z.read('scene.json')).hexdigest()
        require(intent(portable)==intent(spec),'Source package changes scene intent or selected clips')
        for i,(name,a) in enumerate(spec['actors'].items()):
            require(portable['actors'][name]['glb']==f'actors/{i}.glb' and members.get(f'actors/{i}.glb')==a['sha256'],
                'Complete exact source actor package required')
    lineage,inherited=origins(scene_folder,spec)
    metadata=dict(schema='strep-studio-surface-export-source-v1',source=dict(kind=kind,job=job,result_sha256=sha256(selected_result)),
        scene_job=scene_job,scene_result_sha256=m['result_sha256'],contacts_sha256=sha256(contacts),
        package_sha256=sha256(package),portable_scene_sha256=portable_hash,scene=intent(spec),
        scene_conditions_pass=m['sampled_conditions_pass'],root_event_tracks_included=kind=='game',
        root_conditions_pass=None if game_result is None else game_result['root_samples_pass'],
        event_dispatch_verified=None if game_result is None else game_result['event_helper_dispatch_verified'],
        normal_origins=lineage,normal_origins_sha256=digest(lineage),inherited_surface=inherited,
        quality_approved=False,release_approved=False)
    scene.check_inputs()
    return metadata,scene_folder,game_folder,contacts,geometry,package,scene,members


def metadata(kind,job):return source(kind,job)[0]


def validate_request(payload):
    fields(payload,('schema','source','surface','normal_origins_sha256','normal_revision'),'surface export request')
    require(payload['schema']==SCHEMA,'Explicit surface export schema required')
    fields(payload['source'],('kind','job','result_sha256'),'selected source package')
    selected=source(payload['source']['kind'],payload['source']['job']);m,*_=selected
    require(payload['source']==m['source'] and payload['normal_origins_sha256']==m['normal_origins_sha256'],
        'Source package or inherited normal intent changed; bind again')
    fields(payload['surface'],('limits','maximum_actor_pose_queries','contacts'),'authored surface conditions')
    policy=dict(schema='strep-native-surface-contact-v1',contacts_sha256=m['contacts_sha256'],**copy.deepcopy(payload['surface']))
    policy_for(policy,selected[-2],m['contacts_sha256'])
    revision=payload['normal_revision'];changed=bool(m['normal_origins'] and payload['surface']!=m['inherited_surface'])
    if changed:
        fields(revision,('notes',),'explicit new normal intent')
        require(isinstance(revision['notes'],str) and 1<=len(revision['notes'].strip())<=1500,'Record why the inherited normal intent changes')
    else:require(revision is None,'Unchanged or freshly authored normals do not need an inherited-intent revision')
    return selected,policy


def prepare(payload,folder):
    selected,policy=validate_request(payload);m,_,_,_,_,package,_,_=selected
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh surface export job required')
    folder.mkdir(parents=True)
    try:
        save(folder/'request.json',payload);save(folder/'source.json',m);save(folder/'surface-policy.json',policy)
        shutil.copyfile(package,folder/'source-assets.zip');require(sha256(folder/'source-assets.zip')==m['package_sha256'],'Source package changed during snapshot')
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in METHODS:
            dest=folder/'implementation'/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(SCRIPT_ROOT/n,dest)
            require(sha256(dest)==methods[n]==sha256(SCRIPT_ROOT/n),'Surface export method changed during snapshot')
        save(folder/'prepared.json',dict(schema=SCHEMA,files_sha256={n:sha256(folder/n) for n in (
            'request.json','source.json','surface-policy.json','source-assets.zip')},implementation_sha256=methods,
            original_selected=True,quality_approved=False,release_approved=False))
        frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained surface export folder required')
    p=read(folder/'prepared.json')
    require(p['schema']==SCHEMA and p['original_selected'] is True and p['quality_approved'] is False
        and p['release_approved'] is False,'Unapproved original-retaining export required')
    require(set(p['files_sha256'])=={'request.json','source.json','surface-policy.json','source-assets.zip'}
        and all(sha256(folder/n)==h for n,h in p['files_sha256'].items()),'Complete source/normal snapshots changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete surface export methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==h==sha256(folder/'implementation'/n),'Surface export implementation changed')
    selected,policy=validate_request(read(folder/'request.json'))
    require(read(folder/'source.json')==selected[0] and read(folder/'surface-policy.json')==policy
        and sha256(folder/'source-assets.zip')==selected[0]['package_sha256'],'Prepared source package or authored normals changed')
    return p,selected


@contextmanager
def job_lock(folder):
    path=ROOT/'.cache'/('surface-export-'+folder.name+'.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        try:_lock(stream,True)
        except OSError as exc:raise RuntimeError('This surface export worker is already running') from exc
        try:yield
        finally:_lock(stream,False)


def package(folder,metadata,audit,members):
    policy=read(folder/'surface-policy.json');policy['contacts_sha256']=metadata['portable_scene_sha256']
    save(folder/'portable-surface-policy.json',policy)
    gate=dict(schema=SCHEMA,source=metadata['source'],source_package_sha256=metadata['package_sha256'],
        scene_job=metadata['scene_job'],portable_scene_sha256=metadata['portable_scene_sha256'],base_members_sha256=members,
        added_files_sha256={'surface-policy.json':sha256(folder/'portable-surface-policy.json'),
            'surface-audit.json':sha256(folder/'audit/result.json')},normal_origins_sha256=metadata['normal_origins_sha256'],
        normal_revision=read(folder/'request.json')['normal_revision'],all_declared_scene_and_surface_samples_pass=True,
        root_event_tracks_included=metadata['root_event_tracks_included'],root_motion_application_unchanged=True,
        original_selected=True,**{k:False for k in FALSE_FLAGS})
    save(folder/'surface-gate.json',gate)
    with zipfile.ZipFile(folder/'source-assets.zip') as src,zipfile.ZipFile(folder/'checked-assets.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():z.writestr(info,src.read(info.filename))
        for name,path in [('surface-policy.json',folder/'portable-surface-policy.json'),('surface-audit.json',folder/'audit/result.json'),('surface-gate.json',folder/'surface-gate.json')]:z.write(path,name)


def outcome(folder,metadata,audit,replay):
    point_pass=all(audit['counts'][n]['point_contacts_pass'] is True for n in ('source-native','native-authoring'))
    surface_pass=audit['native_and_imported_surface_contacts_pass']
    game_pass=not metadata['root_event_tracks_included'] or (metadata['root_conditions_pass'] is True and metadata['event_dispatch_verified'] is True)
    passed=metadata['scene_conditions_pass'] is True and point_pass and surface_pass is True and game_pass
    return dict(schema=SCHEMA,status='complete',prepared_sha256=sha256(folder/'prepared.json'),
        imported_surface_result_sha256=sha256(folder/'audit/result.json'),replay_sha256=sha256(folder/'replay.json'),
        source=metadata['source'],normal_origins_sha256=metadata['normal_origins_sha256'],normal_intent_revised=read(folder/'request.json')['normal_revision'] is not None,
        scene_conditions_pass=metadata['scene_conditions_pass'],point_conditions_pass=point_pass,surface_conditions_pass=surface_pass,
        root_event_conditions_pass=game_pass,all_declared_scene_and_surface_samples_pass=passed,checked_package_available=passed,
        root_event_tracks_included=metadata['root_event_tracks_included'],engine_queries_reused=True,new_engine_executed=False,
        original_selected=True,**{k:False for k in FALSE_FLAGS},
        scope='Authored surface conditions replayed on complete imported CPU skin and saved object-resource observations. '
            'Separate package retains exact source scene/resources and optional root/contact/event files. '
            'Winding normals are not anatomical/outward-volume inference; no dynamics, continuous collision, GPU, real-time or human-quality approval.')


def downloads(passed):
    return ['result.json','audit/result.json','replay.json','source.json','surface-policy.json']+(['checked-assets.zip','surface-gate.json','portable-surface-policy.json'] if passed else [])


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained surface export worker required')
    with job_lock(folder):
        _,selected=frozen(folder);m,scene_folder,_,contacts,geometry,_,_,members=selected
        require(read(folder/'pipeline.json')['status']=='starting' and not (folder/'audit').exists(),'Fresh prepared surface export required')
        try:
            save(folder/'pipeline.json',dict(status='processing',stage='imported-surface-replay',original_selected=True,quality_approved=False))
            audit=imported.run(contacts,folder/'surface-policy.json',geometry,scene_folder/'authoring/actors-engine',folder/'audit',
                object_dir=scene_folder/'authoring/objects-engine' if m['scene']['objects'] else None)
            replay=imported.verify(folder/'audit');save(folder/'replay.json',replay);frozen(folder)
            r=outcome(folder,m,audit,replay)
            if r['checked_package_available']:package(folder,m,audit,members)
            r['files_sha256']={n:sha256(folder/n) for n in downloads(r['checked_package_available']) if n!='result.json'}
            save(folder/'result.json',r);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
            checked(folder);save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return r
        except Exception as exc:
            save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def verify(folder):
    _,selected=frozen(folder);m,_,_,_,_,_,scene,members=selected;r=read(folder/'result.json');audit=read(folder/'audit/result.json');replay=read(folder/'replay.json')
    require(read(folder/'completion.json')==dict(result_sha256=sha256(folder/'result.json')),'Selected surface export changed')
    expected=outcome(folder,m,audit,replay)
    require(set(r)==set(expected)|{'files_sha256'} and all(type(r[k]) is type(v) and r[k]==v for k,v in expected.items()),'Typed surface export decisions/scope changed')
    require(set(r['files_sha256'])==set(downloads(r['checked_package_available']))-{'result.json'}
        and all(sha256(folder/n)==h for n,h in r['files_sha256'].items()),'Complete fixed surface export downloads changed')
    if r['checked_package_available']:
        policy=read(folder/'surface-policy.json');policy['contacts_sha256']=m['portable_scene_sha256']
        require(read(folder/'portable-surface-policy.json')==policy,'Portable normal policy changes authored intent')
        gate=read(folder/'surface-gate.json');expected_gate=dict(schema=SCHEMA,source=m['source'],source_package_sha256=m['package_sha256'],
            scene_job=m['scene_job'],portable_scene_sha256=m['portable_scene_sha256'],base_members_sha256=members,
            added_files_sha256={'surface-policy.json':sha256(folder/'portable-surface-policy.json'),'surface-audit.json':sha256(folder/'audit/result.json')},
            normal_origins_sha256=m['normal_origins_sha256'],normal_revision=read(folder/'request.json')['normal_revision'],all_declared_scene_and_surface_samples_pass=True,
            root_event_tracks_included=m['root_event_tracks_included'],root_motion_application_unchanged=True,original_selected=True,**{k:False for k in FALSE_FLAGS})
        require(gate==expected_gate and all(type(gate[k]) is type(v) for k,v in expected_gate.items()),'Surface package gate/lineage changed')
        with zipfile.ZipFile(folder/'checked-assets.zip') as z,zipfile.ZipFile(folder/'source-assets.zip') as src:
            require(len(z.namelist())==len(members)+len(ADDED) and set(z.namelist())==set(members)|set(ADDED),'Exact checked ZIP population required')
            require(all(z.read(n)==src.read(n) for n in members),'Scene, resources, root or event payloads changed')
            for n,path in [('surface-policy.json',folder/'portable-surface-policy.json'),('surface-audit.json',folder/'audit/result.json'),('surface-gate.json',folder/'surface-gate.json')]:
                require(z.read(n)==path.read_bytes(),'Checked ZIP surface payload changed')
    else:require(not any((folder/n).exists() for n in ('checked-assets.zip','surface-gate.json','portable-surface-policy.json')),'Failed conditions cannot publish a checked package')
    require(imported.verify(folder/'audit')==replay,'Complete imported normals, points, clocks or replay changed')
    request=read(folder/'audit/request.json')
    require(request['surface_policy']==str(folder/'surface-policy.json') and request['contacts']==str(selected[3])
        and request['geometry_policy']==str(selected[4]) and request['actor_dir']==str(selected[1]/'authoring/actors-engine')
        and request['object_dir']==(str(selected[1]/'authoring/objects-engine') if scene.objects else None),'Surface audit belongs to another source/normal policy')
    return r


def signature(folder):
    files={p.resolve() for p in folder.rglob('*') if p.is_file() and p.name not in ('pipeline.json','worker.json','supervisor.log')}
    payload=read(folder/'request.json');kind=payload['source']['kind'];job=payload['source']['job']
    if kind=='game':game_folder=games.folder_for(job);job=read(game_folder/'result.json')['source_scene_job'];files.update(p.resolve() for p in game_folder.rglob('*') if p.is_file())
    scene_folder=scenes.folder_for(job);files.update(p.resolve() for p in scene_folder.rglob('*') if p.is_file())
    p=read(scene_folder/'prepared.json');files.update(Path(s['path']).resolve() for s in p['sources'].values());files.add(Path(p['engine_path']).resolve())
    for origin in read(folder/'source.json')['normal_origins']:
        files.update(Path(path) for path,h in transfers.signature(transfers.folder_for(origin['job'])))
    files.update((SCRIPT_ROOT/n).resolve() for n in METHODS)
    return tuple((str(path),sha256(path)) for path in sorted(files))


def checked(folder):
    folder=Path(folder).resolve();before=signature(folder);cached=_VERIFIED.get(str(folder))
    if cached is not None and cached[0]==before:return copy.deepcopy(cached[1])
    result=verify(folder);require(signature(folder)==before,'Surface export evidence changed during replay')
    if len(_VERIFIED)>=32:_VERIFIED.clear()
    _VERIFIED[str(folder)]=(before,copy.deepcopy(result));return result


def manifest(job):
    from contact_edit_job import observed_state
    folder=folder_for(job);state=observed_state(folder)
    m=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,release_approved=False)
    if state['status']!='complete':return m
    r=checked(folder);m.update(**r,result_sha256=sha256(folder/'result.json'),authoring_request=read(folder/'request.json'),counts=read(folder/'audit/result.json')['counts'])
    m['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in downloads(r['checked_package_available'])]
    return m


def listing():
    from contact_edit_job import observed_state
    return dict(jobs=[dict(id=p.name,status=observed_state(p)['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True)
        if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve();require(target.is_relative_to(folder),'Surface download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    print(run(parser.parse_args().folder))
