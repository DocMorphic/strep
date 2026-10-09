"""Independent replay of synthetic cleanup records; never animator evidence."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save,read,sha256
from gltf_tools import write_glb
from review_session import CATEGORIES
from audit_cleanup_timing import audit


@pytest.fixture
def data(tmp_path):
    packet=tmp_path/'packet';source=packet/'clips/clip-001.glb';source.parent.mkdir(parents=True)
    write_glb(source,dict(asset=dict(version='2.0'),scenes=[dict(nodes=[])],scene=0),b'')
    save(packet/'manifest.json',dict(schema='strep-review-packet-v1',packet_id='synthetic',review_type='developer',cases=[dict(id='clip-001',path='clips/clip-001.glb',sha256=sha256(source))]))
    at='2026-10-09T12:00:00.000Z';context=dict(packet_id='synthetic',manifest_sha256=sha256(packet/'manifest.json'),clip_id='clip-001',source_sha256=sha256(source),review_type='developer',reviewer_id='synthetic')
    trace=dict(schema='strep-cleanup-timing-v1',session_id='synthetic-session',context=context,preselected_limit_seconds=60,state='finished',segments=[
        dict(page_id='page',start_ms=0,end_ms=2000,started_at=at,ended_at=at),
        dict(page_id='page',start_ms=100000,end_ms=158000,started_at=at,ended_at=at)],open=None,interruptions=[],finished_at=at,output_artifact=None,quality_approved=False,release_approved=False,active_seconds=60,duration_complete=True)
    path=tmp_path/'trace.json';save(path,trace)
    review=dict(schema='strep-developer-packet-review-v1',packet_id='synthetic',manifest_sha256=context['manifest_sha256'],reviewer_id='synthetic',human_review=True,independent_human=False,review_type='developer',quality_approved=False,release_approved=False,reviews=[dict(clip_id='clip-001',scores={c:3 for c in CATEGORIES},not_applicable={},major_defect=True,confidence='medium',notes='Synthetic test only',cleanup=dict(status='time_limit',active_seconds=60,operations='Synthetic fixture editing',time_limit_seconds=60))])
    response=tmp_path/'review.json';save(response,review)
    return packet,path,response


def test_trace_and_saved_censored_review_match_without_any_quality_approval(data):
    packet,path,response=data;result=audit(packet,path,review=response)
    assert result['active_seconds']==60 and result['intervals_replayed']==2 and result['saved_review_matched']
    assert result['duration_complete'] and not result['edited_artifact_verified'] and not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('change',['packet','source','reviewer','role','sum','reversed','overlap','bool','missing','approval','complete_flag','limit'])
def test_changed_sources_or_inconsistent_timing_are_rejected(data,change):
    packet,path,response=data;trace=read(path)
    if change=='packet':trace['context']['manifest_sha256']='a'*64
    if change=='source':(packet/'clips/clip-001.glb').write_bytes(b'changed')
    if change=='reviewer':trace['context']['reviewer_id']='another'
    if change=='role':trace['context']['review_type']='independent'
    if change=='sum':trace['active_seconds']=59
    if change=='reversed':trace['segments'][0]['end_ms']=-1
    if change=='overlap':trace['segments'][1]['start_ms']=1000;trace['active_seconds']=159
    if change=='bool':trace['segments'][0]['start_ms']=False
    if change=='missing':trace['segments'][0].pop('ended_at')
    if change=='approval':trace['release_approved']=True
    if change=='complete_flag':trace['duration_complete']=False
    if change=='limit':trace['preselected_limit_seconds']=30
    save(path,trace)
    with pytest.raises(ValueError):audit(packet,path,review=response)


def test_interrupted_tail_remains_partial_and_cannot_replace_complete_review_time(data):
    packet,path,response=data;trace=read(path)
    trace['interruptions']=[dict(page_id='old-page',start_ms=1,started_at=trace['finished_at'],detected_at=trace['finished_at'])];trace['duration_complete']=False;save(path,trace)
    assert not audit(packet,path)['duration_complete']
    with pytest.raises(ValueError):audit(packet,path,review=response)


def test_completed_cleanup_requires_matching_actual_edited_asset(data,tmp_path):
    packet,path,response=data;review=read(response);review['reviews'][0]['cleanup']['status']='completed';save(response,review)
    with pytest.raises(ValueError,match='edited GLB'):audit(packet,path,review=response)
    edited=tmp_path/'edited.glb';write_glb(edited,dict(asset=dict(version='2.0'),scenes=[dict(nodes=[])],scene=0),b'')
    trace=read(path);trace['output_artifact']=dict(name='edited.glb',bytes=edited.stat().st_size,sha256=sha256(edited));save(path,trace)
    result=audit(packet,path,review=response,edited_glb=edited);assert result['edited_artifact_verified'] and not result['quality_approved']
    edited.write_bytes(b'changed')
    with pytest.raises(ValueError):audit(packet,path,review=response,edited_glb=edited)


def test_escaping_source_and_extra_event_fields_rejected(data):
    packet,path,response=data;manifest=read(packet/'manifest.json');manifest['cases'][0]['path']='../../escape.glb';save(packet/'manifest.json',manifest)
    trace=read(path);trace['context']['manifest_sha256']=sha256(packet/'manifest.json');save(path,trace)
    with pytest.raises(ValueError):audit(packet,path)


def test_replay_rejects_evidence_changed_during_verification(data,monkeypatch):
    import audit_cleanup_timing as module
    packet,path,response=data;original=module.sha256;calls=0
    def changed(p):
        nonlocal calls
        if Path(p)==path:
            calls+=1
            if calls>1:return 'a'*64
        return original(p)
    monkeypatch.setattr(module,'sha256',changed)
    with pytest.raises(ValueError,match='changed during replay'):audit(packet,path)


def test_duplicate_trace_fields_are_not_silently_accepted(data):
    packet,path,response=data;text=path.read_text();path.write_text(text.replace('"active_seconds": 60','"active_seconds": 60, "active_seconds": 60'))
    with pytest.raises(ValueError,match='Duplicate'):audit(packet,path)
