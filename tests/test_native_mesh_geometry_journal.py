"""Interrupted imported-mesh geometry retains exact complete-frame evidence."""
import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_mesh_geometry_journal as journal
from native_mesh_prop_scene import MeshPropScene
from native_observation_archive import verify
from strep import read,save,sha256
from test_native_mesh_prop_scene import fixture as source_fixture,contact


def fixture(tmp_path,monkeypatch,overlap=False):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    path,spec,policy,_,grip=source_fixture(tmp_path)
    actor_path=tmp_path/'contacts.json';actors=read(actor_path)
    actors['actors']['B']=copy.deepcopy(actors['actors']['A'])
    actors['actors']['B']['placement']['translation_m']=[5.,0.,0.]
    actors['objects']['ball']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
        keyframes=[dict(time_s=0.,translation_m=[10.,1.,0.],rotation_xyzw=[0.,0.,0.,1.])])
    save(actor_path,actors);spec['actor_scene_sha256']=sha256(actor_path)
    spec['props']['other']=copy.deepcopy(spec['props']['crate'])
    spec['props']['other']['keyframes'][0]['translation_m']=[7.,1.,0.]
    if overlap:spec['props']['crate']['keyframes'][0]['translation_m']=[0.,.2,0.]
    else:
        spec['props']['crate']['keyframes'].append(dict(time_s=2.,translation_m=[3.3,1.,0.],rotation_xyzw=[0.,0.,0.,1.]))
    save(path,spec);policy['mesh_scene_sha256']=sha256(path)
    pp=tmp_path/'policy.json';save(pp,policy)
    return path,pp,spec,policy,grip


def advance(folder,receipt,count=1):
    return journal.advance(folder,receipt['checkpoint'],receipt['sha256'],maximum_samples=count)


def equal_arrays(path,expected):
    with np.load(path,allow_pickle=False) as saved:
        assert set(saved.files)==set(expected)
        for name,value in expected.items():
            assert saved[name].dtype==value.dtype and saved[name].shape==value.shape
            assert saved[name].tobytes()==value.tobytes(),name


@pytest.mark.parametrize('overlap',[False,True])
def test_recovery_reuses_completed_frames_and_retains_all_pair_failures(tmp_path,monkeypatch,overlap):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch,overlap)
    scene=MeshPropScene(path);before={name:sha256(name) for name in scene.inputs}
    expected,arrays=scene.geometry(policy)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    first=advance(folder,initial);pin=(folder/first['checkpoint']).read_bytes()
    real=MeshPropScene.geometry;calls=[]
    def interrupted(self,*args,**kwargs):
        calls.extend(kwargs['sample_indices'])
        if kwargs['sample_indices']==[2]:raise RuntimeError('Simulated interrupted mesh frame')
        return real(self,*args,**kwargs)
    monkeypatch.setattr(MeshPropScene,'geometry',interrupted)
    with pytest.raises(RuntimeError,match='interrupted'):advance(folder,first,2)
    assert calls==[1,2]
    committed=read(folder/'progress.json');assert committed['completed_samples']==2
    assert (folder/first['checkpoint']).read_bytes()==pin and not committed['sampled_conditions_pass']
    assert len(list((folder/'frames').glob('000002-*')))==1
    calls=[]
    def measured(self,*args,**kwargs):calls.extend(kwargs['sample_indices']);return real(self,*args,**kwargs)
    monkeypatch.setattr(MeshPropScene,'geometry',measured)
    final=advance(folder,committed)
    assert calls==[2] and final['population_complete'] and not final['sampled_conditions_pass']
    assert len(list((folder/'frames').glob('000002-*')))==2
    result=journal.finalize(folder,final['checkpoint'],final['sha256'],tmp_path/'final')
    assert read(tmp_path/'final/geometry.json')==expected
    equal_arrays(tmp_path/'final/observations.npz',arrays)
    assert verify(tmp_path/'final/observations.npz')['all_values_exact']
    assert result['samples']==3 and result['sampled_conditions_pass'] is (not overlap)
    assert not result['quality_approved'] and not result['release_approved']
    assert all(sha256(name)==digest for name,digest in before.items())
    for row in expected['samples']:
        assert len(row['mesh_pairs'])==5 and len(row['mesh_primitive_pairs'])==2 and len(row['mesh_world_planes'])==2
        assert len(row['base_scene']['actor_pairs'])==1 and len(row['base_scene']['actor_objects'])==2


@pytest.mark.parametrize('batch',[1,4,32])
def test_pinned_query_batch_matches_direct_complete_mesh_audit(tmp_path,monkeypatch,batch):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch,True)
    expected,arrays=MeshPropScene(path).geometry(policy,query_batch_size=batch)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder,query_batch_size=batch)
    real=MeshPropScene.geometry;seen=[]
    def measured(self,*args,**kwargs):seen.append(kwargs['query_batch_size']);return real(self,*args,**kwargs)
    monkeypatch.setattr(MeshPropScene,'geometry',measured)
    final=advance(folder,initial,3)
    assert seen==[batch]*3
    result=journal.finalize(folder,final['checkpoint'],final['sha256'],tmp_path/'final')
    assert result['query_batch_size']==batch and read(tmp_path/'final/geometry.json')==expected
    equal_arrays(tmp_path/'final/observations.npz',arrays)


@pytest.mark.parametrize('batch',[0,33,True,1.])
def test_bad_batch_rejects_before_loading_sources(tmp_path,monkeypatch,batch):
    monkeypatch.setattr(journal,'MeshPropScene',lambda *a:pytest.fail('Invalid batch loaded a scene'))
    with pytest.raises(ValueError,match='Mesh query batch'):
        journal.prepare(tmp_path/'missing',tmp_path/'missing-policy',tmp_path/'journal',query_batch_size=batch)
    assert not (tmp_path/'journal').exists()


@pytest.mark.parametrize('fault',['pin','request','source','snapshot','method','frame-json','frame-array','frame-receipt','passing-prefix','gap'])
def test_changed_or_incomplete_evidence_cannot_resume(tmp_path,monkeypatch,fault):
    path,pp,_,_,_=fixture(tmp_path,monkeypatch)
    folder=tmp_path/'journal';receipt=advance(folder,journal.prepare(path,pp,folder))
    checkpoint=read(folder/receipt['checkpoint']);directory=folder/checkpoint['frame']['directory']
    if fault=='pin':receipt['sha256']='0'*64
    elif fault=='request':save(folder/'request.json',{**read(folder/'request.json'),'query_batch_size':2})
    elif fault=='source':(tmp_path/'prop.glb').write_bytes(b'changed')
    elif fault=='snapshot':next((folder/'input').iterdir()).write_bytes(b'changed')
    elif fault=='method':next((folder/'implementation').iterdir()).write_bytes(b'changed')
    elif fault=='frame-json':save(directory/'geometry.json',{})
    elif fault=='frame-array':(directory/'observations.npz').write_bytes(b'changed')
    elif fault=='frame-receipt':save(directory/'receipt.json',{})
    else:
        if fault=='passing-prefix':checkpoint['sampled_conditions_pass']=True
        else:checkpoint['next_sample']=2
        save(folder/receipt['checkpoint'],checkpoint);receipt['sha256']=sha256(folder/receipt['checkpoint'])
    monkeypatch.setattr(MeshPropScene,'geometry',lambda *a,**k:pytest.fail('Invalid evidence evaluated another frame'))
    with pytest.raises(ValueError):advance(folder,receipt)


def test_partial_prefix_cannot_finalize_or_publish_after_source_change(tmp_path,monkeypatch):
    path,pp,_,_,_=fixture(tmp_path,monkeypatch)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    with pytest.raises(ValueError,match='Full original mesh'):journal.finalize(folder,initial['checkpoint'],initial['sha256'],tmp_path/'final')
    assert not (tmp_path/'final').exists()
    real=MeshPropScene.geometry
    def changed(self,*args,**kwargs):
        result=real(self,*args,**kwargs)
        source=tmp_path/'prop.glb';source.write_bytes(source.read_bytes()+b'x')
        return result
    monkeypatch.setattr(MeshPropScene,'geometry',changed)
    with pytest.raises(ValueError,match='source changed'):advance(folder,initial)
    assert read(folder/'progress.json')==initial


def test_native_frame_clock_keeps_prop_keys_and_contact_boundaries(tmp_path,monkeypatch):
    path,pp,spec,policy,grip=fixture(tmp_path,monkeypatch)
    spec['props']['crate']['keyframes'].insert(1,dict(time_s=.456789,translation_m=[3.1,1.,0.],rotation_xyzw=[0.,0.,0.,1.]))
    row=contact(grip);row['interval_s']=[.777777777,.777777777];spec['mesh_contacts']=[row]
    save(path,spec);policy['mesh_scene_sha256']=sha256(path);policy['clock']['mode']='native-and-frame-populations';save(pp,policy)
    expected=MeshPropScene(path)._clock(policy)[0].tolist()
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    request=read(folder/'request.json')
    assert request['times_s']==expected and .456789 in expected and .777777777 in expected and len(expected)>900
    first=advance(folder,initial)
    with pytest.raises(ValueError,match='Full original mesh'):journal.finalize(folder,first['checkpoint'],first['sha256'],tmp_path/'final')
    assert not first['population_complete'] and not first['sampled_conditions_pass']


def test_single_sample_policy_cannot_drop_required_clip_endpoints(tmp_path,monkeypatch):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch)
    policy['clock']['times_s']=[1.];save(pp,policy)
    folder=tmp_path/'journal'
    with pytest.raises(ValueError,match='both clip endpoints'):
        journal.prepare(path,pp,folder)
    assert not folder.exists()


def test_indexed_finalization_reuses_arrays_and_nests_under_the_current_worker(tmp_path,monkeypatch):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch)
    expected,arrays=MeshPropScene(path).geometry(policy)
    folder=tmp_path/'journal'
    with action_worker_lock.worker_lock():
        final=advance(folder,journal.prepare(path,pp,folder),3)
        result=journal.finalize(folder,final['checkpoint'],final['sha256'],tmp_path/'final',materialize_observations=False)
        assert result['observations_format']=='frame-index'
        index=tmp_path/'final/observations-index.json'
        actual=dict(journal.iter_observations(index,result['observation_index_sha256']))
    assert not (tmp_path/'final/observations.npz').exists()
    assert len(list(folder.rglob('observations.npz')))==3
    assert read(tmp_path/'final/geometry.json')==expected and set(actual)==set(arrays)
    for name,value in arrays.items():
        assert actual[name].dtype==value.dtype and actual[name].shape==value.shape
        assert actual[name].tobytes()==value.tobytes()


@pytest.mark.parametrize('fault',['pin','missing-frame','clock','approval','frame-content'])
def test_index_cannot_hide_missing_or_changed_observations(tmp_path,monkeypatch,fault):
    path,pp,_,_,_=fixture(tmp_path,monkeypatch)
    folder=tmp_path/'journal';final=advance(folder,journal.prepare(path,pp,folder),3)
    result=journal.finalize(folder,final['checkpoint'],final['sha256'],tmp_path/'final',materialize_observations=False)
    index=tmp_path/'final/observations-index.json';value=read(index);pin=result['observation_index_sha256']
    if fault=='pin':pin='0'*64
    elif fault=='frame-content':(folder/value['frames'][0]['directory']/'observations.npz').write_bytes(b'changed')
    else:
        if fault=='missing-frame':value['frames'].pop()
        elif fault=='clock':value['times_s'][1]+=.01
        else:value['quality_approved']=True
        save(index,value);pin=sha256(index)
    with pytest.raises(ValueError):dict(journal.iter_observations(index,pin))


@pytest.mark.parametrize('count',[0,1,3])
@pytest.mark.parametrize('overlap',[False,True])
def test_verify_replays_saved_prefix_without_queries_or_approving_geometry(tmp_path,monkeypatch,count,overlap):
    path,pp,_,_,_=fixture(tmp_path,monkeypatch,overlap)
    folder=tmp_path/'journal';receipt=journal.prepare(path,pp,folder)
    if count:receipt=advance(folder,receipt,count)
    monkeypatch.setattr(MeshPropScene,'geometry',lambda *a,**k:pytest.fail('Verification re-evaluated geometry'))
    before={str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file()}
    result=journal.verify(folder,receipt['checkpoint'],receipt['sha256'])
    assert result['status']=='verified' and result['completed_samples']==count and result['total_samples']==3
    assert result['population_complete'] is (count==3)
    assert result['checked_prefix_pass'] is (not overlap or count==0)
    assert not result['sampled_conditions_pass'] and not result['quality_approved'] and not result['release_approved']
    assert {str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file()}==before


def test_request_changed_during_query_cannot_rebind_completed_frame(tmp_path,monkeypatch):
    path,pp,_,_,_=fixture(tmp_path,monkeypatch)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    real=MeshPropScene.geometry
    def changed(self,*args,**kwargs):
        result=real(self,*args,**kwargs)
        request=read(folder/'request.json');request['query_batch_size']=2;save(folder/'request.json',request)
        return result
    monkeypatch.setattr(MeshPropScene,'geometry',changed)
    with pytest.raises(ValueError,match='Pinned journal request changed'):advance(folder,initial)
    assert read(folder/'progress.json')==initial
    assert not list((folder/'frames').glob('*/receipt.json'))


def test_cli_prepares_advances_verifies_and_finalizes_exact_indexed_population(tmp_path,monkeypatch,capsys):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch)
    expected,arrays=MeshPropScene(path).geometry(policy)
    folder=tmp_path/'journal'
    assert journal.main(['prepare',str(path),str(pp),str(folder)])==0
    initial=json.loads(capsys.readouterr().out)
    assert journal.main(['advance',str(folder),initial['checkpoint'],initial['sha256'],'--maximum-samples','3'])==0
    done=json.loads(capsys.readouterr().out)
    assert journal.main(['verify',str(folder),done['checkpoint'],done['sha256']])==0
    verified=json.loads(capsys.readouterr().out)
    assert verified['population_complete'] and not verified['sampled_conditions_pass']
    assert journal.main(['finalize',str(folder),done['checkpoint'],done['sha256'],str(tmp_path/'final'),
        '--indexed-observations'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='complete' and result['observations_format']=='frame-index'
    assert read(tmp_path/'final/geometry.json')==expected
    actual=dict(journal.iter_observations(tmp_path/'final/observations-index.json',result['observation_index_sha256']))
    assert set(actual)==set(arrays)
    for name,value in arrays.items():assert actual[name].tobytes()==value.tobytes()


def test_hard_exit_preserves_committed_frames_for_fresh_process_resume(tmp_path,monkeypatch):
    path,pp,_,policy,_=fixture(tmp_path,monkeypatch)
    expected,arrays=MeshPropScene(path).geometry(policy)
    folder=tmp_path/'journal';initial=journal.prepare(path,pp,folder)
    scripts=str(Path(journal.__file__).parent)
    setup=(f'import sys,os;from pathlib import Path;sys.path.insert(0,{scripts!r});'
        f'import action_worker_lock;action_worker_lock.ROOT=Path({str(tmp_path/"locks")!r});'
        'import native_mesh_geometry_journal as journal\n')
    child=setup+'''real=journal.MeshPropScene.geometry
def interrupted(self,*args,**kwargs):
    if kwargs['sample_indices']==[2]:os._exit(23)
    return real(self,*args,**kwargs)
journal.MeshPropScene.geometry=interrupted
'''+f'journal.advance({str(folder)!r},{initial["checkpoint"]!r},{initial["sha256"]!r},maximum_samples=3)\n'
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    result=subprocess.run([sys.executable,'-c',child],capture_output=True,text=True,env=env,timeout=60)
    assert result.returncode==23,result.stdout+result.stderr
    committed=read(folder/'progress.json')
    assert committed['completed_samples']==2 and not committed['population_complete']
    pinned={str(p.relative_to(folder)):sha256(p) for p in (folder/'checkpoints').iterdir()}
    abandoned=list((folder/'frames').glob('000002-*'))
    assert len(abandoned)==1 and not (abandoned[0]/'receipt.json').exists()
    # A genuinely new interpreter must acquire the OS-released lock and visit
    # only the remaining original frame, without recomputing the saved prefix.
    resume=setup+'''real=journal.MeshPropScene.geometry
def remaining(self,*args,**kwargs):
    assert kwargs['sample_indices']==[2]
    return real(self,*args,**kwargs)
journal.MeshPropScene.geometry=remaining
'''+f'journal.main({["advance",str(folder),committed["checkpoint"],committed["sha256"],"--maximum-samples","3"]!r})\n'
    result=subprocess.run([sys.executable,'-c',resume],capture_output=True,text=True,env=env,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    done=json.loads(result.stdout)
    assert done['population_complete'] and done['completed_samples']==3 and not done['sampled_conditions_pass']
    assert all(sha256(folder/name)==digest for name,digest in pinned.items())
    assert abandoned[0].exists() and len(list((folder/'frames').glob('000002-*')))==2
    finalize=setup+'''def no_queries(*args,**kwargs):raise AssertionError('Finalization queried geometry again')
journal.MeshPropScene.geometry=no_queries
'''+f'journal.main({["finalize",str(folder),done["checkpoint"],done["sha256"],str(tmp_path/"final")]!r})\n'
    result=subprocess.run([sys.executable,'-c',finalize],capture_output=True,text=True,env=env,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['status']=='complete'
    assert read(tmp_path/'final/geometry.json')==expected
    equal_arrays(tmp_path/'final/observations.npz',arrays)


def test_rotating_props_and_placed_actors_match_full_clock_arithmetic(tmp_path,monkeypatch):
    from scipy.spatial.transform import Rotation
    path,pp,spec,policy,_=fixture(tmp_path,monkeypatch)
    actors_path=tmp_path/'contacts.json';actors=read(actors_path)
    actors['actors']['A']['placement']['rotation_xyzw']=Rotation.from_euler('xyz',[.1,.2,.3]).as_quat().tolist()
    save(actors_path,actors);spec['actor_scene_sha256']=sha256(actors_path)
    spec['props']['crate']['keyframes']=[
        dict(time_s=t,translation_m=p,rotation_xyzw=Rotation.from_euler('xyz',r).as_quat().tolist())
        for t,p,r in [(0.,[3.,1.,0.],[.2,-.1,.4]),(.7,[3.1,1.1,.2],[.5,.6,-.2]),(2.,[3.3,1.2,.4],[.3,-.8,.9])]]
    save(path,spec);policy['mesh_scene_sha256']=sha256(path)
    policy['clock']['times_s']=[0.,.37,.7,1.41,2.];save(pp,policy)
    expected,arrays=MeshPropScene(path).geometry(policy)
    folder=tmp_path/'journal';receipt=journal.prepare(path,pp,folder)
    receipt=advance(folder,receipt,2);receipt=advance(folder,receipt,3)
    journal.finalize(folder,receipt['checkpoint'],receipt['sha256'],tmp_path/'final')
    assert read(tmp_path/'final/geometry.json')==expected
    equal_arrays(tmp_path/'final/observations.npz',arrays)
