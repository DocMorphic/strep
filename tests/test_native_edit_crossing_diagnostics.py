"""Actual frozen/interpolated export support and full crossing diagnostics."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_edit_crossing_diagnostics import EditInfluence,sampling_keys,descendants,vertex_influence,diagnose,run
from native_stored_pair_job import Job
from native_support_clock import NativeSupportSampler
from test_native_stored_pair_job import prepare
from strep import read,sha256


def test_hierarchy_keeps_all_descendants_and_rejects_cycles():
    assert descendants([-1,0,1,0,2],1)==[1,2,4]
    assert descendants([-1,0,1,0,2],3)==[3]
    for parents,node in [([-1,2,1],1),([-1,9],0),([-2],0),([-1],True)]:
        with pytest.raises(ValueError):descendants(parents,node)


def test_every_positive_skin_slot_counts_without_dominant_weight_approximation():
    nodes=np.array([[1,2,3],[1,3,2]]);weights=np.array([[0.,1.,0.],[1e-300,0.,1.]])
    np.testing.assert_array_equal(vertex_influence(nodes,weights,[1]),[False,True])
    nodes=np.zeros((2,8),int);nodes[:,7]=2;weights=np.zeros((2,8));weights[:,0]=1.;weights[1,7]=1e-8
    np.testing.assert_array_equal(vertex_influence(nodes,weights,[2]),[False,True])
    with pytest.raises(ValueError):vertex_influence(nodes,-weights,[2])


def test_scalar_key_support_covers_actual_float32_endpoint_and_interpolation_behavior():
    clock=np.array([0.,.1,.2,1.],np.float32)
    times=[-1.,0.,1.,2.,.05,.15,.5]
    for t in clock:
        times.extend([float(t),np.nextafter(float(t),-np.inf),np.nextafter(float(t),np.inf)])
    for time in times:
        support=sampling_keys(clock,time)
        for key in range(len(clock)):
            payload=np.zeros((len(clock),3));payload[key,0]=1.
            actual=NativeSupportSampler.value('translation',clock,payload,'LINEAR',time)
            if actual[0]!=0:assert key in support
    for bad in (True,np.nan,'0',1j):
        with pytest.raises(ValueError):sampling_keys(clock,bad)


def test_protected_endpoints_and_frozen_partner_have_no_edit_influence(tmp_path):
    job=Job(prepare(tmp_path));influence=EditInfluence(job.edits)
    assert not influence.vertices('A',0.).any() and not influence.vertices('A',2.).any()
    assert influence.vertices('A',1.).all() and not influence.vertices('B',1.).any()
    for name,time in [('absent',1.),('A',True),('A',-1.),('A',3.)]:
        with pytest.raises(ValueError):influence.vertices(name,time)


def test_actual_exports_preserve_every_structurally_fixed_surface_vertex(tmp_path):
    job=Job(prepare(tmp_path));influence=EditInfluence(job.edits);actor=job.scene.actors['A']
    for value in (np.zeros(job.problem.size),np.full(job.problem.size,.2),np.full(job.problem.size,-.2)):
        p=tmp_path/('probe-'+str(value[0])+'.glb');job.edits.export('A',value,p)
        from rig_asset import RigAsset
        rig=RigAsset.load(p);reader=NativeSupportSampler(rig.document,rig.binary,actor['animation_index'])
        for time in (0.,2.):
            source=actor['rig'].vertices(actor['sampler'].sample(time));actual=rig.vertices(reader.sample(time));fixed=~influence.vertices('A',time)
            np.testing.assert_array_equal(source[fixed],actual[fixed])
        if value[0]:assert not np.array_equal(rig.vertices(reader.sample(1.)),actor['rig'].vertices(actor['sampler'].sample(1.)))


def test_full_job_distinguishes_fixed_crossings_and_keeps_all_inputs(tmp_path):
    path=prepare(tmp_path);job=Job(path);before=job.inputs.copy();out=tmp_path/'diagnostics'
    result=run(path,out)
    assert result['status']=='complete' and result['complete_crossing_records']>0
    assert result['edit_classes']['both_structurally_fixed']>0 and result['edit_classes']['one_potentially_editable']>0
    assert result['edit_classes']['both_potentially_editable']==0
    assert sum(result['edit_classes'].values())==sum(len(p['records']) for s in result['samples'] for p in s['pairs'])==result['complete_crossing_records']
    assert result['times_s']==job.geometry_times.tolist() and result['original_selected']
    assert not result['quality_approved'] and not result['release_approved']
    for p,h in before.items():assert sha256(p)==h
    for snapshot in result['input_snapshots'].values():assert sha256(out/snapshot['path'])==snapshot['sha256']
    with pytest.raises(ValueError,match='Fresh'):run(path,out)


@pytest.mark.parametrize('limit',[True,0,1000001])
def test_invalid_or_incomplete_record_budgets_never_return_a_subset(tmp_path,limit):
    job=Job(prepare(tmp_path))
    with pytest.raises(ValueError):diagnose(job,maximum_records=limit)


def test_exceeded_budget_retains_explicit_failure(tmp_path):
    path=prepare(tmp_path);out=tmp_path/'failed'
    with pytest.raises(ValueError,match='no subset'):run(path,out,maximum_records=1)
    assert read(out/'pipeline.json')['status']=='failed' and (out/'failure.json').is_file()
    assert not (out/'result.json').exists()
