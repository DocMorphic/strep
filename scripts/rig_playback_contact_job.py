"""Adapt a bound playback experiment into a reviewable Studio contact candidate."""
from pathlib import Path
import copy,shutil
from strep import read,save,sha256,now
from rig_contact_fit_options import validate,bind


def run(folder):
    folder=Path(folder);request=read(folder/'request.json');transfer=folder/'transfer'
    options=validate(read(folder/'contact-fit.json'),transfer/'character.glb')
    if options!=request.get('contact_fit') or sha256(folder/'contact-fit.json')!=request.get('contact_fit_sha256'):
        raise ValueError('Playback fit options changed')
    expected=request.get('contact_fit_implementation')
    if not isinstance(expected,dict) or bind()!=expected:raise ValueError('Playback fitting implementation changed before worker')
    archive=folder/'source/implementation'
    if not archive.is_dir():raise ValueError('Playback worker implementation archive required')
    for name,digest in expected.items():
        if sha256(archive/name)!=digest:raise ValueError('Playback worker archive changed')
    if sha256(transfer/'character.glb')!=request['input_glb_sha256'] or sha256(folder/'contact-spec.json')!=request['authored_spec_sha256']:
        raise ValueError('Authored playback input snapshot changed')
    from rig_mesh_trajectory import run as fit
    result=fit(transfer/'character.glb',folder/'contact-spec.json',folder/'mesh-fit',
        options['spacing_frames'],options['contact_iterations'],True,options['floor_iterations'],True,True,options['contact_clock'])
    measured=folder/'mesh-fit';output=folder/'corrected';output.mkdir(exist_ok=False)
    shutil.copyfile(measured/'candidate.glb',output/'character.glb')
    shutil.copyfile(measured/'root-motion.json',output/'root-motion.json')
    report=copy.deepcopy(read(transfer/'report.json'));report['glb_sha256']=sha256(output/'character.glb')
    report['contact_fit']=dict(method='whole_clip_playback',contact_clock=options['contact_clock'],
        original_glb_sha256=request['input_glb_sha256'],result_sha256=sha256(measured/'result.json'),quality_approved=False)
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (transfer/name).exists():shutil.copyfile(transfer/name,output/name)
    save(output/'report.json',report)
    evidence=read(measured/'audit.json')
    evidence.update(created_at=now(),source_glb_sha256=request['input_glb_sha256'],contact_spec_sha256=request['authored_spec_sha256'],
        glb_sha256=report['glb_sha256'],frames=report['frames'],fps=report['fps'],quality_approved=False,
        numerical_screen_passed=result['numerical_screen_passed'],retained_input=result['retained_input'],
        contact_clock=options['contact_clock'],experiment_result_sha256=sha256(measured/'result.json'))
    save(output/'audit.json',evidence)
    contacts=read(measured/'playback-contact-inspection.json');floor=read(measured/'subframe-floor-inspection.json')
    review=dict(method='whole_clip_playback',contact_clock=options['contact_clock'],failed_intervals=contacts['failed_intervals'],
        contact_intervals=len(contacts['contacts']),contact_error_max_m=max(c['error_max_m'] for c in contacts['contacts']),
        floor_depth_max_m=floor['floor_depth_max_m'],floor_failed_samples=floor['failed_samples'],
        numerical_screen_passed=result['numerical_screen_passed'],retained_input=result['retained_input'],quality_approved=False)
    save(folder/'contact-fit-review.json',review)
    if bind()!=expected or sha256(folder/'contact-fit.json')!=request['contact_fit_sha256'] or sha256(folder/'contact-spec.json')!=request['authored_spec_sha256']:
        raise ValueError('Playback fit options, draft or implementation changed during worker')
    for name,digest in expected.items():
        if sha256(archive/name)!=digest:raise ValueError('Playback worker archive changed during worker')
    if sha256(transfer/'character.glb')!=request['input_glb_sha256']:raise ValueError('Playback input changed during worker')
    return evidence,review
