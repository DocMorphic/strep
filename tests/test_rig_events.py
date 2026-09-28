import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_events import edit,remap,runtime_markers,validate_markers
from strep import ROOT,read,sha256


def marker(id='cue',frame=2,confirmed=True):return dict(id=id,name=id,frame=frame,confirmed=confirmed)


@pytest.mark.parametrize('fault',['duplicate','float','outside','reserved','reserved_whitespace','review_type'])
def test_marker_validation(fault):
    markers=[marker()]
    if fault=='duplicate':markers*=2
    if fault=='float':markers[0]['frame']=2.2
    if fault=='outside':markers[0]['frame']=10
    if fault=='reserved':markers[0]['name']='cycle_boundary'
    if fault=='reserved_whitespace':markers[0]['name']=' cycle_boundary '
    if fault=='review_type':markers[0]['confirmed']=1
    with pytest.raises(ValueError):validate_markers(markers,10)


def test_blend_events_remain_reviewable_and_zero_weight_is_recorded():
    doc=edit(dict(events=[]),[marker('zero',0),marker('partial',1),marker('full',2)],'hash',3)
    result=remap([doc],[[dict(frame=0,weight=0),dict(frame=1,weight=.25)],[dict(frame=2,weight=1)]],[])
    assert [(e['name'],e['frame'],e['requires_review']) for e in result['events']]==[('partial',0,True),('full',1,False)]
    assert result['omitted'][0]['event']['name']=='zero'
    eligible,excluded=runtime_markers(result,2)
    assert [e['name'] for e in eligible]==['cycle_boundary','full']
    assert len(excluded)==1
    # Explicit timing confirmation clears ambiguity without losing its lineage.
    confirmed=edit(result,[dict(id=e['id'],name=e['name'],frame=e['frame'],confirmed=True) for e in result['events']],'newhash',2)
    assert [e['name'] for e in runtime_markers(confirmed,2)[0]]==['cycle_boundary','partial','full']
    assert confirmed['events'][0]['lineage'][1]['weight']==.25


def test_same_name_events_from_both_sources_are_not_deduplicated():
    doc=edit(dict(events=[]),[marker()], 'hash',4)
    mapped=remap([doc,doc],[[dict(source=0,frame=2,weight=.5),dict(source=1,frame=2,weight=.5)]],[])
    assert len(mapped['events'])==2 and len({e['id'] for e in mapped['events']})==2
    assert all(e['requires_review'] for e in mapped['events'])


def test_event_only_job_preserves_geometry_and_cycle_contract(tmp_path,monkeypatch):
    import action_worker_lock
    from rig_event_edit import prepare
    from rig_studio_job import run
    job='20260926-220650-1da442bb';glb=ROOT/'reports/rig-jobs'/job/'transfer/character.glb'
    request=dict(schema='strep-rig-events-v1',job=job,variant='transfer',glb_sha256=sha256(glb),label='Authored wave cues',markers=[marker('accent',15),marker('blend',3,False)])
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    folder=tmp_path/'events';prepare(request,folder);run(folder)
    assert sha256(folder/'transfer/character.glb')==sha256(glb)
    assert [e['name'] for e in read(folder/'transfer/runtime-cycle.json')['markers']]==['cycle_boundary','accent']
    assert read(folder/'result.json')['loop_period_frames']==45
    assert read(folder/'transfer/contacts.json')==read(folder/'input/contacts.json')


def test_marker_edit_of_rejected_periodic_candidate_keeps_rejection(tmp_path,monkeypatch):
    import action_worker_lock
    from rig_event_edit import prepare
    from rig_studio_job import run
    job='20260926-225025-7cb4f8f4';source=ROOT/'reports/rig-jobs'/job
    request=dict(schema='strep-rig-events-v1',job=job,variant='corrected',glb_sha256=sha256(source/'corrected/character.glb'),label='Marker change retains rejected motion',markers=[marker('cue',0)])
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    folder=tmp_path/'marked';prepare(request,folder);run(folder);result=read(folder/'result.json')
    assert result['correction_status']=='rejected'
    assert result['correction_audit']['flags']==read(source/'result.json')['correction_audit']['flags']
    assert sha256(folder/'repeated/character.glb')==sha256(source/'corrected/repeated/character.glb')
    assert result['runtime_cycle'].endswith('/transfer/runtime-cycle.json')
