import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_decoded_motion_edges import rig_fixture
from independent_hand_motion import IndependentHandMotion
from native_finger_motion import NativeFingerMotion
from coupled_hand_finger_motion import CoupledHandFingerMotion
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from gltf_tools import read_glb


def setup(actor=0):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    rig.document['animations'][0]['channels'].append(dict(sampler=2,target=dict(node=4,path='rotation')))
    times=np.arange(241)/120
    arm=IndependentHandMotion(rig,[1,2,3],clock[3:8].astype(float),times,[],np.eye(3),actor)
    finger=NativeFingerMotion(rig,3,[4],[5.],times,[.1,1.3],.8)
    rows=np.zeros((3,14));rows[:,3*actor:3*actor+3]=[.001,-.002,.003]
    rows[:,6+actor]=[1.,-2.,.5];rows[:,8+3*actor:11+3*actor]=[.5,-.6,.3]
    return rig,arm,finger,rows.ravel(),np.array([.02,-.01,.005])


@pytest.mark.parametrize('actor',[0,1])
def test_coupled_export_matches_sequential_editing_and_preserves_other_channels(actor,tmp_path):
    rig,arm,finger,a,f=setup(actor);model=CoupledHandFingerMotion(arm,finger)
    path=tmp_path/'coupled.glb';model.export(a,f,path);doc,binary=read_glb(path)
    reader=AnimationSampler(doc,binary,0);decoded=np.array([reader.sample(t) for t in arm.model.times])
    np.testing.assert_allclose(model.evaluate(a,f)[0],decoded,atol=2e-12,rtol=0)
    # Independently compose serialized arm edit then serialized finger edit.
    intermediate=tmp_path/'arm.glb';arm.export_vector(a,intermediate);ad,ab=read_glb(intermediate)
    donor=SimpleNamespace(document=ad,binary=ab,joints=rig.joints,parents=rig.parents)
    donor_finger=NativeFingerMotion(donor,3,[4],[5.],arm.model.times,[.1,1.3],.8)
    sequential=tmp_path/'sequential.glb';donor_finger.export(f,sequential);sd,sb=read_glb(sequential)
    second=AnimationSampler(sd,sb,0)
    np.testing.assert_array_equal(decoded,np.array([second.sample(t) for t in arm.model.times]))
    # Different arm baseline on the finger donor does not rebase original arms.
    donated=CoupledHandFingerMotion(arm,donor_finger)
    np.testing.assert_array_equal(donated.evaluate(a,f)[0],model.evaluate(a,f)[0])
    before,after=rotation_channels(rig.document,rig.binary),rotation_channels(doc,binary)
    for node in before:
        np.testing.assert_array_equal(before[node][1],after[node][1])
        if node not in [1,2,3,4]:np.testing.assert_array_equal(before[node][2],after[node][2])
    source=AnimationSampler(rig.document,rig.binary,0)
    for t in [0.,.1,1.3,2.]:np.testing.assert_array_equal(reader.sample(t),source.sample(t))
    assert not np.array_equal(decoded[:,4],arm.evaluate_vector(a)[0][:,4])


def test_zero_controls_and_single_editor_limits_are_retained(tmp_path):
    rig,arm,finger,a,f=setup();model=CoupledHandFingerMotion(arm,finger)
    np.testing.assert_array_equal(model.evaluate(np.zeros_like(a),np.zeros_like(f))[0],arm.model.model.source_world)
    np.testing.assert_allclose(model.evaluate(a,np.zeros_like(f))[0],arm.evaluate_vector(a)[0],atol=2e-12,rtol=0)
    np.testing.assert_allclose(model.evaluate(np.zeros_like(a),f)[0],finger.world(f),atol=2e-12,rtol=0)
    with pytest.raises(ValueError,match='per-finger'):model.export(a,[.2,0,0],tmp_path/'invalid.glb')
    a.reshape(-1,14)[:,8]=60.
    with pytest.raises(ValueError,match='arm edit budget'):model.export(a,np.zeros_like(f),tmp_path/'invalid.glb')


def test_smooth_proposal_is_distinct_from_serialized_acceptance():
    rig,arm,finger,a,f=setup();model=CoupledHandFingerMotion(arm,finger)
    exact,_=model.quaternions(a,f,quantize=True);smooth,_=model.quaternions(a,f,quantize=False)
    assert any(not np.array_equal(exact[n],smooth[n]) for n in exact)
    assert all(np.array_equal(q,q.astype(np.float32).astype(float)) for q in exact.values())


def test_finger_reference_cannot_be_silently_rebased(tmp_path):
    rig,arm,finger,a,f=setup();path=tmp_path/'finger.glb';finger.export(f,path)
    doc,binary=read_glb(path);donor=SimpleNamespace(document=doc,binary=binary,joints=rig.joints,parents=rig.parents)
    rebased=NativeFingerMotion(donor,3,[4],[5.],arm.model.times,[.1,1.3],.8)
    with pytest.raises(AssertionError):CoupledHandFingerMotion(arm,rebased)


def test_clock_and_finger_ancestry_must_match():
    rig,arm,finger,a,f=setup()
    different=NativeFingerMotion(rig,3,[4],[5.],[0.,1.,2.],[.1,1.3],.8)
    with pytest.raises(ValueError,match='clocks'):CoupledHandFingerMotion(arm,different)
    arm.model.chain=[1,2,6]
    with pytest.raises(ValueError,match='descend'):CoupledHandFingerMotion(arm,finger)
