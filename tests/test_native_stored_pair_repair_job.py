"""Actual fixed-control repairs/exports and pinned study protocol rejections."""
import copy,gc,sys,weakref
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_stored_pair_repair_job import RepairJob,run,SCHEMA
import native_stored_pair_repair_job as repairer
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import evaluate_to_archive
from native_surface_model import surface_points,geometry_score
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import ROOT,read,save,sha256
from test_native_stored_pair_job import prepare as prepare_v1
from test_native_static_reference_job import prepare as prepare_v2


def prepare(tmp_path,version=1):
    path=prepare_v1(tmp_path) if version==1 else prepare_v2(tmp_path)[0];job=Job(path)
    study=tmp_path/'study';folder=study/'fraction-00';folder.mkdir(parents=True);files={}
    for n in job.edits.actors:
        files[n]=folder/(n+'.glb');job.edits.export(n,job.value,files[n])
    residual,worlds=job.problem.decoded(files,job.value)
    np.savez_compressed(folder/'observations.npz',controls=job.value,residual=residual,**{n+'_worlds':w for n,w in worlds.items()})
    centered=copy.copy(job.problem);centered.edits=StoredCurveProxy(job.edits,job.value,job.files)
    smooth=centered.constraints(job.value,centered.worlds(job.value,quantized=False))
    geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),folder/'geometry-observations.npz',actor_vertices=surface_points(job.problem,worlds))
    save(folder/'geometry.json',geometry)
    record=dict(label='fraction-00',fraction=1.,failed_native_rows=int((residual>0).sum()),unrounded_failed_native_rows=int((smooth>0).sum()),
        reference_bounds=job.reference_bounds(files,worlds),geometry_assessed=True,geometry_conditions_pass=geometry['sampled_conditions_pass'],geometry_score=list(geometry_score(geometry)))
    save(folder/'result.json',record)
    # These protocol fixture receipts use actual exports/observations but do not
    # claim that a solver/Jacobian replay ran. End-to-end study evidence is separate.
    result=dict(schema=job.request['schema'],status='complete',job_request_sha256=sha256(path),inputs_sha256=job.inputs,
        methods_sha256={n:sha256(ROOT/'scripts'/n) for n in JOB_METHODS},records=[record],files_sha256={str(p.relative_to(study)):sha256(p) for p in study.rglob('*') if p.is_file()})
    result_path=study/'result.json';save(result_path,result)
    replay=tmp_path/'protocol-replay.json';save(replay,dict(status='complete',producer_result_sha256=sha256(result_path),
        all_original_native_norms_and_jacobian_exact=True,all_scalar_derivative_columns=job.problem.size,original_rate_arrays_recomputed=True))
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    request=tmp_path/'repair.json';save(request,dict(schema=SCHEMA,job=pin(path),study=pin(result_path),independent_replay=pin(replay),
        settings=dict(maximum_stages=8,maximum_probes_per_stage=32),label='Separate unapproved stored repair'))
    return request


def rebind(path,study=None,replay=None):
    request=read(path);p=Path(request['study']['path']);rp=Path(request['independent_replay']['path'])
    if study is not None:save(p,study)
    value=read(rp) if replay is None else replay;value['producer_result_sha256']=sha256(p);save(rp,value)
    for role in ('study','independent_replay'):request[role]['sha256']=sha256(request[role]['path'])
    save(path,request)


@pytest.mark.parametrize('version',[1,2])
def test_actual_passing_source_needs_no_neighbors_and_preserves_originals(tmp_path,version):
    path=prepare(tmp_path,version);job=RepairJob(path);before=job.inputs.copy();out=tmp_path/'repair-output';result=run(path,out)
    assert result['status']=='complete' and result['native_conditions_pass'] and result['reference_bounds']['passed']
    assert result['tested_neighbors']==0 and result['corrections']==job.job.request['anchor']['corrections']
    assert result['geometry_assessed'] and result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert len(result['records'])==1 and result['final_label']=='start' and result['controls']==3*version
    for p,h in before.items():assert sha256(p)==h
    with np.load(out/'controls.npz',allow_pickle=False) as z:np.testing.assert_array_equal(z['controls'],job.value)
    for entry in result['appended_library']:
        n=entry['actor'];rig=RigAsset.load(out/'appended'/(n+'.glb'));source=job.job.scene.actors[n]['rig']
        assert rig.document['animations'][:-1]==source.document['animations'] and rig.binary[:len(source.binary)]==source.binary
        sampler=NativeSupportSampler(rig.document,rig.binary,entry['animation_index'])
        with np.load(out/'start'/'observations.npz',allow_pickle=False) as z:np.testing.assert_array_equal(np.array([sampler.sample(float(t)) for t in job.problem.times]),z[n+'_worlds'])
    if version==2:assert any(r.get('baseline')=='original-static-transform' for r in result['reference_bounds']['tracks'])
    with pytest.raises(ValueError,match='Fresh immutable'):run(path,out)


@pytest.mark.parametrize('fault',['schema','extra','budget-bool','budget-limit','label','pin','study-status','job-binding','methods','inputs',
    'replay-status','replay-columns','replay-native','artifact','escape','selected-binding','no-choice','score-bool','geometry-score'])
def test_invalid_protocol_rejects_before_output_creation(tmp_path,fault):
    path=prepare(tmp_path);request=read(path);study=read(request['study']['path']);replay=read(request['independent_replay']['path'])
    if fault=='schema':request['schema']='other'
    elif fault=='extra':request['approve']=True
    elif fault=='budget-bool':request['settings']['maximum_stages']=True
    elif fault=='budget-limit':request['settings']['maximum_probes_per_stage']=65
    elif fault=='label':request['label']=' '
    elif fault=='pin':request['job']['sha256']='0'*64
    elif fault=='study-status':study['status']='processing'
    elif fault=='job-binding':study['job_request_sha256']='0'*64
    elif fault=='methods':study['methods_sha256']['native_stored_pair_job.py']='0'*64
    elif fault=='inputs':study['inputs_sha256']={}
    elif fault=='replay-status':replay['status']='processing'
    elif fault=='replay-columns':replay['all_scalar_derivative_columns']=1
    elif fault=='replay-native':replay['all_original_native_norms_and_jacobian_exact']=False
    elif fault=='artifact':study['files_sha256']['fraction-00/observations.npz']='0'*64
    elif fault=='escape':
        outside=tmp_path/'outside.txt';outside.write_text('outside');study['files_sha256']['../outside.txt']=sha256(outside)
    elif fault=='selected-binding':study['files_sha256'].pop(str(Path('fraction-00')/'A.glb'))
    elif fault=='no-choice':study['records'][0]['unrounded_failed_native_rows']=1
    elif fault=='score-bool':study['records'][0]['geometry_score'][0]=True
    elif fault=='geometry-score':
        study['records'][0]['geometry_score'][0]+=.01
        p=Path(request['study']['path']).parent/'fraction-00/result.json';save(p,study['records'][0]);study['files_sha256'][str(Path('fraction-00')/'result.json')]=sha256(p)
    save(path,request);rebind(path,study,replay);out=tmp_path/'repair-output'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


def test_repinned_false_raw_observation_retains_failure_without_success(tmp_path):
    path=prepare(tmp_path);request=read(path);study=read(request['study']['path']);p=Path(request['study']['path']).parent/'fraction-00/observations.npz'
    with np.load(p,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    data['residual'][0]+=.01;np.savez_compressed(p,**data);study['files_sha256'][str(Path('fraction-00')/'observations.npz')]=sha256(p);rebind(path,study)
    out=tmp_path/'repair-output'
    with pytest.raises(AssertionError):run(path,out)
    assert (out/'failure.json').is_file() and read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()
    assert (out/'start'/'A.glb').is_file() and (out/'implementation'/'native_stored_pair_repair_job.py').is_file()


@pytest.mark.parametrize('version',[1,2])
def test_nested_output_preserves_original_study_inventory(tmp_path,version):
    path=prepare(tmp_path,version);source=Path(read(path)['study']['path']).parent
    before={str(p.relative_to(source)):sha256(p) for p in source.rglob('*') if p.is_file()}
    out=source/'nested'/'repair'
    with pytest.raises(ValueError,match='outside the immutable saved study'):run(path,out)
    assert not (source/'nested').exists()
    assert {str(p.relative_to(source)):sha256(p) for p in source.rglob('*') if p.is_file()}==before


def test_input_mutation_after_preflight_rejects(tmp_path):
    path=prepare(tmp_path);job=RepairJob(path);p=job.roles['independent_replay'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='input bytes changed'):job.check()


def test_archived_probe_worlds_are_released_instead_of_accumulating(tmp_path,monkeypatch):
    path=prepare(tmp_path);references=[]
    def controlled_search(problem,value,policy,corrections,decode,**settings):
        for label in ('start','memory-probe-1','memory-probe-2','memory-probe-3'):
            residual,worlds=decode(corrections,label)
            assert np.all(residual<=0);references.append(weakref.ref(worlds['A']))
            del residual,worlds;gc.collect()
            assert all(r() is None for r in references),'archived edited poses must not stay in the job cache'
        return corrections,dict(final_label='start',native_conditions_pass=True,tested_neighbors=3)
    monkeypatch.setattr(repairer,'search',controlled_search)
    result=run(path,tmp_path/'repair-output')
    assert result['native_conditions_pass'] and result['geometry_assessed'] and len(result['records'])==4
    for label in ('start','memory-probe-1','memory-probe-2','memory-probe-3'):
        assert (tmp_path/'repair-output'/label/'observations.npz').is_file()
