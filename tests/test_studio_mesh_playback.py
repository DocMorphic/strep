"""Portable source-bound Studio playback options and actual fitter adaptation."""
from pathlib import Path
import copy,shutil,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_mesh_contact_feasibility import setup
from rig_loop import encode
from rig_contact_fit_options import defaults,validate,bind
import rig_contact_authoring as author
from rig_playback_contact_job import run
from strep import read,save,sha256


def seed(tmp_path,monkeypatch):
    source,spec,f,c,_=setup(tmp_path);jobs=tmp_path/'jobs';parent=jobs/'parent';original=parent/'source';transfer=parent/'transfer'
    original.mkdir(parents=True);transfer.mkdir()
    shutil.copyfile(source,original/'character.glb');save(original/'rig-profile.json',dict(mapping={'Hips':0,'LeftLeg':1,'LeftShin':2,'LeftFoot':3,'LeftToeBase':4}))
    encode(f.rig,f.world,set(range(len(f.order))),0,transfer/'character.glb','portable source')
    digest=sha256(transfer/'character.glb');spec['glb_sha256']=digest
    report=dict(frames=7,fps=30,root_node=0,mapping={'Hips':0,'LeftLeg':1,'LeftShin':2,'LeftFoot':3,'LeftToeBase':4},
        glb_sha256=digest,source_kind='gltf_animation',source=str(original/'character.glb'),source_sha256=sha256(source),
        character=str(original/'character.glb'),target_mesh_floor_depth_max_m=0.)
    save(transfer/'report.json',report);save(transfer/'inventory.json',{})
    shutil.copyfile(original/'rig-profile.json',transfer/'rig-profile.json')
    save(transfer/'contacts.json',dict(intervals=[],origin='none_supplied'))
    save(transfer/'root-motion.json',dict(times_s=(np.arange(7)/30).tolist(),positions_m=f.world[:,0,:3,3].tolist()))
    save(parent/'request.json',dict(label='Synthetic',asset_id=sha256(source),profile_id=sha256(original/'rig-profile.json'),kind='rough_import',source_kind='gltf_animation'))
    save(parent/'result.json',dict(kind='rough_import',label='Synthetic',variants=dict(transfer=dict(sha256=digest))))
    save(parent/'pipeline.json',dict(status='complete'))
    monkeypatch.setattr(author,'JOBS',jobs)
    payload=dict(source_job='parent',variant='transfer',spec=spec,
        fit_options={**defaults(),'spacing_frames':2,'floor_iterations':3,'contact_iterations':8})
    return parent,payload


def archive(folder):
    snapshot=folder/'source/implementation';snapshot.mkdir()
    for name,digest in bind().items():shutil.copyfile(Path('scripts')/name,snapshot/name)


@pytest.mark.parametrize('field,value',[('schema','other'),('contact_clock','hold'),('spacing_frames',True),('spacing_frames',0),
    ('spacing_frames',121),('floor_iterations',1.5),('floor_iterations',201),('contact_iterations',0),('contact_iterations',None)])
def test_options_are_exact_bounded_and_not_coerced(tmp_path,field,value):
    q=defaults();q[field]=value
    with pytest.raises(ValueError):validate(q,tmp_path/'clip.glb')


@pytest.mark.parametrize('value',[None,True,{},dict(defaults(),extra=True)])
def test_options_require_the_complete_explicit_schema(tmp_path,value):
    with pytest.raises(ValueError):validate(value,tmp_path/'clip.glb')


def test_periodic_metadata_and_api_never_silently_fall_back(tmp_path,monkeypatch):
    parent,payload=seed(tmp_path,monkeypatch);save(parent/'transfer/timeline.json',dict(period_frames=6))
    metadata=author.metadata('parent','transfer');assert not metadata['playback_fit']['available']
    with pytest.raises(ValueError,match='periodic closure'):author.validate_request(payload)
    payload.pop('fit_options');assert author.validate_request(payload)[-1]==payload['spec']


def test_fit_choice_is_separate_and_hash_bound_before_worker(tmp_path,monkeypatch):
    parent,payload=seed(tmp_path,monkeypatch);out=tmp_path/'edit';request=author.prepare(payload,out)
    assert request['contact_fit']==payload['fit_options'] and request['contact_fit_sha256']==sha256(out/'contact-fit.json')
    assert read(out/'contact-spec.json')==payload['spec'] and 'contact_clock' not in read(out/'contact-spec.json')
    assert request['contact_fit_implementation']==bind() and sha256(out/'transfer/character.glb')==sha256(parent/'transfer/character.glb')


@pytest.mark.parametrize('clock',['authored-keys','frame-hold'])
def test_actual_fitter_builds_candidate_metadata_and_strict_review(tmp_path,monkeypatch,clock):
    parent,payload=seed(tmp_path,monkeypatch);payload['fit_options']['contact_clock']=clock
    out=tmp_path/'edit';author.prepare(payload,out);archive(out)
    evidence,review=run(out)
    assert review['contact_clock']==clock and not review['quality_approved']
    fit=read(out/'mesh-fit/result.json')
    assert review['numerical_screen_passed']==fit['numerical_screen_passed']
    assert review['retained_input']==fit['retained_input'] and evidence['glb_sha256']==sha256(out/'corrected/character.glb')
    assert read(out/'corrected/report.json')['glb_sha256']==sha256(out/'corrected/character.glb')
    assert sha256(out/'transfer/character.glb')==sha256(parent/'transfer/character.glb')
    assert sha256(out/'corrected/character.glb')==sha256(out/'mesh-fit/candidate.glb')
    assert (out/'corrected/contacts.json').exists() and (out/'corrected/root-motion.json').exists()


@pytest.mark.parametrize('fault',['options','implementation','archive','input','spec'])
def test_changed_worker_bindings_reject_before_fitting(tmp_path,monkeypatch,fault):
    _,payload=seed(tmp_path,monkeypatch);out=tmp_path/'edit';author.prepare(payload,out);archive(out)
    if fault=='options':save(out/'contact-fit.json',{**payload['fit_options'],'contact_iterations':9})
    if fault=='implementation':
        q=read(out/'request.json');q['contact_fit_implementation']['rig_mesh_trajectory.py']='0'*64;save(out/'request.json',q)
    if fault=='archive':(out/'source/implementation/mesh_contact_clock.py').write_text('changed',encoding='utf8')
    if fault=='input':(out/'transfer/character.glb').write_bytes((out/'transfer/character.glb').read_bytes()+b'\0')
    if fault=='spec':q=read(out/'contact-spec.json');q['contacts'][0]['target_position_m'][0]+=.001;save(out/'contact-spec.json',q)
    with pytest.raises(ValueError,match='changed'):run(out)
    assert not (out/'mesh-fit').exists()


def test_source_inspection_uses_the_requested_clock_and_remains_read_only(tmp_path,monkeypatch):
    parent,payload=seed(tmp_path,monkeypatch);payload['fit_options']['contact_clock']='frame-hold'
    before={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}
    result=author.inspect_request(payload)
    assert result['playback_contacts']['contact_clock']=='frame-hold'
    assert result['playback_floor']['samples']>=7
    assert before=={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}
    payload.pop('fit_options');assert 'playback_contacts' not in author.inspect_request(payload)


def test_legacy_request_never_gains_playback_options(tmp_path,monkeypatch):
    _,payload=seed(tmp_path,monkeypatch);payload.pop('fit_options');out=tmp_path/'legacy'
    request=author.prepare(payload,out)
    assert 'contact_fit' not in request and not (out/'contact-fit.json').exists()


def test_progress_reports_phase_without_trial_quality_claim(tmp_path,monkeypatch):
    parent,payload=seed(tmp_path,monkeypatch);out=parent.parent/'edit';author.prepare(payload,out)
    save(out/'pipeline.json',dict(status='processing'));save(out/'mesh-fit/pipeline.json',
        dict(status='fitting_mesh_feasibility',phase='contacts',iteration=8,floor_reached=False,protected_contacts_reached=False))
    import studio_characters as studio
    monkeypatch.setattr(studio,'JOBS',parent.parent)
    item=next(j for j in studio.jobs() if j['id']=='edit')
    assert item['contact_fit_progress']==dict(phase='contacts',iteration=8)
    assert 'quality_approved' not in item and 'floor_reached' not in item['contact_fit_progress']
