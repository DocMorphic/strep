"""Full-frame recovery, complete topology/arrays and sealed capture inputs.

Capture fixtures are explicitly synthetic transport tests, not Godot runs.
"""
import copy
from pathlib import Path
import shutil
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_geometry_journal as journal
import native_scene_capture as capture
from native_scene_contacts import SceneContacts
from native_scene_engine import EngineObservations,sample_times
from native_engine_clock import clock_wire
from native_scene_geometry import evaluate
from native_observation_archive import verify
from strep import ROOT,read,save,sha256
from test_native_scene_geometry import closed_fixture,policy
from test_native_scene_engine import mock_actor


def fixture(tmp_path,monkeypatch,overlap=False):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    source,path,spec=closed_fixture(tmp_path);spec['contacts']=[]
    spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m']=[.2 if overlap else 5.,0.,0.]
    spec['objects']['far']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
        keyframes=[dict(time_s=0.,translation_m=[10.,0.,0.],rotation_xyzw=[0.,0.,0.,1.])])
    save(path,spec);pp=tmp_path/'policy.json';save(pp,policy(path,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.))))
    return source,path,pp,spec


def advance(folder,receipt,maximum_samples=1):
    return journal.advance(folder,receipt['checkpoint'],receipt['sha256'],maximum_samples=maximum_samples)


@pytest.mark.parametrize('overlap',[False,True])
def test_interrupted_prefix_recovers_without_recomputing_completed_frames_and_matches_whole(tmp_path,monkeypatch,overlap):
    source,path,pp,spec=fixture(tmp_path,monkeypatch,overlap);original=source.read_bytes()
    whole,arrays=evaluate(SceneContacts(spec,tmp_path),read(pp),sha256(path))
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    assert initial['completed_samples']==0 and not initial['sampled_conditions_pass']
    first=advance(folder,initial);saved=(folder/first['checkpoint']).read_bytes()
    real=journal.evaluate;calls=[]
    def interrupted(*args,**kwargs):
        calls.extend(kwargs['sample_indices'])
        if kwargs['sample_indices']==[2]:raise RuntimeError('Simulated interrupted geometry query')
        return real(*args,**kwargs)
    monkeypatch.setattr(journal,'evaluate',interrupted)
    with pytest.raises(RuntimeError,match='interrupted'):advance(folder,first,2)
    assert calls==[1,2]
    committed=read(folder/'progress.json');assert committed['completed_samples']==2
    assert (folder/first['checkpoint']).read_bytes()==saved
    assert list((folder/'frames').glob('000002-*'))
    monkeypatch.setattr(journal,'evaluate',real);calls=[]
    def observed(*args,**kwargs):calls.extend(kwargs['sample_indices']);return real(*args,**kwargs)
    monkeypatch.setattr(journal,'evaluate',observed)
    final=advance(folder,committed);assert calls==[2] and final['population_complete']
    assert not final['sampled_conditions_pass']
    assert len(list((folder/'frames').glob('000002-*')))==2
    result=journal.finalize(folder,final['checkpoint'],final['sha256'],tmp_path/'final')
    assert read(tmp_path/'final/geometry.json')==whole
    with np.load(tmp_path/'final/observations.npz',allow_pickle=False) as actual:
        assert set(actual.files)==set(arrays)
        for key,value in arrays.items():
            assert actual[key].dtype==value.dtype and actual[key].shape==value.shape and actual[key].tobytes()==value.tobytes()
    assert verify(tmp_path/'final/observations.npz')['all_values_exact']
    assert result['samples']==3 and result['sampled_conditions_pass'] is whole['sampled_conditions_pass']
    assert result['sampled_conditions_pass'] is (not overlap)
    assert not result['quality_approved'] and not result['release_approved'] and source.read_bytes()==original


@pytest.mark.parametrize('indices',[[],[True],[1.],[2,1],[1,1],[-1],[3],[[0]],['0'],np.array([2**64-1,1],dtype=np.uint64)])
def test_slice_requires_existing_sorted_integer_indices(tmp_path,monkeypatch,indices):
    _,path,pp,spec=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError):evaluate(SceneContacts(spec,tmp_path),read(pp),sha256(path),sample_indices=indices)


def test_slice_keeps_global_array_keys_and_never_claims_full_pass(tmp_path,monkeypatch):
    _,path,pp,spec=fixture(tmp_path,monkeypatch);scene=SceneContacts(spec,tmp_path)
    whole,arrays=evaluate(scene,read(pp),sha256(path));part,subset=evaluate(scene,read(pp),sha256(path),sample_indices=[1])
    assert part['status']=='partial' and part['checked_conditions_pass'] and not part['sampled_conditions_pass']
    assert part['samples']==whole['samples'][1:2] and part['sample_indices']==[1]
    assert any(k.startswith('frame_1_') for k in subset) and not any(k.startswith('frame_0_') for k in subset)
    for key in subset:
        np.testing.assert_array_equal(subset[key],arrays[key][[1]] if key=='times_s' else arrays[key])


def test_native_clock_and_all_phase_populations_survive_slicing(tmp_path,monkeypatch):
    from native_scene_geometry import policy_for
    _,path,pp,spec=fixture(tmp_path,monkeypatch);scene=SceneContacts(spec,tmp_path);value=read(pp);value['clock']['mode']='native-and-frame-populations'
    times,populations,_=policy_for(value,scene,sha256(path))
    part,arrays=evaluate(scene,value,sha256(path),sample_indices=[0,len(times)-1])
    assert len(times)>100 and len(populations)==12
    assert part['complete_clock_s']==times.tolist() and part['times_s']==[0.,2.]
    assert [p['id'] for p in part['frame_populations']]==[p['id'] for p in populations]
    assert part['sample_indices']==[0,len(times)-1] and not part['sampled_conditions_pass']
    np.testing.assert_array_equal(arrays['times_s'],times[[0,-1]])


@pytest.mark.parametrize('fault',['checkpoint-digest','request','input','snapshot','method-archive','frame-json','frame-array','frame-receipt','passing-checkpoint','gap'])
def test_mutated_or_incomplete_evidence_cannot_resume(tmp_path,monkeypatch,fault):
    source,path,pp,spec=fixture(tmp_path,monkeypatch);folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder);receipt=advance(folder,initial)
    cp=read(folder/receipt['checkpoint']);directory=folder/cp['frame']['directory']
    if fault=='checkpoint-digest':receipt['sha256']='0'*64
    if fault=='request':save(folder/'request.json',{**read(folder/'request.json'),'runtime':{}})
    if fault=='input':source.write_bytes(source.read_bytes()+b'x')
    if fault=='snapshot':next((folder/'input').iterdir()).write_bytes(b'changed')
    if fault=='method-archive':next((folder/'implementation').iterdir()).write_bytes(b'changed')
    if fault=='frame-json':save(directory/'geometry.json',{})
    if fault=='frame-array':(directory/'observations.npz').write_bytes(b'changed')
    if fault=='frame-receipt':save(directory/'receipt.json',{})
    if fault=='passing-checkpoint':
        cp['sampled_conditions_pass']=True;save(folder/receipt['checkpoint'],cp);receipt['sha256']=sha256(folder/receipt['checkpoint'])
    if fault=='gap':
        cp['next_sample']=2;save(folder/receipt['checkpoint'],cp);receipt['sha256']=sha256(folder/receipt['checkpoint'])
    with pytest.raises(ValueError):advance(folder,receipt)


def test_partial_prefix_cannot_finalize_and_changed_source_during_query_does_not_publish(tmp_path,monkeypatch):
    source,path,pp,spec=fixture(tmp_path,monkeypatch);folder=tmp_path/'journal';receipt=journal.prepare(path,pp,folder)
    with pytest.raises(ValueError,match='Full original'):journal.finalize(folder,receipt['checkpoint'],receipt['sha256'],tmp_path/'final')
    assert not (tmp_path/'final').exists()
    real=journal.evaluate
    def changed(*args,**kwargs):
        result=real(*args,**kwargs);source.write_bytes(source.read_bytes()+b'x');return result
    monkeypatch.setattr(journal,'evaluate',changed)
    with pytest.raises(ValueError,match='Source changed'):advance(folder,receipt)
    assert read(folder/'progress.json')==receipt


def synthetic_capture(tmp_path,path,pp,spec):
    # No actual engine executable is run in these model-free tests.
    scene=SceneContacts(spec,tmp_path);_,arrays=scene.evaluate();times=sample_times(scene,arrays,read(pp),sha256(path))
    folder=tmp_path/'synthetic-capture';folder.mkdir();(folder/'project').mkdir();(folder/'implementation').mkdir()
    engine=tmp_path/'fixture.exe';engine.write_bytes(b'Synthetic transport fixture, not a Godot binary')
    methods={};scripts={}
    for n in ('godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd','native_engine_clock.gd'):
        methods[n]=sha256(ROOT/'scripts'/n);scripts[n]=methods[n]
        shutil.copyfile(ROOT/'scripts'/n,folder/'implementation'/n);shutil.copyfile(ROOT/'scripts'/n,folder/'project'/('audit.gd' if n=='godot_native_scene_audit.gd' else n))
    cases=[];actual=[]
    for name,actor in scene.actors.items():
        resource=folder/(name+'-animation.res');resource.write_bytes(b'Synthetic resource hash fixture')
        source=(path.parent/spec['actors'][name]['glb']).resolve()
        cases.append(dict(id=name,path=str(source),animation_index=0,animation_output=str(resource)))
        observed=mock_actor(actor['rig'],actor['sampler'],times,path=str(source));observed['id']=name;actual.append(observed)
    inputs={str(path):sha256(path),str(pp):sha256(pp),**scene.inputs,str(engine):sha256(engine)}
    request=dict(cases=cases,objects=spec['objects'],sample_times_s=times.tolist(),sample_clock=clock_wire(times),
        inputs_sha256=inputs,implementation_sha256=methods,playback_mode='native-authoring',import_bake_fps=30.,engine_sha256=sha256(engine))
    # Test captured actor geometry only; object fixtures use the native path.
    save(folder/'request.json',request);save(folder/'engine-output.json',dict(engine='Synthetic fixture',import_bake_fps=30.,cases=actual,objects=[]));(folder/'engine.log').write_text('Synthetic fixture',encoding='utf-8')
    receipt=dict(returncode=0,engine_executable_sha256=sha256(engine),request_sha256=sha256(folder/'request.json'),
        engine_output_sha256=sha256(folder/'engine-output.json'),engine_log_sha256=sha256(folder/'engine.log'),
        executed_scripts_sha256=scripts,animation_resources_sha256={c['id']:sha256(c['animation_output']) for c in cases})
    save(folder/'raw-engine-receipt.json',receipt)
    return folder,sha256(folder/'raw-engine-receipt.json')


def test_sealed_capture_cpu_geometry_journal_matches_original_observer(tmp_path,monkeypatch):
    _,path,pp,spec=fixture(tmp_path,monkeypatch,True);spec['objects']={};save(path,spec);save(pp,policy(path))
    captured,pin=synthetic_capture(tmp_path,path,pp,spec);scene=SceneContacts(spec,tmp_path)
    observed=capture.load(scene,path,pp,captured,pin)
    expected,arrays=evaluate(scene,read(pp),sha256(path),actor_vertices=observed.actor_vertices,object_poses=observed.object_poses)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder,engine_capture=captured,capture_receipt_sha256=pin)
    done=advance(folder,initial,3);result=journal.finalize(folder,done['checkpoint'],done['sha256'],tmp_path/'final')
    assert result['measurement_source']=='Sealed actual engine capture CPU skin' # Method label; fixture remains synthetic.
    assert read(tmp_path/'final/geometry.json')==expected and not result['sampled_conditions_pass']
    with np.load(tmp_path/'final/observations.npz',allow_pickle=False) as actual:
        for key,value in arrays.items():np.testing.assert_array_equal(actual[key],value)


@pytest.mark.parametrize('fault',['receipt','output','log','resource','script','clock','population'])
def test_capture_mismatch_cannot_be_used_as_observer(tmp_path,monkeypatch,fault):
    _,path,pp,spec=fixture(tmp_path,monkeypatch);spec['objects']={};save(path,spec);save(pp,policy(path));scene=SceneContacts(spec,tmp_path)
    folder,pin=synthetic_capture(tmp_path,path,pp,spec)
    if fault=='receipt':pin='0'*64
    if fault=='output':(folder/'engine-output.json').write_bytes(b'changed')
    if fault=='log':(folder/'engine.log').write_bytes(b'changed')
    if fault=='resource':(folder/'A-animation.res').write_bytes(b'changed')
    if fault=='script':(folder/'project/audit.gd').write_bytes(b'changed')
    if fault in ('clock','population'):
        request=read(folder/'request.json')
        if fault=='clock':request['sample_times_s'][1]+=.01
        else:request['cases'].pop()
        save(folder/'request.json',request);receipt=read(folder/'raw-engine-receipt.json');receipt['request_sha256']=sha256(folder/'request.json');save(folder/'raw-engine-receipt.json',receipt);pin=sha256(folder/'raw-engine-receipt.json')
    with pytest.raises(ValueError):capture.load(scene,path,pp,folder,pin)
