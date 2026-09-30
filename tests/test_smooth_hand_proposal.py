import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_decoded_motion_edges import rig_fixture
from independent_hand_motion import IndependentHandMotion, actor_controls
from smooth_hand_proposal import SmoothIndependentHandProposal, proposal_type
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


@pytest.mark.parametrize('actor', [0, 1])
@pytest.mark.parametrize('hand_only', [False, True])
def test_proposal_rounds_to_actual_native_keys_and_keeps_frozen_motion(actor, hand_only, tmp_path):
    rig, clock = rig_fixture(); rig.document['skins'] = [dict(joints=rig.joints)]
    native = clock[2:7].astype(float); times = np.arange(241)/120
    placement = Rotation.from_euler('xyz', [13, -37, 8], degrees=True).as_matrix()
    args = (rig, [1, 2, 3], native, times, [], placement, actor)
    exact = IndependentHandMotion(*args); proposal = SmoothIndependentHandProposal(*args)
    rows = np.array([.3, 1., .6])[:, None]*np.array([.001, -.002, .003, .004, .001, -.002, 1., -2., .3, -.7, .2, -.4, .8, -.6])
    if hand_only: rows[:, :8] = 0
    control = rows.ravel(); mapped = actor_controls(control, 3, actor)
    rounded, _ = exact.model.quaternions_vector(mapped)
    smooth, _ = proposal.model.quaternions_vector(mapped)
    for node in rounded:
        np.testing.assert_array_equal(smooth[node].astype(np.float32), rounded[node])
    for entry in exact.model.model.entries:
        frozen = np.ones(len(entry['source']), bool); frozen[entry['ids']] = False
        np.testing.assert_array_equal(smooth[entry['node']][frozen], entry['source'][frozen])
    world, _ = proposal.evaluate_vector(control)
    original, _ = exact.evaluate_vector(np.zeros(42))
    outside = (times <= native[0]) | (times >= native[-1])
    # Stored frozen keys are exact above. Rebuilding the same transforms through
    # batched FK versus the cached source can differ by a few float64 ULPs.
    np.testing.assert_allclose(world[outside], original[outside], atol=1e-14, rtol=0)
    np.testing.assert_array_equal(proposal.evaluate_vector(np.zeros(42))[0], original)
    path = tmp_path/'actual.glb'; exact.export_vector(control, path)
    document, binary = read_glb(path); reader = AnimationSampler(document, binary, 0)
    decoded = np.array([reader.sample(t) for t in times])
    error = float(np.max(np.abs(world-decoded)))
    assert 0 < error < 5e-7
    np.testing.assert_allclose(exact.evaluate_vector(control)[0], decoded, atol=2e-12, rtol=0)
    with pytest.raises(ValueError, match='not an export'):
        proposal.export_vector(control, tmp_path/'unapproved.glb')
    assert not (tmp_path/'unapproved.glb').exists()


def test_proposal_layout_is_explicit():
    assert proposal_type('independent-wrists-v1') is SmoothIndependentHandProposal
    with pytest.raises(ValueError): proposal_type('unknown')
