"""Immutable event-only edits preserve selected geometry and periodic metadata."""
import shutil
from pathlib import Path
from strep import read,save,sha256
from rig_contact_authoring import source
from rig_events import load,edit,validate_markers


def inherited_joint_status(result,variant,glb,source_job):
    """Only the unchanged selected joint candidate may inherit its original audit."""
    if variant!='transfer' or not result.get('joint_edit_status'):return None
    audit_path=glb.parent/'joint-edit-audit.json';audit=read(audit_path)
    expected='numerical_screens_met' if audit['numerical_screen_passed'] else 'rejected'
    if audit.get('glb_sha256')!=sha256(glb) or result['joint_edit_status']!=expected:
        raise ValueError('Joint quality audit does not match selected motion/status')
    prior=result.get('inherited_joint_edit')
    if prior and (prior['audit_sha256']!=sha256(audit_path) or prior['glb_sha256']!=sha256(glb)):
        raise ValueError('Inherited joint quality evidence changed')
    return dict(status=expected,targets_reached=audit['targets_reached'],
        audit_sha256=sha256(audit_path),glb_sha256=sha256(glb),
        source_job=source_job,source_variant=variant,
        origin_job=prior['origin_job'] if prior else source_job,
        scope='Unchanged motion only. Marker timing edits do not re-evaluate or approve joint/contact quality.')


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'schema','job','variant','glb_sha256','label','markers'} or payload['schema']!='strep-rig-events-v1':raise ValueError('Invalid event edit request')
    snapshot=source(payload['job'],payload['variant'])
    if sha256(snapshot[4])!=payload['glb_sha256']:raise ValueError('Event source changed')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'])<=160:raise ValueError('Name the marked clip')
    validate_markers(payload['markers'],snapshot[3]['frames']);return snapshot


def prepare(payload,folder):
    previous,result,original,report,glb=validate(payload)
    joint_status=inherited_joint_status(result,payload['variant'],glb,previous.name)
    folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    target=folder/'input';shutil.copytree(glb.parent,target)
    metadata=glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json'):
        if not (target/name).exists():shutil.copyfile(metadata/name,target/name)
    if not (target/'events.json').exists() and (metadata/'events.json').exists():shutil.copyfile(metadata/'events.json',target/'events.json')
    spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if spec.exists():shutil.copyfile(spec,folder/'contact-spec.json')
    from rig_contact_timing import snapshot,bind_inputs
    snapshot(glb,target)
    name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((target/'contacts.json').resolve())
    save(target/'report.json',report);save(folder/'event-edit.json',payload)
    history=folder/'source/event-history'/folder.name;history.mkdir(parents=True);shutil.copytree(target,history/'input');shutil.copyfile(folder/'event-edit.json',history/'event-edit.json')
    request=dict(kind='event_edit',label=payload['label'],asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/name),correct_contacts=False,recipe_sha256=sha256(folder/'event-edit.json'))
    if payload['variant']=='corrected' and 'correction_status' in result:
        request['inherited_correction']=dict(status=result['correction_status'],audit=result.get('correction_audit'),source_job=previous.name,source_variant=payload['variant'])
    elif payload['variant']=='transfer' and result.get('inherited_correction'):
        request['inherited_correction']=result['inherited_correction']
    if joint_status:request['inherited_joint_edit']=joint_status
    if 'repeated' in result['variants'] and payload['variant']==result['variants']['repeated'].get('source_variant','transfer'):
        expected=result['variants']['repeated']['sha256']
        repeated=previous/'corrected/repeated' if payload['variant']=='corrected' else previous/'repeated'
        if sha256(repeated/'character.glb')!=expected:raise ValueError('Repeated source changed')
        shutil.copytree(repeated,folder/'repeated');request['repeated_sha256']=expected
    bind_inputs(folder,request)
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def run(folder):
    folder=Path(folder);recipe=read(folder/'event-edit.json');request=read(folder/'request.json');report=read(folder/'input/report.json')
    from rig_contact_timing import verify_inputs,load as load_timing,write as write_timing
    verify_inputs(folder,request)
    if sha256(folder/'input/character.glb')!=recipe['glb_sha256'] or sha256(folder/'event-edit.json')!=request['recipe_sha256']:raise ValueError('Event snapshot changed')
    if request.get('inherited_joint_edit'):
        inherited=request['inherited_joint_edit']
        if sha256(folder/'input/joint-edit-audit.json')!=inherited['audit_sha256'] or sha256(folder/'input/character.glb')!=inherited['glb_sha256']:
            raise ValueError('Inherited joint quality snapshot changed')
    target=folder/'transfer';shutil.copytree(folder/'input',target)
    timing=load_timing(folder/'input/character.glb')
    if timing is not None:write_timing(target,timing[0],timing[1]['fit_options'],'event_markers',timing[2])
    save(target/'events.json',edit(load(folder/'input'),recipe['markers'],recipe['glb_sha256'],report['frames']))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((target/'contacts.json').resolve())
    save(target/'report.json',report)
    if (target/'timeline.json').exists() and 'period_frames' in read(target/'timeline.json'):
        from rig_runtime_cycle import write
        try:write(target)
        except ValueError as exc:save(target/'runtime-unavailable.json',dict(reason=str(exc)))
        if (folder/'repeated').exists():
            from rig_events import remap
            repeated=folder/'repeated';rep=read(repeated/'report.json');p=read(target/'timeline.json')['period_frames'];count=rep['frames']
            if sha256(repeated/'character.glb')!=request['repeated_sha256']:raise ValueError('Repeated snapshot changed')
            save(repeated/'events.json',remap([load(target)],[[dict(frame=f%p,weight=1.,cycle_offset=f//p)] for f in range(count)],[dict(name='cycle_boundary',frame=f,time_s=f/30) for f in range(p,count,p)]))
            rep.update(source=report['source'],character=report['character'],contact_annotations_file=str((repeated/'contacts.json').resolve()))
            save(repeated/'report.json',rep)
    return report
