import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from strep import ROOT,read
from rig_asset import RigAsset
from target_rig_contact import baseline
from build_soma_preview import ASSET
from paired_hand_fit import HandActor,PairFitter,envelope


def setup():
    folder=ROOT/'reports/breadth-partners-v2'
    scene=read(folder/'partner_interaction-left-high-five-seed-1301/scene.json')['scene']
    skin=dict(np.load(ASSET,allow_pickle=False));actors=[]
    for name in ['A','B']:
        entry=scene['actors'][name];rig=RigAsset.load(folder/entry['preview_glb']);_,local=baseline(rig,scene['frame_count'])
        actors.append(HandActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],entry['transform']))
    return actors,scene


def test_coupled_surface_frame_derivatives_include_both_actors():
    actors,_=setup();fitter=PairFitter(*actors,event=75)
    x=np.random.default_rng(117).normal(size=len(fitter.bounds))*.02
    residual,jac=fitter.objective_pair(x)
    for col in range(len(x)):
        d=np.eye(len(x))[col]*1e-7
        numeric=(fitter.objective_pair(x+d)[0]-fitter.objective_pair(x-d)[0])/2e-7
        np.testing.assert_allclose(jac[:,col],numeric,atol=2e-5,rtol=2e-4)
    assert np.linalg.norm(jac[:3,:12])>1 and np.linalg.norm(jac[:3,12:])>1
    for actor,values in zip(actors,[x[:12],x[12:]]):
        p,normal,tangent,*_=actor.frame_pair(75,values)
        independent=actor.rig.vertices(actor.pose(75,values))[actor.vertices[actor.palm]]
        np.testing.assert_allclose(p,actor.rotation@independent+actor.translation,atol=1e-10)
        assert abs(normal@tangent)<1e-10


def test_event_envelope_preserves_context_and_bounded_solution():
    actors,_=setup();fitter=PairFitter(*actors,event=75)
    values,result=fitter.solve()
    assert result['final_squared_residual']<=result['initial_squared_residual']
    assert np.all(np.abs(values)<=fitter.bounds+1e-12)
    assert np.count_nonzero(fitter.envelope[:61])==0 and np.count_nonzero(fitter.envelope[90:])==0
    for actor,x in zip(actors,[values[:12],values[12:]]):
        delta=fitter.envelope[:,None,None]*x.reshape(1,-1,3)
        assert np.linalg.norm(delta,axis=2).max()<=actor.limits.max()+1e-9
        assert np.linalg.norm(np.diff(delta,axis=0),axis=2).max()<=np.radians(5)+1e-9
        np.testing.assert_array_equal(actor.pose(0,delta[0].ravel()),actor.pose(0,np.zeros(actor.dim)))
    assert result['quality_approved'] is False


def test_invalid_event_context():
    with pytest.raises(ValueError):envelope(150,3,15)
