"""Synthetic developer submissions only; no human evidence is created."""
import copy
from pathlib import Path
import sys
import zipfile

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import developer_packet_review as developer
import portable_review_packet as portable
from review_session import validate as independent, CATEGORIES
from strep import save, read, sha256

MANIFEST = dict(packet_id='synthetic', review_type='developer', cases=[dict(id='clip-001'), dict(id='clip-002')])


def evidence():
    return dict(schema='strep-developer-packet-review-v1', packet_id='synthetic', manifest_sha256='a'*64,
        reviewer_id='synthetic-test', human_review=True, independent_human=False, review_type='developer',
        quality_approved=False, release_approved=False, reviews=[dict(clip_id='clip-001',
        scores={k: 4 for k in CATEGORIES}, not_applicable={}, major_defect=False, confidence='medium',
        notes='Synthetic fixture', cleanup=dict(status='not_performed', active_seconds=None,
        operations='', time_limit_seconds=None))])


def test_developer_evidence_cannot_become_independent_review():
    data=evidence();result=developer.validate(data, MANIFEST, 'a'*64)
    assert result['reviewed']==1 and result['missing']==['clip-002'] and not result['complete']
    assert not result['independent_review'] and not result['quality_approved'] and not result['release_approved']
    with pytest.raises(ValueError):independent(data, MANIFEST, 'a'*64)
    forged={k:data[k] for k in ('packet_id','manifest_sha256','reviewer_id','reviews')}
    forged.update(schema='strep-human-review-v1', independent_human=True)
    with pytest.raises(ValueError, match='independent packet'):independent(forged, MANIFEST, 'a'*64)


@pytest.mark.parametrize('field,value', [
    ('human_review',False), ('human_review',1), ('independent_human',True),
    ('quality_approved',True), ('release_approved',True), ('review_type','independent'),
    ('packet_id','other'), ('manifest_sha256','b'*64), ('reviewer_id',' '),
    ('schema','strep-human-review-v1'),
])
def test_mismatched_identity_or_approval_rejected(field,value):
    data=evidence();data[field]=value
    with pytest.raises(ValueError):developer.validate(data, MANIFEST, 'a'*64)


def test_developer_response_requires_developer_packet():
    manifest=copy.deepcopy(MANIFEST);del manifest['review_type']
    with pytest.raises(ValueError,match='developer packet'):developer.validate(evidence(),manifest,'a'*64)


def test_missing_context_and_actual_cleanup_rules_are_shared():
    manifest=copy.deepcopy(MANIFEST)
    manifest['cases'][0]['review_context']={'unavailable_categories':{'contacts_collisions':'Partner absent'}}
    data=evidence()
    with pytest.raises(ValueError,match='scene evidence'):developer.validate(data,manifest,'a'*64)
    data['reviews'][0]['scores']['contacts_collisions']=None
    data['reviews'][0]['not_applicable']['contacts_collisions']='Cannot see partner geometry'
    data['reviews'][0]['cleanup'].update(active_seconds=0)
    with pytest.raises(ValueError,match='Unperformed'):developer.validate(data,manifest,'a'*64)
    for status in ['completed','time_limit','abandoned']:
        data['reviews'][0]['cleanup']=dict(status=status,active_seconds=60,operations='Synthetic editing fixture',time_limit_seconds=60)
        assert developer.validate(data,manifest,'a'*64)['reviewed']==1
    data['reviews'][0]['cleanup']['active_seconds']=float('nan')
    with pytest.raises(ValueError):developer.validate(data,manifest,'a'*64)


def source_packet(tmp_path,monkeypatch):
    root=tmp_path/'project';scripts=root/'scripts';scripts.mkdir(parents=True)
    for name in ['soma-preview-skin.js','serve_review_packet.py','review-identity.js']:
        (scripts/name).write_text('synthetic runtime fixture')
    (scripts/'human-review.html').write_text('../../assets/viewer/node_modules/three/build/three.module.js ../../scripts/soma-preview-skin.js ../../scripts/review-identity.js')
    three=root/'assets/viewer/node_modules/three'
    for name in ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','LICENSE']:
        p=three/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic runtime fixture')
    monkeypatch.setattr(developer,'ROOT',root);monkeypatch.setattr(portable,'ROOT',root)
    packet=tmp_path/'source';(packet/'clips').mkdir(parents=True)
    cases=[]
    for n in [1,2]:
        name=f'clips/clip-{n:03d}.glb';(packet/name).write_bytes(b'synthetic motion '+bytes([n]))
        cases.append(dict(id=f'clip-{n:03d}',path=name,sha256=sha256(packet/name),frames=120,fps=30,
            segments=[dict(prompt='Synthetic action',duration_s=4)],
            review_context={'unavailable_categories':{'contacts_collisions':'Missing object'}}))
    save(packet/'manifest.json',dict(schema='strep-review-packet-v1',packet_id='original',cases=cases))
    for name in ['viewer.html','LICENSE.txt','README.txt','serve.py']:(packet/name).write_text('synthetic fixture')
    save(packet/'package-integrity.json',dict(files={p.relative_to(packet).as_posix():sha256(p) for p in packet.rglob('*') if p.is_file()}))
    return packet


def test_new_packet_preserves_every_clip_and_context_without_source_mutation(tmp_path,monkeypatch):
    source=source_packet(tmp_path,monkeypatch);before={p.relative_to(source).as_posix():sha256(p) for p in source.rglob('*') if p.is_file()}
    packet=tmp_path/'developer';archive=tmp_path/'developer.zip'
    result=developer.prepare(source,packet,archive)
    original=read(source/'manifest.json');manifest=read(packet/'manifest.json')
    assert manifest['cases']==original['cases'] and manifest['packet_id']!=original['packet_id']
    assert manifest['review_type']=='developer' and result['human_reviews_collected']==0
    assert result['source_files_sha256']==before
    assert {p.relative_to(source).as_posix():sha256(p) for p in source.rglob('*') if p.is_file()}==before
    assert (packet/'runtime/review-identity.js').is_file() and '../../' not in (packet/'viewer.html').read_text()
    assert 'developer animation review' in (packet/'README.txt').read_text()
    inventory=read(packet/'package-integrity.json')['files']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(inventory)|{'package-integrity.json'}
    data=evidence();data.update(packet_id=manifest['packet_id'],manifest_sha256=sha256(packet/'manifest.json'))
    data['reviews'][0]['scores']['contacts_collisions']=None
    data['reviews'][0]['not_applicable']['contacts_collisions']='Missing object'
    response=tmp_path/'synthetic.json';save(response,data)
    imported=tmp_path/'imported';developer.import_reviews(packet,response,imported)
    assert sha256(imported/'response.json')==sha256(response)
    assert not read(imported/'validation.json')['independent_review']
    with pytest.raises(ValueError):developer.import_reviews(packet,response,imported)
    (packet/'clips/clip-001.glb').write_bytes(b'changed')
    with pytest.raises(ValueError,match='clip changed'):developer.import_reviews(packet,response,tmp_path/'bad-import')


@pytest.mark.parametrize('failure',['changed_clip','changed_manifest','extra_key','inventoried_key','escaping_clip','duplicate_id','existing_output'])
def test_invalid_source_or_output_rejected_before_copy(tmp_path,monkeypatch,failure):
    source=source_packet(tmp_path,monkeypatch);packet=tmp_path/'developer';archive=tmp_path/'developer.zip'
    if failure=='changed_clip':(source/'clips/clip-001.glb').write_bytes(b'changed')
    if failure=='changed_manifest':(source/'manifest.json').write_text('{}')
    if failure in ['extra_key','inventoried_key']:
        (source/'organizer-key.json').write_text('private fixture')
        if failure=='inventoried_key':
            inventory=read(source/'package-integrity.json');inventory['files']['organizer-key.json']=sha256(source/'organizer-key.json');save(source/'package-integrity.json',inventory)
    if failure in ['escaping_clip','duplicate_id']:
        manifest=read(source/'manifest.json')
        if failure=='escaping_clip':manifest['cases'][0]['path']='../secret.glb'
        else:manifest['cases'][1]['id']=manifest['cases'][0]['id']
        save(source/'manifest.json',manifest)
    if failure=='existing_output':packet.mkdir()
    with pytest.raises(ValueError):developer.prepare(source,packet,archive)
    assert not archive.exists() and (not packet.exists() or not list(packet.iterdir()))
