"""Hash-bound mesh contact drafts and snapshotted edits of existing rig clips."""
import copy
import re
import shutil
import threading
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256
from studio_characters import JOBS

INSPECTION_LOCK=threading.Lock()


def inspect_request(payload):
    from inspect_rig_contacts import inspect
    if not INSPECTION_LOCK.acquire(blocking=False):raise ValueError('A contact inspection is already running')
    try:
        _,_,report,glb,spec=validate_request(payload)
        result=inspect(glb,spec,report['mapping'])
        if 'fit_options' in payload:
            from rig_subframe_contacts import inspect as playback_contacts
            from rig_subframe_floor import inspect as playback_floor
            result['playback_contacts']=playback_contacts(glb,spec,payload['fit_options']['contact_clock'],contact_clock_overrides=payload['fit_options'].get('contact_clock_overrides'))
            result['playback_floor']=playback_floor(glb,spec['screen']['floor_depth_m'])
        return result
    finally:INSPECTION_LOCK.release()


def source(job_id,variant):
    if not isinstance(job_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',job_id) or variant not in ('transfer','corrected','input'):
        raise ValueError('Choose an existing character result and version')
    folder=JOBS/job_id
    if not (folder/'result.json').is_file() or read(folder/'pipeline.json')['status']!='complete':
        raise ValueError('Source character job is not complete')
    result=read(folder/'result.json')
    if result['kind']=='neutral' or variant not in result['variants']:raise ValueError('Choose a motion result, not neutral alignment')
    glb=folder/variant/'character.glb';expected=result['variants'][variant]['sha256']
    if sha256(glb)!=expected:raise ValueError('Source character motion changed')
    request=read(folder/'request.json');report_path=folder/variant/'report.json'
    report=read(report_path if report_path.exists() else folder/'transfer/report.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(glb_sha256=expected,source=str(folder/'source'/source_name))
    if sha256(report['source'])!=report['source_sha256']:raise ValueError('Source native motion changed')
    return folder,result,request,report,glb


def empty_spec(report):
    return dict(schema='strep-target-contact-v1',glb_sha256=report['glb_sha256'],fps=report['fps'],frames=report['frames'],
        provenance='Authored mesh patches, intervals and world targets in Studio; not independently annotated or approved.',
        root_node=report['root_node'],patches={},contacts=[],
        edit_joints={role:dict(node=node,limit_degrees=35 if 'Shin' in role else 25 if 'ToeBase' not in role else 15)
            for role,node in report['mapping'].items() if role.startswith(('Left','Right')) and role.endswith(('Leg','Shin','Foot','ToeBase'))},
        limits=dict(root_horizontal_m=.04,root_vertical_m=.12,root_step_m=.015,joint_step_degrees=5),
        screen=dict(floor_depth_m=.005,contact_error_m=.02),
        objective=dict(contact_weight=12.,floor_weight=4.,rotation_prior_m_per_radian=.15,root_prior=1.,temporal_weight=.5),max_nfev=120)


def metadata(job_id,variant):
    from rig_asset import RigAsset
    from gltf_tools import sample_animation
    folder,result,request,report,glb=source(job_id,variant);rig=RigAsset.load(glb)
    spec=empty_spec(report)
    saved_spec=folder/'input/contact-spec.json' if variant=='input' else folder/'contact-spec.json'
    if saved_spec.is_file():
        spec=read(saved_spec);spec['glb_sha256']=report['glb_sha256']
        spec['patches']={name:dict(vertices=patch['vertices']) for name,patch in spec['patches'].items()}
    primitives=[];offset=0
    for p in rig.primitives:
        primitives.append(dict(node=p['node'],mesh=rig.document['nodes'][p['node']]['mesh'],primitive=p['primitive'],
            vertex_offset=offset,vertices=len(p['positions'])))
        offset+=len(p['positions'])
    world=sample_animation(rig.document,rig.binary,0,0);vertices=rig.vertices(world)
    checks=sorted({p['vertex_offset']+v for p in primitives for v in [0,p['vertices']//2,p['vertices']-1]})
    def descendant(node):
        parent=rig.parents[node]
        while parent>=0 and parent!=report['root_node']:parent=rig.parents[parent]
        return parent==report['root_node']
    aliases={node:role for role,node in report['mapping'].items()}
    from rig_events import load as load_events
    timeline_path=glb.parent/'timeline.json'
    timeline=read(timeline_path) if timeline_path.exists() else {}
    periodic=timeline.get('period_frames')
    from rig_contact_fit_options import defaults,validate as validate_fit
    saved_options=None
    if request.get('contact_fit') is not None and request['kind']=='contact_edit' and variant in ('transfer','corrected'):
        saved=folder/'contact-fit.json'
        if sha256(saved)!=request.get('contact_fit_sha256') or read(saved)!=request['contact_fit'] or sha256(folder/'contact-spec.json')!=request['authored_spec_sha256']:
            raise ValueError('Saved contact fitting choice or draft changed')
        saved_options=validate_fit(request['contact_fit'],glb,spec)
    return dict(job_id=job_id,variant=variant,glb_sha256=report['glb_sha256'],frames=report['frames'],fps=report['fps'],period_frames=periodic,events=load_events(glb.parent if (glb.parent/'events.json').exists() or variant!='corrected' else folder/'transfer'),
        asset_id=request['asset_id'],spec=spec,primitives=primitives,vertex_count=offset,
        verification_vertices=[dict(index=i,position_m=vertices[i].tolist()) for i in checks],
        playback_fit=dict(available='period_frames' not in timeline,defaults=defaults(),saved_options=saved_options,
            reason='Whole-clip playback fitting does not preserve cycle closure.' if 'period_frames' in timeline else None),
        editable_joints=[dict(node=n,label=aliases.get(n,rig.document['nodes'][n].get('name','Bone')+' · '+str(n)))
            for n in rig.joints if n!=report['root_node'] and descendant(n)])


def validate_request(payload):
    from rig_asset import RigAsset
    from target_rig_contact import validate
    if not isinstance(payload,dict) or not {'source_job','variant','spec'}<=set(payload) or set(payload)-{'source_job','variant','spec','fit_options'}:raise ValueError('Source job, version and contact draft required')
    folder,result,request,report,glb=source(payload['source_job'],payload['variant'])
    spec=payload['spec']
    if not isinstance(spec,dict) or spec.get('glb_sha256')!=report['glb_sha256'] or spec.get('frames')!=report['frames'] or spec.get('root_node')!=report['root_node']:
        raise ValueError('Contact draft does not match the selected animation')
    if not isinstance(spec.get('patches'),dict) or not 1<=len(spec['patches'])<=24:raise ValueError('Choose 1–24 mesh patches')
    for name,patch in spec['patches'].items():
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9 _.-]{1,48}',name) or not isinstance(patch,dict) or set(patch)!={'vertices'}:
            raise ValueError('Patch needs a short name and vertex list')
        if not isinstance(patch['vertices'],list) or not 1<=len(patch['vertices'])<=256:raise ValueError('Choose 1–256 vertices per patch')
    if not isinstance(spec.get('contacts'),list) or not 1<=len(spec['contacts'])<=64:raise ValueError('Choose 1–64 contact intervals')
    if not isinstance(spec.get('edit_joints'),dict) or not 1<=len(spec['edit_joints'])<=20:raise ValueError('Choose 1–20 editable joints')
    if not isinstance(spec.get('provenance'),str) or len(spec['provenance'])>2000:raise ValueError('Invalid contact provenance')
    if spec.get('screen')!={'floor_depth_m':.005,'contact_error_m':.02}:raise ValueError('Studio contact screens cannot be relaxed')
    validate(spec,RigAsset.load(glb))
    if 'fit_options' in payload:
        from rig_contact_fit_options import validate as validate_fit
        validate_fit(payload['fit_options'],glb,spec)
    return folder,request,report,glb,copy.deepcopy(spec)


def prepare(payload,folder):
    previous,original,report,glb,spec=validate_request(payload)
    folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    target=folder/'transfer';target.mkdir()
    shutil.copyfile(glb,target/'character.glb')
    metadata=glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json'):
        shutil.copyfile(metadata/name,target/name)
    for name in ('events.json','timeline.json','contact-review.json'):
        if (metadata/name).exists():shutil.copyfile(metadata/name,target/name)
    shutil.copyfile(glb.parent/'root-motion.json',target/'root-motion.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()),character=str((folder/'source/character.glb').resolve()),
        contact_edit_parent=dict(job_id=previous.name,variant=payload['variant'],glb_sha256=spec['glb_sha256']))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((target/'contacts.json').resolve())
    save(target/'report.json',report);save(folder/'contact-spec.json',spec)
    request=dict(asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),kind='contact_edit',
        label=('Contact edit · '+read(previous/'result.json')['label'])[:160],correct_contacts=True,
        source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/source_name),source_job=previous.name,input_variant=payload['variant'],input_glb_sha256=sha256(glb),
        authored_spec_sha256=sha256(folder/'contact-spec.json'))
    if 'fit_options' in payload:
        from rig_contact_fit_options import validate as validate_fit,bind
        options=validate_fit(payload['fit_options'],target/'character.glb',spec);save(folder/'contact-fit.json',options)
        request.update(contact_fit=options,contact_fit_sha256=sha256(folder/'contact-fit.json'),contact_fit_implementation=bind())
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'))
    return request
