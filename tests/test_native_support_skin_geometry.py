"""Every surface/influence must survive support skin projection and derivatives."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_skin import NativeSupportSkin
from paired_approach_basis import BoundSkin
from native_leg_floor import foot_region
from contact_rate_path import ProjectedSkin
from test_native_support import fixture


def multiprimitive(tmp_path):
    _,rig,reader,_=fixture(tmp_path)
    rig=copy.deepcopy(rig)
    body=rig.primitives[0]
    second=dict(node=6,primitive=1,positions=np.array([[-.3,.18,0],[-.2,.18,.1],[-.1,.18,0]]),
        joints=np.array([[3,4,0,0,0,0,0,0],[3,4,0,0,0,0,0,0],[3,2,0,0,0,0,0,0]]),
        weights=np.array([[.7,.3,0,0,0,0,0,0],[0,1.,0,0,0,0,0,0],[.5,.5,0,0,0,0,0,0]]))
    third=dict(node=6,primitive=2,positions=np.array([[.4,1.3,0],[.6,1.3,0],[.5,1.4,0]]),
        joints=np.tile([5,0,0,0],(3,1)),weights=np.tile([1.,0,0,0],(3,1)))
    rig.primitives=[body,second,third]
    return rig,reader


def test_single_primitive_is_exact_legacy_skin_without_extra_normalization(tmp_path):
    _,rig,reader,_=fixture(tmp_path);old=BoundSkin(rig);new=NativeSupportSkin(rig)
    for name in ('nodes','weights','points'):np.testing.assert_array_equal(getattr(new,name),getattr(old,name))
    assert new.primitive_offsets==[0,3]
    np.testing.assert_array_equal(new.vertex_references,[[6,0,0],[6,0,1],[6,0,2]])


@pytest.mark.parametrize('axis',[[0,1,0],[1,0,0],[1/np.sqrt(3)]*3])
def test_all_surfaces_match_independent_rig_skinning_at_arbitrary_poses(tmp_path,axis):
    rig,reader=multiprimitive(tmp_path);skin=NativeSupportSkin(rig)
    worlds=np.array([reader.sample(t) for t in (0.,.853725,1.,1.371,2.)])
    for k,w in enumerate(worlds):
        w[3,:3,:3]=Rotation.from_rotvec([.13*k,-.04,.07]).as_matrix()
        w[4,:3,:3]=Rotation.from_rotvec([-.05,.02*k,.19]).as_matrix()
        w[5,:3,3]+=[.01*k,.02,-.03]
    expected=np.array([rig.vertices(w) for w in worlds]);ids=np.arange(len(expected[0]))
    actual=skin.evaluate(worlds,np.repeat(np.arange(len(worlds)),len(ids)),np.tile(ids,len(worlds))).reshape(expected.shape)
    np.testing.assert_allclose(actual,expected,atol=5e-15,rtol=0)
    projection=ProjectedSkin(skin,ids,axis,.12)
    np.testing.assert_allclose(projection.evaluate(worlds),expected@axis+.12,atol=5e-15,rtol=0)
    assert skin.primitive_offsets==[0,3,6,9] and skin.weights.shape==(9,8)
    np.testing.assert_array_equal(skin.weights[:3,4:],0.)
    np.testing.assert_array_equal(skin.vertex_references[3:6],[[6,1,0],[6,1,1],[6,1,2]])


def test_positive_ownership_keeps_other_surfaces_and_excludes_cross_shin_weights(tmp_path):
    rig,reader=multiprimitive(tmp_path);skin=NativeSupportSkin(rig)
    # Includes two lower foot/toe vertices on another material. A shin blend and
    # the head/hand-attached third surface cannot enter the foot-owned region.
    np.testing.assert_array_equal(foot_region(skin,rig.parents,3),[0,1,2,3,4])
    world=reader.sample(.853725);expected=rig.vertices(world)
    ids=foot_region(skin,rig.parents,3)
    lowest=ProjectedSkin(skin,ids,[0,1,0],0).evaluate(world[None]).min()
    assert abs(lowest-expected[ids,1].min())<1e-15
    assert lowest<expected[:3,1].min()


def test_inherited_derivative_matches_all_surface_reference_difference(tmp_path):
    rig,reader=multiprimitive(tmp_path);skin=NativeSupportSkin(rig)
    world=reader.sample(1.);rng=np.random.default_rng(9)
    jac=rng.normal(size=world.shape+(2,));jac[:,3]=0
    ids=np.array([0,3,4,5,7]);frames=np.zeros(len(ids),int)
    actual=skin.derivative(jac[None],frames,ids)
    for col in range(2):
        h=1e-5
        expected=(rig.vertices(world+h*jac[...,col])[ids]-rig.vertices(world-h*jac[...,col])[ids])/(2*h)
        np.testing.assert_allclose(actual[...,col],expected,atol=3e-11,rtol=0)


@pytest.mark.parametrize('primitives',[[],[dict(joints=None)]])
def test_unskinned_surfaces_are_not_silently_dropped(primitives):
    with pytest.raises(ValueError,match='all primitives'):NativeSupportSkin(SimpleNamespace(primitives=primitives))
