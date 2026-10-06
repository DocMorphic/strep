"""Portable bridge edit epochs and original shared-transition history."""
import copy,re,shutil
from pathlib import Path
from native_rig_transition import equal
from native_scene_contacts import fields
from native_transition_lineage import transition_material
from strep import read,save,sha256

PREFIX='/files/native-transition-fit-jobs/'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')


def require(ok,message):
    if not ok:raise ValueError(message)


def origin(url):
    if not isinstance(url,str) or not url.startswith(PREFIX):return None
    parts=url[len(PREFIX):].split('/')
    require(len(parts)==4 and NAME.fullmatch(parts[0]) and parts[1:3]==['candidate','actors'] and re.fullmatch(r'[0-9]+\.glb',parts[3])
        and not any(c in url for c in ('?','#','%','\\')),'Exact bridge candidate URL required')
    return parts[0],int(parts[3][:-4])


def has_origins(draft):return any(origin(a['glb']) is not None for a in draft['scene']['actors'].values())


def plan(draft):
    import studio_native_transition_scene_fit as studio
    selection={};jobs={};files={};bindings={}
    def material(name,path):
        path=Path(path).resolve();h=sha256(path);bindings[str(path)]=h;files[name]=('file',path,h)
    def document(name,value):files[name]=('json',copy.deepcopy(value),None)
    for actor,entry in draft['scene']['actors'].items():
        chosen=origin(entry['glb'])
        if chosen is None:continue
        job,index=chosen;folder=studio.folder_for(job);m=studio.manifest(job);candidate=folder/'candidate';names=list(m['draft']['scene']['actors'])
        require(index<len(names),'Unknown bridge actor');name=names[index];row=m['draft']['scene']['actors'][name]
        require(entry['glb']==row['glb'] and entry['sha256']==row['sha256'] and entry['animation_index']==row['animation_index'],'Selected bridge correction clip changed')
        selection[actor]=dict(job=job,source_actor=name,selected_sha256=row['sha256'],animation_index=row['animation_index'])
        if job in jobs:continue
        require(len(jobs)<8,'At most eight complete bridge correction origins')
        base='jobs/'+job;transition_material(candidate/'original-transition',base+'/transition',material,document,bindings)
        source=read(candidate/'contacts.json');changed=read(candidate/'scene.json')
        for i,n in enumerate(names):
            before=Path(source['actors'][n]['glb']);material(base+'/source/'+str(i)+'.glb',before);source['actors'][n]['glb']='source/'+str(i)+'.glb'
            after=candidate/changed['actors'][n]['glb'];material(base+'/candidate/'+str(i)+'.glb',after);changed['actors'][n]['glb']='candidate/'+str(i)+'.glb'
        document(base+'/original-scene.json',source);document(base+'/candidate-scene.json',changed)
        for n in ('contacts.json','recipe.json','result.json','prepared.json','contacts-audit.json','geometry.json','permissions.json','geometry-policy.json','game-tracks-request.json',
                  'fit/result.json','fit/request.json','fit/source-rate-caps.npz','tracks/root-motion.json','tracks/root-observations.npz','tracks/contacts.json','tracks/events.json','tracks/request.json'):
            material(base+'/'+n,candidate/n)
        material(base+'/studio-completion.json',folder/'completion.json')
        jobs[job]=dict(candidate_result_sha256=m['candidate_result_sha256'],source_checks=m['source_checks'],checks=m['checks'],all_declared_samples_pass=m['all_declared_samples_pass'],
            authoring_request=read(folder/'request.json'),correction_scene_context_preserved=equal(draft,m['draft']),
            source_libraries_and_annotations_included=True,source_motion_caps_and_permissions_included=True,native_tracks_only=True,complete_fit_trials_included=False,
            numerical_decisions_apply_to_parent_only=True,quality_approved=False,release_approved=False)
    require(selection,'No bridge correction origins selected')
    require(len(files)<=256 and sum(v[1].stat().st_size for v in files.values() if v[0]=='file')<=768*1024**2,'Complete bridge history exceeds its material budget; no partial snapshot')
    return dict(schema='strep-native-transition-fit-lineage-v1',selection=selection,jobs=jobs,quality_approved=False,training_admitted=False,release_approved=False),files,bindings


def snapshot(draft,folder):
    folder=Path(folder);require(not folder.exists(),'Fresh bridge history required');record,files,bindings=plan(draft);folder.mkdir()
    for name,(kind,value,h) in files.items():
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        if kind=='file':shutil.copyfile(value,path);require(sha256(path)==h,'Bridge history copy changed')
        else:save(path,value)
    record['files_sha256']={n:sha256(folder/n) for n in files};save(folder/'record.json',record)
    require(all(sha256(p)==h for p,h in bindings.items()),'Bridge history sources changed')
    return dict(record_sha256=sha256(folder/'record.json'),files_sha256=record['files_sha256'])


def verify(draft,folder,receipt):
    folder=Path(folder);fields(receipt,('record_sha256','files_sha256'),'bridge history receipt')
    require(sha256(folder/'record.json')==receipt['record_sha256'],'Bridge history record changed')
    record,files,bindings=plan(draft);record['files_sha256']={n:sha256(folder/n) for n in files}
    require(equal(read(folder/'record.json'),record) and equal(receipt['files_sha256'],record['files_sha256']),'Bridge history decisions or complete population changed')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(files)|{'record.json'},'Complete bridge history file population required')
    for n,(kind,value,h) in files.items():require(sha256(folder/n)==h if kind=='file' else equal(read(folder/n),value),'Bridge history payload changed')
    require(all(sha256(p)==h for p,h in bindings.items()),'Bridge history source changed');return receipt


def package_files(folder,receipt):
    folder=Path(folder);return {'transition-corrections/'+n:folder/n for n in ['record.json']+list(receipt['files_sha256'])}
