"""Offline routes and synthetic review fixtures; never a real human review."""
from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest
from safetensors.torch import load_file

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_kimodo_training_corpus import fixture as corpus_fixture, NAMES, WHEN
import studio_correction_review as studio
import kimodo_training_corpus as corpus
import inspect_motion
import action_studio_server as server
from gltf_tools import write_glb
from strep import read,save,sha256


@pytest.fixture
def setup(corpus_fixture,monkeypatch):
    f=corpus_fixture
    monkeypatch.setattr(studio,'ROOT',f.root)
    monkeypatch.setattr(server,'ROOT',f.root)
    monkeypatch.setattr(inspect_motion,'skeleton_metadata',lambda _: (NAMES,[],[]))
    draft=read(f.draft);audit=read(f.audit)
    for index,item in enumerate(draft['items']):
        source=Path(item['source_motion']);preview=Path(item['source_preview'])
        np.savez(source,local_rot_mats=np.tile(np.eye(3,dtype=np.float32),(3,77,1,1)),
                 root_positions=np.full((3,3),index/10,dtype=np.float32),foot_contacts=np.zeros((3,6),dtype=np.float32))
        write_glb(preview,{'asset':{'version':'2.0'},'buffers':[{'byteLength':4}]},b'\0'*4)
        item['source_motion_sha256']=sha256(source);item['source_preview_sha256']=sha256(preview)
        audit['inputs_sha256'][str(source)]=sha256(source)
    save(f.audit,audit);draft['audit_result_sha256']=sha256(f.audit)
    path=f.root/'reports/kimodo-target-review-fixture/draft.json';path.parent.mkdir();save(path,draft)
    reservations=f.root/'benchmarks/release-prompt-reservations-v1.json';reservations.parent.mkdir()
    save(reservations,read(f.reservations))
    evidence=f.root/'reports/fixture-rights.txt';evidence.write_text('Synthetic fixture only, no actual permission.')
    return SimpleNamespace(root=f.root,draft=path,identifier=path.parent.name,digest=sha256(path),evidence=evidence,reservations=reservations)


def selection(f,item='segment0'):
    return studio.metadata(f.identifier,f.digest,item)


def packed(f,item='segment0'):
    data=selection(f,item);recipe=data['recipe']
    for channel,row in enumerate(recipe['contacts']):row['intervals'][0]['contact']=channel%2==0
    return studio.pack_request({'draft_id':f.identifier,'draft_sha256':f.digest,'recipe':recipe})


def review(f):
    return {'draft_id':f.identifier,'draft_sha256':f.digest,
            'reviewer':{'name':'Numerical fixture only','role':'developer','reviewed_at':WHEN},
            'items':[dict(id='segment'+str(i),decision='exclude',split=None,semantic_pass=None,
                          motion_quality_pass=None,contact_schedule_pass=None,cleanup_seconds=None,
                          notes='Synthetic exclusion only',pack_id=None,rights=None) for i in range(2)]}


def accept(f,body,pack):
    body['items'][0].update(decision='accept_corrected',split='train',semantic_pass=True,motion_quality_pass=True,
                           contact_schedule_pass=True,cleanup_seconds=12.5,pack_id=pack['id'],
                           rights=dict(authorized_by='Numerical fixture',attested_at=WHEN,permitted=True,
                                       evidence_paths=[f.evidence.relative_to(f.root).as_posix()],
                                       obligations='Fixture only',notes='No real human authorization'))


def test_listing_and_bound_metadata_start_unknown(setup):
    result=studio.listing();assert result['drafts'][0]['sha256']==setup.digest
    data=studio.first(setup.identifier,setup.digest)
    assert data['frames']==3 and data['preview_start_s']==0 and data['preview_end_s']==2/30
    assert data['preview_url'].startswith('/files/action-jobs/')
    assert all(row['intervals'][0]['contact'] is None for row in data['recipe']['contacts'])
    assert data['quality_approved'] is data['training_admitted'] is False


@pytest.mark.parametrize('fault',['hash','item','traversal','candidate','window','external_preview'])
def test_invalid_selections_rejected(setup,fault):
    args=[setup.identifier,setup.digest,'segment0']
    if fault=='hash':args[1]='f'*64
    if fault=='item':args[2]='missing'
    if fault=='traversal':args[0]='../kimodo-target-review-fixture'
    if fault=='candidate':args.extend([str(setup.root/'outside.npz'),0])
    if fault=='window':args.extend([selection(setup)['candidate_relative'],1])
    if fault=='external_preview':
        data=read(setup.draft);preview=Path(data['items'][0]['source_preview'])
        write_glb(preview,{'asset':{'version':'2.0'},'buffers':[{'byteLength':4}],'images':[{'uri':'other.png'}]},b'\0'*4)
        data['items'][0]['source_preview_sha256']=sha256(preview);save(setup.draft,data);args[1]=sha256(setup.draft)
    with pytest.raises((ValueError,OSError)):studio.metadata(*args)


def test_pack_requires_every_on_off_label_and_preserves_exact_geometry(setup):
    data=selection(setup)
    with pytest.raises(ValueError,match='Unreviewed'):studio.pack_request({'draft_id':setup.identifier,'draft_sha256':setup.digest,'recipe':data['recipe']})
    result=packed(setup);values=load_file(result['correction']['path'])
    assert values['foot_contacts'].tolist()==[[True,False,True,False]]*3
    assert values['root_positions'].numpy().tolist()==[[0.,0.,0.]]*3
    assert not result['training_admitted'] and not result['quality_approved']


def test_recipe_source_cannot_be_substituted(setup):
    data=selection(setup);data['recipe']['fps']=60
    with pytest.raises(ValueError,match='source/clock'):studio.pack_request({'draft_id':setup.identifier,'draft_sha256':setup.digest,'recipe':data['recipe']})


def test_all_exclusions_are_recordable_but_cannot_enter_training(setup):
    result=studio.save_review(review(setup));assert result['reviewed_corrections']==0
    assert all(result[k] is False for k in ('training_admitted','quality_approved','release_approved'))
    with pytest.raises(ValueError,match='training correction'):
        corpus.validate(result['submission']['path'],setup.reservations,NAMES)


def test_synthetic_acceptance_records_actual_fields_without_admission(setup):
    body=review(setup);accept(setup,body,packed(setup));result=studio.save_review(body)
    assert result['reviewed_corrections']==1 and not result['training_admitted']
    data,accepted,_=corpus.validate(result['submission']['path'],setup.reservations,NAMES)
    assert data['reviewer']['name']=='Numerical fixture only' and accepted[0]['row']['cleanup_seconds']==12.5


@pytest.mark.parametrize('fault',['permission','cleanup','checkbox','other_pack','stale_pack','path','missing_row','reviewer'])
def test_incomplete_or_misbound_human_claims_rejected_and_failure_retained(setup,fault):
    body=review(setup);pack=packed(setup);accept(setup,body,pack)
    if fault=='permission':body['items'][0]['rights']['permitted']=False
    if fault=='cleanup':body['items'][0]['cleanup_seconds']=None
    if fault=='checkbox':body['items'][0]['motion_quality_pass']=False
    if fault=='other_pack':body['items'][0]['pack_id']=packed(setup,'segment1')['id']
    if fault=='stale_pack':Path(pack['correction']['path']).write_bytes(b'stale')
    if fault=='path':body['items'][0]['rights']['evidence_paths']=['../outside.txt']
    if fault=='missing_row':body['items'].pop()
    if fault=='reviewer':body['reviewer']['name']=''
    with pytest.raises((ValueError,OSError)):studio.save_review(body)
    if fault!='missing_row':
        results=list((setup.root/'reports/native-correction-submissions').glob('*/result.json'))
        assert len(results)==1 and read(results[0])['status']=='failed'


def handler(path,body=None,**headers):
    h=server.Handler.__new__(server.Handler);h.path=path
    raw=__import__('json').dumps(body).encode() if body is not None else b''
    h.headers={'Host':'127.0.0.1:8768','Origin':'http://127.0.0.1:8768','Content-Type':'application/json','Content-Length':str(len(raw)),**headers}
    h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},job_lock=threading.Lock())
    h.rfile=BytesIO(raw);h.respond=lambda code,data:setattr(h,'response',(code,data))
    return h


def test_routes_offline_use_existing_origin_and_size_guards(setup,monkeypatch):
    # The real inference lock uses Windows msvcrt; these in-memory handler tests
    # must neither acquire it nor require a platform-specific runtime in CI.
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_lock=lambda:nullcontext()))
    h=handler('/api/correction-review-drafts');h.do_GET();assert h.response[0]==200
    h=handler('/api/correction-review-packet?draft='+setup.identifier+'&sha256='+setup.digest);h.do_GET();assert h.response[0]==200
    for query in ['&extra=x','&draft=duplicate']:
        h=handler('/api/correction-review-packet?draft='+setup.identifier+'&sha256='+setup.digest+query);h.do_GET();assert h.response[0]==400
    h=handler('/api/correction-review-submission',review(setup));h.do_POST();assert h.response[0]==201
    for headers,code in [({'Origin':'http://foreign'},403),({'Content-Type':'text/plain'},415),({'Content-Length':'1048577'},400)]:
        h=handler('/api/correction-review-submission',review(setup),**headers);h.do_POST();assert h.response[0]==code
    h=handler('/api/correction-review-pack',{'draft_id':setup.identifier,'draft_sha256':setup.digest,'recipe':None});h.do_POST();assert h.response[0]==400
    assert server.allowed_file('/correction-review-panel.mjs')==setup.root/'scripts/correction-review-panel.mjs'


def test_record_only_policy_cannot_disable_other_validation(setup):
    result=studio.save_review(review(setup))
    with pytest.raises(ValueError,match='policy'):
        corpus.validate(result['submission']['path'],setup.reservations,NAMES,require_training=1)


def preview_fixture(f,monkeypatch):
    from test_native_candidate_preview import native_fixture
    names,parents,source,path,_=native_fixture(f.root)
    monkeypatch.setattr(inspect_motion,'skeleton_metadata',lambda _: (names,parents,[]))
    draft=read(f.draft);item=draft['items'][0]
    np.savez(item['source_motion'],**source);Path(item['source_preview']).write_bytes(path.read_bytes())
    item['source_motion_sha256']=sha256(item['source_motion']);item['source_preview_sha256']=sha256(item['source_preview'])
    audit_path=Path(draft['audit_result']);audit=read(audit_path);audit['inputs_sha256'][item['source_motion']]=item['source_motion_sha256'];save(audit_path,audit)
    draft['audit_result_sha256']=sha256(audit_path);save(f.draft,draft);f.digest=sha256(f.draft)
    candidate=f.root/'reports/edited.npz';roots=source['root_positions'].copy();roots[:,0]+=.2
    np.savez(candidate,local_rot_mats=source['local_rot_mats'],root_positions=roots)
    data=studio.metadata(f.identifier,f.digest,'segment0',str(candidate),0)
    return dict(draft_id=f.identifier,draft_sha256=f.digest,item_id='segment0',candidate_motion=data['recipe']['candidate_motion'],candidate_start_frame=0)


def test_preview_api_exports_actual_candidate_without_admitting_contacts(setup,monkeypatch):
    payload=preview_fixture(setup,monkeypatch);result=studio.preview_request(payload)
    assert result['selection']==payload and result['preview_start_s']==0 and not result['training_admitted']
    relative=result['preview_url'].removeprefix('/files/');path=studio.served_preview(relative)
    assert path.is_file() and server.allowed_file(result['preview_url'])==path
    for invalid in [relative.replace('candidate.glb','result.json'),relative.replace('candidate.glb','../candidate.glb')]:
        assert studio.served_preview(invalid) is None
    path.write_bytes(path.read_bytes()+b'changed');assert studio.served_preview(relative) is None


def test_preview_requires_current_candidate_hash_and_offline_route_lock(setup,monkeypatch):
    payload=preview_fixture(setup,monkeypatch)
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_lock=lambda:nullcontext()))
    h=handler('/api/correction-review-preview',payload);h.do_POST();assert h.response[0]==201
    payload['candidate_motion']['sha256']='f'*64
    h=handler('/api/correction-review-preview',payload);h.do_POST();assert h.response[0]==400


def test_failed_preview_is_retained_and_never_served(setup,monkeypatch):
    payload=preview_fixture(setup,monkeypatch)
    import native_candidate_preview
    def failed(*args):raise ValueError('Numerical export failure')
    monkeypatch.setattr(native_candidate_preview,'export_candidate',failed)
    with pytest.raises(ValueError,match='export failure'):studio.preview_request(payload)
    files=list((setup.root/'reports/native-correction-previews').glob('*/result.json'))
    assert len(files)==1 and read(files[0])['status']=='failed'
    assert studio.served_preview('native-correction-previews/'+files[0].parent.name+'/candidate.glb') is None


def edit_selection(f,monkeypatch):
    payload=preview_fixture(f,monkeypatch)
    payload['edit']=dict(joint='Joint4',rotation_vector_degrees=[3,0,0],root_offset_m=[0,.01,0],
                         start_frame=0,peak_frame=1,end_frame=2)
    return payload


def test_edit_saves_new_native_geometry_and_checked_preview_with_no_contact_labels(setup,monkeypatch):
    payload=edit_selection(setup,monkeypatch)
    before=Path(payload['candidate_motion']['path']).read_bytes()
    result=studio.edit_request(payload)
    assert result['selection']==payload and result['candidate_start_frame']==0
    assert all(result[k] is False for k in ('quality_approved','training_admitted','release_approved'))
    data=result['metadata'];assert data['recipe']['candidate_motion']==result['candidate_motion']
    assert all(row['intervals'][0]['contact'] is None for row in data['recipe']['contacts'])
    with np.load(result['candidate_motion']['path'],allow_pickle=False) as archive:
        assert set(archive.files)=={'local_rot_mats','root_positions','posed_joints','global_rot_mats'}
        local=archive['local_rot_mats'];roots=archive['root_positions']
    with np.load(payload['candidate_motion']['path'],allow_pickle=False) as archive:
        for frame in (0,2):
            np.testing.assert_array_equal(local[frame],archive['local_rot_mats'][frame])
            np.testing.assert_array_equal(roots[frame],archive['root_positions'][frame])
    assert Path(payload['candidate_motion']['path']).read_bytes()==before
    assert studio.served_preview(result['preview']['preview_url'].removeprefix('/files/')).is_file()
    assert result['report']['measured']['joint_from_original_degrees']==pytest.approx(3,abs=1e-5)
    assert result['report']['joint_position_change_m']['Joint5']>=.009


def test_edit_route_uses_current_binding_origin_size_and_worker_lock(setup,monkeypatch):
    payload=edit_selection(setup,monkeypatch)
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_lock=lambda:nullcontext()))
    h=handler('/api/correction-review-edit',payload);h.do_POST();assert h.response[0]==201
    for headers,code in [({'Origin':'http://foreign'},403),({'Content-Type':'text/plain'},415),({'Content-Length':'1048577'},400)]:
        h=handler('/api/correction-review-edit',payload,**headers);h.do_POST();assert h.response[0]==code
    from contextlib import contextmanager
    @contextmanager
    def busy():raise RuntimeError('Another local action job is running');yield
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_lock=busy))
    h=handler('/api/correction-review-edit',payload);h.do_POST();assert h.response[0]==409
    payload['candidate_motion']['sha256']='f'*64
    with pytest.raises(ValueError,match='changed'):studio.edit_request(payload)


def test_edit_failure_retained_when_cumulative_original_bound_exceeded(setup,monkeypatch):
    payload=edit_selection(setup,monkeypatch);payload['edit']['root_offset_m']=[.1,0,0]
    with pytest.raises(ValueError,match='Cumulative'):studio.edit_request(payload)
    results=list((setup.root/'reports/native-correction-edits').glob('*/result.json'))
    assert len(results)==1 and read(results[0])['status']=='failed'
    assert not (results[0].parent/'candidate.npz').exists()


def test_edit_chains_against_original_and_source_and_methods_remain_hash_bound(setup,monkeypatch):
    payload=edit_selection(setup,monkeypatch);payload['edit']['rotation_vector_degrees']=[2,0,0]
    result=studio.edit_request(payload);payload['candidate_motion']=result['candidate_motion'];payload['candidate_start_frame']=0
    second=studio.edit_request(payload)
    assert second['report']['measured']['joint_from_original_degrees']==pytest.approx(4,abs=1e-4)
    record=read(Path(second['candidate_motion']['path']).parent/'result.json')
    assert all(sha256(path)==digest for path,digest in record['inputs_sha256'].items())
    assert record['methods_sha256']['native_motion_edit.py']==sha256(Path(studio.__file__).parent/'native_motion_edit.py')


def test_failed_edit_preview_does_not_report_complete_edit(setup,monkeypatch):
    payload=edit_selection(setup,monkeypatch)
    def failed(*args):raise ValueError('Preview unavailable')
    monkeypatch.setattr(studio,'preview_request',failed)
    with pytest.raises(ValueError,match='Preview unavailable'):studio.edit_request(payload)
    record=read(next((setup.root/'reports/native-correction-edits').glob('*/result.json')))
    assert record['status']=='failed' and not record['quality_approved']
