"""Opt-in fit geometry checkpoints retain the existing decoded acceptance."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
import native_mesh_character_fit as fitting
from native_mesh_geometry_journal import iter_observations,verify
from native_mesh_prop_scene import MeshPropScene
from strep import read,save,sha256
from test_native_mesh_character_fit import prepared


@pytest.mark.parametrize('obstacle',[False,True])
def test_checkpointed_fit_matches_full_archive_acceptance_and_arrays(tmp_path,monkeypatch,obstacle):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    path,permissions,policy=prepared(tmp_path)
    if obstacle:
        spec=read(path);scene=MeshPropScene(path)
        point=scene._scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
        extra=copy.deepcopy(spec['props']['crate'])
        extra['keyframes']=[dict(time_s=0.,translation_m=(point+[-.105,-.2,.2]).tolist(),rotation_xyzw=[0,0,0,1])]
        spec['props']['obstacle']=extra;save(path,spec)
        authored=read(permissions);authored['mesh_scene_sha256']=sha256(path);save(permissions,authored)
        geometry=read(policy);geometry['mesh_scene_sha256']=sha256(path);save(policy,geometry)
    before={source:sha256(source) for source in fitting.MeshCharacterProblem(permissions).inputs}
    plain=tmp_path/'plain';checked=tmp_path/'checked'
    with action_worker_lock.worker_lock():
        baseline=fitting.fit(permissions,policy,plain,iterations=4,trust=.25,backtracks=4)
        result=fitting.fit(permissions,policy,checked,iterations=4,trust=.25,backtracks=4,checkpoint_geometry=True)
    assert baseline.pop('checkpoint_geometry') is False
    assert result.pop('checkpoint_geometry') is True
    assert result==baseline
    probes=read(checked/'probes.json')
    assert probes==read(plain/'probes.json')
    if obstacle:
        assert any(row['geometry_evaluated'] and not row['geometry_conditions_no_regression'] and not row['accepted'] for row in probes)
        assert not result['sampled_candidate_pass']
    else:assert result['accepted_steps']>0 and result['sampled_candidate_pass']
    for directory in [checked/'original']+[checked/f'probe-{p["probe"]:03d}' for p in probes if p['geometry_evaluated']]:
        original=plain/directory.name
        report=read(directory/'geometry.json');old=read(original/'geometry.json')
        # Each exported candidate has its own source paths and manifest digest;
        # compare complete numerical reports after removing only those bindings.
        report.pop('inputs_sha256');old.pop('inputs_sha256');assert report==old
        complete=directory/'geometry-complete';receipt=read(complete/'result.json')
        assert receipt['observations_format']=='frame-index' and not (directory/'geometry-observations.npz').exists()
        assert sha256(directory/'geometry.json')==receipt['geometry_sha256']
        arrays=dict(iter_observations(complete/'observations-index.json',receipt['observation_index_sha256']))
        with np.load(original/'geometry-observations.npz',allow_pickle=False) as saved:
            assert set(saved.files)==set(arrays)
            for name,value in arrays.items():
                assert value.dtype==saved[name].dtype and value.shape==saved[name].shape
                assert value.tobytes()==saved[name].tobytes(),name
    request=read(checked/'input.json')
    assert request['checkpoint_geometry'] and 'native_mesh_geometry_journal.py' in request['implementation_sha256']
    assert all(sha256(source)==digest for source,digest in before.items())


def test_interrupted_fit_retains_geometry_prefix_without_optimizer_completion(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    _,permissions,policy=prepared(tmp_path);output=tmp_path/'fit';real=MeshPropScene.geometry
    def interrupted(self,*args,**kwargs):
        if kwargs.get('sample_indices')==[1]:raise RuntimeError('Interrupted original geometry')
        return real(self,*args,**kwargs)
    monkeypatch.setattr(MeshPropScene,'geometry',interrupted)
    with pytest.raises(RuntimeError,match='Interrupted original geometry'):
        fitting.fit(permissions,policy,output,checkpoint_geometry=True)
    journal=output/'original/geometry-journal';receipt=read(journal/'progress.json')
    assert receipt['completed_samples']==1 and not receipt['population_complete']
    assert not (output/'result.json').exists() and not (output/'original/geometry.json').exists()
    assert not (output/'original/geometry-complete/result.json').exists()
    checked=verify(journal,receipt['checkpoint'],receipt['sha256'])
    assert checked['completed_samples']==1 and not checked['sampled_conditions_pass']
    assert read(output/'input.json')['checkpoint_geometry']
    source_digest=sha256(output/'input.json')
    monkeypatch.setattr(MeshPropScene,'geometry',real)
    problem=fitting.MeshCharacterProblem(permissions)
    report=fitting.resume_geometry(problem.mesh,read(policy),output/'original',receipt['checkpoint'],receipt['sha256'])
    assert report['all_policy_samples_evaluated']
    assert read(output/'original/geometry.json')==report and sha256(output/'input.json')==source_digest
    assert not (output/'result.json').exists() and not (output/'probes.json').exists()
    completion=read(output/'original/geometry-journal-result.json')
    assert not completion['optimizer_completed'] and not completion['quality_approved']
    with pytest.raises(ValueError,match='already published'):
        fitting.resume_geometry(problem.mesh,read(policy),output/'original',receipt['checkpoint'],receipt['sha256'])
    # The current integration records recoverable geometry, not solver state;
    # attempting to restart the fitter over it must still reject, not overwrite.
    with pytest.raises(ValueError,match='Fresh character fitting output'):
        fitting.fit(permissions,policy,output,checkpoint_geometry=True)


@pytest.mark.parametrize('value',[1,0,'true',None])
def test_checkpoint_choice_rejects_ambiguous_values_before_loading_sources(tmp_path,value):
    with pytest.raises(ValueError,match='geometry checkpoint choice'):
        fitting.fit(tmp_path/'missing',tmp_path/'missing-policy',tmp_path/'output',checkpoint_geometry=value)
    assert not (tmp_path/'output').exists()


def test_geometry_recovery_retains_interrupted_finalization_and_rejects_changed_policy(tmp_path,monkeypatch):
    import native_mesh_geometry_journal as journal
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    path,_,policy_path=prepared(tmp_path);scene=MeshPropScene(path);policy=read(policy_path)
    output=tmp_path/'audit';output.mkdir();real=journal.finalize
    def interrupted(folder,checkpoint,pin,destination,**kwargs):
        destination.mkdir();(destination/'unfinished').write_bytes(b'Retained incomplete assembly')
        raise RuntimeError('Interrupted finalization')
    monkeypatch.setattr(journal,'finalize',interrupted)
    with pytest.raises(RuntimeError,match='Interrupted finalization'):
        fitting.audit_geometry(scene,policy,output,checkpoint_geometry=True)
    receipt=read(output/'geometry-journal/progress.json');assert receipt['population_complete']
    abandoned=output/'geometry-complete/unfinished';before=sha256(abandoned)
    saved_policy=sha256(output/'geometry-policy.json')
    with pytest.raises(ValueError,match='Fresh checkpointed audit'):
        fitting.audit_geometry(scene,{**policy,'new':'invalid replacement'},output,checkpoint_geometry=True)
    assert sha256(output/'geometry-policy.json')==saved_policy
    monkeypatch.setattr(journal,'finalize',real)
    changed=copy.deepcopy(policy);changed['limits']['penetration_m']*=2
    with pytest.raises(ValueError,match='exact original scene and policy'):
        fitting.resume_geometry(scene,changed,output,receipt['checkpoint'],receipt['sha256'])
    assert not (output/'geometry.json').exists() and sha256(abandoned)==before
    monkeypatch.setattr(MeshPropScene,'geometry',lambda *a,**k:pytest.fail('Completed frames were recomputed'))
    report=fitting.resume_geometry(scene,policy,output,receipt['checkpoint'],receipt['sha256'])
    completion=read(output/'geometry-journal-result.json')
    assert completion['directory'].startswith('geometry-complete-')
    assert (output/completion['directory']/'result.json').is_file() and sha256(abandoned)==before
    assert report==read(output/'geometry.json') and report['all_policy_samples_evaluated']
    assert not completion['optimizer_completed'] and not (output/'result.json').exists()


def test_interruption_before_atomic_report_publication_can_retry_without_partial_report(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    path,_,policy_path=prepared(tmp_path);scene=MeshPropScene(path);policy=read(policy_path)
    output=tmp_path/'audit';output.mkdir();real=fitting.os.link
    def interrupted(source,destination,*args,**kwargs):
        if Path(destination)==output/'geometry.json':raise RuntimeError('Interrupted report publication')
        return real(source,destination,*args,**kwargs)
    monkeypatch.setattr(fitting.os,'link',interrupted)
    with pytest.raises(RuntimeError,match='Interrupted report publication'):
        fitting.audit_geometry(scene,policy,output,checkpoint_geometry=True)
    assert not (output/'geometry.json').exists()
    original=output/'geometry-complete/result.json';before=sha256(original)
    receipt=read(output/'geometry-journal/progress.json')
    monkeypatch.setattr(fitting.os,'link',real)
    monkeypatch.setattr(MeshPropScene,'geometry',lambda *a,**k:pytest.fail('Committed geometry was queried again'))
    report=fitting.resume_geometry(scene,policy,output,receipt['checkpoint'],receipt['sha256'])
    completion=read(output/'geometry-journal-result.json')
    assert completion['directory']!='geometry-complete' and sha256(original)==before
    assert fitting.os.path.samefile(output/'geometry.json',output/completion['directory']/'geometry.json')
    assert report==read(output/'geometry.json') and not completion['optimizer_completed']
