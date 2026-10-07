"""Actual pinned offline orchestration, rejection and immutable failure records."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_pair_clearance_job as module
from native_pair_clearance_job import run,SCHEMA
from native_stored_pair_job import Job
from native_scene_norms import rows
from native_observation_archive import verify
from test_native_stored_pair_job import prepare
from strep import read,save,sha256


def request(tmp_path):
    path=prepare(tmp_path);guide=tmp_path/'guide.json'
    save(guide,dict(actor_a='A',vertices_a=[0,1],actor_b='B',vertices_b=[0,2,3],
                   time_s=1.,axis_world=[-1.,0.,0.],clearance_m=.0001,scale_m=.03))
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    spec=dict(schema=SCHEMA,job=pin(path),guide=pin(guide),families=['original-norms','event-key-preserved'],event_times_s=[0.])
    target=tmp_path/'request.json';save(target,spec);return target


def test_actual_pipeline_retains_complete_model_and_every_requested_export_without_promotion(tmp_path):
    path=request(tmp_path);job=Job(read(path)['job']['path']);before={**job.inputs,str(path):sha256(path),read(path)['guide']['path']:read(path)['guide']['sha256']}
    out=tmp_path/'output';result=run(path,out)
    assert result['status']=='complete' and result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert read(out/'pipeline.json')['status']=='complete'
    assert result['controls']==job.problem.size==3 and result['records']
    with np.load(out/'system.npz',allow_pickle=False) as z:
        _,worlds=job.problem.decoded(job.files,job.value);native=rows(job.problem,job.value,worlds)
        for k in ('vectors','caps','scales'):np.testing.assert_array_equal(z[k],getattr(native,k))
        assert len(z['guide_residual'])==6 and z['parameter_rows'].shape==(3,3)
    identity=read(out/'model.json');assert len(list((out/'stencils').glob('*.npz')))==identity['column_proxy_evaluations']
    solvers={f:read(out/(f+'-solver.json')) for f in read(path)['families']}
    expected=[f+f'-fraction-{i:02d}' for f,s in solvers.items() if s['delta'] is not None for i in range(len(job.request['settings']['fractions']))]
    assert [v['label'] for v in result['records']]==expected
    for record in result['records']:
        folder=out/record['label'];assert read(folder/'result.json')==record
        with np.load(folder/'observations.npz',allow_pickle=False) as z:
            value=z['controls'].copy();actual,worlds=job.problem.decoded({'A':folder/'A.glb'},value)
            native=rows(job.problem,value,worlds);np.testing.assert_array_equal(actual,z['residual'])
            for k in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(native,k),z[k])
            for n,w in worlds.items():np.testing.assert_array_equal(w,z[n+'_worlds'])
        assert record['native_conditions_pass'] is bool(np.all(actual<=0) and np.all(native.residual()<=0))
        assert record['reference_bounds']==job.reference_bounds({'A':folder/'A.glb'},worlds)
        assert not record['retained'] and not record['quality_approved'] and not record['release_approved']
        if record['full_geometry_assessed']:verify(folder/'geometry-observations.npz')
    assert sum(v['full_geometry_assessed'] for v in result['records'])==(result['full_geometry_selection'] is not None)
    for name,h in before.items():assert sha256(name)==h
    for name,h in result['files_sha256'].items():assert sha256(out/name)==h
    with pytest.raises(ValueError,match='Fresh'):run(path,out)


@pytest.mark.parametrize('fault',['schema','extra','pin','families-empty','family','duplicate-family','event-required','event-unwanted','event-bool','event-off-clock','event-duplicate','immutable-parent'])
def test_bad_pins_variants_or_event_requests_reject_before_output(tmp_path,fault):
    path=request(tmp_path);r=read(path);out=tmp_path/'output'
    if fault=='schema':r['schema']='other'
    elif fault=='extra':r['extra']=True
    elif fault=='pin':r['guide']['sha256']='a'*64
    elif fault=='families-empty':r['families']=[]
    elif fault=='family':r['families']=['unknown']
    elif fault=='duplicate-family':r['families']=['original-norms']*2
    elif fault=='event-required':r['event_times_s']=[]
    elif fault=='event-unwanted':r['families']=['original-norms']
    elif fault=='event-bool':r['event_times_s']=[True]
    elif fault=='event-off-clock':r['event_times_s']=[.1234567]
    elif fault=='event-duplicate':r['event_times_s']=[0.,0.]
    elif fault=='immutable-parent':save(tmp_path/'result.json',dict(status='retained original'))
    save(path,r)
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


def test_invalid_guide_retains_failure_and_never_writes_completed_result(tmp_path):
    path=request(tmp_path);r=read(path);guide=Path(r['guide']['path']);g=read(guide);g['vertices_a']=[True];save(guide,g)
    r['guide']['sha256']=sha256(guide);save(path,r);out=tmp_path/'output'
    with pytest.raises(ValueError,match='vertex IDs'):run(path,out)
    assert read(out/'failure.json')['status']=='failed' and read(out/'pipeline.json')['status']=='failed'
    assert not (out/'result.json').exists() and read(out/'guide.json')==g


def test_input_change_during_solver_is_rejected_with_original_snapshots_retained(tmp_path,monkeypatch):
    path=request(tmp_path);r=read(path);guide=Path(r['guide']['path']);original=guide.read_bytes()
    def mutate(*a,**kw):
        guide.write_bytes(original+b' ');return None,dict(status='controlled-no-candidate')
    monkeypatch.setattr(module,'direction',mutate);out=tmp_path/'output'
    with pytest.raises(ValueError,match='input bytes changed'):run(path,out)
    assert read(out/'failure.json')['status']=='failed' and not (out/'result.json').exists()
    assert read(out/'guide.json')==read(guide) and read(out/'request.json')['guide']['sha256']==r['guide']['sha256']
