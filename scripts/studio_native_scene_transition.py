"""Stage a sealed shared transition as a separate Studio scene draft."""
import copy,re,shutil
from pathlib import Path,PurePosixPath
import native_scene_transition as assembly
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import policy_for
from strep import ROOT,read,save,sha256,now

NAMESPACE='native-scene-transition-jobs'
PREFIX='/files/'+NAMESPACE+'/'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(assembly.METHODS+('studio_native_scene_transition.py',)))
require=assembly.require


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid transition staging job')
    return (ROOT/'reports'/NAMESPACE/job).resolve()


def source(binding):
    fields(binding,('folder','result_sha256'),'sealed shared transition')
    text=binding['folder'];require(isinstance(text,str) and text and not any(c in text for c in ('\\',':','%','?','#')),'Relative report folder required')
    p=PurePosixPath(text);require(not p.is_absolute() and all(x not in ('','.','..') for x in text.split('/')),'Contained report folder required')
    base=(ROOT/'reports').resolve();folder=(base/text).resolve();require(folder.is_relative_to(base) and folder!=base,'Transition source escapes reports')
    require(sha256(folder/'result.json')==binding['result_sha256'],'Selected transition result changed')
    prepared=read(folder/'prepared.json')
    # Do not inspect arbitrary external folders through a staging request.
    for path in list(prepared['inputs'])+[prepared['recipe_original_path']]:require(Path(path).resolve().is_relative_to(base),'Transition has inputs outside workspace reports')
    result=assembly.verify(folder);return folder,result


def inspect(payload):
    folder,r=source(payload);scene=read(folder/'scene.json');game=read(folder/'game-tracks-request.json')
    return dict(source=copy.deepcopy(payload),duration_s=r['duration_s'],bridge_interval_s=r['bridge_interval_s'],actors=list(scene['actors']),objects=list(scene['objects']),
        checks=r['checks'],timeline_mapping=r['timeline_mapping'],markers=game['markers'],floor=read(folder/'recipe.json')['floor'],times_s=read(folder/'roots.json')['times_s'],
        original_selected=True,quality_approved=False,release_approved=False)


def validate_request(payload):
    fields(payload,('schema','source','geometry'),'transition staging request');require(payload['schema']=='strep-studio-native-scene-transition-v1','Transition staging schema required')
    folder,r=source(payload['source']);spec=read(folder/'scene.json');scene=SceneContacts(spec,folder)
    fields(payload['geometry'],('clock','limits','planes'),'explicit staged scene geometry')
    policy_for(dict(schema='strep-native-scene-geometry-v1',contacts_sha256='draft',**payload['geometry']),scene,'draft')
    return folder,r


def draft(folder):
    spec=copy.deepcopy(read(folder/'transition/scene.json'))
    for name,a in spec['actors'].items():a['glb']=PREFIX+folder.name+'/transition/actors/'+name+'.glb'
    return dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=copy.deepcopy(read(folder/'request.json')['geometry']),object_edit=None)


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh transition stage required')
    original,r=validate_request(payload)
    files={p.relative_to(original).as_posix():sha256(p) for p in original.rglob('*') if p.is_file()}
    require(len(files)<=256 and sum((original/n).stat().st_size for n in files)<=1024**3,'Whole transition snapshot exceeds its material budget; no truncation')
    folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='preparing',original_selected=True))
    try:
        save(folder/'request.json',payload);shutil.copytree(original,folder/'transition');methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in METHODS:
            dest=folder/'implementation'/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(SCRIPT_ROOT/n,dest)
        save(folder/'prepared.json',dict(schema='strep-studio-native-scene-transition-prepared-v1',at=now(),source_folder=str(original),source_files_sha256=files,
            request_sha256=sha256(folder/'request.json'),implementation_sha256=methods))
        save(folder/'stage-draft.json',draft(folder));shutil.copyfile(original/'game-tracks-request.json',folder/'stage-game-tracks.json')
        result=dict(schema='strep-studio-native-scene-transition-v1',status='complete',prepared_sha256=sha256(folder/'prepared.json'),source_result_sha256=payload['source']['result_sha256'],
            source_checks=r['checks'],source_conditions_pass=r['all_declared_samples_pass'],staging_conditions_pass=True,original_selected=True,studio_selection_changed=False,
            quality_approved=False,training_admitted=False,release_approved=False,engine_playback_verified=False,
            files_sha256={n:sha256(folder/n) for n in ('stage-draft.json','stage-game-tracks.json')},
            scope='Separate draft from a sealed shared transition. Source failures and annotations remain in the snapshot; stage success is not motion, contact, engine or release approval.')
        save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')));save(folder/'pipeline.json',dict(status='complete',original_selected=True));verify(folder);return result
    except Exception as exc:save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def verify(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained transition stage required')
    p=read(folder/'prepared.json');require(p['schema']=='strep-studio-native-scene-transition-prepared-v1' and p['request_sha256']==sha256(folder/'request.json'),'Transition stage request changed')
    original,r=validate_request(read(folder/'request.json'));require(str(original)==p['source_folder'],'Transition stage source changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete transition stage methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(folder/'implementation'/n)==h,'Transition stage methods changed')
    actual={v.relative_to(original).as_posix():sha256(v) for v in original.rglob('*') if v.is_file()};require(actual==p['source_files_sha256'],'Complete original transition changed')
    copied={v.relative_to(folder/'transition').as_posix():sha256(v) for v in (folder/'transition').rglob('*') if v.is_file()};require(copied==actual,'Complete transition snapshot changed')
    require(assembly.transition.equal(read(folder/'stage-draft.json'),draft(folder)) and assembly.transition.equal(read(folder/'stage-game-tracks.json'),read(original/'game-tracks-request.json')),'Staged scene or timing changed')
    expected=dict(schema='strep-studio-native-scene-transition-v1',status='complete',prepared_sha256=sha256(folder/'prepared.json'),source_result_sha256=sha256(original/'result.json'),
        source_checks=r['checks'],source_conditions_pass=r['all_declared_samples_pass'],staging_conditions_pass=True,original_selected=True,studio_selection_changed=False,
        quality_approved=False,training_admitted=False,release_approved=False,engine_playback_verified=False,
        files_sha256={n:sha256(folder/n) for n in ('stage-draft.json','stage-game-tracks.json')},
        scope='Separate draft from a sealed shared transition. Source failures and annotations remain in the snapshot; stage success is not motion, contact, engine or release approval.')
    require(assembly.transition.equal(read(folder/'result.json'),expected),'Transition stage decisions changed')
    require(assembly.transition.equal(read(folder/'completion.json'),dict(result_sha256=sha256(folder/'result.json'))) and assembly.transition.equal(read(folder/'pipeline.json'),dict(status='complete',original_selected=True)),'Completed transition stage required');return expected


def manifest(job):
    folder=folder_for(job);r=verify(folder);names=['result.json','stage-draft.json','stage-game-tracks.json','transition/result.json','transition/events.json','transition/contacts.json','transition/roots.json']
    names+=['transition/actors/'+n+'.glb' for n in read(folder/'stage-draft.json')['scene']['actors']]
    return dict(id=job,**r,result_sha256=sha256(folder/'result.json'),draft=read(folder/'stage-draft.json'),game_tracks=read(folder/'stage-game-tracks.json'),
        downloads=[dict(label=n,url=PREFIX+job+'/'+n,sha256=sha256(folder/n)) for n in names])


def listing():
    base=ROOT/'reports'/NAMESPACE;rows=[]
    for folder in sorted(base.glob('*')) if base.exists() else []:
        if folder.is_dir() and NAME.fullmatch(folder.name):
            try:rows.append(dict(id=folder.name,status=read(folder/'pipeline.json')['status']))
            except (OSError,ValueError):pass
    return dict(jobs=rows)


def served_file(relative):
    parts=relative.split('/');require(len(parts)>=3 and parts[0]==NAMESPACE and all(x not in ('','.','..') for x in parts),'Contained transition file required')
    m=manifest(parts[1]);name='/'.join(parts[2:]);allowed={d['label'] for d in m['downloads']};require(name in allowed,'File is not a published transition artifact')
    path=(folder_for(parts[1])/name).resolve();require(path.is_relative_to(folder_for(parts[1])),'Transition file escapes job');return path
