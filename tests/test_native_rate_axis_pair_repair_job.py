"""Actual resume exports with synthetic protocol fixtures; no solver claim."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_axis_pair_repair_job import run as base_run,CONTROL_SCHEMA,SEGMENT_SCHEMA
from native_rate_axis_pair_repair_job import RepairJob,run,SCHEMA
from test_native_axis_pair_repair_job import prepare as prepare_base
from strep import read,save,sha256


def prepare(folder,version=1,profile=SEGMENT_SCHEMA):
    base=prepare_base(folder,version,profile);resume=folder/'base-repair';r=base_run(base,resume)
    bindings=dict(r['inputs_sha256']);bindings[str(resume/'result.json')]=sha256(resume/'result.json')
    for n,h in r['files_sha256'].items():bindings[str((resume/n).resolve())]=h
    p=folder/'resume-protocol-replay.json'
    save(p,dict(status='complete',producer_result_sha256=sha256(resume/'result.json'),controls=r['controls'],selected_fraction=r['selected_fraction'],
        every_probe_controls_payloads_native_worlds_and_residuals_exact=True,every_absolute_one_neighbor_choice_verified=True,
        original_rate_arrays_recomputed=True,original_static_reference_tracks_replayed=True,all_native_reference_bounds_replayed=True,no_receipt_schema_normalization=True,
        records=[dict(label=v['label'],failed_native_rows=v['failed_native_rows'],failed_contact_rows=v['failed_contact_rows'],absolute_choices=len(v['corrections'])) for v in r['records']],
        complete_native_samples=read(read(base)['study']['path'])['complete_native_samples'],geometry_samples=read(read(base)['study']['path'])['geometry_samples'],
        native_conditions_pass=r['native_conditions_pass'],geometry_conditions_pass=r['geometry_conditions_pass'],inputs_sha256=bindings,quality_approved=False,release_approved=False))
    pin=lambda p:dict(path=str(p.resolve()),sha256=sha256(p))
    path=folder/'rate-repair.json';save(path,dict(schema=SCHEMA,base_request=pin(base),resume_result=pin(resume/'result.json'),resume_replay=pin(p),
        settings=dict(maximum_stages=8,maximum_probes_per_stage=32),label='Unapproved rate-resume diagnostic'))
    return path


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    return prepare(tmp_path_factory.mktemp('rate-source'),2)


@pytest.mark.parametrize('version,profile',[(1,CONTROL_SCHEMA),(2,SEGMENT_SCHEMA)])
def test_actual_resume_preserves_fixed_controls_probe_and_sources(tmp_path,version,profile):
    path=prepare(tmp_path,version,profile);job=RepairJob(path);before=job.inputs.copy();out=tmp_path/'rate-output';r=run(path,out)
    assert r['status']=='complete' and r['native_conditions_pass'] and r['reference_bounds']['passed']
    assert r['tested_neighbors']==0 and r['resumed_result_sha256']==sha256(job.roles['resume_result']) and r['corrections']==job.seed
    assert r['geometry_assessed'] and len(r['appended_library'])==1 and r['original_selected'] and not r['quality_approved'] and not r['release_approved']
    for n,h in before.items():assert sha256(n)==h
    assert (out/'start/A.glb').read_bytes()==(job.start_folder/'A.glb').read_bytes()
    with np.load(out/'start/observations.npz',allow_pickle=False) as z:
        with np.load(job.start_folder/'observations.npz',allow_pickle=False) as old:
            for k in old.files:np.testing.assert_array_equal(z[k],old[k])


@pytest.mark.parametrize('fault',['schema','extra','missing-pin','pin','budget-bool','budget-large','label','peer-status','peer-producer','peer-rate','peer-static',
    'peer-native','peer-records','peer-columns','peer-clock','peer-reference','peer-binding','peer-quality','peer-schema-normalization'])
def test_protocol_rejects_before_output(source,tmp_path,fault):
    r=read(source);peer=read(r['resume_replay']['path'])
    if fault=='schema':r['schema']='other'
    elif fault=='extra':r['approve']=True
    elif fault=='missing-pin':r['resume_result'].pop('sha256')
    elif fault=='pin':r['resume_result']['sha256']='0'*64
    elif fault=='budget-bool':r['settings']['maximum_stages']=True
    elif fault=='budget-large':r['settings']['maximum_probes_per_stage']=65
    elif fault=='label':r['label']=' '
    elif fault=='peer-status':peer['status']='processing'
    elif fault=='peer-producer':peer['producer_result_sha256']='0'*64
    elif fault=='peer-rate':peer['original_rate_arrays_recomputed']=False
    elif fault=='peer-static':peer['original_static_reference_tracks_replayed']=False
    elif fault=='peer-native':peer['every_probe_controls_payloads_native_worlds_and_residuals_exact']=False
    elif fault=='peer-records':peer['records']=[]
    elif fault=='peer-columns':peer['controls']-=1
    elif fault=='peer-clock':peer['complete_native_samples']-=1
    elif fault=='peer-reference':peer['all_native_reference_bounds_replayed']=False
    elif fault=='peer-binding':peer['inputs_sha256']={}
    elif fault=='peer-quality':peer['quality_approved']=True
    elif fault=='peer-schema-normalization':peer['no_receipt_schema_normalization']=False
    if fault.startswith('peer-'):
        p=tmp_path/'peer.json';save(p,peer);r['resume_replay']=dict(path=str(p),sha256=sha256(p))
    path=tmp_path/'request.json';save(path,r);out=tmp_path/'output'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


def test_resume_output_cannot_change_source_population(source):
    job=RepairJob(source);out=job.roles['resume_result'].parent/'nested-rate-output'
    before={str(p):sha256(p) for p in job.roles['resume_result'].parent.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='outside the immutable'):run(source,out)
    assert not out.exists()
    assert {str(p):sha256(p) for p in job.roles['resume_result'].parent.rglob('*') if p.is_file()}==before


def test_resume_population_stays_bound_after_preflight(source):
    job=RepairJob(source);p=job.roles['resume_result'].parent/'unbound.txt'
    try:
        p.write_text('unbound temporary protocol test artifact')
        with pytest.raises(ValueError,match='artifact population changed'):job.check()
    finally:p.unlink(missing_ok=True)


def test_resume_bytes_stay_bound_after_preflight(source,tmp_path):
    r=read(source);p=tmp_path/'peer.json';save(p,read(r['resume_replay']['path']));r['resume_replay']=dict(path=str(p),sha256=sha256(p));path=tmp_path/'request.json';save(path,r)
    job=RepairJob(path);p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='input bytes changed'):job.check()
