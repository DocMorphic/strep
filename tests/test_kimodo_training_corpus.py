"""Admission and contact-label fixtures; never claim a real human review."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch
from safetensors.torch import load_file, save_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import kimodo_training_corpus as corpus
from strep import read, save, sha256

NAMES = [f'Joint{index}' for index in range(77)]
WHEN = '2026-10-02T12:00:00+00:00'


def reference(path):return {'path': str(path), 'sha256': sha256(path)}


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, 'ROOT', tmp_path)
    evidence = tmp_path/'ownership.txt'
    evidence.write_text('Numerical fixture only; not a license or human authorization.')
    reservations = tmp_path/'reserved.json'
    save(reservations, {'schema_version':1, 'cases':[{'id':'reserved', 'prompt':'A person walks reserved circles.', 'seeds':[61001]}]})
    inputs, targets, draft_items, rows = {}, [], [], []
    protocol = tmp_path/'protocol.json'; save(protocol, {'job':'fixture'})
    for index in range(2):
        folder = tmp_path/f'reports/action-jobs/fixture/takes/case{index}-seed-77'
        folder.mkdir(parents=True)
        source = folder/'motion.npz'; source.write_bytes(f'original{index}'.encode())
        preview = folder/'soma.glb'; preview.write_bytes(f'preview{index}'.encode())
        encoded = tmp_path/f'encoded{index}.safetensors'; encoded.write_bytes(f'target{index}'.encode())
        inputs[str(source)] = sha256(source)
        target = {'id':f'segment{index}', 'case':f'case{index}', 'source_seed':77, 'prompt':f'A person makes gesture {index}.',
                  'source_start_frame':0, 'source_end_frame_exclusive':3, 'target_file':str(encoded), 'target_sha256':sha256(encoded)}
        targets.append(target)
        draft_items.append({key:target[key] for key in ('id','prompt','source_start_frame','source_end_frame_exclusive')})
        draft_items[-1].update(fps=30, source_motion=str(source), source_motion_sha256=sha256(source),
                               source_preview=str(preview), source_preview_sha256=sha256(preview),
                               encoded_target=str(encoded), encoded_target_sha256=sha256(encoded))
        corrected = tmp_path/f'corrected{index}.safetensors'
        labels = torch.zeros(3,4,dtype=torch.bool); labels[index,0]=True
        metadata={'schema':'strep-native-correction-v1','skeleton':'somaskel77','joint_names':json.dumps(NAMES,separators=(',',':')),
                  'fps':'30','units':'metres','coordinates':'right-handed-Y-up','contact_joints':json.dumps(corpus.CONTACT_JOINTS,separators=(',',':'))}
        save_file({'local_rotations':torch.eye(3).repeat(3,77,1,1),'root_positions':torch.zeros(3,3), 'foot_contacts':labels},str(corrected),metadata=metadata)
        rights = tmp_path/f'rights{index}.json'
        save(rights, {'schema':corpus.RIGHTS, 'authorized_by':'Numerical fixture', 'attested_at':WHEN,
                     'source_motion_sha256':sha256(source), 'correction_sha256':sha256(corrected),
                     'source_kind':'model_output_and_authored_correction','use':'commercial_generative_game_motion_training',
                     'permitted':True, 'evidence_files':[reference(evidence)], 'obligations':'Fixture only', 'notes':'No real authorization'})
        rows.append({'id':target['id'],'decision':'accept_corrected','split':'train' if index==0 else 'development_validation',
                     'semantic_pass':True, 'motion_quality_pass':True,'contact_schedule_pass':True,'cleanup_seconds':12.5,
                     'notes':'Synthetic test review only','correction':reference(corrected),'rights_attestation':reference(rights)})
    audit = tmp_path/'audit.json'
    save(audit, {'schema':'strep-denoising-target-audit-result-v1','status':'complete','base_unchanged':True,
                 'input_files_unchanged':True,'methods_unchanged':True,'protocol_sha256':sha256(protocol),
                 'inputs_sha256':inputs,'targets':targets})
    draft = tmp_path/'draft.json'
    save(draft, {'schema':'strep-native-target-review-draft-v1','training_admitted':False,'quality_approved':False,
                 'audit_result':str(audit),'audit_result_sha256':sha256(audit),'items':draft_items})
    submission = tmp_path/'submission.json'
    save(submission, {'schema':corpus.SUBMISSION,'draft':reference(draft),
                      'reviewer':{'name':'Numerical fixture','role':'developer','reviewed_at':WHEN}, 'items':rows})
    return SimpleNamespace(root=tmp_path,submission=submission,draft=draft,audit=audit,protocol=protocol,
                           reservations=reservations,evidence=evidence)


def change_submission(f, change):
    value=read(f.submission);change(value);save(f.submission,value)


def change_draft(f, change):
    value=read(f.draft);change(value);save(f.draft,value)
    change_submission(f, lambda d:d.update(draft=reference(f.draft)))


def change_audit(f, change):
    value=read(f.audit);change(value);save(f.audit,value)
    change_draft(f, lambda d:d.update(audit_result_sha256=sha256(f.audit)))


def test_completed_fixture_has_source_bound_groups_and_keeps_draft_unapproved(fixture):
    data,accepted,inputs=corpus.validate(fixture.submission,fixture.reservations,NAMES)
    assert len(accepted)==2 and len(inputs)>=12
    assert [row['row']['split'] for row in accepted]==['train','development_validation']
    assert read(fixture.draft)['training_admitted'] is False


def test_actual_draft_schema_cannot_be_submitted_as_review(fixture):
    with pytest.raises(ValueError,match='completed correction submission'):
        corpus.validate(fixture.draft,fixture.reservations,NAMES)


def test_template_is_unreviewed_bound_and_cannot_overwrite(fixture):
    path=fixture.root/'new-submission.json'
    result=corpus.template(fixture.draft,path)
    assert result['draft']==reference(fixture.draft)
    assert all(row['decision']=='unreviewed' for row in result['items'])
    with pytest.raises(ValueError,match='Human reviewer'):
        corpus.validate(path,fixture.reservations,NAMES)
    with pytest.raises(ValueError,match='Fresh'):
        corpus.template(fixture.draft,path)


@pytest.mark.parametrize('field,value',[('semantic_pass',None),('motion_quality_pass',False),('contact_schedule_pass',1),
                                        ('cleanup_seconds',True),('cleanup_seconds',float('nan')),('decision','unreviewed')])
def test_incomplete_reviews_and_unmeasured_cleanup_rejected(fixture,field,value):
    value_data=read(fixture.submission);value_data['items'][0][field]=value
    # Use standard JSON to expose NaN rejection without the helper's writer guard.
    fixture.submission.write_text(json.dumps(value_data))
    with pytest.raises(ValueError):corpus.validate(fixture.submission,fixture.reservations,NAMES)


@pytest.mark.parametrize('file',['ownership.txt','corrected0.safetensors','encoded0.safetensors'])
def test_changed_bound_sources_corrections_and_rights_evidence_rejected(fixture,file):
    path=fixture.root/file;path.write_bytes(path.read_bytes()+b'stale')
    with pytest.raises(ValueError,match='changed'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


@pytest.mark.parametrize('field,value',[('permitted',False),('use','research_only'),('source_motion_sha256','f'*64),('evidence_files',[])])
def test_rights_must_cover_exact_source_and_product_training_use(fixture,field,value):
    path=fixture.root/'rights0.json';data=read(path);data[field]=value;save(path,data)
    change_submission(fixture,lambda d:d['items'][0].update(rights_attestation=reference(path)))
    with pytest.raises(ValueError):corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_retitled_or_rebound_draft_cannot_change_audited_source(fixture):
    change_draft(fixture,lambda d:d['items'][0].update(prompt='Different action'))
    with pytest.raises(ValueError,match='audited source'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_audit_project_relative_target_paths_are_resolved_at_project_root(fixture):
    change_audit(fixture,lambda d:d['targets'][0].update(target_file='encoded0.safetensors'))
    assert len(corpus.validate(fixture.submission,fixture.reservations,NAMES)[1])==2


def test_source_substitution_cannot_hide_behind_valid_file_checksum(fixture):
    other=fixture.root/'different.npz';other.write_bytes(b'different real hash')
    change_draft(fixture,lambda d:d['items'][0].update(source_motion=str(other),source_motion_sha256=sha256(other)))
    with pytest.raises(ValueError,match='original audited take'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


@pytest.mark.parametrize('kind',['seed','prompt','id'])
def test_reserved_seed_and_normalized_prompt_are_rejected(fixture,kind):
    if kind=='seed':
        data=read(fixture.reservations);data['cases'][0]['seeds']=[77];save(fixture.reservations,data)
    elif kind=='prompt':
        data=read(fixture.reservations);data['cases'][0]['prompt']='  A PERSON MAKES GESTURE 0!!! ';save(fixture.reservations,data)
    else:
        data=read(fixture.reservations);data['cases'][0]['id']='case0';save(fixture.reservations,data)
    with pytest.raises(ValueError,match='Reserved'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_every_original_segment_needs_an_explicit_decision(fixture):
    change_submission(fixture,lambda d:d['items'].pop())
    with pytest.raises(ValueError,match='Every segment'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_same_original_hash_cannot_leak_across_train_and_validation(fixture):
    source0=fixture.root/'reports/action-jobs/fixture/takes/case0-seed-77/motion.npz'
    source1=fixture.root/'reports/action-jobs/fixture/takes/case1-seed-77/motion.npz'
    source1.write_bytes(source0.read_bytes());source_hash=sha256(source1)
    change_audit(fixture,lambda d:d['inputs_sha256'].update({str(source1):source_hash}))
    change_draft(fixture,lambda d:d['items'][1].update(source_motion_sha256=source_hash))
    rights=fixture.root/'rights1.json';data=read(rights);data['source_motion_sha256']=source_hash;save(rights,data)
    change_submission(fixture,lambda d:d['items'][1].update(rights_attestation=reference(rights)))
    with pytest.raises(ValueError,match='cannot cross'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_partial_contact_labels_are_rejected_even_with_updated_checksum(fixture):
    path=fixture.root/'corrected0.safetensors'
    from safetensors import safe_open
    with safe_open(str(path),framework='pt') as archive:metadata=archive.metadata()
    values=load_file(str(path));values['foot_contacts']=values['foot_contacts'][:,:3].contiguous();save_file(values,str(path),metadata=metadata)
    change_submission(fixture,lambda d:d['items'][0].update(correction=reference(path)))
    with pytest.raises(ValueError,match='Every frame'):
        corpus.validate(fixture.submission,fixture.reservations,NAMES)


def test_exclusion_requires_explicit_reason_without_silent_approval(fixture):
    def exclude(d):
        row=d['items'][1]
        for key in set(row)-{'id','decision','notes'}:row[key]=None
        row.update(decision='exclude',notes='Not usable supervision')
    change_submission(fixture,exclude)
    _,accepted,_=corpus.validate(fixture.submission,fixture.reservations,NAMES)
    assert len(accepted)==1


class Rep:
    skeleton=SimpleNamespace(somaskel77=SimpleNamespace(bone_order_names=NAMES))
    def normalize(self,value):return (value-2)/3
    def unnormalize(self,value):return value*3+2


def test_prepared_targets_preserve_geometry_and_use_full_reviewed_contacts(fixture,monkeypatch):
    clean=torch.arange(3*369,dtype=torch.float32).reshape(1,3,369)/100
    clean[:,:,-4:]=-2/3  # all heuristic contacts false, normalization mean2/std3
    def encode(*args):return clean.clone(),torch.tensor([.25]),{'quality_approved':False}
    monkeypatch.setattr(corpus,'encode_native_target',encode)
    binding={'inputs_sha256':{str(fixture.evidence):sha256(fixture.evidence)}}
    output=fixture.root/'corpus'
    result=corpus.prepare(fixture.submission,fixture.reservations,output,Rep(),binding)
    assert result['release_approved'] is result['quality_approved'] is False
    assert len(result['items'])==2 and result['items'][0]['heuristic_vs_reviewed_contact_difference_count']==1
    for item in result['items']:
        tensors=load_file(str(output/item['target_file']))
        assert torch.equal(tensors['clean_features'][...,:-4],clean[...,:-4])
        actual=Rep().unnormalize(tensors['clean_features'])[0,:,-4:]
        assert torch.allclose(actual,tensors['reviewed_foot_contacts'].float(),atol=1e-7)
        assert sha256(output/item['target_file'])==item['target_sha256']
    for path,archived in result['archived_evidence'].items():
        assert sha256(output/archived)==result['inputs_sha256'][path]
    with pytest.raises(ValueError,match='Fresh corpus'):
        corpus.prepare(fixture.submission,fixture.reservations,output,Rep(),binding)


def test_stale_input_during_encoding_never_publishes_manifest(fixture,monkeypatch):
    def mutate(*args):
        fixture.evidence.write_text('Changed during encoding')
        return torch.zeros(1,3,369),torch.zeros(1),{}
    monkeypatch.setattr(corpus,'encode_native_target',mutate)
    output=fixture.root/'stale-corpus'
    with pytest.raises(ValueError,match='changed during'):
        corpus.prepare(fixture.submission,fixture.reservations,output,Rep(),{'inputs_sha256':{str(fixture.evidence):sha256(fixture.evidence)}})
    assert not (output/'manifest.json').exists()
