import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review_session import CATEGORIES,validate,scrub,build,build_many,import_reviews
from strep import save,read,sha256
from gltf_tools import read_glb,write_glb

MANIFEST=dict(packet_id='test',cases=[dict(id='clip-001'),dict(id='clip-002')])
def evidence():
 # Synthetic validator fixture, never a real animator rating.
 return dict(schema='strep-human-review-v1',packet_id='test',manifest_sha256='a'*64,reviewer_id='synthetic-test',independent_human=True,reviews=[dict(clip_id='clip-001',scores={k:4 for k in CATEGORIES},not_applicable={},major_defect=False,confidence='medium',notes='Synthetic test',cleanup=dict(status='not_performed',active_seconds=None,operations='',time_limit_seconds=None))])

def test_partial_review_is_not_release_approval():
 result=validate(evidence(),MANIFEST,'a'*64)
 assert result['reviewed']==1 and result['missing']==['clip-002'] and not result['complete'] and not result['quality_approved']

@pytest.mark.parametrize('failure',['identity','attestation','packet','hash','duplicate','unknown','rating','missing_score','unexplained_na','action_na','cleanup_faked','cleanup_negative','cleanup_nan','censored_without_limit'])
def test_invalid_evidence_rejected(failure):
 d=evidence();r=d['reviews'][0]
 if failure=='identity':d['reviewer_id']=' '
 if failure=='attestation':d['independent_human']=False
 if failure=='packet':d['packet_id']='other'
 if failure=='hash':d['manifest_sha256']='b'*64
 if failure=='duplicate':d['reviews'].append(copy.deepcopy(r))
 if failure=='unknown':r['clip_id']='clip-999'
 if failure=='rating':r['scores']['action']=True
 if failure=='missing_score':del r['scores']['action']
 if failure=='unexplained_na':r['scores']['contacts_collisions']=None
 if failure=='action_na':r['scores']['action']=None;r['not_applicable']['action']='No action'
 if failure=='cleanup_faked':r['cleanup']['active_seconds']=0
 if failure in ['cleanup_negative','cleanup_nan']:r['cleanup']=dict(status='completed',active_seconds=-1 if failure=='cleanup_negative' else float('nan'),operations='Test',time_limit_seconds=None)
 if failure=='censored_without_limit':r['cleanup']=dict(status='time_limit',active_seconds=60,operations='Test',time_limit_seconds=None)
 with pytest.raises(ValueError):validate(d,MANIFEST,'a'*64)

def test_censored_and_abandoned_attempts_preserved():
 for status in ['time_limit','abandoned']:
  d=evidence();d['reviews'][0]['cleanup']=dict(status=status,active_seconds=60,operations='Test edit',time_limit_seconds=60)
  assert validate(d,MANIFEST,'a'*64)['reviewed']==1

def test_explained_non_action_na():
 d=evidence();d['reviews'][0]['scores']['contacts_collisions']=None;d['reviews'][0]['not_applicable']['contacts_collisions']='No contact in intended action'
 assert validate(d,MANIFEST,'a'*64)['reviewed']==1

def test_packet_blinding_and_import_hashes(tmp_path):
 job=tmp_path/'job';take=job/'takes/secret-offset-seed-501';take.mkdir(parents=True)
 source=take/'soma.glb';doc=dict(asset=dict(version='2.0'),scenes=[dict(name='secret',nodes=[])],scene=0,animations=[dict(name='secret-offset',extras=dict(source='secret'),channels=[],samplers=[])],extras=dict(condition='offset'))
 write_glb(source,doc,b'');save(job/'pipeline.json',dict(status='complete'))
 save(job/'summary.json',dict(trials=[dict(id=take.name,frames=120,seed=501,request=dict(id='secret-offset',segments=[dict(prompt='Wave.',duration_s=4)]),hashes={'soma.glb':sha256(source)})]))
 packet=tmp_path/'packet';key=tmp_path/'private/key.json';build(job,packet,key,17)
 manifest=read(packet/'manifest.json');review,binary=read_glb(packet/manifest['cases'][0]['path'])
 assert review['animations'][0]['name']=='Motion' and 'extras' not in review and 'extras' not in review['animations'][0]
 assert binary==read_glb(source)[1] and read_glb(source)[0]['animations'][0]['name']=='secret-offset'
 assert 'secret' not in (packet/'manifest.json').read_text() and read(key)['cases'][0]['trial_id']==take.name
 with pytest.raises(ValueError):build(job,packet,key,17)
 response=evidence();response.update(packet_id=manifest['packet_id'],manifest_sha256=sha256(packet/'manifest.json'));save(tmp_path/'synthetic.json',response)
 import_reviews(packet,tmp_path/'synthetic.json',tmp_path/'imported');assert read(tmp_path/'imported/validation.json')['complete']
 (packet/manifest['cases'][0]['path']).write_bytes(b'changed')
 with pytest.raises(ValueError):import_reviews(packet,tmp_path/'synthetic.json',tmp_path/'bad')

def test_key_must_be_outside_packet(tmp_path):
 with pytest.raises(ValueError):build(tmp_path/'missing',tmp_path/'packet',tmp_path/'packet/key.json',1)


def test_missing_context_cannot_receive_contact_score():
 manifest=copy.deepcopy(MANIFEST)
 manifest['cases'][0]['review_context']={'unavailable_categories':{'contacts_collisions':'Partner absent'}}
 with pytest.raises(ValueError,match='scene evidence'):validate(evidence(),manifest,'a'*64)
 d=evidence();d['reviews'][0]['scores']['contacts_collisions']=None
 d['reviews'][0]['not_applicable']['contacts_collisions']='Cannot inspect absent partner'
 assert validate(d,manifest,'a'*64)['reviewed']==1


def make_job(folder,seed):
 take=folder/'takes'/f'condition-seed-{seed}';take.mkdir(parents=True)
 source=take/'soma.glb';write_glb(source,dict(asset=dict(version='2.0'),scenes=[dict(nodes=[])],scene=0),b'')
 save(folder/'pipeline.json',dict(status='complete'))
 save(folder/'summary.json',dict(trials=[dict(id=take.name,frames=120,seed=seed,request=dict(id='condition',segments=[dict(prompt='Wave.',duration_s=4)]),hashes={'soma.glb':sha256(source)})]))
 return source


def test_multi_job_packet_keeps_all_seeds_and_neutral_ids(tmp_path):
 jobs=[tmp_path/'one',tmp_path/'two']
 for i,job in enumerate(jobs):make_job(job,500+i)
 packet=tmp_path/'packet';key=tmp_path/'key.json'
 build_many(jobs,packet,key,9,{'condition':{'note':'Visible actor only','unavailable_categories':{'contacts_collisions':'Object missing'}}})
 manifest=read(packet/'manifest.json')
 assert len(manifest['cases'])==2 and {c['seed'] for c in read(key)['cases']}=={500,501}
 assert 'condition' not in str([c.get('path') for c in manifest['cases']])
 assert all(c['review_context']['note']=='Visible actor only' for c in manifest['cases'])


def test_duplicate_or_incomplete_job_is_not_silently_filtered(tmp_path):
 job=tmp_path/'job';make_job(job,1)
 with pytest.raises(ValueError,match='distinct'):build_many([job,job],tmp_path/'packet',tmp_path/'key.json',1)
 save(job/'pipeline.json',dict(status='failed'))
 with pytest.raises(ValueError,match='completed'):build_many([job],tmp_path/'packet',tmp_path/'key.json',1)


def test_source_path_escape_is_rejected_before_packet_creation(tmp_path):
 job=tmp_path/'job';make_job(job,1);data=read(job/'summary.json');data['trials'][0]['id']='../../../elsewhere'
 save(job/'summary.json',data)
 with pytest.raises(ValueError,match='escaping'):build(job,tmp_path/'packet',tmp_path/'key.json',1)
 assert not (tmp_path/'packet').exists()
