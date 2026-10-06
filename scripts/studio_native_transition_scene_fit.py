"""Source-bound Studio bridge correction jobs, review and explicit candidate drafts."""
import argparse,copy,re,shutil
from contextlib import contextmanager
from pathlib import Path,PurePosixPath
import numpy as np
import native_transition_scene_fit as correction
import studio_native_scene_transition as transitions
from action_worker_lock import _lock
from native_scene_contacts import fields
from strep import ROOT,read,save,sha256,now

NAMESPACE='native-transition-fit-jobs';PREFIX='/files/'+NAMESPACE+'/'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
SCHEMA='strep-studio-native-transition-fit-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(correction.METHODS+transitions.METHODS+('studio_native_transition_scene_fit.py',)))
require=correction.require;equal=correction.equal


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Exact bridge correction job required')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Bridge correction job escapes reports');return folder


def contained(binding):
    fields(binding,('folder','result_sha256'),'contained correction result')
    text=binding['folder'];require(isinstance(text,str) and text and not any(c in text for c in ('\\',':','%','?','#')),'Relative report folder required')
    p=PurePosixPath(text);base=(ROOT/'reports').resolve();folder=(base/text).resolve()
    require(not p.is_absolute() and all(x not in ('','.','..') for x in text.split('/')) and folder.is_relative_to(base) and folder!=base,'Correction source escapes reports')
    require(sha256(folder/'result.json')==binding['result_sha256'],'Correction source changed');return folder


def recipe_for(payload):
    fields(payload,('schema','source','label','actors','geometry','iterations','maximum_pose_vertex_queries','resume_from'),'Studio bridge correction')
    require(payload['schema']==SCHEMA,'Studio bridge correction schema required')
    source,_=transitions.source(payload['source'])
    recipe={k:copy.deepcopy(payload[k]) for k in ('label','actors','geometry','iterations','maximum_pose_vertex_queries')}
    recipe.update(schema=correction.SCHEMA,source=dict(folder=str(source),result_sha256=payload['source']['result_sha256']))
    return recipe


def validate_request(payload):
    recipe=recipe_for(payload);problem=correction.Problem(recipe,ROOT);prior=None
    if payload['resume_from'] is not None:
        prior=contained(payload['resume_from']);prepared=read(prior/'prepared.json')
        for path in [prepared['recipe_original'],prepared['recipe_base']]:require(Path(path).resolve().is_relative_to((ROOT/'reports').resolve()),'Resume epoch outside reports')
        original=read(prior/'recipe.json');require(equal({k:v for k,v in original.items() if k not in ('iterations','label')},{k:v for k,v in recipe.items() if k not in ('iterations','label')}),'Resume source permissions, geometry or budget changed')
        seen=set();fit=prior/'fit';base=(ROOT/'reports').resolve()
        while fit is not None:
            fit=fit.resolve();require(fit.is_relative_to(base) and fit not in seen and len(seen)<16,'Contained finite resume epoch required');seen.add(fit)
            request=read(fit/'request.json')
            for path in list(request['inputs_sha256'])+list(request['source_inputs_sha256']):require(Path(path).resolve().is_relative_to(base),'Resume input outside reports')
            link=request['resume'];fit=None if link is None else Path(link['source_directory'])
        correction.verify(prior)
    return recipe,problem,prior


def catalog(binding):
    source,r=transitions.source(binding);spec=read(source/'scene.json')
    from native_scene_contacts import SceneContacts
    scene=SceneContacts(spec,source);start,end=r['bridge_interval_s'];actors={}
    for name,a in scene.actors.items():
        tracks=[]
        for node in a['rig'].joints:
            for path in ('rotation','translation'):
                rows=[c for c in a['sampler'].channels if c[:2]==(node,path)];eligible=False;guards=[]
                if len(rows)==1 and rows[0][4]=='LINEAR':
                    clock=rows[0][2];lo,hi=np.searchsorted(clock,[start,end])
                    eligible=bool(hi<len(clock) and clock[lo]==start and clock[hi]==end and hi-lo>=4)
                    if eligible:guards=[[start,float(clock[lo+1])],[float(clock[hi-1]),end]]
                tracks.append(dict(node=int(node),path=path,name=a['rig'].document['nodes'][node].get('name',str(node)),eligible=eligible,tangent_guards=guards,
                    reason=None if eligible else 'Needs existing linear bridge endpoint, tangent and interior keys'))
        actors[name]=dict(sha256=spec['actors'][name]['sha256'],animation_index=a['animation_index'],original_clip_count=len(a['rig'].document['animations']),tracks=tracks)
    return dict(schema='strep-studio-native-transition-fit-catalog-v1',source=copy.deepcopy(binding),actors=actors,objects=list(scene.objects),duration_s=scene.duration,
        bridge_interval_s=[start,end],times_s=read(source/'roots.json')['times_s'],floor=read(source/'recipe.json')['floor'],source_checks=r['checks'],
        maximum_controls=96,maximum_pose_vertex_queries=1000000,quality_approved=False,release_approved=False)


def prepare(payload,folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh Studio bridge correction required')
    recipe,problem,prior=validate_request(payload)
    folder.mkdir(parents=True)
    try:
        save(folder/'request.json',payload);save(folder/'recipe.json',recipe)
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};(folder/'implementation').mkdir()
        for n in METHODS:shutil.copyfile(SCRIPT_ROOT/n,folder/'implementation'/n)
        save(folder/'prepared.json',dict(schema=SCHEMA,at=now(),request_sha256=sha256(folder/'request.json'),recipe_sha256=sha256(folder/'recipe.json'),
            source_result_sha256=recipe['source']['result_sha256'],resume_result_sha256=None if prior is None else sha256(prior/'result.json'),implementation_sha256=methods))
        save(folder/'pipeline.json',dict(status='starting',original_selected=True));return read(folder/'prepared.json')
    except Exception as exc:save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def frozen(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained bridge correction job required');p=read(folder/'prepared.json')
    require(p['schema']==SCHEMA and p['request_sha256']==sha256(folder/'request.json') and p['recipe_sha256']==sha256(folder/'recipe.json'),'Bridge job request changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete bridge job methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(folder/'implementation'/n)==h,'Bridge job methods changed')
    recipe,problem,prior=validate_request(read(folder/'request.json'));require(equal(read(folder/'recipe.json'),recipe),'Bridge job recipe changed')
    require(p['source_result_sha256']==recipe['source']['result_sha256'] and p['resume_result_sha256']==(None if prior is None else sha256(prior/'result.json')),'Bridge job source epoch changed')
    return p,prior


@contextmanager
def job_lock(folder):
    with (folder/'job.lock').open('a+b') as stream:
        if stream.tell()==0:stream.write(b'0');stream.flush()
        try:_lock(stream,True)
        except OSError as exc:raise RuntimeError('Bridge correction worker already running') from exc
        try:yield
        finally:_lock(stream,False)


def draft(folder):
    spec=read(folder/'candidate/scene.json')
    for number,a in enumerate(spec['actors'].values()):a['glb']=PREFIX+folder.name+'/candidate/actors/'+str(number)+'.glb'
    return dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=copy.deepcopy(read(folder/'request.json')['geometry']),object_edit=None)


def downloads(folder):
    names=['stage-draft.json','stage-game-tracks.json','candidate/result.json','candidate/contacts-audit.json','candidate/geometry.json','candidate/fit/result.json',
        'candidate/permissions.json','candidate/geometry-policy.json','candidate/fit/source-rate-caps.npz','candidate/tracks/root-motion.json','candidate/tracks/events.json']
    names+=['candidate/actors/'+str(i)+'.glb' for i in range(len(read(folder/'candidate/scene.json')['actors']))]
    return {n:sha256(folder/n) for n in names}


def completion(folder,result):
    return dict(schema=SCHEMA,status='complete',prepared_sha256=sha256(folder/'prepared.json'),candidate_result_sha256=sha256(folder/'candidate/result.json'),
        checks=result['checks'],all_declared_samples_pass=result['all_declared_samples_pass'],source_checks=result['parent_checks'],original_selected=True,studio_selection_changed=False,
        native_roots_only=True,quality_approved=False,training_admitted=False,release_approved=False,engine_playback_verified=False,files_sha256=downloads(folder))


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained bridge correction worker required')
    with job_lock(folder):
        p,prior=frozen(folder);state=read(folder/'pipeline.json')
        if state['status']=='complete':return manifest(folder.name)
        require(state['status']=='starting','Only a prepared bridge correction can run; earlier evidence stays retained')
        save(folder/'pipeline.json',dict(status='processing',stage='bridge-fit',original_selected=True))
        try:
            result=correction.run(folder/'recipe.json',folder/'candidate',resume_from=None if prior is None else prior/'fit')
            frozen(folder);save(folder/'stage-draft.json',draft(folder));shutil.copyfile(folder/'candidate/game-tracks-request.json',folder/'stage-game-tracks.json')
            save(folder/'completion.json',completion(folder,result));save(folder/'pipeline.json',dict(status='complete',original_selected=True));return manifest(folder.name)
        except Exception as exc:save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json')
    base=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],original_selected=True,studio_selection_changed=False,quality_approved=False,release_approved=False)
    if state['status']!='complete':return base
    frozen(folder);r=correction.verify(folder/'candidate');c=read(folder/'completion.json');require(equal(c,completion(folder,r)),'Bridge completion decisions or artifact population changed')
    require(equal(read(folder/'stage-draft.json'),draft(folder)) and equal(read(folder/'stage-game-tracks.json'),read(folder/'candidate/game-tracks-request.json')),'Bridge draft or unconfirmed timing changed')
    require(equal(state,dict(status='complete',original_selected=True)),'Completed bridge job state required')
    original=read(folder/'candidate/contacts.json')
    counts={n:len(correction.RigAsset.load(a['glb']).document['animations']) for n,a in original['actors'].items()}
    return dict(base,original_animation_counts=counts,**{k:v for k,v in c.items() if k not in ('schema','status')},result_sha256=sha256(folder/'completion.json'),draft=read(folder/'stage-draft.json'),
        game_tracks=read(folder/'stage-game-tracks.json'),authoring_request=read(folder/'request.json'),candidate_binding=dict(folder=NAMESPACE+'/'+job+'/candidate',result_sha256=sha256(folder/'candidate/result.json')),
        downloads=[dict(label=n,url=PREFIX+job+'/'+n,sha256=h) for n,h in c['files_sha256'].items()])


def listing():
    rows=[]
    for folder in sorted((ROOT/'reports'/NAMESPACE).glob('*')):
        if folder.is_dir() and NAME.fullmatch(folder.name):
            try:rows.append(dict(id=folder.name,status=read(folder/'pipeline.json')['status']))
            except (OSError,ValueError):pass
    return dict(jobs=rows)


def served_file(relative):
    parts=relative.split('/');require(len(parts)>=3 and parts[0]==NAMESPACE and all(x not in ('','.','..') for x in parts) and not any(c in relative for c in ('\\','%','?','#')), 'Contained published bridge artifact required')
    m=manifest(parts[1]);name='/'.join(parts[2:]);require(name in m['files_sha256'],'Unpublished bridge artifact')
    path=(folder_for(parts[1])/name).resolve();require(path.is_relative_to(folder_for(parts[1])),'Bridge artifact escapes job');return path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);run(p.parse_args().folder)
