"""Portable actual clip operators preserve mixed contact timing and source bytes."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_mesh_playback import seed
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from rig_loop import encode
from strep import read,save,sha256
from rig_contact_fit_options import defaults
from rig_contact_timing import write,load,snapshot,bind_inputs,verify_inputs,clocks
import rig_contact_authoring as author
import rig_clip_edit as clip
import rig_event_edit as events
import rig_transition as transition
import rig_loop as loop
import rig_mirror_edit as mirror
from rig_mirror import descendants


def publish(folder,kind):
    variants={}
    for name in ('transfer','input','corrected','repeated'):
        if not (folder/name/'character.glb').exists():continue
        variants[name]=dict(sha256=sha256(folder/name/'character.glb'))
        if (folder/name/'contact-timing.json').exists():variants[name]['contact_timing_sha256']=sha256(folder/name/'contact-timing.json')
    save(folder/'result.json',dict(kind=kind,label='Portable source',variants=variants))
    save(folder/'pipeline.json',dict(status='complete'))


def fixture(tmp_path,monkeypatch):
    parent,payload=seed(tmp_path,monkeypatch);glb=parent/'transfer/character.glb';rig=RigAsset.load(glb)
    sampler=NativeSupportSampler(rig.document,rig.binary,0);poses=np.tile(sampler.sample(0),(40,1,1,1))
    poses[:,:,:3,3]+=np.column_stack([np.sin(np.arange(40)/6)*.01,np.zeros(40),np.arange(40)*.001])[:,None,:]
    encode(rig,poses,set(range(len(rig.parents))),0,glb,'Portable timed intent')
    report=read(parent/'transfer/report.json');report.update(frames=40,glb_sha256=sha256(glb));save(parent/'transfer/report.json',report)
    save(parent/'transfer/root-motion.json',dict(times_s=(np.arange(40)/30).tolist(),positions_m=poses[:,0,:3,3].tolist()))
    save(parent/'transfer/contacts.json',dict(intervals=[],origin='none_supplied',mapping={'Hips':0}))
    spec=payload['spec'];spec.update(frames=40,glb_sha256=sha256(glb));patch=next(iter(spec['patches'].values()))
    spec['patches']={f'proxy{i}':copy.deepcopy(patch) for i in range(3)}
    spec['contacts']=[dict(patch=f'proxy{i}',start_frame=a,end_frame_exclusive=b,target_position_m=[i*.1,0,0]) for i,(a,b) in enumerate([(0,2),(12,18),(26,29)])]
    options={**defaults(),'contact_clock_overrides':{'1':'frame-hold','2':'authored-keys'}}
    save(parent/'contact-spec.json',spec);save(parent/'contact-fit.json',options)
    request=read(parent/'request.json');request.update(kind='contact_edit',contact_fit=options,
        contact_fit_sha256=sha256(parent/'contact-fit.json'),authored_spec_sha256=sha256(parent/'contact-spec.json'))
    save(parent/'request.json',request);write(parent/'transfer',spec,options,'portable_fixture');publish(parent,'contact_edit')
    return parent,spec,options


def edit_payload(folder,start=10,last=34,speed=1.5):
    return dict(source_job=folder.name,variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',glb_sha256=sha256(folder/'transfer/character.glb'),
        label='Timing edit',start_frame=start,last_frame=last,speed=speed,poses=[]))


def test_trim_speed_and_chained_drop_remap_explicit_choices(tmp_path,monkeypatch):
    parent,_,options=fixture(tmp_path,monkeypatch);before={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}
    out=parent.parent/'trim';clip.prepare(edit_payload(parent),out);clip.run(out);publish(out,'clip_edit')
    spec,record,_=load(out/'transfer/character.glb')
    assert record['interval_mapping']==[1,2] and record['fit_options']['contact_clock_overrides']=={'0':'frame-hold','1':'authored-keys'}
    assert clocks(record,2)==['frame-hold','authored-keys'] and record['requires_review'] and not record['quality_approved']
    assert author.metadata('trim','transfer')['playback_fit']['saved_options']==record['fit_options']
    assert author.metadata('trim','input')['playback_fit']['saved_options']==options
    newer=parent.parent/'shorter';clip.prepare(edit_payload(out,0,10,1.25),newer);clip.run(newer);publish(newer,'clip_edit')
    assert load(newer/'transfer/character.glb')[1]['fit_options']['contact_clock_overrides']=={'0':'frame-hold'}
    assert before=={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}


def test_empty_trim_retains_explicit_empty_clock_map_and_original(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch);out=parent.parent/'empty'
    clip.prepare(edit_payload(parent,3,8,1),out);clip.run(out);publish(out,'clip_edit')
    spec,record,_=load(out/'transfer/character.glb')
    assert spec['contacts']==[] and record['interval_mapping']==[] and record['fit_options']['contact_clock_overrides']=={}
    assert clocks(load(out/'input/character.glb')[1],3)==['authored-keys','frame-hold','authored-keys']


def test_marker_edit_and_marker_chain_preserve_geometry_and_timing(tmp_path,monkeypatch):
    parent,_,options=fixture(tmp_path,monkeypatch);previous=parent
    for name in ('marked','marked_again'):
        out=parent.parent/name;payload=dict(schema='strep-rig-events-v1',job=previous.name,variant='transfer',glb_sha256=sha256(previous/'transfer/character.glb'),label=name,
            markers=[dict(id='touch',name='touch',frame=15,confirmed=True)])
        events.prepare(payload,out);events.run(out);publish(out,'event_edit')
        assert sha256(out/'transfer/character.glb')==sha256(parent/'transfer/character.glb')
        assert load(out/'transfer/character.glb')[1]['fit_options']==options
        assert author.metadata(name,'transfer')['playback_fit']['saved_options']==options
        assert not load(out/'transfer/character.glb')[1]['quality_approved'];previous=out


def test_marked_clip_trim_remaps_events_and_contact_clocks(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch);marked=parent.parent/'marked'
    events.prepare(dict(schema='strep-rig-events-v1',job=parent.name,variant='transfer',glb_sha256=sha256(parent/'transfer/character.glb'),label='Marked',
        markers=[dict(id='touch',name='touch',frame=15,confirmed=True)]),marked)
    events.run(marked);publish(marked,'event_edit');out=parent.parent/'trim_marked'
    clip.prepare(edit_payload(marked),out);clip.run(out);publish(out,'clip_edit')
    assert load(out/'transfer/character.glb')[1]['fit_options']['contact_clock_overrides']=={'0':'frame-hold','1':'authored-keys'}
    assert read(out/'transfer/events.json')['events'][0]['frame']==3


def test_join_and_joined_loop_retain_clock_and_weighted_intent(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch);out=parent.parent/'joined'
    recipe=dict(schema='strep-rig-transition-v1',label='Mixed timing join',clips=[dict(job=parent.name,variant='transfer',glb_sha256=sha256(parent/'transfer/character.glb'),first_frame=a,last_frame=b) for a,b in [(0,29),(10,39)]],blend_frames=6,yaw_degrees=25)
    transition.prepare(recipe,out);transition.run(out);publish(out,'transition')
    review=read(out/'transfer/contact-review.json');assert review['requires_review']
    for row in review['authored_targets']:
        assert row['contact_clock']==('frame-hold' if row['source_interval_index']==1 else 'authored-keys')
    clocks_out=read(out/'transfer/timeline.json')['contributors']
    for row in review['authored_targets']:
        expected=[dict(frame=f,weight=e['weight']) for f,entries in enumerate(clocks_out) for e in entries if e['source']==row['source'] and e['weight']>0 and row['original_interval']['start_frame']<=e['frame']<row['original_interval']['end_frame_exclusive']]
        assert row['output_frames']==expected
    assert not (out/'transfer/contact-timing.json').exists(),'Blended review must not become an executable fixed-target condition'
    cycle=parent.parent/'cycle';loop.prepare(dict(schema='strep-rig-loop-v1',label='Joined cycle',job=out.name,variant='transfer',glb_sha256=sha256(out/'transfer/character.glb'),start_frame=0,period_frames=30,blend_frames=4,turn_degrees=5),cycle)
    loop.run(cycle);publish(cycle,'loop')
    for name in ('transfer','repeated'):
        rows=read(cycle/name/'contact-review.json')['authored_targets'];assert rows and any(r['contact_clock']=='frame-hold' for r in rows)
        assert all(r['source_contact_timing']['timing_sha256'] for r in rows)
        assert not (cycle/name/'contact-timing.json').exists()


def test_mirror_retains_clock_and_requires_patch_remapping(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch);glb=parent/'transfer/character.glb';rig=RigAsset.load(glb);out=parent.parent/'mirrored'
    recipe=dict(schema='strep-rig-mirror-v1',source_sha256=sha256(glb),frames=40,fps=30,root_node=0,
        counterparts={str(n):n for n in descendants(rig.parents,0)},plane_normal=[1,0,0],plane_point=[0,0,0],label='Mirror timing intent')
    mirror.prepare(dict(source_job=parent.name,variant='transfer',recipe=recipe),out);mirror.run(out);publish(out,'mirror_edit')
    rows=read(out/'transfer/contact-review.json')['authored_targets']
    assert [r['contact_clock'] for r in rows]==['authored-keys','frame-hold','authored-keys']
    assert all(r['requires_anatomical_remap'] for r in rows)
    assert not (out/'transfer/contact-spec.json').exists() and not (out/'transfer/contact-timing.json').exists()
    assert load(out/'input/character.glb')[1]['fit_options']['contact_clock_overrides']=={'1':'frame-hold','2':'authored-keys'}


@pytest.mark.parametrize('fault',['timing','draft','geometry','review','missing_binding'])
def test_changed_input_conditions_reject_before_export(tmp_path,monkeypatch,fault):
    parent,_,_=fixture(tmp_path,monkeypatch)
    if fault=='review':save(parent/'transfer/contact-review.json',dict(authored_targets=[],requires_review=True))
    out=parent.parent/'edit';clip.prepare(edit_payload(parent),out)
    if fault=='timing':p=out/'input/contact-timing.json';data=read(p);data['fit_options']['contact_clock']='frame-hold';save(p,data)
    if fault=='draft':p=out/'input/contact-spec.json';data=read(p);data['contacts'][1]['target_position_m'][0]+=.1;save(p,data)
    if fault=='geometry':p=out/'input/character.glb';p.write_bytes(p.read_bytes()+b'\0')
    if fault=='review':save(out/'input/contact-review.json',dict(authored_targets=[],requires_review=False))
    if fault=='missing_binding':p=out/'request.json';data=read(p);data.pop('contact_timing_inputs');save(p,data)
    with pytest.raises(ValueError,match='changed|missing'):clip.run(out)
    assert not (out/'transfer').exists()


def test_source_published_record_is_bound_and_cannot_assert_approval(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch);record=parent/'transfer/contact-timing.json';data=read(record);data['quality_approved']=True;save(record,data)
    with pytest.raises(ValueError,match='record changed'):author.metadata(parent.name,'transfer')
    result=read(parent/'result.json');result['variants']['transfer']['contact_timing_sha256']=sha256(record);save(parent/'result.json',result)
    with pytest.raises(ValueError,match='cannot establish approval'):author.metadata(parent.name,'transfer')


def test_deleted_published_record_cannot_silently_reset_clocks(tmp_path,monkeypatch):
    parent,_,_=fixture(tmp_path,monkeypatch)
    (parent/'transfer/contact-timing.json').unlink()
    with pytest.raises(ValueError,match='record changed'):author.metadata(parent.name,'transfer')
