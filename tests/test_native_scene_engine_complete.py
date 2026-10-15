"""Journal-to-engine replay bridge; synthetic captures never run Godot."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from native_scene_contacts import SceneContacts
from native_godot_payload import payload
import native_geometry_journal as journal
import native_scene_engine_complete as completion
import verify_native_scene_engine as ordinary
import verify_native_actor_scene_engine as actor_replay
from test_native_geometry_journal import fixture,synthetic_capture
from test_native_scene_engine import serialized


def study(tmp_path,monkeypatch,*,overlap=False,objects=False,payload_fault=False):
    source,path,pp,spec=fixture(tmp_path,monkeypatch,overlap)
    if not objects:spec['objects']={}
    else:
        spec['objects']['far']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.2,.3,.4]),
            keyframes=[dict(time_s=t,translation_m=p,rotation_xyzw=Rotation.from_euler('y',angle,degrees=True).as_quat().tolist())
                for t,p,angle in [(0.,[10.,0.,0.],0.),(2.,[10.5,.2,.1],60.)]])
    save(path,spec)
    # One actual contact time lies outside the explicit geometry clock.
    scene=SceneContacts(spec,tmp_path);time=.853725
    vertex=scene.actor_points('A',np.array([0]),np.array([time]))[0,0]
    spec['contacts']=[dict(id='touch',actor='A',vertices=[[6,0,0]],reduction='individual',
        target=dict(space='world',points_m=[vertex.tolist()]),mode='touch',interval_s=[time,time],limits=dict(position_m=.001))]
    save(path,spec);policy=read(pp);policy['contacts_sha256']=sha256(path);save(pp,policy)
    capture,pin=synthetic_capture(tmp_path,path,pp,spec);scene=SceneContacts(spec,tmp_path)
    executed=read(capture/'request.json');actual=read(capture/'engine-output.json')
    for case in executed['cases']:
        actor=scene.actors[case['id']];case['native_payload']={} if payload_fault else payload(actor['rig'],actor['sampler'],spec['actors'][case['id']]['sha256'])
    for name in scene.objects:
        frames=[]
        for i,t in enumerate(executed['sample_times_s']):
            # Independent analytic linear translation / fixed-axis rotation;
            # do not generate the observed object poses through the sampler
            # which the producer and verifier are meant to check.
            r=Rotation.from_euler('y',30.*t,degrees=True);p=np.array([10.,0.,0.])+t*np.array([.25,.1,.05])
            m=np.eye(4);m[:3,:3]=r.as_matrix();m[:3,3]=p
            frames.append(dict(requested_time_s=t,matrix=serialized(m),rotation_xyzw=r.as_quat().tolist()))
        actual['objects'].append(dict(id=name,frames=frames))
    save(capture/'request.json',executed);save(capture/'engine-output.json',actual)
    receipt=read(capture/'raw-engine-receipt.json');receipt.update(request_sha256=sha256(capture/'request.json'),engine_output_sha256=sha256(capture/'engine-output.json'));save(capture/'raw-engine-receipt.json',receipt)
    pin=sha256(capture/'raw-engine-receipt.json');folder=tmp_path/'journal'
    initial=journal.prepare(path,pp,folder,engine_capture=capture,capture_receipt_sha256=pin)
    ready=journal.advance(folder,initial['checkpoint'],initial['sha256'],maximum_samples=3)
    final=tmp_path/'journal-final';journal.finalize(folder,ready['checkpoint'],ready['sha256'],final)
    return source,path,pp,spec,capture,folder,final


@pytest.mark.parametrize('overlap,objects',[(False,False),(True,False),(False,True)])
def test_completed_journal_feeds_existing_full_skin_contact_and_geometry_replay(tmp_path,monkeypatch,overlap,objects):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch,overlap=overlap,objects=objects)
    before={p:sha256(p) for p in (source,capture/'request.json',capture/'engine-output.json',capture/'raw-engine-receipt.json')}
    out=tmp_path/'complete';result=completion.run(folder,final/'result.json',sha256(final/'result.json'),out)
    assert result['schema']==completion.SCHEMA and result['samples']==4 # geometry3 plus the exact touch time
    assert result['all_sampled_conditions_pass'] is (not overlap)
    assert result['imported_contact_samples_pass'] and result['imported_skin_position_samples_pass']
    assert result['engine_executed_in_completion'] is False and not result['release_approved']
    assert (out/'request.json').read_bytes()==(capture/'request.json').read_bytes()
    assert (out/'raw-engine-receipt.json').read_bytes()==(capture/'raw-engine-receipt.json').read_bytes()
    assert read(out/'request.json')['implementation_sha256']!=result['implementation_sha256']
    replay=ordinary.run(path,pp,out,tmp_path/'replay')
    assert replay['all_replayed_observations_exact'] and replay['recorded_sampled_conditions_pass'] is result['all_sampled_conditions_pass']
    if not objects:
        a=actor_replay.run(path,pp,out,tmp_path/'actor-replay')
        assert a['all_replayed_observations_exact'] and a['recorded_sampled_conditions_pass'] is result['all_sampled_conditions_pass']
    else:
        with pytest.raises(ValueError,match='Actor-only'):actor_replay.load(path,pp,out)
    # Existing original-reference and explicit game-track consumers use the
    # completed producer without another import. Geometry rejection stays separate.
    from audit_conditioned_skin_fidelity import run as fidelity
    references={name:dict(path=str(source),sha256=sha256(source)) for name in spec['actors']}
    original=fidelity(path,pp,out,references,tmp_path/'fidelity')
    assert original['all_original_reference_fidelity_pass'] and original['additional_engine_executions']==0
    loaded,_,observed,times,_=ordinary.load(path,pp,out)
    if objects:
        assert observed.object_report['far']['samples']==4
        positions,rotations=observed.object_poses('far',times)
        np.testing.assert_allclose(positions,np.array([10.,0.,0.])+times[:,None]*np.array([.25,.1,.05]),atol=1e-14)
        assert not np.array_equal(rotations[0],rotations[-1])
    from native_scene_game_tracks import export
    binding=copy.deepcopy(spec)
    for entry in binding['actors'].values():entry['glb']=str(source)
    roots=dict(schema='strep-native-scene-game-tracks-v1',actors={name:dict(root_node=a['rig'].joints[0]) for name,a in loaded.actors.items()},
        markers=[dict(id='test-start',name='test-start',actor='A',time_s=0.,confirmed=True)])
    tracks=export(loaded,roots,times,observed.worlds,result['imported_contacts'],tmp_path/'tracks',source_spec=binding,
        portable_scene_sha256=sha256(path),contact_report_sha256=sha256(out/'result.json'))
    assert tracks['all_root_samples_pass'] and tracks['samples']==4 and not tracks['release_approved']
    events=read(tmp_path/'tracks/events.json')['events']
    assert all(not row['runtime_dispatch_allowed'] for row in events if row['kind']=='contact_intent')
    assert read(out/'result.json')['all_sampled_conditions_pass'] is (not overlap)
    assert all(sha256(p)==h for p,h in before.items())


def test_even_rebound_capture_payload_must_match_complete_original_native_tracks(tmp_path,monkeypatch):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch,payload_fault=True)
    with pytest.raises(ValueError,match='source-derived native payload'):
        completion.run(folder,final/'result.json',sha256(final/'result.json'),tmp_path/'complete')


def test_archive_write_failure_is_recorded_without_publishing_a_completed_result(tmp_path,monkeypatch):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch)
    def failed(*args,**kwargs):raise OSError('Simulated archive write failure')
    monkeypatch.setattr(completion.np,'savez_compressed',failed)
    with pytest.raises(OSError,match='archive write'):
        completion.run(folder,final/'result.json',sha256(final/'result.json'),tmp_path/'complete')
    assert read(tmp_path/'complete/pipeline.json')['status']=='failed'
    assert not (tmp_path/'complete/result.json').exists()
    assert (tmp_path/'complete/raw-engine-receipt.json').read_bytes()==(capture/'raw-engine-receipt.json').read_bytes()


@pytest.mark.parametrize('fault',['pin','native-observer','sample','array-clock','captured-resource','payload'])
def test_bad_full_assembly_or_capture_cannot_be_completed(tmp_path,monkeypatch,fault):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch)
    result=read(final/'result.json');pin=sha256(final/'result.json')
    if fault=='pin':pin='0'*64
    if fault=='native-observer':
        result['measurement_source']='Native source skin';save(final/'result.json',result);pin=sha256(final/'result.json')
    if fault=='sample':
        value=read(final/'geometry.json');value['samples'][0]['world_planes'][0]['maximum_depth_m']=.1;save(final/'geometry.json',value)
        result['geometry_sha256']=sha256(final/'geometry.json');save(final/'result.json',result);pin=sha256(final/'result.json')
    if fault=='array-clock':
        (final/'observations.npz').write_bytes(b'changed')
    if fault=='captured-resource':(capture/'A-animation.res').write_bytes(b'changed')
    if fault=='payload':
        # Raw request/receipt cannot be silently rebound through a pinned journal.
        value=read(capture/'request.json');value['cases'][0]['native_payload']={};save(capture/'request.json',value)
    with pytest.raises(ValueError):completion.run(folder,final/'result.json',pin,tmp_path/'complete')
    assert not (tmp_path/'complete/result.json').exists()


def test_partial_checkpoint_cannot_be_presented_as_complete_engine_audit(tmp_path,monkeypatch):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch)
    zero=next(p for p in (folder/'checkpoints').iterdir() if read(p)['next_sample']==0)
    forged=read(final/'result.json');forged.update(source_checkpoint=zero.relative_to(folder).as_posix(),source_checkpoint_sha256=sha256(zero),samples=0)
    save(final/'result.json',forged)
    with pytest.raises(ValueError,match='Complete original geometry'):completion.run(folder,final/'result.json',sha256(final/'result.json'),tmp_path/'complete')


@pytest.mark.parametrize('fault',['request','raw-receipt','resource','skin-arrays','geometry','method'])
def test_completed_producer_tampering_cannot_enter_ordinary_replay(tmp_path,monkeypatch,fault):
    source,path,pp,spec,capture,folder,final=study(tmp_path,monkeypatch)
    out=tmp_path/'complete';completion.run(folder,final/'result.json',sha256(final/'result.json'),out)
    target={'request':'request.json','raw-receipt':'raw-engine-receipt.json','resource':'A-animation.res',
        'skin-arrays':'native-observations.npz','geometry':'geometry.json','method':'implementation/native_scene_engine_complete.py'}[fault]
    (out/target).write_bytes(b'changed')
    with pytest.raises((ValueError,KeyError)):ordinary.load(path,pp,out)
