"""Independent LBS oracles separate pose displacement from raw weight packing."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_native_skin_encoding import SkinEncodingComparison, TERMS
from native_scene_imported_skin import ImportedSceneSkin
from gltf_tools import append_accessor
from test_native_scene_engine import mock_actor
from test_native_support_skin_geometry import multiprimitive


def setup(tmp_path):
    rig, sampler = multiprimitive(tmp_path)
    data = bytearray(rig.binary)
    for p in rig.primitives[1:]:
        attributes = {}
        for slot in range(p['weights'].shape[1]//4):
            attributes['WEIGHTS_'+str(slot)] = append_accessor(
                rig.document, data, p['weights'][:, slot*4:(slot+1)*4], 'VEC4')
        rig.document['meshes'][0]['primitives'].append(dict(attributes=attributes))
    rig.binary = bytes(data)
    imported = ImportedSceneSkin(rig, mock_actor(rig, sampler, [0.]))
    return rig, sampler, imported, SkinEncodingComparison(rig, imported)


def slow_imported_skin(skin, world):
    result = []
    for nodes, points, weights in zip(skin.nodes, skin.points, skin.weights):
        vertex = np.zeros(3)
        for node, point, weight in zip(nodes, points, weights):
            vertex += (world[node] @ point)[:3]*weight
        result.append(vertex)
    return np.array(result)


def test_exact_pose_preserves_packed_weight_drift_with_reordered_bones_and_surfaces(tmp_path):
    rig, sampler, skin, comparison = setup(tmp_path)
    world = sampler.sample(.853725)[rig.joints]
    native, measured, terms = comparison.sample(world, world)
    np.testing.assert_allclose(native, rig.vertices(sampler.sample(.853725)), rtol=0, atol=1e-12)
    np.testing.assert_allclose(measured, slow_imported_skin(skin, world), rtol=0, atol=1e-12)
    np.testing.assert_array_equal(terms['pose'], np.zeros_like(native))
    assert np.linalg.norm(terms['weight_packing'], axis=1).max() > 1e-7
    assert np.any(comparison.imported_weight_sums < 1.)
    np.testing.assert_allclose(sum(terms[k] for k in TERMS), measured-native, rtol=0, atol=1e-12)


def test_known_common_translation_is_pose_effect_and_packing_remains_separate(tmp_path):
    rig, sampler, skin, comparison = setup(tmp_path)
    world = sampler.sample(.3)[rig.joints]
    changed = world.copy(); shift = np.array([.125, -.25, 200.])
    changed[:, :3, 3] += shift
    _, measured, terms = comparison.sample(world, changed)
    np.testing.assert_allclose(terms['pose'], comparison.source_weight_sums[:, None]*shift, rtol=0, atol=1e-12)
    np.testing.assert_allclose(measured, slow_imported_skin(skin, changed), rtol=0, atol=1e-12)
    _, _, baseline = comparison.sample(world, world)
    expected_drift = (comparison.imported_weight_sums-comparison.source_weight_sums)[:, None]*shift
    # Loader normalization is a distinct step; include it in this independent
    # total encoding oracle rather than attributing it to the packing term.
    old_encoding = baseline['total']-baseline['pose']
    new_encoding = terms['total']-terms['pose']
    np.testing.assert_allclose(new_encoding-old_encoding, expected_drift, rtol=0, atol=1e-12)
    assert np.linalg.norm(new_encoding, axis=1).max() > .001
    np.testing.assert_allclose(terms['telescoping_residual'], 0., rtol=0, atol=1e-12)


@pytest.mark.parametrize('fault', ['shape', 'nan'])
@pytest.mark.parametrize('side', [0, 1])
def test_invalid_native_or_observed_world_cannot_create_diagnostic(tmp_path, fault, side):
    rig, sampler, _, comparison = setup(tmp_path)
    worlds = [sampler.sample(0.)[rig.joints].copy() for _ in range(2)]
    if fault == 'shape': worlds[side] = worlds[side][:-1]
    else: worlds[side][0, 0, 0] = np.nan
    with pytest.raises(ValueError, match='Complete finite'):
        comparison.sample(*worlds)
