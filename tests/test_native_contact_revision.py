"""Explicit contact changes preserve source epochs, bounds and original intent."""
import copy
from pathlib import Path
import sys
import zipfile
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_contact_revision import apply,validate,portable_record,SCHEMA
import studio_native_scene as studio
import action_studio_server as server
from native_scene_contacts import SceneContacts
from strep import read,save,sha256
from test_studio_native_scene import setup,handler,mock_author


def revised(tmp_path,monkeypatch,*,partner=False,world=False):
    baseline,source,resolver=setup(tmp_path,monkeypatch)
    node=baseline['scene']['contacts'][0]['vertices'][0][0]
    if partner or world:
        row=copy.deepcopy(baseline['scene']['contacts'][0]);row['id']='meeting';row['mode']='touch';row['interval_s']=[1.,1.];row['limits']={'position_m':.005}
        row['target']=dict(space='actor',actor='B',vertices=[[node,0,0]],reduction='individual') if partner else dict(space='world',points_m=[[1.,2.,3.]])
        baseline['scene']['contacts'].append(row)
    name='meeting' if partner or world else 'left-grip'
    patch=lambda actor,ids:dict(glb_sha256=baseline['scene']['actors'][actor]['sha256'],vertices=[[node,0,i] for i in ids],reduction='centroid')
    edits=[dict(id=name,source=patch('A',[1,2]),partner=patch('B',[0,3,4]) if partner else None)]
    payload=apply(baseline,edits);payload['contact_revision']=dict(schema=SCHEMA,baseline=copy.deepcopy(baseline),edits=edits)
    return baseline,source,resolver,payload


@pytest.mark.parametrize('space',['object','world','partner'])
def test_revision_preserves_whole_original_draft_and_explicit_patch_meaning(tmp_path,monkeypatch,space):
    baseline,source,resolver,payload=revised(tmp_path,monkeypatch,partner=space=='partner',world=space=='world')
    before=copy.deepcopy(payload);original_hash=sha256(source)
    spec,geometry,edit,sources=studio.validate_request(payload,resolver)
    assert payload==before and sha256(source)==original_hash
    assert payload['geometry']==baseline['geometry'] and payload['object_edit']==baseline['object_edit']
    assert spec['objects']==baseline['scene']['objects']
    for old,new in zip(baseline['scene']['contacts'],spec['contacts']):
        assert new['limits']==old['limits'] and new['mode']==old['mode'] and new['interval_s']==old['interval_s']
    assert validate(payload)[1]==payload['contact_revision']
    record=portable_record(payload)
    assert record['original_contacts']==baseline['scene']['contacts'] and record['authored_contacts']==payload['scene']['contacts']
    assert record['original_intent_retained'] and record['contact_intent_revised'] and not record['animation_edited']
    assert not any(record[k] for k in ('quality_approved','training_admitted','release_approved'))


@pytest.mark.parametrize('fault',['limits','timing','mode','placement','sha','duration','object','geometry','object-edit','other-contact','target-point','actor-name','vertices','reduction','extra','nested-baseline'])
def test_hidden_draft_changes_cannot_pass_as_a_patch_revision(tmp_path,monkeypatch,fault):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch);row=p['scene']['contacts'][0]
    if fault=='limits':row['limits']['position_m']*=2
    elif fault=='timing':row['interval_s'][0]+=.01
    elif fault=='mode':row['mode']='touch'
    elif fault=='placement':p['scene']['actors']['A']['placement']['translation_m'][0]+=.1
    elif fault=='sha':p['scene']['actors']['A']['sha256']='0'*64
    elif fault=='duration':p['scene']['duration_s']+=1
    elif fault=='object':p['scene']['objects']['item']['geometry']['radius_m']+=.1
    elif fault=='geometry':p['geometry']['limits']['penetration_m']*=2
    elif fault=='object-edit':p['object_edit']['maximum_translation_m']*=2
    elif fault=='other-contact':p['scene']['contacts'][1]['vertices'][0][2]=1
    elif fault=='target-point':row['target']['points_m'][0][0]+=.01
    elif fault=='actor-name':row['actor']='B'
    elif fault=='vertices':row['vertices'][0][2]=3
    elif fault=='reduction':row['reduction']='individual'
    elif fault=='extra':p['contact_revision']['approved']=True
    else:p['contact_revision']['baseline']['contact_revision']={}
    with pytest.raises(ValueError):studio.validate_request(p,resolver)


@pytest.mark.parametrize('fault',['wrong-rig','unknown-contact','duplicate-contact','duplicate-ref','bool-ref','oversized','no-change','none','partner-on-object','unknown-ref','correspondence'])
def test_invalid_choices_reject_without_truncation_or_implicit_correspondence(tmp_path,monkeypatch,fault):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch);edits=p['contact_revision']['edits'];e=edits[0];node=e['source']['vertices'][0][0]
    if fault=='wrong-rig':e['source']['glb_sha256']='0'*64
    elif fault=='unknown-contact':e['id']='other'
    elif fault=='duplicate-contact':edits.append(copy.deepcopy(e))
    elif fault=='duplicate-ref':e['source']['vertices'][1]=e['source']['vertices'][0]
    elif fault=='bool-ref':e['source']['vertices'][0][2]=True
    elif fault=='oversized':e['source']['vertices']=[[node,0,i] for i in range(257)]
    elif fault=='no-change':e['source']['vertices']=copy.deepcopy(baseline['scene']['contacts'][0]['vertices']);e['source']['reduction']='individual'
    elif fault=='none':e['source']=None
    elif fault=='partner-on-object':e['partner']=copy.deepcopy(e['source'])
    elif fault=='unknown-ref':e['source']['vertices'][0][2]=500
    else:e['source']['reduction']='individual'
    with pytest.raises(ValueError):
        value=apply(baseline,edits);value['contact_revision']=p['contact_revision'];studio.validate_request(value,resolver)


def test_both_partner_sides_can_be_changed_atomically_with_individual_correspondence(tmp_path,monkeypatch):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch,partner=True);e=p['contact_revision']['edits'][0]
    e['source']['reduction']=e['partner']['reduction']='individual';e['partner']['vertices']=e['partner']['vertices'][:2]
    changed=apply(baseline,[e]);changed['contact_revision']=p['contact_revision'];spec,*_=studio.validate_request(changed,resolver)
    meeting=SceneContacts(spec,studio.ROOT).rows[-1];assert len(meeting['ids'])==len(meeting['target_ids'])==2
    with pytest.raises(ValueError,match='correspondence'):apply(baseline,[dict(e,partner=None)])


def test_read_only_preview_inspects_original_and_authored_endpoints_without_acceptance(tmp_path,monkeypatch):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch);before=copy.deepcopy(p);digest=sha256(source)
    a=studio.revision_preview(p,resolver);b=studio.revision_preview(p,resolver)
    assert a==b and p==before and sha256(source)==digest and a['record']['other_authoring_fields_unchanged']
    assert a['animation_edited'] is False and a['anatomical_review_pending']
    change=a['changes'][0];old=change['original_endpoint_inspection'];new=change['authored_endpoint_inspection']
    assert old['times_s']==new['times_s']==[.8,1.]
    assert not np.array_equal(old['source_world_m'],new['source_world_m'])
    assert old['target_world_m']==new['target_world_m']
    assert 'whole-hold acceptance' in a['scope']


def test_character_only_partner_preview_needs_no_artificial_object(tmp_path,monkeypatch):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch,partner=True)
    baseline['scene']['contacts']=baseline['scene']['contacts'][-1:];baseline['scene']['objects']={};baseline['object_edit']=None
    edits=p['contact_revision']['edits'];p=apply(baseline,edits);p['contact_revision']=dict(schema=SCHEMA,baseline=baseline,edits=edits)
    result=studio.revision_preview(p,resolver)
    assert result['changes'][0]['id']=='meeting' and result['record']['original_intent_retained']
    assert result['changes'][0]['authored_endpoint_inspection']['times_s']==[1.]
    with pytest.raises(ValueError,match='requires at least one scene object'):studio.validate_request(p,resolver)


@pytest.mark.parametrize('fault,code',[('valid',200),('busy',200),('host',403),('origin',403),('type',415),('size',400),('protected-change',400),('source-change',400)])
def test_revision_handler_is_guarded_read_only_and_never_launches_worker(tmp_path,monkeypatch,fault,code):
    _,source,resolver,p=revised(tmp_path,monkeypatch);monkeypatch.setattr(server,'allowed_file',resolver)
    monkeypatch.setattr(server,'worker_busy',lambda:fault=='busy')
    def forbidden(*a,**k):raise AssertionError('Read-only preview launched a worker')
    monkeypatch.setattr(server.subprocess,'Popen',forbidden)
    if fault=='protected-change':p['geometry']['limits']['penetration_m']+=.01
    if fault=='source-change':source.write_bytes(source.read_bytes()+b'changed')
    h=handler(p,'/api/native-scene-contact-revision')
    if fault=='host':h.headers['Host']='example.test'
    if fault=='origin':h.headers['Origin']='https://example.test'
    if fault=='type':h.headers['Content-Type']='text/plain'
    if fault=='size':h.headers['Content-Length']='1048577'
    h.do_POST();assert h.responses[-1][0]==code
    assert not (tmp_path/'reports/native-scene-jobs').exists()


def test_revised_intent_is_archived_and_portable_package_keeps_both_conditions(tmp_path,monkeypatch):
    baseline,source,resolver,p=revised(tmp_path,monkeypatch);folder=studio.folder_for('revised');prepared=studio.prepare(p,folder,resolver)
    assert prepared['contact_revision_requested'] and 'native_contact_revision.py' in prepared['implementation_sha256']
    assert read(folder/'draft.json')['contact_revision']['baseline']==baseline
    assert read(folder/'geometry-policy.json')['limits']==baseline['geometry']['limits']
    monkeypatch.setattr(studio,'author',mock_author(folder,passed=False));studio.run(folder)
    m=studio.manifest(folder.name);assert not m['sampled_conditions_pass'] and not m['quality_approved']
    record=read(folder/'exports/contact-revision.json')
    assert record['original_contacts']==baseline['scene']['contacts'] and record['authored_contacts']==p['scene']['contacts']
    assert record['portable_scene_sha256']==sha256(folder/'exports/scene.json')
    assert record['actor_sha256']['A']==sha256(source)
    with zipfile.ZipFile(folder/'assets.zip') as archive:
        assert archive.read('contact-revision.json')==(folder/'exports/contact-revision.json').read_bytes()
        assert read(folder/'exports/package.json')['files_sha256']['contact-revision.json']==sha256(folder/'exports/contact-revision.json')
    url=f'/files/native-scene-jobs/{folder.name}/exports/contact-revision.json';assert any(e['url']==url for e in m['downloads'])
    (folder/'exports/contact-revision.json').write_bytes(b'changed')
    with pytest.raises(ValueError):studio.manifest(folder.name)


def test_legacy_ordinary_prepared_archive_remains_readable_but_cannot_start_as_current_methods(tmp_path,monkeypatch):
    baseline,source,resolver=setup(tmp_path,monkeypatch);folder=studio.folder_for('legacy');p=studio.prepare(baseline,folder,resolver)
    p['implementation_sha256'].pop('native_contact_revision.py');p.pop('contact_revision_requested');save(folder/'prepared.json',p)
    assert studio.frozen(folder,current_methods=False)==p
    with pytest.raises(ValueError,match='methods'):studio.frozen(folder)
