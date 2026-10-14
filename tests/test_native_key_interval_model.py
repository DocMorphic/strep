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
