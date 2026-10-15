"""Coupled interval proposals retain clocks, complete rows and decoded authority."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_key_contact_initializer import run as initialize
from native_key_interval_model import KeyIntervalModel
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import save,sha256
from test_native_key_contact_initializer import setup


@pytest.fixture(scope='module')
def producer(tmp_path_factory):
    folder=tmp_path_factory.mktemp('interval-model');_,_,contacts,policy,request=setup(folder)
    gp=folder/'geometry.json';rp=folder/'permissions.json';save(gp,policy);save(rp,request)
    initialize(contacts,gp,rp,folder/'producer');return folder/'producer'


def model(producer,keys=None):
    return KeyIntervalModel(producer,sha256(producer/'result.json'),sha256(producer/'request.json'),[3,4,5] if keys is None else keys)


@pytest.mark.parametrize('keys',[[0,1],[1,3],[4,3],[3,3],[True,2],[]])
def test_incomplete_or_frozen_interval_rejects(producer,keys):
    with pytest.raises(ValueError):model(producer,keys)


def test_batch_curve_matches_actual_new_animation_at_all_native_and_geometry_times(producer,tmp_path):
    problem=model(producer);value=problem.initial.copy();value+=np.tile([.012,-.009,.006],3)
    path=tmp_path/'actual.glb';index=problem.export(value,path);rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,index)
    actual=np.asarray([sampler.sample(float(t)) for t in problem.times]);preview=problem.worlds(value)
    np.testing.assert_allclose(preview,actual,atol=1e-12,rtol=0)
    assert np.array_equal(actual[:,problem.request['root_node']],problem.source_world[:,problem.request['root_node']])
    current=problem.controls(value);np.testing.assert_array_equal(current[np.setdiff1d(np.arange(len(problem.clock)),problem.active)],problem.seed[np.setdiff1d(np.arange(len(problem.clock)),problem.active)])
    rows=problem.rows(value,actual);np.testing.assert_array_equal(rows.caps[problem.edit_count:],np.concatenate([(c+1e-5).ravel() for c in problem.original_caps]))
    report=problem.displacement_diagnostics(value,actual)
    expected=max(np.linalg.norm(actual[t,node,:3,3]-problem.source_world[t,node,:3,3])
        for node in problem.rig.joints for t in range(len(problem.times)))
    assert report['maximum']['displacement_m']==pytest.approx(expected,abs=1e-15)
    assert report['checked_rows']==len(problem.times)*len(problem.rig.joints)


def test_sparse_model_keeps_complete_rate_and_plane_populations(producer):
    problem=model(producer,[3,4]);value=problem.initial;worlds=problem.worlds(value);original=problem.rows(value,worlds)
    system,jac,identity=problem.linearize(value,worlds,.02)
    floors=len(problem.geometry_times)*len(problem.policy['planes']);hard=problem.edit_count+problem.rate_count+floors
    assert identity['hard_rows']==hard and identity['original_rate_rows']==problem.rate_count and identity['complete_floor_rows']==floors
    assert len(system.caps)==problem.edit_count+2*problem.rate_count+2*floors and jac.shape==(3*len(system.caps),problem.size)
    np.testing.assert_array_equal(system.caps[hard:hard+problem.rate_count],original.caps[problem.edit_count:])
    np.testing.assert_array_equal(system.scales[hard:hard+problem.rate_count],original.scales[problem.edit_count:])
    assert np.all(system.residual()[:hard]<=0) and identity['original_caps_unchanged']
    gaps,witnesses=problem.floor(worlds);np.testing.assert_allclose(gaps,problem.witness_gaps(worlds,witnesses),atol=1e-14,rtol=0)
    with pytest.raises(ValueError,match='resource budget'):problem.linearize(value,worlds,.02,maximum_nonzeros=1)


def test_mutated_source_caps_cannot_become_the_restoration_reference(producer):
    problem=model(producer);problem.rate.caps[0][0,0]+=1
    with pytest.raises(ValueError,match='source-rate caps changed'):problem.rows(problem.initial)


def test_displacement_failure_witnesses_use_actual_joint_major_row_order(producer):
    problem=model(producer);worlds=problem.source_world.copy();count=len(problem.times)
    assert count!=len(problem.rig.joints)
    expected=[(0,1,.26),(len(problem.rig.joints)-1,count-2,.29)]
    for joint,stamp,distance in expected:worlds[stamp,problem.rig.joints[joint],0,3]+=distance
    before=problem.rows(problem.initial,worlds);saved=[a.copy() for a in (before.vectors,before.caps,before.scales)]
    report=problem.displacement_diagnostics(problem.initial,worlds)
    assert len(report['failures'])==2 and not report['displacement_conditions_pass']
    for row,(joint,stamp,distance) in zip(report['failures'],expected):
        assert row['node']==problem.rig.joints[joint] and row['time_index']==stamp
        assert row['time_s']==problem.times[stamp] and row['row']==count*len(problem.nodes)+joint*count+stamp
        assert row['displacement_m']==pytest.approx(distance,abs=1e-14) and row['limit_m']==problem.request['maximum_joint_displacement_m']
        # The old time-major interpretation points to a different physical pose.
        assert divmod(row['row']-report['row_start'],len(problem.rig.joints))!=(stamp,joint)
    assert report['maximum']==report['failures'][-1] and report['checked_rows']==count*len(problem.rig.joints)
    assert report['all_original_vectors_match'] and not report['native_export_reconstructed'] and not report['quality_approved']
    after=problem.rows(problem.initial,worlds)
    for a,b in zip(saved,(after.vectors,after.caps,after.scales)):np.testing.assert_array_equal(a,b)


def test_source_displacement_diagnostic_keeps_other_acceptance_separate(producer):
    problem=model(producer);report=problem.displacement_diagnostics(problem.initial,problem.source_world)
    assert report['displacement_conditions_pass'] and not report['failures'] and report['maximum']['displacement_m']==0.
    assert not report['engine_verified'] and not report['release_approved']


@pytest.mark.parametrize('fault',['shape','nan','infinite'])
def test_incomplete_or_nonfinite_displacement_observations_reject(producer,fault):
    problem=model(producer);worlds=problem.source_world.copy()
    if fault=='shape':worlds=worlds[:-1]
    elif fault=='nan':worlds[0,0,0,0]=np.nan
    else:worlds[0,0,0,0]=np.inf
    with pytest.raises(ValueError,match='Complete finite interval world'):problem.displacement_diagnostics(problem.initial,worlds)
