"""Portable original clip/scene/annotation evidence for staged transitions."""
import copy,re,shutil
from pathlib import Path
from native_scene_contacts import fields
from native_rig_transition import equal
from strep import read,save,sha256

PREFIX='/files/native-scene-transition-jobs/'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')


def require(ok,message):
    if not ok:raise ValueError(message)


def origin(url):
    if not isinstance(url,str) or not url.startswith(PREFIX):return None
    parts=url[len(PREFIX):].split('/');require(len(parts)==4 and NAME.fullmatch(parts[0]) and parts[1:3]==['transition','actors']
        and re.fullmatch(r'[A-Za-z0-9_-]{1,64}\.glb',parts[3]),'Exact transition actor URL required');return parts[0],parts[3][:-4]


def has_origins(draft):return any(origin(a['glb']) is not None for a in draft['scene']['actors'].values())


def transition_material(artifact,base,material,document,bindings):
    """Portable original sources and annotations, without creating another stage."""
    artifact=Path(artifact);prepared=read(artifact/'prepared.json');recipe=read(artifact/'recipe.json')
    for side,bind in enumerate(recipe['sources']):
        sp=(Path(prepared['recipe_base'])/bind['scene']['path']).resolve();gp=(Path(prepared['recipe_base'])/bind['game_tracks']['path']).resolve()
        require(sha256(sp)==bind['scene']['sha256'] and sha256(gp)==bind['game_tracks']['sha256'],'Original transition scene/timing changed')
        bindings[str(sp)]=sha256(sp);bindings[str(gp)]=sha256(gp);spec=read(sp)
        for a in spec['actors'].values():
            path=(sp.parent/a['glb']).resolve();require(sha256(path)==a['sha256'],'Original clip library changed')
            name='libraries/'+a['sha256']+'.glb';material(base+'/'+name,path);a['glb']=name
        document(base+('/first-scene.json' if side==0 else '/second-scene.json'),spec)
        document(base+('/first-game-tracks.json' if side==0 else '/second-game-tracks.json'),read(gp))
    spec=read(artifact/'scene.json')
    for name,a in spec['actors'].items():
        path=(artifact/a['glb']).resolve();material(base+'/candidate/'+name+'.glb',path);a['glb']='candidate/'+name+'.glb'
    document(base+'/candidate-scene.json',spec)
    for n in ('result.json','game-tracks-request.json','events.json','contacts.json','roots.json'):material(base+'/'+n,artifact/n)


def plan(draft):
    import studio_native_scene_transition as stages
    selection={};jobs={};files={};bindings={}
    def material(name,path):
        path=Path(path).resolve();h=sha256(path);bindings[str(path)]=h;files[name]=('file',path,h)
    def document(name,value):files[name]=('json',copy.deepcopy(value),None)
    for actor,entry in draft['scene']['actors'].items():
        selected=origin(entry['glb'])
        if selected is None:continue
        job,name=selected;folder=stages.folder_for(job);m=stages.manifest(job);source=m['draft']['scene']['actors'].get(name)
        require(source is not None and source['sha256']==entry['sha256'] and source['animation_index']==entry['animation_index'],'Selected transition clip binding changed')
        selection[actor]=dict(job=job,source_actor=name,selected_sha256=entry['sha256'],animation_index=entry['animation_index'])
        if job in jobs:continue
        require(len(jobs)<8,'At most eight complete transition origins; no truncation')
        base='jobs/'+job;artifact=folder/'transition';prepared=read(artifact/'prepared.json');recipe=read(artifact/'recipe.json')
        transition_material(artifact,base,material,document,bindings)
        material(base+'/stage-result.json',folder/'result.json')
        jobs[job]=dict(stage_result_sha256=sha256(folder/'result.json'),assembly_result_sha256=sha256(artifact/'result.json'),
            source_scene_sha256=[b['scene']['sha256'] for b in recipe['sources']],source_game_tracks_sha256=[b['game_tracks']['sha256'] for b in recipe['sources']],
            source_conditions_pass=m['source_conditions_pass'],source_checks=m['source_checks'],
            original_sources_and_annotations_included=True,transferred_marker_confirmations_reset=True,
            numerical_decisions_apply_to_parent_only=True,quality_approved=False,release_approved=False)
    require(selection,'No transition origins selected')
    require(len(files)<=128 and sum(v[1].stat().st_size for v in files.values() if v[0]=='file')<=768*1024**2,'Complete transition lineage exceeds its material budget; no partial snapshot')
    return dict(schema='strep-native-transition-lineage-v1',selection=selection,jobs=jobs,quality_approved=False,training_admitted=False,release_approved=False),files,bindings


def snapshot(draft,folder):
    folder=Path(folder);require(not folder.exists(),'Fresh transition lineage required');record,files,bindings=plan(draft);folder.mkdir()
    for name,(kind,value,h) in files.items():
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        if kind=='file':shutil.copyfile(value,path);require(sha256(path)==h,'Transition lineage snapshot changed')
        else:save(path,value)
    record['files_sha256']={n:sha256(folder/n) for n in files};save(folder/'record.json',record)
    require(all(sha256(p)==h for p,h in bindings.items()),'Transition lineage inputs changed');return dict(record_sha256=sha256(folder/'record.json'),files_sha256=record['files_sha256'])


def verify(draft,folder,receipt):
    folder=Path(folder);fields(receipt,('record_sha256','files_sha256'),'transition lineage receipt')
    require(sha256(folder/'record.json')==receipt['record_sha256'],'Transition lineage record changed')
    record,files,bindings=plan(draft);record['files_sha256']={n:sha256(folder/n) for n in files}
    require(receipt['files_sha256']==record['files_sha256'] and equal(read(folder/'record.json'),record),'Transition lineage decisions or population changed')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(files)|{'record.json'},'Complete transition lineage files required')
    for name,(kind,value,h) in files.items():
        require(sha256(folder/name)==h if kind=='file' else equal(read(folder/name),value),'Transition lineage payload changed')
    require(all(sha256(p)==h for p,h in bindings.items()),'Transition lineage source changed');return receipt


def package_files(folder,receipt):
    folder=Path(folder);return {'transition-lineage/'+n:folder/n for n in ['record.json']+list(receipt['files_sha256'])}
