"""Saved-model protocol and real generated-fixture export preservation.

Protocol proof flags below are synthetic receiver fixtures, not independent
scientific replay evidence. The separate full retained-model study supplies
that evidence. Tiny source jobs genuinely build the complete saved matrices.
"""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_stored_surface_restore_job as module
from native_stored_pair_job import Job,run as source_run
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_observation_archive import verify
from strep import read,save,sha256
from test_native_stored_pair_job import prepare as prepare_v1
from test_native_static_reference_job import prepare as prepare_v2
from test_native_partner_depth_restore import fixture as math_fixture
from test_native_partner_depth_phase_selection import solver as fake_solver


def prepare(tmp_path,version=1):
    path=prepare_v1(tmp_path) if version==1 else prepare_v2(tmp_path)[0]
    job=Job(path);folder=tmp_path/'source-study';study=source_run(path,folder);sp=folder/'result.json'
    with np.load(folder/'system.npz',allow_pickle=False) as z:surface_rows=len(z['gaps']);guards=len(z['guard_ids'])
    proof=tmp_path/'protocol-proof.json'
    save(proof,dict(status='complete',producer_result_sha256=sha256(sp),all_original_native_norms_and_jacobian_exact=True,
        all_scalar_derivative_columns=job.problem.size,original_rate_arrays_recomputed=True,reference_displacement_replayed_at_all_native_times=True,
        original_static_reference_tracks_replayed=True,original_surface_rows=surface_rows,exact_partner_guard_rows=guards))
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    request=tmp_path/'restore.json';save(request,dict(schema=module.SCHEMA,job=pin(path),study=pin(sp),independent_replay=pin(proof),
        settings=dict(depth_reserve_m=.00002,iterations=32,append_native_passing=True),label='Unapproved diagnostic variant'))
    return request


def rebind(path,study=None,proof=None):
    request=read(path);sp=Path(request['study']['path']);pp=Path(request['independent_replay']['path'])
    if study is not None:save(sp,study)
    proof=read(pp) if proof is None else proof;proof['producer_result_sha256']=sha256(sp);save(pp,proof)
    for role in ('study','independent_replay'):request[role]['sha256']=sha256(request[role]['path'])
    save(path,request)


@pytest.mark.parametrize('version',[1,2])
def test_real_exports_keep_original_acceptance_and_clip_libraries(tmp_path,version):
    path=prepare(tmp_path,version);request=module.RestoreJob(path);original=request.inputs.copy();out=tmp_path/'restored'
    factory=module.phase_engine.solver_module;result=module.run(path,out)
    assert module.phase_engine.solver_module is factory
    assert result['status']=='complete' and result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert not result['model_and_jacobian_rebuilt'] and result['original_external_acceptance_unchanged']
    assert result['guidance_depth_limit_m']==pytest.approx(result['external_depth_limit_m']-.00002)
    solver=read(out/'solver.json');assert 'source_result' in solver and 'result' not in solver
    assert solver['direction_source']==result['direction_source']
    assert result['request_path']==str(path.resolve()) and result['request_sha256']==sha256(path)
    assert result['role_pins']=={role:dict(path=str(p),sha256=sha256(p)) for role,p in request.roles.items()}
    assert result['records'] and len(result['records'])==len(request.job.request['settings']['fractions'])
    for p,h in original.items():assert sha256(p)==h
    for record in result['records']:
        folder=out/record['label'];geometry=read(folder/'geometry.json');assert geometry['limits']==request.job.policy['limits']
        verify(folder/'geometry-observations.npz');assert record['geometry_assessed'] and not record['retained']
        assert record['numerical_conditions_pass']==(record['native_conditions_pass'] and record['reference_bounds']['passed'] and record['geometry_conditions_pass'])
        with np.load(folder/'observations.npz',allow_pickle=False) as z:worlds={n:z[n+'_worlds'].copy() for n in request.job.scene.actors}
        for entry in record['appended_library']:
            n=entry['actor'];rig=RigAsset.load(out/entry['path']);source=request.job.scene.actors[n]['rig']
            assert rig.document['animations'][:-1]==source.document['animations'] and rig.binary[:len(source.binary)]==source.binary
            reader=NativeSupportSampler(rig.document,rig.binary,entry['animation_index'])
            np.testing.assert_array_equal(np.array([reader.sample(float(t)) for t in request.job.problem.times]),worlds[n])
        np.testing.assert_array_equal(worlds['B'],request.job.problem.source_world['B'])
    with pytest.raises(ValueError,match='Fresh immutable'):module.run(path,out)


@pytest.mark.parametrize('fault',['schema','extra','reserve-bool','reserve-negative','reserve-limit','iterations-bool','iterations-limit','append-type','label',
    'pin','study-status','study-schema','study-approval','job-binding','inputs','methods','replay-status','replay-columns','replay-native','replay-reference',
    'artifact','missing-matrix','escape','control','vector','clock','guide-policy','witness','guard-count-bool'])
def test_invalid_or_repinned_incomplete_model_rejects_before_output(tmp_path,fault):
    path=prepare(tmp_path);request=read(path);study=read(request['study']['path']);proof=read(request['independent_replay']['path']);folder=Path(request['study']['path']).parent
    if fault=='schema':request['schema']='other'
    elif fault=='extra':request['approve']=True
    elif fault=='reserve-bool':request['settings']['depth_reserve_m']=True
    elif fault=='reserve-negative':request['settings']['depth_reserve_m']=-.001
    elif fault=='reserve-limit':request['settings']['depth_reserve_m']=.001
    elif fault=='iterations-bool':request['settings']['iterations']=True
    elif fault=='iterations-limit':request['settings']['iterations']=65
    elif fault=='append-type':request['settings']['append_native_passing']=1
    elif fault=='label':request['label']=' '
    elif fault=='pin':request['job']['sha256']='0'*64
    elif fault=='study-status':study['status']='processing'
    elif fault=='study-schema':study['schema']='other'
    elif fault=='study-approval':study['quality_approved']=True
    elif fault=='job-binding':study['job_request_sha256']='0'*64
    elif fault=='inputs':study['inputs_sha256']={}
    elif fault=='methods':study['methods_sha256']['native_stored_pair_job.py']='0'*64
    elif fault=='replay-status':proof['status']='processing'
    elif fault=='replay-columns':proof['all_scalar_derivative_columns']=0
    elif fault=='replay-native':proof['all_original_native_norms_and_jacobian_exact']=False
    elif fault=='replay-reference':proof['reference_displacement_replayed_at_all_native_times']=False
    elif fault=='guard-count-bool':proof['exact_partner_guard_rows']=bool(proof['exact_partner_guard_rows'])
    elif fault=='artifact':study['files_sha256']['system.npz']='0'*64
    elif fault=='missing-matrix':study['files_sha256'].pop('surface-jacobian.npz')
    elif fault=='escape':
        p=tmp_path/'outside';p.write_text('not an artifact');study['files_sha256']['../outside']=sha256(p)
    elif fault in ('control','vector','witness'):
        p=folder/'system.npz'
        with np.load(p,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
        if fault=='control':data['controls'][0]+=.001
        elif fault=='vector':data['vectors'][0,0]+=.01
        else:data['guard_ids']=np.array([-1],int)
        np.savez_compressed(p,**data);study['files_sha256']['system.npz']=sha256(p)
    elif fault=='clock':
        p=folder/'clock-reference.npz'
        with np.load(p,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
        data['times_s'][0]+=.001;np.savez_compressed(p,**data);study['files_sha256']['clock-reference.npz']=sha256(p)
    elif fault=='guide-policy':
        p=folder/'guide-policy.json';policy=read(p);policy['limits']['penetration_m']+=.001;save(p,policy);study['files_sha256']['guide-policy.json']=sha256(p)
    save(path,request);rebind(path,study,proof)
    out=tmp_path/'invalid-output'
    with pytest.raises((ValueError,AssertionError)):module.run(path,out)
    assert not out.exists()


def math_request():
    a,k=math_fixture()
    return SimpleNamespace(native=a[0],nj=a[1],sj=a[3],state=dict(gaps=a[2],offsets=np.asarray(a[4]),guard_ids=np.array([9,10])),blocks=a[5],
        policy=k['policy'],guide=k['scene'],guide_digest=k['digest'],request=dict(settings=dict(iterations=32)),
        job=SimpleNamespace(value=a[6],problem=SimpleNamespace(lower=a[7],upper=a[8]),request=dict(settings=dict(trust=a[9]))))


def test_valid_minimum_norm_phase_is_not_replaced(monkeypatch):
    fake_solver(monkeypatch,[[.025,.3,3.],[.025,.3,1.9],[.025,.3,1.9]],'Solved');original=module.phase_engine.solver_module
    delta,info,_,points,_,restored=module.solve(math_request())
    assert restored is None and len(points)==3 and info['selected_phase']=='minimum-norm'
    assert delta[0]==pytest.approx(.0005) and module.phase_engine.solver_module is original


def test_only_numeric_native_surface_failure_is_restored(monkeypatch):
    fake_solver(monkeypatch,[[.02,.32,3.],[.0250005,.32,1.91]],'Solved');r=math_request();r.native.caps[:]=.0005
    delta,info,_,points,_,restored=module.solve(r)
    assert info['phase_checks'][1]['rejections']==['native_conditions'] and len(points)==2
    assert restored['status']=='RestoredSurfaceDirection' and restored['selected']['native_excess']<=0.
    assert .0004<delta[0]<=.0005


def test_non_native_phase_failure_cannot_trigger_interpolation(monkeypatch):
    fake_solver(monkeypatch,[[.025,.3,3.],[.025,.3,1.8]],'Solved')
    delta,info,_,points,_,restored=module.solve(math_request())
    assert restored is None and len(points)==2 and 'surface_epigraph' in info['phase_checks'][1]['rejections']
    assert delta[0]==pytest.approx(.0005)


def test_static_reference_proof_required_for_v2(tmp_path):
    path=prepare(tmp_path,2);r=read(path);proof=read(r['independent_replay']['path']);proof['original_static_reference_tracks_replayed']=False
    rebind(path,proof=proof)
    with pytest.raises(ValueError,match='static reference'):module.run(path,tmp_path/'invalid-static')
    assert not (tmp_path/'invalid-static').exists()


def test_failed_solver_preserves_module_and_prior_phase_checkpoint(monkeypatch):
    real=module.phase_engine.solver_module();calls=[];checkpoints=[]
    class Failing:
        __version__=real.__version__;DefaultSettings=real.DefaultSettings;NonnegativeConeT=real.NonnegativeConeT;SecondOrderConeT=real.SecondOrderConeT
        @staticmethod
        def DefaultSolver(*args):
            calls.append(1)
            if len(calls)==2:raise RuntimeError('deliberate second-phase failure')
            return SimpleNamespace(solve=lambda:SimpleNamespace(status='Solved',iterations=1,x=[.025,.3,3.]))
    factory=lambda:Failing;monkeypatch.setattr(module.phase_engine,'solver_module',factory)
    with pytest.raises(RuntimeError,match='deliberate'):
        module.solve(math_request(),on_phase=lambda points,phases:checkpoints.append((len(points),len(phases))))
    assert checkpoints==[(1,1)] and module.phase_engine.solver_module is factory


def test_input_mutation_after_preflight_rejects(tmp_path):
    path=prepare(tmp_path);r=module.RestoreJob(path);p=r.roles['independent_replay'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='input bytes changed'):r.check()


def test_runtime_failure_is_archived_without_success(tmp_path,monkeypatch):
    path=prepare(tmp_path)
    def fail(*args,**kwargs):raise RuntimeError('deliberate runtime failure')
    monkeypatch.setattr(module,'solve',fail);out=tmp_path/'failed'
    with pytest.raises(RuntimeError,match='deliberate'):module.run(path,out)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'failure.json').is_file() and not (out/'result.json').exists()
    assert (out/'implementation'/'native_stored_surface_restore_job.py').is_file()
