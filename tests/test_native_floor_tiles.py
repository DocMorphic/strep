"""Full floor populations and stable witnesses under bounded skin workspace."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_key_interval_model as model
from test_native_interval_track_selection import two_tracks,build


def legacy_floor(problem,worlds):
    planes=list(problem.policy['planes'].values());gaps=np.empty((len(planes),len(problem.geometry_ids)));witness=np.empty(gaps.shape,int)
    for start in range(0,len(problem.geometry_ids),32):
        stop=min(start+32,len(problem.geometry_ids));points=problem.points(worlds,problem.used,problem.geometry_ids[start:stop])
        for i,plane in enumerate(planes):
            distance=points@np.asarray(plane['normal_world'])-plane['offset_m'];ids=np.argmin(distance,axis=1)
            witness[i,start:stop]=problem.used[ids];gaps[i,start:stop]=distance[np.arange(len(ids)),ids]+problem.policy['limits']['penetration_m']
    return gaps.ravel(),witness


@pytest.mark.parametrize('vertices,influences',[(1029,4),(18056,8),(100000,8),(300000,16)])
def test_gather_budget_is_respected_without_dropping_vertices_or_influences(vertices,influences):
    frames,span=model.floor_tiles(vertices,influences)
    assert 1<=frames<=32 and 1<=span<=vertices
    assert frames*span*influences*3*4*8<=model.FLOOR_GATHER_BUDGET_BYTES


@pytest.mark.parametrize('args',[(True,8),(-1,8),(3,0),(3,8,1),(3,8,False)])
def test_invalid_or_incomplete_gather_budget_rejects(args):
    with pytest.raises(ValueError):model.floor_tiles(*args)


@pytest.mark.parametrize('budget',[4096,65536])
@pytest.mark.parametrize('random_weights',[False,True])
def test_complete_time_vertex_population_and_first_ties_match_old_floor(monkeypatch,budget,random_weights):
    rng=np.random.default_rng(973);problem=model.KeyIntervalModel.__new__(model.KeyIntervalModel)
    count=131;influences=8;problem.used=np.arange(count);problem.geometry_ids=np.r_[0,np.arange(2,42)]
    xyz=rng.normal(size=(count,3));xyz[7]=[0.,-20.,0.];xyz[129]=xyz[7]
    points=np.tile(np.c_[xyz,np.ones(count)][:,None,:],(1,influences,1))
    weights=rng.uniform(.05,.2,(count,influences)) if random_weights else np.full((count,influences),.125)
    weights[129]=weights[7]
    problem.skin=SimpleNamespace(nodes=np.zeros((count,influences),int),points=points,weights=weights)
    problem.actor=dict(placement=(np.array([.25,0.,-.125]),np.eye(3)))
    problem.policy=dict(limits=dict(penetration_m=.005),planes=dict(ground=dict(normal_world=[0.,1.,0.],offset_m=0.),side=dict(normal_world=[1.,0.,0.],offset_m=.1)))
    world=np.tile(np.eye(4),(42,1,1,1));world[:,0,1,3]=np.arange(42)/64
    expected=legacy_floor(problem,world);calls=[];original=problem.points
    def measured(w,ids,times):
        assert len(ids)*len(times)*influences*3*4*8<=budget
        calls.append((ids.copy(),times.copy()));return original(w,ids,times)
    problem.points=measured;monkeypatch.setattr(model,'FLOOR_GATHER_BUDGET_BYTES',budget)
    actual=problem.floor(world)
    np.testing.assert_array_equal(actual[0],expected[0]);np.testing.assert_array_equal(actual[1],expected[1])
    assert np.all(actual[1][0]==7)
    covered={int(t):[] for t in problem.geometry_ids}
    for ids,times in calls:
        for t in times:covered[int(t)].extend(ids.tolist())
    assert all(ids==problem.used.tolist() for ids in covered.values())


def test_real_native_export_floor_keeps_exact_gaps_and_witnesses_across_tiles(tmp_path,monkeypatch):
    paths=two_tracks(tmp_path);problem=build(paths,tmp_path/'model',[2]);value=problem.initial+.012
    # Use the actual native Float32 curve reader through the export, not merely
    # the preview transform implementation that is also used by the old oracle.
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    out=tmp_path/'actual.glb';index=problem.export(value,out);rig=RigAsset.load(out)
    sampler=NativeSupportSampler(rig.document,rig.binary,index)
    worlds=np.array([sampler.sample(float(t)) for t in problem.times]);expected=legacy_floor(problem,worlds)
    for budget in (4096,16384,model.FLOOR_GATHER_BUDGET_BYTES):
        monkeypatch.setattr(model,'FLOOR_GATHER_BUDGET_BYTES',budget);actual=problem.floor(worlds)
        np.testing.assert_array_equal(actual[0],expected[0]);np.testing.assert_array_equal(actual[1],expected[1])
