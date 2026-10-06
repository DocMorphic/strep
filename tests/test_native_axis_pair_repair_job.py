"""Actual fixed-control repairs/exports and pinned study protocol rejections."""
import copy,gc,sys,weakref,shutil
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_axis_pair_repair_job import RepairJob,run,SCHEMA,CONTROL_SCHEMA,SEGMENT_SCHEMA,BASE_STUDY_METHODS,STUDY_METHODS
import native_axis_pair_repair_job as repairer
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import evaluate_to_archive
from native_surface_model import surface_points,geometry_score
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import ROOT,read,save,sha256
from test_native_stored_pair_job import prepare as prepare_v1
from test_native_static_reference_job import prepare as prepare_v2


from test_native_control_axis_pair_repair_job import prepare as prepare_direct


def prepare(tmp_path,version=1,profile=SEGMENT_SCHEMA):
    # Actual GLB exports/worlds/geometry come from the existing fixture. These
    # synthetic protocol proofs do not claim that any model/solver replay ran.
    source=tmp_path/'cache-source';source.mkdir()
    previous=prepare_direct(source,version);request=read(previous)
    parent=Path(request['study']['path']);parent_proof=Path(request['independent_replay']['path'])
    if profile==CONTROL_SCHEMA:
        request['schema']=SCHEMA;path=tmp_path/'repair.json';save(path,request);return path
    folder=tmp_path/'segment-study';shutil.copytree(parent.parent,folder)
    result=read(folder/'result.json');result['schema']=SEGMENT_SCHEMA
    name='native_triangle_segment_axis.py';(folder/'implementation'/name).write_bytes((ROOT/'scripts'/name).read_bytes())
    result['methods_sha256'][name]=sha256(ROOT/'scripts'/name)
    bindings={str(parent):sha256(parent),str(parent_proof):sha256(parent_proof)}
    for name,h in read(parent)['files_sha256'].items():bindings[str((parent.parent/name).resolve())]=h
    result['cached_inputs_sha256']=bindings
    save(folder/'cached-input-bindings.json',bindings)
    save(folder/'model.json',dict(source_model_result_sha256=sha256(parent),source_model_replay_sha256=sha256(parent_proof)))
    result['files_sha256']={str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file() and p!=folder/'result.json'}
    save(folder/'result.json',result)
    peer=read(parent_proof);peer.pop('all_point_derivative_columns');peer.pop('every_axis_choice_scalar_gap_and_surface_jacobian_exact')
    peer.update(producer_result_sha256=sha256(folder/'result.json'),all_point_derivative_columns_bound_to_completed_source=3*version,
        every_joint_segment_axis_choice_scalar_gap_and_surface_jacobian_exact=True,cached_native_point_derivative_arrays_exact=True,
        strict_affine_native_segment_endpoints_independently_checked=True)
    proof=tmp_path/'segment-protocol-replay.json';save(proof,peer)
    request.update(schema=SCHEMA,study=dict(path=str(folder/'result.json'),sha256=sha256(folder/'result.json')),
        independent_replay=dict(path=str(proof),sha256=sha256(proof)))
    path=tmp_path/'repair.json';save(path,request);return path


def rebind(path,study=None,replay=None):
    request=read(path);p=Path(request['study']['path']);rp=Path(request['independent_replay']['path'])
    if study is not None:save(p,study)
    value=read(rp) if replay is None else replay;value['producer_result_sha256']=sha256(p);value['records']=read(p)['records'];save(rp,value)
    for role in ('study','independent_replay'):request[role]['sha256']=sha256(request[role]['path'])
    save(path,request)


@pytest.mark.parametrize('profile',[CONTROL_SCHEMA,SEGMENT_SCHEMA])
@pytest.mark.parametrize('version',[1,2])
def test_actual_passing_source_needs_no_neighbors_and_preserves_originals(tmp_path,version,profile):
    path=prepare(tmp_path,version,profile);job=RepairJob(path);before=job.inputs.copy();out=tmp_path/'repair-output';result=run(path,out)
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
    'replay-status','replay-columns','replay-native','artifact','escape','selected-binding','no-choice','score-bool','geometry-score','study-schema','job-schema','quality','columns-bool','point-gap','export-replay','transport','native-clock','geometry-clock','archived-method','extra-artifact'])
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
    elif fault=='replay-columns':replay['all_point_derivative_columns_bound_to_completed_source']=1
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
    elif fault=='study-schema':study['schema']='strep-native-stored-pair-job-v1'
    elif fault=='job-schema':study['job_schema']='strep-native-stored-pair-job-v2'
    elif fault=='quality':study['quality_approved']=True
    elif fault=='columns-bool':replay['all_point_derivative_columns_bound_to_completed_source']=True
    elif fault=='point-gap':replay['every_joint_segment_axis_choice_scalar_gap_and_surface_jacobian_exact']=False
    elif fault=='export-replay':replay['every_export_payload_world_native_centered_count_and_reference_bound_exact']=False
    elif fault=='transport':replay['geometry_transport_verified']=False
    elif fault=='native-clock':study['complete_native_samples']-=1
    elif fault=='geometry-clock':study['geometry_samples']-=1
    elif fault=='archived-method':study['files_sha256'].pop(str(Path('implementation')/'native_stored_pair_job.py'))
    elif fault=='extra-artifact':(Path(request['study']['path']).parent/'extra.txt').write_text('unbound')
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
    assert (out/'start'/'A.glb').is_file() and (out/'implementation'/'native_axis_pair_repair_job.py').is_file()


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


@pytest.mark.parametrize('fault',['missing','empty','peer-arrays','peer-endpoints','relative-path','map-mismatch','lineage','cache-mutation'])
def test_invalid_cached_lineage_rejects_before_output_creation(tmp_path,fault):
    path=prepare(tmp_path);request=read(path);study=read(request['study']['path']);peer=read(request['independent_replay']['path']);folder=Path(request['study']['path']).parent
    if fault=='missing':study.pop('cached_inputs_sha256')
    elif fault=='empty':study['cached_inputs_sha256']={}
    elif fault=='peer-arrays':peer['cached_native_point_derivative_arrays_exact']=False
    elif fault=='peer-endpoints':peer['strict_affine_native_segment_endpoints_independently_checked']=False
    elif fault=='relative-path':
        h=next(iter(study['cached_inputs_sha256'].values()));study['cached_inputs_sha256']={'relative.json':h};save(folder/'cached-input-bindings.json',study['cached_inputs_sha256'])
        study['files_sha256']['cached-input-bindings.json']=sha256(folder/'cached-input-bindings.json')
    elif fault=='map-mismatch':save(folder/'cached-input-bindings.json',{})
    elif fault=='lineage':
        identity=read(folder/'model.json');identity['source_model_result_sha256']='0'*64;save(folder/'model.json',identity);study['files_sha256']['model.json']=sha256(folder/'model.json')
    elif fault=='cache-mutation':
        cached=Path(next(iter(study['cached_inputs_sha256'])));cached.write_bytes(cached.read_bytes()+b' ')
    rebind(path,study,peer);out=tmp_path/'repair-output'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


def test_replayed_records_must_match_producer_population(tmp_path):
    path=prepare(tmp_path);request=read(path);peer=read(request['independent_replay']['path']);peer['records']=[]
    save(request['independent_replay']['path'],peer);request['independent_replay']['sha256']=sha256(request['independent_replay']['path']);save(path,request)
    with pytest.raises(ValueError,match='format-bound'):run(path,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_cache_lineage_binding_persists_after_preflight(tmp_path):
    path=prepare(tmp_path);job=RepairJob(path);parent=next(Path(p) for p in job.study['cached_inputs_sha256'] if Path(p).name=='result.json')
    parent.write_bytes(parent.read_bytes()+b' ')
    with pytest.raises(ValueError,match='input bytes changed'):job.check()


@pytest.mark.parametrize('location',['inside','ancestor'])
def test_output_cannot_change_cached_source_population(tmp_path,location):
    path=prepare(tmp_path);source=tmp_path/'cache-source'/'study'
    before={str(p.relative_to(source)):sha256(p) for p in source.rglob('*') if p.is_file()}
    out=source/'nested'/'repair' if location=='inside' else tmp_path
    with pytest.raises(ValueError,match='outside the immutable saved study' if location=='inside' else 'Fresh immutable'):
        run(path,out)
    assert not (source/'nested').exists()
    assert {str(p.relative_to(source)):sha256(p) for p in source.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('location',['current','cached'])
def test_input_population_addition_after_preflight_rejects(tmp_path,location):
    path=prepare(tmp_path);job=RepairJob(path)
    folder=job.folder if location=='current' else tmp_path/'cache-source'/'study'
    (folder/'unbound.txt').write_text('new unbound artifact')
    with pytest.raises(ValueError,match='artifact population changed'):job.check()
