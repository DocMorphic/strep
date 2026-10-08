"""Weight association, immutable derivative payload and explicit failures."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from godot_weight_derivative import balanced_pairs, derivative
from rig_asset import RigAsset, array
from gltf_tools import write_glb
from native_scene_imported_skin import godot_normalize
from native_engine_contacts import packed_weights
from strep import sha256
from test_scene_import_measurements import fixture


@pytest.mark.parametrize('width', [4, 8])
def test_balancing_retains_influence_association_and_bounds_coefficient_error(width):
    rng = np.random.default_rng(718)
    weights = rng.random((400, width)); weights[0] = 0; weights[0, -1] = 1
    weights[1] = 1
    normalized = weights / weights.sum(axis=1, keepdims=True)
    joints = np.tile(np.arange(width, dtype=np.uint16), (len(weights), 1))
    ids, encoded = balanced_pairs(joints, weights)
    assert encoded.dtype == np.float32 and ids.dtype == joints.dtype
    restored = np.take_along_axis(encoded, np.argsort(ids, axis=1), axis=1)
    assert abs(restored - normalized).max() <= 1/65535 + 1e-7
    integers = np.rint(encoded.astype(float)*65535).astype(int)
    assert np.all(integers.sum(axis=1) == 65535)
    imported = packed_weights(godot_normalize(encoded))
    # Import simulation is a coefficient check, never an engine fidelity claim.
    np.testing.assert_array_equal(np.rint(imported*65535).astype(int), integers)
    assert np.max(abs(1-imported.sum(axis=1))) < 1e-7


def test_cyclic_pair_fallback_preserves_allocation_when_ascending_import_loses_mass():
    rng = np.random.default_rng(718); weights = rng.random((400, 8))
    joints = np.tile(np.arange(8, dtype=np.uint16), (len(weights), 1))
    ids, encoded = balanced_pairs(joints, weights)
    ascending = np.sort(encoded, axis=1)
    assert np.max(1-packed_weights(godot_normalize(ascending)).sum(axis=1)) > 7/65535
    assert np.any(np.diff(encoded, axis=1) < 0)
    assert np.max(abs(1-packed_weights(godot_normalize(encoded)).sum(axis=1))) < 1e-7


def test_unverified_pair_order_rejects_instead_of_relaxing_mass_bound(monkeypatch):
    import godot_weight_derivative
    monkeypatch.setattr(godot_weight_derivative, 'packed_weights', lambda a: np.zeros_like(a))
    with pytest.raises(ValueError, match='No checked cyclic'):
        balanced_pairs(np.array([[0, 1, 2, 3]], np.uint16), np.ones((1, 4)))


def test_fresh_derivative_retains_every_unrelated_payload_and_original_asset(tmp_path):
    fixture(tmp_path); source = tmp_path/'source.glb'; original = RigAsset.load(source)
    before = source.read_bytes(); output = tmp_path/'derived.glb'
    receipt = derivative(source, output, source_sha256=sha256(source)); loaded = RigAsset.load(output)
    assert source.read_bytes() == before and receipt['original_asset_preserved']
    assert not receipt['engine_playback_verified'] and not receipt['original_skin_fidelity_verified']
    assert not receipt['release_approved'] and Path(str(output)+'.weights.json').exists()
    assert loaded.document == original.document
    attrs = original.document['meshes'][0]['primitives'][0]['attributes']
    affected = {n for k,n in attrs.items() if k.startswith(('JOINTS_', 'WEIGHTS_'))}
    for number in range(len(original.document['accessors'])):
        if number not in affected:
            np.testing.assert_array_equal(array(original.document, original.binary, number),
                                          array(loaded.document, loaded.binary, number))
    for left, right in zip(original.primitives, loaded.primitives):
        for a, b, w, z in zip(left['joints'], right['joints'], left['weights'], right['weights']):
            for joint in set(a):
                assert abs(w[a==joint].sum()-z[b==joint].sum()) < 2/65535


@pytest.mark.parametrize('fault', ['digest', 'existing', 'bounds', 'alias'])
def test_derivative_rejects_unsafe_or_ambiguous_rewrites(tmp_path, fault):
    fixture(tmp_path); source = tmp_path/'source.glb'; output = tmp_path/'derived.glb'
    if fault in ('bounds', 'alias'):
        rig = RigAsset.load(source); d = copy.deepcopy(rig.document)
        attrs = d['meshes'][0]['primitives'][0]['attributes']
        if fault == 'bounds': d['accessors'][attrs['WEIGHTS_0']]['min'] = [0, 0, 0, 0]
        else:
            item = copy.deepcopy(d['accessors'][attrs['WEIGHTS_0']]);d['accessors'].append(item)
        write_glb(source, d, rig.binary)
    digest = 'incorrect' if fault == 'digest' else sha256(source)
    if fault == 'existing': output.write_bytes(b'existing')
    with pytest.raises(ValueError): derivative(source, output, source_sha256=digest)
    if fault != 'existing': assert not output.exists()


@pytest.mark.parametrize('weights', [np.zeros((2,4)), np.ones((1,3)), np.array([[np.nan,0,0,1]]), np.array([[-1,0,0,2]])])
def test_invalid_pairs_reject(weights):
    with pytest.raises(ValueError): balanced_pairs(np.zeros_like(weights, dtype=np.uint16), weights)
