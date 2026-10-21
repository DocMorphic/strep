"""Optimizer interruption cannot change bounds, skip checks or commit twice."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_mesh_character_recovery as recovery
import native_mesh_character_fit as fitting
from strep import read,save,sha256
from test_native_mesh_character_fit import prepared


def fixture(tmp_path,monkeypatch,obstacle=False):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    path,permissions,policy=prepared(tmp_path)
    if obstacle:
        spec=read(path);scene=fitting.MeshPropScene(path)
        point=scene._scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
        extra=copy.deepcopy(spec['props']['crate'])
        extra['keyframes']=[dict(time_s=0.,translation_m=(point+[-.105,-.2,.2]).tolist(),rotation_xyzw=[0,0,0,1])]
        spec['props']['obstacle']=extra;save(path,spec)
        authored=read(permissions);authored['mesh_scene_sha256']=sha256(path);save(permissions,authored)
        geometry=read(policy);geometry['mesh_scene_sha256']=sha256(path);save(policy,geometry)
    return permissions,policy


def advance(folder,receipt):return recovery.advance(folder,receipt['checkpoint'],receipt['sha256'])


def finish(folder,receipt):return recovery.finish(folder,receipt['checkpoint'],receipt['sha256'])


def until(folder,receipt,phase):
    for _ in range(40):
        if read(folder/receipt['checkpoint'])['phase']==phase:return receipt
        receipt=advance(folder,receipt)
    raise AssertionError('Requested phase was not reached')


def compare(plain,folder):
    expected=read(plain/'result.json');actual=read(folder/'result.json')
    for name in ('scope','candidate','checkpoint_geometry'):expected.pop(name);actual.pop(name)
    assert actual.pop('optimizer_completed') is True
    assert actual==expected
    assert read(folder/'probes.json')==read(plain/'probes.json')
    a=read(plain/'result.json')['candidate'];b=read(folder/'result.json')['candidate']
    assert (a is None)==(b is None)
    if a is not None:assert sha256(plain/a/'A.glb')==sha256(folder/b/'A.glb')


@pytest.mark.parametrize('obstacle',[False,True])
def test_complete_recoverable_optimizer_matches_existing_acceptance(tmp_path,monkeypatch,obstacle):
    permissions,policy=fixture(tmp_path,monkeypatch,obstacle)
    plain=tmp_path/'plain';folder=tmp_path/'recovery'
    with action_worker_lock.worker_lock():
        fitting.fit(permissions,policy,plain,iterations=4,trust=.25,backtracks=4)
        receipt=recovery.prepare(permissions,policy,folder,iterations=4,trust=.25,backtracks=4)
        final=finish(folder,receipt)
    compare(plain,folder)
    checked=recovery.verify(folder,final['checkpoint'],final['sha256'])
    assert checked['optimizer_completed'] and checked['original_selected'] and not checked['release_approved']
    assert read(folder/'request.json')['original_signature']['lower']==fitting.MeshCharacterProblem(permissions).lower.tolist()
    if obstacle:assert any(row['geometry_evaluated'] and not row['accepted'] for row in read(folder/'probes.json'))
    with pytest.raises(ValueError,match='already complete'):advance(folder,final)


@pytest.mark.parametrize('next_phase',['geometry','initialize','direction','proposal','decision','complete'])
def test_interruption_before_stage_publication_replays_without_duplicate_decisions(tmp_path,monkeypatch,next_phase):
    permissions,policy=fixture(tmp_path,monkeypatch)
    plain=tmp_path/'plain';folder=tmp_path/'recovery'
    fitting.fit(permissions,policy,plain,iterations=4,trust=.25,backtracks=4)
    receipt=recovery.prepare(permissions,policy,folder,iterations=4,trust=.25,backtracks=4)
    real=recovery.publish;hit=[]
    def crash(folder,state,previous):
        if state['phase']==next_phase and not hit:
            hit.append(state['phase']);raise RuntimeError('Interrupted stage publication')
        return real(folder,state,previous)
    monkeypatch.setattr(recovery,'publish',crash)
    with pytest.raises(RuntimeError,match='Interrupted'):finish(folder,receipt)
    assert hit==[next_phase]
    saved=read(folder/'progress.json');pin=sha256(folder/saved['checkpoint'])
    monkeypatch.setattr(recovery,'publish',real)
    finish(folder,saved)
    assert sha256(folder/saved['checkpoint'])==pin
    compare(plain,folder)
    probes=read(folder/'probes.json')
    assert [row['probe'] for row in probes]==list(range(len(probes)))


def test_persisted_direction_is_used_without_rerunning_solver(tmp_path,monkeypatch):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=4)
    receipt=until(folder,receipt,'proposal');state=read(folder/receipt['checkpoint'])
    with np.load(folder/state['direction']['data']) as arrays:delta=arrays['delta']
    value,_,_=recovery.data_read(folder,state['current'])
    monkeypatch.setattr(fitting,'direction',lambda *args,**kwargs:pytest.fail('Committed direction must not be recomputed'))
    next_receipt=advance(folder,receipt);next_state=read(folder/next_receipt['checkpoint'])
    proposed,_,_=recovery.data_read(folder,next_state['pending'])
    np.testing.assert_array_equal(proposed,value+delta)
    finish(folder,next_receipt)


@pytest.mark.parametrize('fault',['permissions','request','checkpoint','snapshot','direction','arrays'])
def test_modified_optimizer_bindings_cannot_resume(tmp_path,monkeypatch,fault):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=until(folder,receipt,'proposal');state=read(folder/receipt['checkpoint'])
    paths=dict(permissions=permissions,request=folder/'request.json',checkpoint=folder/receipt['checkpoint'],
        snapshot=folder/'implementation/native_mesh_character_recovery.py',direction=folder/state['direction']['data'],
        arrays=folder/state['current']['data'])
    with paths[fault].open('ab') as stream:stream.write(b' ')
    before=list((folder/'work').iterdir())
    with pytest.raises(ValueError):advance(folder,receipt)
    assert list((folder/'work').iterdir())==before and not (folder/'result.json').exists()


def test_geometry_assembly_not_committed_by_outer_state_is_never_trusted(tmp_path,monkeypatch):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=until(folder,receipt,'geometry');state=read(folder/receipt['checkpoint'])
    audit=folder/state['pending']['audit'];real=recovery.publish
    def crash(*args,**kwargs):raise RuntimeError('After assembly before commit')
    monkeypatch.setattr(recovery,'publish',crash)
    with pytest.raises(RuntimeError):advance(folder,receipt)
    assemblies=list(audit.glob('complete-*'));assert len(assemblies)==1
    report=read(assemblies[0]/'geometry.json');report['samples']=[];save(assemblies[0]/'geometry.json',report)
    monkeypatch.setattr(recovery,'publish',real)
    monkeypatch.setattr(fitting.MeshPropScene,'geometry',lambda *args,**kwargs:pytest.fail('Complete frames must not be queried again'))
    resumed=advance(folder,receipt);committed=read(folder/resumed['checkpoint'])
    assert len(list(audit.glob('complete-*')))==2
    assert read(assemblies[0]/'geometry.json')['samples']==[]
    assert len(read(folder/committed['pending']['geometry'])['samples'])>0


def test_stale_optimizer_pin_and_rolled_back_complete_geometry_are_rejected(tmp_path,monkeypatch):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    first=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=advance(folder,first)
    with pytest.raises(ValueError,match='no rollback'):advance(folder,first)
    state=read(folder/receipt['checkpoint']);journal=folder/state['pending']['audit']/'geometry-journal'
    genesis=read(journal/'progress.json');receipt=advance(folder,receipt)
    save(journal/'progress.json',genesis)
    with pytest.raises(ValueError,match='rolled back'):advance(folder,receipt)


def test_completed_geometry_seal_checks_saved_bytes_without_requery_or_decompression(tmp_path,monkeypatch):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=until(folder,receipt,'initialize');state=read(folder/receipt['checkpoint'])
    relative,entry=next(iter(state['journals'].items()));seal=read(folder/entry['seal'])
    assert seal['files_sha256'] and any(name.endswith('observations.npz') for name in seal['files_sha256'])
    monkeypatch.setattr(recovery.geometry,'verify',lambda *args,**kwargs:pytest.fail('Sealed complete files need byte verification, not repeated decompression'))
    checked=recovery.verify(folder,receipt['checkpoint'],receipt['sha256']);assert not checked['optimizer_completed']
    archive=next(name for name in seal['files_sha256'] if name.endswith('observations.npz'))
    with (folder/relative/archive).open('ab') as stream:stream.write(b' ')
    with pytest.raises(ValueError,match='complete geometry files changed'):advance(folder,receipt)


@pytest.mark.parametrize('role',['original','proposal'])
def test_hard_exit_during_geometry_resumes_optimizer_in_fresh_process(tmp_path,monkeypatch,role):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery'
    plain=tmp_path/'plain';fitting.fit(permissions,policy,plain,iterations=1,trust=.25,backtracks=2)
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=until(folder,receipt,'geometry')
    if role=='proposal':
        receipt=advance(folder,receipt);receipt=until(folder,receipt,'geometry')
        state=read(folder/receipt['checkpoint'])
        assert state['pending']['role']=='proposal'
        assert state['probes']==read(plain/'probes.json')[:len(state['probes'])]
        assert all(not row['geometry_evaluated'] and not row['accepted'] for row in state['probes'])
    scripts=Path(recovery.__file__).parent
    setup=f"import sys,os;sys.path.insert(0,{str(scripts)!r});import action_worker_lock;from pathlib import Path;action_worker_lock.ROOT=Path({str(tmp_path/'locks')!r});import native_mesh_character_recovery as r;from strep import read;folder=Path({str(folder)!r});receipt=read(folder/'progress.json');"
    program=setup+"\nreal=r.fit.MeshPropScene.geometry\ndef crash(self,*args,**kwargs):\n if kwargs.get('sample_indices')==[1]:os._exit(79)\n return real(self,*args,**kwargs)\nr.fit.MeshPropScene.geometry=crash\nr.advance(folder,receipt['checkpoint'],receipt['sha256'])\n"
    result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True,timeout=120)
    assert result.returncode==79,(result.stdout,result.stderr)
    state=read(folder/receipt['checkpoint']);journal=folder/state['pending']['audit']/'geometry-journal'
    assert read(journal/'progress.json')['completed_samples']==1
    assert not (folder/'result.json').exists()
    program=setup+"r.finish(folder,receipt['checkpoint'],receipt['sha256'])"
    result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,(result.stdout,result.stderr)
    compare(plain,folder)


def test_partial_export_interruption_retains_orphan_and_retries_same_direction(tmp_path,monkeypatch):
    permissions,policy=fixture(tmp_path,monkeypatch);folder=tmp_path/'recovery';plain=tmp_path/'plain'
    fitting.fit(permissions,policy,plain,iterations=1,trust=.25,backtracks=2)
    receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=2)
    receipt=until(folder,receipt,'proposal');real=fitting.SceneEdits.export;abandoned=[]
    def partial(self,*args,**kwargs):
        result=real(self,*args,**kwargs)
        abandoned.append(Path(args[2]))
        raise RuntimeError('Stopped after actor export, before scene publication')
    monkeypatch.setattr(fitting.SceneEdits,'export',partial)
    with pytest.raises(RuntimeError,match='Stopped after actor export'):advance(folder,receipt)
    assert len(abandoned)==1 and abandoned[0].is_file()
    assert not (abandoned[0].parent/'actor-scene.json').exists()
    digest=sha256(abandoned[0]);assert read(folder/'progress.json')==receipt
    monkeypatch.setattr(fitting.SceneEdits,'export',real)
    finish(folder,receipt)
    assert abandoned[0].is_file() and sha256(abandoned[0])==digest
    assert len(list((folder/'work').glob('probe-*')))==1+len(read(plain/'probes.json'))
    compare(plain,folder)
