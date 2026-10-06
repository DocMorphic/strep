"""Explicit Studio scene correspondence and bounded transfer calibration.

Staging is a new authoring draft, not an engine export or quality approval.
Original clips, upstream transfers, correspondence and failed fits stay retained.
"""
import argparse
import copy
from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import zipfile

from action_worker_lock import _lock
import native_transfer_scene as bridge
import native_transfer_surface_calibration as calibration
import native_surface_contact as surface
from native_scene_contacts import SceneContacts,fields,scalar
import studio_native_rig_transfer as transfers
import studio_native_scene as scenes
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-studio-native-scene-transfer-v1'
NAMESPACE='native-scene-transfer-jobs'
NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(sorted(set(calibration.METHODS+transfers.METHODS+(
    'studio_native_scene_transfer.py','studio_native_scene.py','native_contact_revision.py'))))
FALSE_FLAGS=('engine_playback_verified','human_reviewed','anatomical_reviewed',
    'quality_approved','release_approved','continuous_collision_certified','studio_selection_changed')
_VERIFIED={}


def require(ok,message):
    if not ok:raise ValueError(message)


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid scene transfer job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Scene transfer job escapes namespace');return folder


def selected(spec,rows,*,mapping):
    require(isinstance(rows,dict) and 1<=len(rows)<=8 and set(rows)<=set(spec['actors']),
        'Choose 1-8 existing scene actors to transfer')
    replacements={};bindings={};catalog={}
    for name,row in rows.items():
        fields(row,('job','result_sha256','vertex_map') if mapping else ('job','result_sha256'),'selected transfer')
        m=transfers.manifest(row['job']);folder=transfers.folder_for(row['job'])
        require(m['status']=='complete' and m['result_sha256']==row['result_sha256']
            and m['sampled_runtime_conditions_pass'] is True,'Select a completed playback-checked native transfer')
        report=read(folder/'transfer/report.json');actor=spec['actors'][name]
        require(actor['sha256']==report['input_snapshots_sha256']['source.glb']
            and actor['animation_index']==report['source_animation_index']
            and spec['duration_s']==report['source_duration_s'],'Transfer belongs to another scene actor, clip or duration')
        required=sorted(bridge.used_vertices(spec,name));require(required,'Choose a transferred actor used by scene contacts')
        profile=read(folder/'input/target-profile.json')
        catalog[name]=dict(source_sha256=actor['sha256'],source_animation_index=actor['animation_index'],
            target_sha256=report['input_snapshots_sha256']['target.glb'],target_roles=sorted(profile['mapping']),
            output_animation_index=report['output_animation_index'],required_vertices=[list(v) for v in required],
            job=row['job'],result_sha256=m['result_sha256'])
        bindings[name]=dict(job=row['job'],result_sha256=m['result_sha256'],
            prepared_sha256=sha256(folder/'prepared.json'),report_sha256=sha256(folder/'transfer/report.json'))
        if mapping:replacements[name]=dict(glb=str(folder/'transfer/character.glb'),sha256=report['glb_sha256'],
            animation_index=report['output_animation_index'],vertex_map=copy.deepcopy(row['vertex_map']))
    return replacements,bindings,catalog


def catalog(payload,resolver):
    fields(payload,('draft','transfers'),'scene transfer catalog')
    spec,_,edit,_=scenes.validate_request(payload['draft'],resolver,require_objects=False)
    require(edit is None,'Turn off the separate object-edit proposal; transfer keeps declared object paths')
    _,_,actors=selected(spec,payload['transfers'],mapping=False)
    return dict(schema='strep-studio-native-scene-transfer-catalog-v1',actors=actors,
        duration_s=spec['duration_s'],quality_approved=False)


def permissions(value,catalog):
    fields(value,('actors','surface','search'),'bounded transfer calibration')
    actors=value['actors'];require(isinstance(actors,dict) and actors and set(actors)<=set(catalog),
        'Choose transferred actors with explicit calibration bounds')
    controls=0
    for name,row in actors.items():
        fields(row,('role_rotations_degrees','maximum_root_offset_m','maximum_joint_displacement_m'),'actor calibration')
        root=scalar(row['maximum_root_offset_m'],0,.22,'root offset bound')
        scalar(row['maximum_joint_displacement_m'],1e-6,.22,'joint displacement bound')
        roles=row['role_rotations_degrees'];require(isinstance(roles,dict) and len(roles)<=16
            and set(roles)<=set(catalog[name]['target_roles']) and (roles or root>0),'Choose existing target roles or a root offset')
        for limit in roles.values():scalar(limit,1e-6,45,'reference rotation bound')
        controls+=3*(len(roles)+(root>0))
    require(controls<=96,'At most 96 complete calibration controls; no truncation')
    search=value['search'];fields(search,('evaluations','calls','seconds','starts'),'search budget')
    for name,maximum in [('evaluations',300),('calls',10000),('starts',7)]:
        require(type(search[name]) is int and 1<=search[name]<=maximum,'Bounded integer search budget required')
    require(search['starts']<=search['evaluations'],'Starts must fit the evaluation budget')
    scalar(search['seconds'],1,3600,'search seconds')
    fields(value['surface'],('limits','maximum_actor_pose_queries','contacts'),'authored surface conditions')


def validate_request(payload,resolver):
    fields(payload,('schema','draft','transfers','calibration'),'Studio scene transfer')
    require(payload['schema']==SCHEMA,'Studio scene transfer schema required')
    spec,gp,edit,sources=scenes.validate_request(payload['draft'],resolver,require_objects=False)
    require(edit is None,'Turn off the separate object-edit proposal; transfer keeps declared object paths')
    replacements,bindings,actors=selected(spec,payload['transfers'],mapping=True)
    changed=bridge.remap(spec,replacements);candidate=SceneContacts(changed,ROOT)
    permissions(payload['calibration'],actors)
    policy=dict(schema='strep-native-surface-contact-v1',contacts_sha256='draft',**copy.deepcopy(payload['calibration']['surface']))
    surface.policy_for(policy,candidate,'draft');candidate.check_inputs()
    return spec,gp,policy,sources,bindings


def prepare(payload,folder,resolver):
    spec,gp,sp,sources,bindings=validate_request(payload,resolver)
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh scene transfer job required')
    folder.mkdir(parents=True);save(folder/'pipeline.json',dict(status='preparing',original_selected=True,quality_approved=False))
    try:
        save(folder/'request.json',payload);snapshots={}
        for i,(name,s) in enumerate(sources.items()):
            path=folder/'input'/f'actor-{i}.glb';path.parent.mkdir(exist_ok=True);shutil.copyfile(s['path'],path)
            require(sha256(path)==sha256(s['path'])==s['sha256'],'Scene actor changed during snapshot')
            snapshots[name]={**s,'snapshot':path.relative_to(folder).as_posix()};spec['actors'][name]['glb']=str(path)
        save(folder/'contacts.json',spec)
        recipe=dict(schema=bridge.SCHEMA,contacts=dict(path='contacts.json',sha256=sha256(folder/'contacts.json')),
            transfers={n:dict(candidate=dict(path=str(transfers.folder_for(b['job'])/'transfer'),sha256=b['report_sha256']),
                vertex_map=copy.deepcopy(payload['transfers'][n]['vertex_map'])) for n,b in bindings.items()})
        save(folder/'bridge.json',recipe)
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in METHODS:
            dest=folder/'implementation'/n;dest.parent.mkdir(exist_ok=True);shutil.copyfile(SCRIPT_ROOT/n,dest)
            require(sha256(dest)==methods[n]==sha256(SCRIPT_ROOT/n),'Scene transfer method changed during snapshot')
        save(folder/'prepared.json',dict(schema=SCHEMA,sources=snapshots,transfers=bindings,implementation_sha256=methods,
            files_sha256={n:sha256(folder/n) for n in ('request.json','contacts.json','bridge.json')},
            original_selected=True,quality_approved=False,release_approved=False))
        frozen(folder);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained scene transfer folder required')
    p=read(folder/'prepared.json');payload=read(folder/'request.json')
    require(p['schema']==SCHEMA and p['original_selected'] is True and p['quality_approved'] is False
        and p['release_approved'] is False,'Unapproved original-retaining preparation required')
    require(set(p['files_sha256'])=={'request.json','contacts.json','bridge.json'}
        and all(sha256(folder/n)==h for n,h in p['files_sha256'].items()),'Complete scene transfer inputs changed')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete scene transfer methods required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT/n)==h==sha256(folder/'implementation'/n),'Scene transfer method binding changed')
    require(set(p['sources'])==set(payload['draft']['scene']['actors']),'Complete source actor population required')
    for i,(name,s) in enumerate(p['sources'].items()):
        require(s['snapshot']==f'input/actor-{i}.glb' and Path(s['path']).resolve().is_relative_to((ROOT/'reports').resolve())
            and s['url']==payload['draft']['scene']['actors'][name]['glb']
            and s['sha256']==payload['draft']['scene']['actors'][name]['sha256']
            and sha256(s['path'])==sha256(folder/s['snapshot'])==s['sha256'],'Original or snapshotted scene actor changed')
    resolver=lambda url:next((Path(s['path']) for s in p['sources'].values() if s['url']==url),None)
    spec,gp,sp,_,bindings=validate_request(payload,resolver)
    require(bindings==p['transfers'],'Selected upstream transfer changed')
    for name,s in p['sources'].items():spec['actors'][name]['glb']=str(folder/s['snapshot'])
    require(read(folder/'contacts.json')==spec,'Prepared scene contact intent changed')
    expected=dict(schema=bridge.SCHEMA,contacts=dict(path='contacts.json',sha256=sha256(folder/'contacts.json')),
        transfers={n:dict(candidate=dict(path=str(transfers.folder_for(b['job'])/'transfer'),sha256=b['report_sha256']),
            vertex_map=payload['transfers'][n]['vertex_map']) for n,b in bindings.items()})
    require(read(folder/'bridge.json')==expected,'Prepared correspondence or upstream binding changed')
    return p,gp,sp


@contextmanager
def job_lock(folder):
    path=ROOT/'.cache'/('scene-transfer-'+folder.name+'.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        try:_lock(stream,True)
        except OSError as exc:raise RuntimeError('This scene transfer worker is already running') from exc
        try:yield
        finally:_lock(stream,False)


def portable_scene(folder):
    spec=copy.deepcopy(read(folder/'fit/contacts.json'))
    for i,(name,a) in enumerate(spec['actors'].items()):a['glb']=f'actors/actor-{i}.glb'
    return spec


def stage_draft(folder):
    payload=read(folder/'request.json');draft=copy.deepcopy(payload['draft']);draft.pop('contact_revision',None)
    draft['scene']=portable_scene(folder)
    for name,a in draft['scene']['actors'].items():
        a['glb']=(f'/files/{NAMESPACE}/{folder.name}/'+a['glb'] if name in payload['transfers']
            else payload['draft']['scene']['actors'][name]['glb'])
    return draft


def download_names(folder,has_candidate):
    names=['result.json','comparison.json','source-scene.json','correspondence.json','surface-conditions.json','calibration-request.json']
    if has_candidate:
        names+=['candidate.zip','scene.json','stage-draft.json','surface-audit.json','geometry-audit.json','motion-bounds.json']
        names += [f'actors/actor-{i}.glb' for i in range(len(read(folder/'request.json')['draft']['scene']['actors']))]
    return names


def summary(folder,fit):
    return dict(schema=SCHEMA,status='complete',calibration_status=fit['status'],
        prepared_sha256=sha256(folder/'prepared.json'),comparison_sha256=sha256(folder/'comparison/result.json'),
        calibration_sha256=sha256(folder/'fit/result.json'),original_selected=True,source_bytes_unchanged=True,
        whole_clip_boundary_poses_may_change=fit['whole_clip_boundary_poses_may_change'],
        staging_conditions_pass=fit['sampled_authoring_conditions_pass'],
        checks={k:fit[k] for k in ('candidate_contact_samples_pass','source_rates_pass','joint_displacement_pass',
            'surface_common_clock_pass','surface_contact_samples_pass','geometry_samples_pass')},
        **{k:False for k in FALSE_FLAGS},
        scope='Separate new rig/clip epoch with explicit mesh correspondence, unchanged targets/timing/limits, '
            'bounded profile calibration and complete declared CPU samples. Staging is a new draft. '
            'Build scene assets for saved-resource engine checks; boundary transitions and human review remain required.')


def run(folder):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained scene transfer worker required')
    with job_lock(folder):
        p,gp,sp=frozen(folder)
        require(read(folder/'pipeline.json')['status']=='starting','Only a fresh prepared scene transfer may start')
        try:
            save(folder/'pipeline.json',dict(status='processing',stage='scene-correspondence',original_selected=True,quality_approved=False))
            bridge.run(folder/'bridge.json',folder/'comparison');digest=sha256(folder/'comparison/contacts.json')
            for name,policy in [('geometry-policy',gp),('surface-policy',sp)]:
                policy['contacts_sha256']=digest;save(folder/(name+'.json'),policy)
            config=read(folder/'request.json')['calibration']
            recipe=dict(schema=calibration.SCHEMA,comparison=dict(path='comparison',sha256=sha256(folder/'comparison/result.json')),
                actors=config['actors'],search=config['search'],
                **{n:dict(path=n.replace('_','-')+'.json',sha256=sha256(folder/(n.replace('_','-')+'.json')))
                    for n in ('surface_policy','geometry_policy')})
            save(folder/'calibration.json',recipe)
            save(folder/'pipeline.json',dict(status='processing',stage='bounded-surface-calibration',original_selected=True,quality_approved=False))
            fit=calibration.run(folder/'calibration.json',folder/'fit');frozen(folder)
            shutil.copyfile(folder/'comparison/result.json',folder/'comparison.json')
            save(folder/'source-scene.json',read(folder/'request.json')['draft'])
            save(folder/'correspondence.json',read(folder/'request.json')['transfers'])
            save(folder/'surface-conditions.json',config['surface']);save(folder/'calibration-request.json',config)
            has_candidate=fit['status']=='complete'
            if has_candidate:
                spec=read(folder/'fit/contacts.json')
                for i,a in enumerate(spec['actors'].values()):
                    dest=folder/'actors'/f'actor-{i}.glb';dest.parent.mkdir(exist_ok=True)
                    shutil.copyfile((folder/'fit'/a['glb']).resolve(),dest);require(sha256(dest)==a['sha256'],'Packed scene actor changed')
                save(folder/'scene.json',portable_scene(folder));save(folder/'stage-draft.json',stage_draft(folder))
                for src,dest in [('surface-audit','surface-audit'),('geometry-audit','geometry-audit'),('decoded-bounds','motion-bounds')]:
                    shutil.copyfile(folder/'fit'/(src+'.json'),folder/(dest+'.json'))
                with zipfile.ZipFile(folder/'candidate.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
                    for n in download_names(folder,True):
                        if n not in ('candidate.zip','result.json'):z.write(folder/n,n)
            result=summary(folder,fit);result['files_sha256']={n:sha256(folder/n) for n in download_names(folder,has_candidate) if n!='result.json'}
            save(folder/'result.json',result);save(folder/'completion.json',dict(result_sha256=sha256(folder/'result.json')))
            checked(folder);save(folder/'pipeline.json',dict(status='complete',finished_at=now(),original_selected=True,quality_approved=False));return result
        except Exception as exc:
            save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def verify(folder):
    p,gp,sp=frozen(folder);payload=read(folder/'request.json');r=read(folder/'result.json')
    require(read(folder/'completion.json')==dict(result_sha256=sha256(folder/'result.json')),'Selected scene transfer result changed')
    require(sha256(folder/'comparison/result.json')==r['comparison_sha256'],'Selected comparison changed')
    comparison=read(folder/'comparison/result.json')
    require(read(folder/'comparison/input/recipe.json')==read(folder/'bridge.json')
        and read(folder/'comparison/input/contacts.json')==read(folder/'contacts.json'),'Scene comparison differs from prepared inputs')
    digest=sha256(folder/'comparison/contacts.json');gp['contacts_sha256']=digest;sp['contacts_sha256']=digest
    require(read(folder/'geometry-policy.json')==gp and read(folder/'surface-policy.json')==sp,'Authored geometry/surface conditions changed')
    config=payload['calibration'];recipe=dict(schema=calibration.SCHEMA,
        comparison=dict(path='comparison',sha256=sha256(folder/'comparison/result.json')),actors=config['actors'],search=config['search'],
        **{n:dict(path=n.replace('_','-')+'.json',sha256=sha256(folder/(n.replace('_','-')+'.json'))) for n in ('surface_policy','geometry_policy')})
    require(read(folder/'calibration.json')==recipe and read(folder/'fit/recipe.json')==recipe,'Selected calibration permissions changed')
    require(sha256(folder/'fit/result.json')==r['calibration_sha256'],'Selected calibration changed')
    fit=read(folder/'fit/result.json');expected=summary(folder,fit)
    require(set(r)==set(expected)|{'files_sha256'} and all(type(r[k]) is type(v) and r[k]==v for k,v in expected.items()),
        'Typed scene transfer decisions or scope disagree with replay')
    has_candidate=fit['status']=='complete';names=download_names(folder,has_candidate)
    require(set(r['files_sha256'])==set(names)-{'result.json'} and all(sha256(folder/n)==h for n,h in r['files_sha256'].items()),'Complete scene transfer downloads changed')
    require(read(folder/'comparison.json')==comparison and read(folder/'source-scene.json')==payload['draft']
        and read(folder/'correspondence.json')==payload['transfers'] and read(folder/'surface-conditions.json')==config['surface']
        and read(folder/'calibration-request.json')==config,'Published scene transfer inputs changed')
    if has_candidate:
        require(read(folder/'scene.json')==portable_scene(folder) and read(folder/'stage-draft.json')==stage_draft(folder),'Staged contact intent or selected clip changed')
        for i,a in enumerate(read(folder/'fit/contacts.json')['actors'].values()):
            require(sha256(folder/'actors'/f'actor-{i}.glb')==a['sha256'],'Complete packed actor population changed')
        for src,dest in [('surface-audit','surface-audit'),('geometry-audit','geometry-audit'),('decoded-bounds','motion-bounds')]:
            require(read(folder/(dest+'.json'))==read(folder/'fit'/(src+'.json')),'Published calibration measurements changed')
        with zipfile.ZipFile(folder/'candidate.zip') as z:
            members=set(names)-{'candidate.zip','result.json'}
            require(len(z.namelist())==len(members) and set(z.namelist())==members
                and all(z.read(n)==(folder/n).read_bytes() for n in members),'Exact scene ZIP payload required')
    else:require(not (folder/'actors').exists() and not (folder/'stage-draft.json').exists(),'Incompatible calibration must not stage a candidate')
    # Cheap publication/shape/typed checks precede expensive numerical replay.
    # No result becomes verified or cacheable until both full core replays pass.
    require(bridge.verify(folder/'comparison',r['comparison_sha256'])==comparison,'Comparison replay changed')
    require(calibration.verify(folder/'fit',r['calibration_sha256'])==fit,'Calibration replay changed')
    return r


def signature(folder):
    """Hash complete payloads and live dependencies; cache only exact identities.

    Mutable supervisor/status files carry no measurements. No mtime shortcut,
    summary-only key or on-disk claimed verification is accepted.
    """
    files={p.resolve() for p in folder.rglob('*') if p.is_file()
        and p.name not in ('pipeline.json','worker.json','supervisor.log')}
    p=read(folder/'prepared.json')
    files.update(Path(s['path']).resolve() for s in p['sources'].values())
    files.update((SCRIPT_ROOT/n).resolve() for n in METHODS)
    for b in p['transfers'].values():
        upstream=transfers.folder_for(b['job'])
        files.update(path.resolve() for path in upstream.rglob('*') if path.is_file()
            and path.name not in ('worker.json','supervisor.log'))
        request=read(upstream/'request.json')
        for side in ('source','target'):
            asset=request[side+'_asset_id'];profile=request[side+'_profile_id']
            files.add((transfers.characters.asset_folder(asset)/'character.glb').resolve())
            files.add(transfers.characters.profile_path(asset,profile).resolve())
    return tuple((str(path),sha256(path)) for path in sorted(files))


def checked(folder):
    folder=Path(folder).resolve();before=signature(folder);cached=_VERIFIED.get(str(folder))
    if cached is not None and cached[0]==before:return copy.deepcopy(cached[1])
    result=verify(folder)
    require(signature(folder)==before,'Scene transfer evidence changed during verification')
    if len(_VERIFIED)>=32:_VERIFIED.clear()
    _VERIFIED[str(folder)]=(before,copy.deepcopy(result));return result


def manifest(job):
    from contact_edit_job import observed_state
    folder=folder_for(job);state=observed_state(folder)
    m=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],quality_approved=False,release_approved=False)
    if state['status']!='complete':return m
    r=checked(folder);m.update(**r,result_sha256=sha256(folder/'result.json'),authoring_request=read(folder/'request.json'))
    m['downloads']=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=sha256(folder/n)) for n in download_names(folder,r['calibration_status']=='complete')]
    m['stage_draft']=read(folder/'stage-draft.json') if r['staging_conditions_pass'] is True else None
    if r['calibration_status']=='complete':
        packed=portable_scene(folder);original=m['authoring_request']['draft']['scene']['actors']
        m['actors']={n:dict(original_sha256=original[n]['sha256'],candidate_sha256=a['sha256'],animation_index=a['animation_index'],
            candidate_url=f'/files/{NAMESPACE}/{job}/'+a['glb']) for n,a in packed['actors'].items()}
    return m


def listing():
    from contact_edit_job import observed_state
    return dict(jobs=[dict(id=p.name,status=observed_state(p)['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True)
        if p.is_dir() and NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        require(target.is_relative_to(folder),'Scene transfer download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    print(run(parser.parse_args().folder))
