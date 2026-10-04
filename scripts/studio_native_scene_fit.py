"""Explicit Studio character corrections with preserved source epochs on resume."""
import argparse
import copy
from pathlib import Path
import re
import shutil
from contextlib import contextmanager
from action_worker_lock import _lock,worker_lock
from strep import ROOT,read,save,sha256
from native_scene_contacts import SceneContacts,fields,run as contact_audit,METHODS as CONTACT_METHODS
from native_scene_edit import SceneEdits
from native_scene_fit import run as fit,METHODS as FIT_METHODS
from native_scene_resume import ResumeState
from native_scene_geometry import policy_for
from native_contact_revision import validate as revision_for
from studio_native_scene import validate_request as scene_request,require

NAMESPACE='native-scene-fit-jobs';NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(sorted(set(FIT_METHODS)|{'studio_native_scene_fit.py','studio_native_scene.py'}))


def folder_for(job):
    require(isinstance(job,str) and NAME.fullmatch(job),'Invalid character correction job')
    base=(ROOT/'reports'/NAMESPACE).resolve();folder=(base/job).resolve()
    require(folder.parent==base,'Correction job escapes namespace');return folder


def catalog(draft,resolver):
    spec,_,_,sources=scene_request(draft,resolver,require_objects=False);scene=SceneContacts(spec,ROOT)
    actors={}
    for name,a in scene.actors.items():
        channels=[]
        for node in a['rig'].joints:
            for path in ('rotation','translation'):
                found=[c for c in a['sampler'].channels if c[:2]==(node,path)]
                eligible=len(found)==1 and found[0][4]=='LINEAR' and len(found[0][2])>=3
                channels.append(dict(node=int(node),name=a['rig'].document['nodes'][int(node)].get('name',str(node)),
                    path=path,eligible=eligible,keys=len(found[0][2]) if len(found)==1 else None,
                    reason=None if eligible else 'Needs one existing LINEAR channel with at least three keys'))
        actors[name]=dict(sha256=spec['actors'][name]['sha256'],channels=channels)
    scene.check_inputs()
    return dict(schema='strep-studio-native-scene-fit-catalog-v1',duration_s=scene.duration,
        actors=actors,maximum_controls=96,maximum_tracks_per_actor=16,maximum_knots_per_actor=12,quality_approved=False)


def options(value):
    fields(value,('iterations',),'character correction effort')
    if type(value['iterations']) is not int or not 1<=value['iterations']<=16:raise ValueError('Choose 1-16 correction iterations')
    return dict(iterations=value['iterations'],trust=.02,proposal_model='storage-vector',
        vector_difference_scheme='central',vector_difference_step=.001,rotation_storage_policy='unit',
        restoration_steps=3,restoration_model='recentered',serialized_ray_probes=64)


def validate_request(payload,resolver):
    fields(payload,('schema','draft','actors','options','resume_from'),'Studio character correction')
    require(payload['schema']=='strep-studio-native-scene-fit-v1','Studio character correction schema required')
    spec,geometry,object_edit,sources=scene_request(payload['draft'],resolver,require_objects=False)
    require(object_edit is None,'Character correction uses the declared object paths. Turn off the separate object-edit proposal first.')
    config=options(payload['options']);scene=SceneContacts(spec,ROOT)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256='draft',actors=copy.deepcopy(payload['actors']))
    edits=SceneEdits(permissions,scene,'draft',rotation_storage_policy=config['rotation_storage_policy'])
    require(edits.size<=96,'Character correction supports at most 96 controls; reduce selected tracks or interior knots')
    prior=None;receipt=None
    if payload['resume_from'] is not None:
        prior=folder_for(payload['resume_from']);manifest(prior.name)
        previous=read(prior/'fit/contacts.json');before=read(prior/'fit/permissions.json')
        # Retain the prior canonical actor paths. New snapshots do not reset the
        # source epoch or the exact contacts/permissions identity used by resume.
        for name,entry in spec['actors'].items():
            require(name in previous['actors'] and entry['sha256']==previous['actors'][name]['sha256'],'Resume actor epoch changed')
            entry['glb']=previous['actors'][name]['glb']
        require(set(spec['actors'])==set(previous['actors']),'Resume actor population changed')
        proposed=copy.deepcopy(permissions);proposed['contacts_sha256']=before['contacts_sha256']
        require(proposed==before,'Resume edit permissions changed; author a separate explicit experiment')
        if spec!=previous:
            edits_patch=[]
            old={c['id']:c for c in previous['contacts']}
            for row in spec['contacts']:
                require(row['id'] in old,'Resume contact population changed');a=old[row['id']]
                source=None;partner=None
                if row['vertices']!=a['vertices'] or row['reduction']!=a['reduction']:
                    source=dict(glb_sha256=spec['actors'][row['actor']]['sha256'],vertices=row['vertices'],reduction=row['reduction'])
                if row['target']['space']=='actor' and a['target']['space']=='actor':
                    target=row['target'];old_target=a['target']
                    if target['vertices']!=old_target['vertices'] or target['reduction']!=old_target['reduction']:
                        partner=dict(glb_sha256=spec['actors'][target['actor']]['sha256'],vertices=target['vertices'],reduction=target['reduction'])
                if source is not None or partner is not None:edits_patch.append(dict(id=row['id'],source=source,partner=partner))
            require(edits_patch,'Resume changes must be explicit contact patch revisions')
            # The core receipt validator rejects every other scene change.
            receipt=dict(schema='strep-native-scene-fit-contact-revision-v1',
                original_contacts_sha256=sha256(prior/'fit/contacts.json'),original_permissions_sha256=sha256(prior/'fit/permissions.json'),edits=edits_patch)
        permissions['contacts_sha256']=before['contacts_sha256']
        canonical_digest=sha256(prior/'fit/contacts.json') if receipt is None else 'draft'
        permissions['contacts_sha256']=canonical_digest;geometry['contacts_sha256']=canonical_digest
        scene=SceneContacts(spec,ROOT);edits=SceneEdits(permissions,scene,canonical_digest)
        state=ResumeState(prior/'fit',canonical_digest,sha256(prior/'fit/permissions.json'),edits,
            contact_revision=receipt,current_contacts=spec,current_permissions=permissions)
        state.check_geometry(geometry,canonical_digest);state.check_inputs()
    return spec,geometry,permissions,sources,config,prior,receipt


def prepare(payload,folder,resolver):
    spec,geometry,permissions,sources,config,prior,receipt=validate_request(payload,resolver)
    folder=Path(folder).resolve();require(folder==folder_for(folder.name) and not folder.exists(),'Fresh character correction job required')
    methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};folder.mkdir(parents=True)
    try:
        save(folder/'draft.json',payload);snapshots={}
        for index,(name,source) in enumerate(sources.items()):
            target=folder/'input'/f'actor-{index}.glb';target.parent.mkdir(exist_ok=True);shutil.copyfile(source['path'],target)
            require(sha256(target)==sha256(source['path'])==source['sha256'],'Character source changed during snapshot')
            snapshots[name]=dict(**source,snapshot=target.relative_to(folder).as_posix())
            if prior is None:spec['actors'][name]['glb']=str(target)
        if prior is not None and receipt is None:
            for name in ('contacts.json','permissions.json','geometry-policy.json'):shutil.copyfile(prior/'fit'/name,folder/name)
            spec=read(folder/'contacts.json');permissions=read(folder/'permissions.json');geometry=read(folder/'geometry-policy.json')
        else:
            save(folder/'contacts.json',spec);permissions['contacts_sha256']=sha256(folder/'contacts.json');save(folder/'permissions.json',permissions)
            geometry['contacts_sha256']=sha256(folder/'contacts.json');save(folder/'geometry-policy.json',geometry)
        ordinary,revision=revision_for(payload['draft'])
        extra=set()
        if receipt is not None:save(folder/'contact-revision.json',receipt);extra.add('contact-revision.json')
        elif prior is None and revision is not None:
            original=copy.deepcopy(spec);original['contacts']=copy.deepcopy(revision['baseline']['scene']['contacts'])
            save(folder/'original-contact-intent.json',original);extra.add('original-contact-intent.json')
        scene=SceneContacts(spec,folder);edits=SceneEdits(permissions,scene,sha256(folder/'contacts.json'),rotation_storage_policy=config['rotation_storage_policy'])
        policy_for(geometry,scene,sha256(folder/'contacts.json'))
        if prior is not None:
            state=ResumeState(prior/'fit',sha256(folder/'contacts.json'),sha256(folder/'permissions.json'),edits,
                contact_revision=receipt,current_contacts=spec,current_permissions=permissions)
            state.check_geometry(geometry,sha256(folder/'contacts.json'));state.check_inputs()
        files={'draft.json','contacts.json','permissions.json','geometry-policy.json'}|extra
        for n in methods:
            target=folder/'implementation'/n;target.parent.mkdir(exist_ok=True);shutil.copyfile(SCRIPT_ROOT/n,target)
            require(sha256(target)==methods[n]==sha256(SCRIPT_ROOT/n),'Correction implementation changed during snapshot')
        p=dict(schema='strep-studio-native-scene-fit-prepared-v1',sources=snapshots,controls=edits.size,
            files_sha256={n:sha256(folder/n) for n in files},implementation_sha256=methods,options=config,
            resume_from=None if prior is None else prior.name,
            resume_prepared_sha256=None if prior is None else sha256(prior/'prepared.json'),
            resume_result_sha256=None if prior is None else sha256(prior/'fit/result.json'),
            original_selected=True,quality_approved=False,release_approved=False)
        save(folder/'prepared.json',p);save(folder/'pipeline.json',dict(status='starting',original_selected=True,quality_approved=False));return p
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def frozen(folder,*,current_methods=True):
    folder=Path(folder).resolve();require(folder==folder_for(folder.name),'Contained correction folder required')
    p=read(folder/'prepared.json');draft=read(folder/'draft.json')
    fields(draft,('schema','draft','actors','options','resume_from'),'retained correction request')
    require(p['schema']=='strep-studio-native-scene-fit-prepared-v1' and p['original_selected'] is True
        and p['quality_approved'] is False and p['release_approved'] is False,'Unapproved original-retaining correction required')
    require(set(p['implementation_sha256'])==set(METHODS),'Complete correction method population required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n)==h,'Correction method archive changed')
        if current_methods:require(sha256(SCRIPT_ROOT/n)==h,'Correction implementation changed')
    expected={'draft.json','contacts.json','permissions.json','geometry-policy.json'}
    _,revision=revision_for(draft['draft'])
    prior=folder_for(p['resume_from']) if p['resume_from'] is not None else None
    if prior is not None:
        previous=read(prior/'fit/contacts.json')
        proposed=copy.deepcopy(draft['draft']['scene'])
        for name,actor in proposed['actors'].items():actor['glb']=previous['actors'][name]['glb']
        if proposed!=previous:expected.add('contact-revision.json')
    elif revision is not None:expected.add('original-contact-intent.json')
    require(set(p['files_sha256'])==expected,'Complete correction input population required')
    for n,h in p['files_sha256'].items():require(sha256(folder/n)==h,'Correction request snapshot changed')
    require(p['options']==options(draft['options']) and p['resume_from']==draft['resume_from'],'Correction options or resume selection changed')
    spec=copy.deepcopy(draft['draft']['scene']);require(set(p['sources'])==set(spec['actors']),'Complete correction actor snapshots required')
    prior=None
    if p['resume_from'] is not None:
        prior=folder_for(p['resume_from']);require(prior!=folder,'Correction cannot resume itself')
        require(sha256(prior/'prepared.json')==p['resume_prepared_sha256'] and sha256(prior/'fit/result.json')==p['resume_result_sha256'],'Resume correction source changed')
        previous=read(prior/'fit/contacts.json')
    for index,(name,s) in enumerate(p['sources'].items()):
        require(s['url']==spec['actors'][name]['glb'] and s['sha256']==spec['actors'][name]['sha256'],'Correction actor selection changed')
        target=(folder/s['snapshot']).resolve()
        require(s['snapshot']==f'input/actor-{index}.glb' and target.parent==folder/'input'
            and Path(s['path']).resolve().is_relative_to((ROOT/'reports').resolve())
            and sha256(target)==sha256(s['path'])==s['sha256'],'Original or snapshotted correction actor changed')
        spec['actors'][name]['glb']=previous['actors'][name]['glb'] if prior is not None else str(target)
    require(read(folder/'contacts.json')==spec,'Correction contacts change submitted scene')
    if prior is None and revision is not None:
        original=copy.deepcopy(spec);original['contacts']=copy.deepcopy(revision['baseline']['scene']['contacts'])
        require(read(folder/'original-contact-intent.json')==original,'Original contact intent changed')
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(folder/'contacts.json'),actors=draft['actors'])
    require(read(folder/'permissions.json')==permissions,'Correction permissions changed')
    require(read(folder/'geometry-policy.json')==dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(folder/'contacts.json'),**draft['draft']['geometry']),'Correction geometry changed')
    scene=SceneContacts(spec,folder);edits=SceneEdits(permissions,scene,sha256(folder/'contacts.json'),rotation_storage_policy=p['options']['rotation_storage_policy'])
    require(edits.size==p['controls']<=96,'Correction control population changed')
    if prior is not None:
        state=ResumeState(prior/'fit',sha256(folder/'contacts.json'),sha256(folder/'permissions.json'),edits,
            contact_revision=read(folder/'contact-revision.json') if 'contact-revision.json' in expected else None,
            current_contacts=spec,current_permissions=permissions)
        state.check_geometry(read(folder/'geometry-policy.json'),sha256(folder/'contacts.json'));state.check_inputs()
    return p


def checked_file(folder,relative,digest):
    target=(folder/relative).resolve()
    require(target.is_relative_to(folder) and sha256(target)==digest,'Correction retained evidence changed')
    return target


def checked_contact_audit(folder,methods):
    audit=read(folder/'result.json')
    checked_file(folder,'spec.json',audit['spec_sha256'])
    checked_file(folder,'observations.npz',audit['observations_sha256'])
    require(audit['implementation_sha256']=={n:methods[n] for n in CONTACT_METHODS},'Contact audit methods changed')
    for n,h in audit['implementation_sha256'].items():checked_file(folder,'implementation/'+n,h)
    for path,s in audit['source_snapshots'].items():
        require(sha256(path)==s['sha256'],'Contact audit source changed');checked_file(folder,s['path'],s['sha256'])
    require(all(audit[k] is False for k in ('quality_approved','training_admitted','release_approved')),'Contact audit approval changed')
    return audit


@contextmanager
def job_lock(folder):
    path=ROOT/'.cache'/('native-scene-fit-'+folder.name+'.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        try:_lock(stream,True)
        except OSError as exc:raise RuntimeError('This character correction worker is already running') from exc
        try:yield
        finally:_lock(stream,False)


def run(folder):
    folder=Path(folder).resolve()
    require(folder==folder_for(folder.name),'Contained correction folder required')
    with job_lock(folder):return execute(folder)


def execute(folder):
    folder=Path(folder).resolve();p=frozen(folder);state=read(folder/'pipeline.json')
    if state['status']=='complete':manifest(folder.name);return read(folder/'completion.json')
    require(state['status']=='starting','Only a prepared correction can start; failed/processing evidence stays retained')
    save(folder/'pipeline.json',dict(status='processing',stage='character-fit',original_selected=True,quality_approved=False))
    try:
        kwargs=dict(p['options'],geometry_policy=folder/'geometry-policy.json')
        if p['resume_from'] is not None:kwargs['resume_from']=folder_for(p['resume_from'])/'fit'
        if (folder/'contact-revision.json').is_file():kwargs['contact_revision']=folder/'contact-revision.json'
        result=fit(folder/'contacts.json',folder/'permissions.json',folder/'fit',**kwargs)
        original_intent=None
        if (folder/'original-contact-intent.json').is_file():
            original=read(folder/'original-contact-intent.json')
            proposal=read(folder/'fit/proposal/contacts.json')
            for name in original['actors']:
                if name in proposal['actors']:original['actors'][name]=copy.deepcopy(proposal['actors'][name])
            save(folder/'original-intent-proposal.json',original)
            with worker_lock():original_intent=contact_audit(folder/'original-intent-proposal.json',folder/'original-intent-audit')
        frozen(folder)
        files={'fit/result.json','fit/contact-audit/result.json','fit/geometry-audit/result.json','fit/contacts.json','fit/permissions.json','fit/source-rate-caps.npz'}
        files|={s['snapshot'] for s in p['sources'].values()}
        files|={f'fit/probes/final/{name}.glb' for name in p['sources'] if name in read(folder/'permissions.json')['actors']}
        if original_intent is not None:files|={'original-intent-audit/result.json','original-intent-proposal.json'}
        if result['original_contact_intent_result_sha256'] is not None:files.add('fit/original-contact-audit/result.json')
        c=dict(schema='strep-studio-native-scene-fit-completion-v1',prepared_sha256=sha256(folder/'prepared.json'),
            fit_result_sha256=sha256(folder/'fit/result.json'),native_conditions_pass=result['native_constraints_pass'],
            geometry_conditions_pass=result['sampled_geometry_conditions_pass'],
            original_intent_pass=None if original_intent is None else original_intent['passed'],
            downloads={n:sha256(folder/n) for n in files},original_selected=True,
            studio_selection_changed=False,quality_approved=False,training_admitted=False,release_approved=False)
        save(folder/'completion.json',c);save(folder/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));return c
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


def manifest(job):
    folder=folder_for(job);state=read(folder/'pipeline.json')
    data=dict(id=job,status=state['status'],stage=state.get('stage'),error=state.get('error'),downloads=[],
        original_selected=True,studio_selection_changed=False,quality_approved=False,release_approved=False)
    if state['status']!='complete':return data
    p=frozen(folder,current_methods=False);c=read(folder/'completion.json');r=read(folder/'fit/result.json')
    require(c['schema']=='strep-studio-native-scene-fit-completion-v1' and c['prepared_sha256']==sha256(folder/'prepared.json')
        and c['fit_result_sha256']==sha256(folder/'fit/result.json'),'Correction completion changed')
    require(r['status']=='complete' and r['original_selected'] is True and c['original_selected'] is True
        and all(c[k] is False for k in ('studio_selection_changed','quality_approved','training_admitted','release_approved'))
        and all(r[k] is False for k in ('quality_approved','training_admitted','release_approved')),'Correction approval or source selection changed')
    require(c['native_conditions_pass'] is r['native_constraints_pass'] and c['geometry_conditions_pass'] is r['sampled_geometry_conditions_pass'],'Correction measured decisions changed')
    request=read(folder/'fit/request.json');require(request['implementation_sha256']=={n:p['implementation_sha256'][n] for n in FIT_METHODS},'Correction fitter methods changed')
    for n,h in request['implementation_sha256'].items():require(sha256(folder/'fit/implementation'/n)==h,'Correction fitter method archive changed')
    for path,h in request['inputs_sha256'].items():require(sha256(path)==h,'Correction fitter input changed')
    scene=SceneContacts(read(folder/'contacts.json'),folder)
    edits=SceneEdits(read(folder/'permissions.json'),scene,sha256(folder/'contacts.json'),rotation_storage_policy=p['options']['rotation_storage_policy'])
    retained=ResumeState(folder/'fit',sha256(folder/'contacts.json'),sha256(folder/'permissions.json'),edits)
    retained.check_geometry(read(folder/'geometry-policy.json'),sha256(folder/'contacts.json'));retained.check_inputs()
    for probe in r['probes']:
        require(read(folder/'fit/probes'/probe['label']/'probe.json')==probe,'Correction probe receipt changed')
        for n,h in probe['files_sha256'].items():checked_file(folder/'fit',n,h)
    require(sha256(folder/'fit/source-rate-caps.npz')==r['source_rate_caps_sha256'],'Correction source cap archive changed')
    require(sha256(folder/'fit/contact-audit/result.json')==r['contacts_result_sha256'] and sha256(folder/'fit/geometry-audit/result.json')==r['geometry_result_sha256'],'Correction contact or geometry audit changed')
    audit=checked_contact_audit(folder/'fit/contact-audit',p['implementation_sha256'])
    require(audit['spec_sha256']==sha256(folder/'fit/proposal/contacts.json'),'Correction proposal intent changed')
    final=next(probe for probe in r['probes'] if probe['label']=='final')
    require(c['native_conditions_pass'] is (final['merit'][0]==0 and audit['passed'] and all(a['passed'] for a in r['edits'].values())),
        'Correction native decision differs from final measured conditions')
    geometry=read(folder/'fit/geometry-audit/result.json')
    for n,k in (('policy.json','derived_policy_sha256'),('observations.npz','observations_sha256'),('observations.npz.receipt.json','observation_receipt_sha256')):
        checked_file(folder/'fit/geometry-audit',n,geometry[k])
    require(geometry['sampled_conditions_pass'] is c['geometry_conditions_pass'],'Correction geometry decision changed')
    original_audit=folder/'original-intent-audit/result.json'
    require(c['original_intent_pass'] is (read(original_audit)['passed'] if original_audit.is_file() else None),'Original contact intent decision changed')
    if original_audit.is_file():
        original=checked_contact_audit(original_audit.parent,p['implementation_sha256'])
        require(original['spec_sha256']==sha256(folder/'original-intent-proposal.json'),'Original contact intent audit changed')
    if r['original_contact_intent_result_sha256'] is not None:
        require(sha256(folder/'fit/original-contact-audit/result.json')==r['original_contact_intent_result_sha256'],'Resumed original contact intent audit changed')
        checked_contact_audit(folder/'fit/original-contact-audit',p['implementation_sha256'])
    expected={'fit/result.json','fit/contact-audit/result.json','fit/geometry-audit/result.json','fit/contacts.json','fit/permissions.json','fit/source-rate-caps.npz'}|{s['snapshot'] for s in p['sources'].values()}
    expected|={f'fit/probes/final/{name}.glb' for name in read(folder/'permissions.json')['actors']}
    if (folder/'original-contact-intent.json').is_file():expected|={'original-intent-audit/result.json','original-intent-proposal.json'}
    if r['original_contact_intent_result_sha256'] is not None:expected.add('fit/original-contact-audit/result.json')
    require(set(c['downloads'])==expected,'Complete fixed correction downloads required')
    for n,h in c['downloads'].items():
        target=(folder/n).resolve();require(target.is_relative_to(folder) and sha256(target)==h,'Correction download changed')
        data['downloads'].append(dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=h))
    data.update(native_conditions_pass=c['native_conditions_pass'],geometry_conditions_pass=c['geometry_conditions_pass'],
        original_intent_pass=c['original_intent_pass'] if c['original_intent_pass'] is not None else r['original_contact_intent_pass'],controls=p['controls'],resume_from=p['resume_from'],
        authoring_request=read(folder/'draft.json'),actors={})
    for name,s in p['sources'].items():
        candidate=f'fit/probes/final/{name}.glb' if name in read(folder/'permissions.json')['actors'] else s['snapshot']
        data['actors'][name]=dict(original_url=f'/files/{NAMESPACE}/{job}/{s["snapshot"]}',original_sha256=s['sha256'],
            candidate_url=f'/files/{NAMESPACE}/{job}/{candidate}',candidate_sha256=c['downloads'][candidate],
            correction_requested=name in read(folder/'permissions.json')['actors'])
    return data


def listing():
    jobs=[]
    for folder in sorted((ROOT/'reports'/NAMESPACE).glob('*'),reverse=True):
        if folder.is_dir() and NAME.fullmatch(folder.name) and (folder/'pipeline.json').is_file():
            try:jobs.append(dict(id=folder.name,status=read(folder/'pipeline.json')['status'],quality_approved=False))
            except (ValueError,OSError,KeyError,TypeError):jobs.append(dict(id=folder.name,status='invalid',quality_approved=False))
    return dict(jobs=jobs)


def served_file(relative):
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE:return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        if not target.is_relative_to(folder):return None
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,OSError,KeyError,TypeError):return None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
