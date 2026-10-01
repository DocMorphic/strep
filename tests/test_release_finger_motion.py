import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_coupled_hand_finger_motion import setup
from release_finger_motion import ReleaseFingerMotion, ReleaseCoupledHandFingerMotion, expand_controls
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from paired_temporal_neighbor import rotation_channels


def build(actor=0):
    rig, arm, finger, a, f = setup(actor)
    expanded = ReleaseFingerMotion(finger, .8, 1.05)
    return rig, arm, finger, expanded, a, f


@pytest.mark.parametrize('actor', [0, 1])
def test_embedding_preserves_every_serialized_key_and_original_model(actor):
    rig, arm, finger, expanded, a, f = build(actor)
    before = finger.model.quaternions(f, quantize=True)
    after = expanded.model.quaternions(expanded.embed(f), quantize=True)
    for node in before: np.testing.assert_array_equal(before[node], after[node])
    np.testing.assert_array_equal(finger.world(f), expanded.world(expanded.embed(f)))
    assert finger.model.width == 1 and finger.size == 3
    assert expanded.size == 6


def test_release_control_changes_return_but_preserves_contact_and_approach(tmp_path):
    rig, arm, finger, expanded, a, f = build()
    controls = expanded.embed(f); controls.reshape(-1,2,3)[:,1] = [.005,-.003,.002]
    old = expanded.world(expanded.embed(f)); new = expanded.world(controls)
    np.testing.assert_array_equal(old[expanded.model.times <= .8], new[expanded.model.times <= .8])
    np.testing.assert_array_equal(old[expanded.model.times >= 1.3], new[expanded.model.times >= 1.3])
    assert np.max(abs(old-new)) > .0001
    model = ReleaseCoupledHandFingerMotion(arm,expanded)
    path = tmp_path/'combined.glb'; model.export(a,controls,path)
    doc,binary = read_glb(path); reader = AnimationSampler(doc,binary,0)
    np.testing.assert_allclose(model.evaluate(a,controls)[0], [reader.sample(t) for t in arm.model.times],atol=2e-12,rtol=0)
    original=rotation_channels(rig.document,rig.binary); written=rotation_channels(doc,binary)
    for node in original:
        np.testing.assert_array_equal(original[node][1],written[node][1])
        if node not in model.channels:np.testing.assert_array_equal(original[node][2],written[node][2])


def test_overlapping_envelopes_cannot_exceed_original_joint_budget(tmp_path):
    rig,arm,finger,expanded,a,f=build()
    controls=np.zeros(6);controls.reshape(2,3)[:,0]=finger.limits[0]
    assert np.min(expanded.margins(controls))<0
    with pytest.raises(ValueError,match='finger angle'):
        ReleaseCoupledHandFingerMotion(arm,expanded).export(a,controls,tmp_path/'bad.glb')


def test_adjacent_corrections_keep_five_degree_limit(tmp_path):
    rig,arm,finger,expanded,a,f=build()
    # Isolate the adjacent correction constraint from the per-joint cap.
    expanded.joint_limits[:]=np.deg2rad(45)
    controls=np.zeros(6);controls[3]=np.deg2rad(20)
    assert np.min(expanded.margins(controls))<0
    with pytest.raises(ValueError,match='adjacent'):expanded.export(controls,tmp_path/'bad.glb')


def test_embedding_combined_controls_keeps_actor_and_joint_order():
    original=np.arange(17,dtype=float)
    result=expand_controls(original,2,[6,9])
    np.testing.assert_array_equal(result[:2],original[:2])
    np.testing.assert_array_equal(result[2:14].reshape(2,2,3)[:,0],original[2:8].reshape(2,3))
    np.testing.assert_array_equal(result[14:].reshape(3,2,3)[:,0],original[8:].reshape(3,3))
    assert np.count_nonzero(result[2:].reshape(5,2,3)[:,1])==0


@pytest.mark.parametrize('contact,peak',[(.7,1.05),(.8,.8),(.8,1.3),(.8,float('nan'))])
def test_invalid_release_intervals_fail(contact,peak):
    _,_,finger,_,_,_=build()
    with pytest.raises(ValueError):ReleaseFingerMotion(finger,contact,peak)
