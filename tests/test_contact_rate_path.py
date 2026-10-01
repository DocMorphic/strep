import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_rate_path import ContactRatePath, ProjectedSkin
from test_native_wrist_retraction import fixture
from paired_approach_basis import BoundSkin
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def model(event=1.4):
    doc, binary = fixture(); times = np.unique(np.r_[np.linspace(0, 3, 121), event])
    return ContactRatePath(doc, binary, ['Upper', 'Elbow', 'Wrist'], times, [0., 3.], [], event, (doc, binary))


def test_contact_is_retained_with_free_noncommuting_endpoints(tmp_path):
    m = model(); x = np.linspace(-.03, .04, m.size); event = np.searchsorted(m.model.times, 1.4)
    before = m.world(np.zeros(m.size)); changed = m.world(x)
    np.testing.assert_allclose(changed[event], before[event], rtol=0, atol=1e-12)
    assert np.abs(changed[np.searchsorted(m.model.times, 1.5)]-before[np.searchsorted(m.model.times, 1.5)]).max() > .001
    p = tmp_path/'candidate.glb'; m.export(x, p); doc, binary = read_glb(p); reader = AnimationSampler(doc, binary, 0)
    np.testing.assert_allclose(reader.sample(1.4), before[event], rtol=0, atol=1e-7)
    np.testing.assert_allclose(m.world(x, True), np.array([reader.sample(t) for t in m.model.times]), rtol=0, atol=1e-12)
    for e in m.model.entries:
        q = m.quaternions(x, True)[e['node']]; frozen = np.ones(len(q), bool); frozen[e['ids']] = False
        np.testing.assert_array_equal(q[frozen], e['source'][frozen])


def test_zero_is_exact_and_native_contact_is_rejected():
    m = model()
    for e in m.model.entries: np.testing.assert_array_equal(m.quaternions(np.zeros(m.size), True)[e['node']], e['source'])
    with pytest.raises(ValueError, match='inter-key'): model(float(np.float32(1.2)))
    x = np.zeros(m.size); x[9] = np.pi
    with pytest.raises(ValueError, match='Ambiguous'): m.quaternions(x)


def test_projected_skin_uses_all_eight_weights_and_matches_direct_skinning():
    rng = np.random.default_rng(24); n = 9
    skin = SimpleNamespace(nodes=rng.integers(0, 3, (n, 8)), weights=rng.uniform(.1, 1, (n, 8)), points=rng.normal(size=(n, 8, 4)))
    skin.weights /= skin.weights.sum(axis=1)[:, None]; skin.points[:, :, 3] = 1
    worlds = np.tile(np.eye(4), (5, 3, 1, 1)); worlds[:, :, :3, :3] = Rotation.random(15, random_state=rng).as_matrix().reshape(5, 3, 3, 3)
    worlds[:, :, :3, 3] = rng.normal(size=(5, 3, 3)); ids = np.array([1, 3, 8]); axis = np.array([1., 2, -3]); axis /= np.linalg.norm(axis)
    projection = ProjectedSkin(skin, ids, axis, .17)
    points = BoundSkin.evaluate(skin, worlds, np.repeat(np.arange(5), len(ids)), np.tile(ids, 5)).reshape(5, len(ids), 3)
    np.testing.assert_allclose(projection.evaluate(worlds), points@axis+.17, rtol=0, atol=1e-14)
    with pytest.raises(ValueError): ProjectedSkin(skin, [1, 1], axis)
