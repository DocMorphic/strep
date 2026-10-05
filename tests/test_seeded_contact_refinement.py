"""An explicit seed remains subject to complete independent admission checks."""
from pathlib import Path
import sys,subprocess
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import seeded_contact_refinement as flow
import verify_seeded_contact_refinement as replay
from test_cumulative_coupled_contacts import fixture,independently_check
from test_warm_coupled_contacts import start,check_fallback
from strep import read,save,sha256


def seed(tmp_path,value=1e-7):
    path=tmp_path/'direction.npy';np.save(path,np.array([value,0,0]));return path


@pytest.mark.parametrize('backend',['continuous-native','stored-native'])
@pytest.mark.parametrize('unsafe',[False,True])
def test_real_complete_affine_export_geometry_and_replay_keep_every_gate(tmp_path,monkeypatch,backend,unsafe):
    paths=fixture(tmp_path,monkeypatch,unsafe_floor=unsafe);baseline=start(tmp_path);explicit=seed(tmp_path)
    result=flow.run(*paths,tmp_path/'out',proposal_backend=backend,seed_direction=explicit,start_controls=baseline,backoffs=1)
    assert result['retained_new_improvement']==(not unsafe)
    assert result['geometry_checked'] and result['complete_geometry_pass']==(not unsafe)
    assert not result['conic_solver_executed'] and result['proposal_source']=='explicit-seed-direction'
    assert result['history'][0]['solver_status']=='ExplicitSeedDirection'
    if unsafe:check_fallback(tmp_path/'out',result,baseline)
    else:independently_check(paths,tmp_path/'out',result)
    checked=replay.run(tmp_path/'out',tmp_path/'replay')
    assert checked['explicit_seed_binding_reproduced'] and not checked['conic_solver_executed']
    assert checked['geometry']['geometry_queries_rerun'] and checked['geometry']['all_numeric_geometry_outputs_exact']
    assert not checked['release_approved']


@pytest.mark.parametrize('backend',['continuous-native','stored-native'])
def test_infeasible_seed_cannot_bypass_affine_native_and_start_protection(tmp_path,monkeypatch,backend):
    paths=fixture(tmp_path,monkeypatch);baseline=start(tmp_path);explicit=seed(tmp_path,.001)
    result=flow.run(*paths,tmp_path/'out',proposal_backend=backend,seed_direction=explicit,start_controls=baseline,backoffs=1)
    check_fallback(tmp_path/'out',result,baseline)
    checked=replay.run(tmp_path/'out',tmp_path/'replay')
    assert checked['retained_claim_reproduced'] and checked['geometry'] is None
    assert not result['retained_new_improvement']


@pytest.mark.parametrize('value',[0,.03,np.nan,np.inf])
def test_invalid_seed_rejects_without_creating_output(tmp_path,monkeypatch,value):
    paths=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError):
        flow.run(*paths,tmp_path/'out',proposal_backend='stored-native',seed_direction=seed(tmp_path,value))
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('iterations',[0,2,True])
def test_seed_is_never_silently_reused_as_a_second_iteration(iterations,tmp_path):
    with pytest.raises(ValueError,match='exactly one'):
        flow.run(*([tmp_path/'missing']*4),tmp_path/'out',proposal_backend='stored-native',
            seed_direction=tmp_path/'missing.npy',iterations=iterations)
    assert not (tmp_path/'out').exists()


def test_cli_requires_explicit_seed_direction(tmp_path):
    process=subprocess.run([sys.executable,str(Path(flow.__file__)),*['missing']*5,'--proposal-backend','stored-native'],
        capture_output=True,text=True)
    assert process.returncode==2 and '--seed-direction' in process.stderr and not (tmp_path/'out').exists()


def test_explicit_input_roles_allow_equal_start_and_seed_bytes(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch);both=start(tmp_path)
    result=flow.run(*paths,tmp_path/'out',proposal_backend='stored-native',seed_direction=both,start_controls=both,backoffs=1)
    request=read(tmp_path/'out/request.json')
    assert request['seed_direction']==request['start_controls']==str(both.resolve())
    assert replay.run(tmp_path/'out',tmp_path/'replay')['explicit_seed_binding_reproduced']


@pytest.mark.parametrize('fault',['seed-bytes','rebound-seed','seed-role','conic-claim','raw-direction','retention-flag'])
def test_changed_or_rebound_seed_and_scope_claims_cannot_pass_replay(tmp_path,monkeypatch,fault):
    paths=fixture(tmp_path,monkeypatch);explicit=seed(tmp_path)
    result=flow.run(*paths,tmp_path/'out',proposal_backend='stored-native',seed_direction=explicit,backoffs=1)
    request=read(tmp_path/'out/request.json')
    if fault in ('seed-bytes','rebound-seed'):
        np.save(explicit,np.array([2e-7,0,0]))
        if fault=='rebound-seed':request['inputs_sha256'][str(explicit.resolve())]=sha256(explicit)
    if fault=='seed-role':request['seed_direction']=str(tmp_path/'absent.npy')
    if fault=='conic-claim':result['conic_solver_executed']=True
    if fault=='retention-flag':result['retained_new_improvement']=not result['retained_new_improvement']
    if fault=='raw-direction':
        path=tmp_path/'out/iteration-1/proposal.json';proposal=read(path)
        proposal['checked_affine_proposal']['raw_delta'][0]+=1e-7;save(path,proposal)
    save(tmp_path/'out/request.json',request);result['request_sha256']=sha256(tmp_path/'out/request.json')
    result['files_sha256']={n:sha256(tmp_path/'out'/n) for n in result['files_sha256']};save(tmp_path/'out/result.json',result)
    with pytest.raises((AssertionError,ValueError)):replay.run(tmp_path/'out',tmp_path/'replay')


@pytest.mark.parametrize('fault',['world','native','source-cap','retained-controls'])
def test_rebound_numeric_observations_are_independently_reconstructed(tmp_path,monkeypatch,fault):
    paths=fixture(tmp_path,monkeypatch,unsafe_floor=True);output=tmp_path/'out'
    result=flow.run(*paths,output,proposal_backend='stored-native',seed_direction=seed(tmp_path),backoffs=1)
    if fault=='retained-controls':
        path=output/'retained-controls.npy';value=np.load(path);value[0]+=.001;np.save(path,value)
    else:
        path=output/('source.npz' if fault=='source-cap' else 'iteration-1/backoff-0/conditions.npz')
        with np.load(path,allow_pickle=False) as archive:values={n:archive[n] for n in archive.files}
        if fault=='world':values['world_A'][0,0,0,3]+=.001
        if fault=='native':values['native'][0]+=.001
        if fault=='source-cap':values['A_metric_0'][0,0]+=.001
        np.savez_compressed(path,**values)
    result['files_sha256']={n:sha256(output/n) for n in result['files_sha256']};save(output/'result.json',result)
    with pytest.raises(AssertionError):replay.run(output,tmp_path/'replay')


def test_seeded_job_respects_busy_worker_and_fresh_output(tmp_path,monkeypatch):
    import action_worker_lock as locks
    paths=fixture(tmp_path,monkeypatch);explicit=seed(tmp_path)
    with locks.worker_lock():
        with pytest.raises(RuntimeError,match='Another local'):
            flow.run(*paths,tmp_path/'out',proposal_backend='stored-native',seed_direction=explicit)
    assert not (tmp_path/'out').exists()
    output=tmp_path/'out';output.mkdir();sentinel=output/'keep';sentinel.write_text('unchanged')
    with pytest.raises(ValueError,match='Fresh'):
        flow.run(*paths,output,proposal_backend='stored-native',seed_direction=explicit)
    assert sentinel.read_text()=='unchanged'
