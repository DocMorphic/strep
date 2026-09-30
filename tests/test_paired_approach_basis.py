import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_approach_basis import ApproachActor,BoundSkin
from test_paired_guarded_temporal import fixture


def test_approach_basis_preserves_event_release_and_unedited_boundaries():
    doc,binary=fixture();frames=np.arange(62,78.001,.25)
    actor=ApproachActor(doc,binary,doc,binary,['Arm'],frames)
    controls=np.array([.01,-.02,.03,-.02,.03,-.01,.02,-.01,.01])
    baseline=actor.world(np.zeros(actor.size));candidate=actor.world(controls)
    # Nominal frame 63 is slightly after its float32 glTF key time.
    # The key is exact; the tiny following interpolation belongs to the edit.
    locked=(frames<63)|(frames>=75)
    np.testing.assert_allclose(candidate[locked],baseline[locked],atol=1e-12,rtol=0)
    assert np.max(np.abs(candidate[~locked]-baseline[~locked]))>.001
    quaternions=actor.base.quaternions(actor.parameters(controls))
    for node,q in quaternions.items():
        np.testing.assert_array_equal(q[[63,75,76]],actor.base.channels[node][2][[63,75,76]])
    vectors=actor.vectors(controls)
    np.testing.assert_allclose(vectors[actor.free.index(66),0],controls[:3],atol=1e-12)


def test_skin_weights_and_derivatives_match_direct_transforms():
    rig=SimpleNamespace(joints=[0,1],inverse=np.tile(np.eye(4),(2,1,1)),primitives=[dict(
        positions=np.array([[1.,2.,3.],[4.,5.,6.]]),joints=np.array([[0,1],[1,0]]),weights=np.array([[.25,.75],[.8,.2]]))])
    skin=BoundSkin(rig);world=np.tile(np.eye(4),(2,2,1,1));world[0,1,0,3]=2;world[1,0,1,3]=3
    frames=np.array([0,1]);ids=np.array([0,1]);points=skin.evaluate(world,frames,ids)
    np.testing.assert_allclose(points,[[2.5,2,3],[4,5.6,6]])
    derivative=np.zeros(world.shape+(2,));derivative[0,1,0,3,0]=1;derivative[1,0,1,3,1]=1
    j=skin.derivative(derivative,frames,ids)
    expected=np.zeros((2,3,2));expected[0,0,0]=.75;expected[1,1,1]=.2
    np.testing.assert_allclose(j,expected)
    repeated_frames=np.tile(frames,150);repeated_ids=np.tile(ids,150)
    np.testing.assert_allclose(skin.evaluate(world,repeated_frames,repeated_ids),np.tile(points,(150,1)))
    np.testing.assert_allclose(skin.derivative(derivative,repeated_frames,repeated_ids),np.tile(expected,(150,1,1)))
