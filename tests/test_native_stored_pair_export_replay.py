"""Real study/export replay and rejection of falsified saved observations."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_stored_pair_job import run as produce
from native_stored_pair_export_replay import run,ExportReplay
from test_native_stored_pair_job import prepare as prepare_v1
from test_native_static_reference_job import prepare as prepare_v2
from strep import read,save,sha256


def prepare(tmp_path,version=1):
    path=prepare_v1(tmp_path) if version==1 else prepare_v2(tmp_path)[0]
    producer=tmp_path/'producer';produce(path,producer);return producer/'result.json'


def refresh(path):
    result=read(path)
    result['files_sha256']={str(p.relative_to(path.parent)):sha256(p) for p in path.parent.rglob('*') if p.is_file() and p not in (path,path.parent/'pipeline.json')}
    save(path,result)


@pytest.mark.parametrize('version',[1,2])
def test_actual_complete_export_population_and_original_reference_replay(tmp_path,version):
    path=prepare(tmp_path,version);binding=ExportReplay(path).bindings.copy();out=tmp_path/'replay';result=run(path,out)
    assert result['status']=='complete' and result['controls']==3*version and len(result['records'])==1
    assert result['every_export_payload_world_and_native_observation_exact'] and result['all_original_rate_arrays_recomputed']
    assert result['reference_displacement_replayed_at_all_native_times'] and result['geometry_transport_verified']
    assert not result['geometry_predicates_independently_recomputed'] and not result['model_and_jacobian_replayed']
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert all(sha256(p)==h for p,h in binding.items())
    if version==2:assert any(r.get('baseline')=='original-static-transform' for r in result['records'][0]['reference_bounds']['tracks'])
    with pytest.raises(ValueError,match='Fresh immutable'):run(path,out)


@pytest.mark.parametrize('fault',['status','schema','input','method','artifact','escape','omitted-artifact','snapshot','request','population','approval','selection'])
def test_bad_provenance_rejects_before_output_creation(tmp_path,fault):
    path=prepare(tmp_path);result=read(path)
    if fault=='status':result['status']='processing'
    elif fault=='schema':result['schema']='other'
    elif fault=='approval':result['quality_approved']=True
    elif fault=='selection':result['original_selected']=False
    elif fault=='input':result['inputs_sha256'][next(iter(result['inputs_sha256']))]='0'*64
    elif fault=='method':result['methods_sha256']['native_stored_pair_job.py']='0'*64
    elif fault=='artifact':result['files_sha256'][str(Path('fraction-00')/'observations.npz')]='0'*64
    elif fault=='escape':result['files_sha256']['../outside.txt']='0'*64
    elif fault=='omitted-artifact':result['files_sha256'].pop(str(Path('fraction-00')/'observations.npz'))
    elif fault=='snapshot':result['input_snapshots']['source_scene']['sha256']='0'*64
    elif fault=='request':result['job_request_sha256']='0'*64
    elif fault=='population':result['complete_native_samples']+=1
    save(path,result);out=tmp_path/'replay'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['residual','world','bounds','contact-bool','fraction','geometry-score','record-omission'])
def test_rehashed_false_export_retains_failed_replay(tmp_path,fault):
    path=prepare(tmp_path);folder=path.parent/'fraction-00';result=read(path);record=copy.deepcopy(result['records'][0])
    if fault in ('residual','world'):
        p=folder/'observations.npz'
        with np.load(p,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
        if fault=='residual':arrays['residual'][0]+=.01
        else:arrays['B_worlds'][0,0,0,3]+=.01
        np.savez_compressed(p,**arrays)
    elif fault=='bounds':record['reference_bounds']['joint_displacement_m']['A']+=.0001
    elif fault=='contact-bool':record['failed_contact_rows']=bool(record['failed_contact_rows'])
    elif fault=='fraction':record['fraction']=.5
    elif fault=='geometry-score':record['geometry_score'][0]+=.01
    if fault=='record-omission':result['records']=[]
    else:
        result['records'][0]=record;save(folder/'result.json',record)
    save(path,result);refresh(path);out=tmp_path/'replay'
    with pytest.raises((ValueError,AssertionError)):run(path,out)
    assert read(out/'failure.json')['status']=='failed' and not (out/'result.json').exists()
    assert (out/'implementation'/'native_stored_pair_export_replay.py').is_file()


def test_input_mutation_after_preflight_rejects(tmp_path):
    path=prepare(tmp_path);replay=ExportReplay(path);p=replay.paths['source_scene'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='bytes differ'):replay.check()


def test_replay_cannot_write_inside_the_producer_archive(tmp_path):
    path=prepare(tmp_path)
    with pytest.raises(ValueError,match='outside the immutable'):run(path,path.parent/'replay')
    assert not (path.parent/'replay').exists()


def test_fully_rebound_weakened_rate_caps_still_fail_original_reference_recomputation(tmp_path):
    path=prepare(tmp_path);result=read(path);snapshot=result['input_snapshots']['source_rate_caps'];caps=Path(snapshot['original_path'])
    with np.load(caps,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    data['A_metric_0']+=.001;np.savez(caps,**data)
    changed=sha256(caps);(path.parent/snapshot['path']).write_bytes(caps.read_bytes());snapshot['sha256']=changed
    result['inputs_sha256'][str(caps)]=changed
    original=next(Path(p) for p,h in result['inputs_sha256'].items() if h==result['job_request_sha256'])
    request=read(original);request['source_rate_caps']['sha256']=changed;save(original,request)
    result['job_request_sha256']=sha256(original);result['inputs_sha256'][str(original)]=sha256(original)
    save(path.parent/'job.json',request);save(path,result);refresh(path)
    out=tmp_path/'replay'
    with pytest.raises(ValueError,match='rate arrays do not recompute'):run(path,out)
    assert not out.exists()
