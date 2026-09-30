import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_timed_rotation_edit import fixture
from gltf_tools import hierarchy, read_glb
from rig_clip_import import AnimationSampler
from paired_temporal_neighbor import rotation_channels
from native_finger_motion import NativeFingerMotion, palm_geometry


def rig_fixture():
    doc, binary = fixture()
    doc['animations'][0]['channels'].append(dict(sampler=0, target=dict(node=2, path='rotation')))
    return SimpleNamespace(document=doc, binary=binary, joints=[0,1,2,3], parents=hierarchy(doc))


def test_native_finger_edit_preserves_body_clocks_and_outside_window(tmp_path):
    rig = rig_fixture(); times = np.unique(np.r_[np.linspace(0, 1.5, 101), .61])
    model = NativeFingerMotion(rig, 1, [2], [5.], times, [.1, 1.3], .61)
    control = np.array([.03, -.01, .005]); world = model.world(control)
    assert model.body == [0,1,3]
    np.testing.assert_allclose(world[:,model.body], model.model.source_world[:,model.body], rtol=0, atol=1e-12)
    assert np.max(abs(world-model.model.source_world)) > .001
    path = tmp_path/'finger.glb'; model.export(control, path)
    document, binary = read_glb(path); reader = AnimationSampler(document, binary, 0)
    decoded = np.array([reader.sample(t) for t in times])
    np.testing.assert_allclose(world, decoded, rtol=0, atol=2e-10)
    source = AnimationSampler(rig.document, rig.binary, 0)
    original = np.array([source.sample(t) for t in times])
    np.testing.assert_array_equal(decoded[:,model.body], original[:,model.body])
    outside = (times <= .1) | (times >= 1.3)
    np.testing.assert_array_equal(decoded[outside], original[outside])
    before, after = rotation_channels(rig.document, rig.binary), rotation_channels(document, binary)
    for node in before:
        np.testing.assert_array_equal(before[node][1], after[node][1])
        if node != 2: np.testing.assert_array_equal(before[node][2], after[node][2])


def test_zero_finger_controls_reproduce_source_exactly():
    model = NativeFingerMotion(rig_fixture(), 1, [2], [5.], [0., .5, 1.5], [.1, 1.3], .7)
    np.testing.assert_array_equal(model.world(np.zeros(3)), model.model.source_world)


def test_narrow_envelope_reduces_limit_to_keep_native_correction_steps():
    model = NativeFingerMotion(rig_fixture(), 1, [2], [45.], [0., .5, 1.5], [.25, .7], .5)
    assert model.limits[0] <= np.deg2rad(5.000001)


@pytest.mark.parametrize('nodes,limits,peak', [([1],[5.],.6), ([3],[5.],.6), ([2,2],[5.,5.],.6), ([2],[-1.],.6), ([2],[5.],1.3)])
def test_invalid_finger_requests_fail(nodes, limits, peak):
    with pytest.raises(ValueError): NativeFingerMotion(rig_fixture(), 1, nodes, limits, [0.,1.5], [.1,1.3], peak)


def test_export_enforces_per_finger_budget(tmp_path):
    model = NativeFingerMotion(rig_fixture(), 1, [2], [5.], [0.,1.5], [.1,1.3], .6)
    with pytest.raises(ValueError, match='limits'): model.export([.2,0,0], tmp_path/'bad.glb')


def test_palm_geometry_tracks_skin_deformation_even_with_fixed_wrist():
    points = np.array([[0.,0,0],[1,0,0],[0,1,0]])
    point, normal = palm_geometry(points, [[0,1,2]], 0)
    np.testing.assert_array_equal(point,[0,0,0]); np.testing.assert_array_equal(normal,[0,0,1])
    points[0,2]=.1
    changed, tilted = palm_geometry(points, [[0,1,2]], 0)
    assert np.linalg.norm(changed-point) == pytest.approx(.1)
    assert np.linalg.norm(tilted-normal) > .1
    with pytest.raises(ValueError, match='Degenerate'): palm_geometry(np.zeros((3,3)), [[0,1,2]], 0)


def test_diagnostic_groups_keep_other_constraints_and_saved_model_unchanged():
    from diagnose_finger_proposal import variant
    model = dict(point=np.zeros(2), base=dict(vectors=np.arange(21.).reshape(7,3), caps=np.arange(7.)+1,
        scales=np.ones(7), margins=np.array([.2,.3]), depths=np.array([.01,.02])),
        jacobian=dict(vectors=np.arange(42.).reshape(7,3,2), margins=np.ones((2,2)), depths=np.ones((2,2))))
    for omitted, selection in [('motion',slice(-5,None)), ('palm',slice(None,-5))]:
        changed = variant(model, omitted)
        np.testing.assert_array_equal(changed['base']['vectors'], model['base']['vectors'][selection])
        np.testing.assert_array_equal(changed['jacobian']['vectors'], model['jacobian']['vectors'][selection])
        np.testing.assert_array_equal(changed['base']['margins'], model['base']['margins'])
        np.testing.assert_array_equal(changed['base']['depths'], model['base']['depths'])
    changed = variant(model, 'old_witnesses')
    np.testing.assert_array_equal(changed['base']['vectors'], model['base']['vectors'])
    np.testing.assert_array_equal(changed['base']['margins'], [1,1])
    np.testing.assert_array_equal(changed['jacobian']['margins'], 0.)
    np.testing.assert_array_equal(model['base']['margins'], [.2,.3])
    np.testing.assert_array_equal(model['jacobian']['margins'], 1.)


def test_unknown_diagnostic_group_cannot_drop_constraints():
    from diagnose_finger_proposal import variant
    with pytest.raises(ValueError, match='Unknown'): variant({}, 'all')
