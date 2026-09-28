import copy
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from strep import ROOT
from rig_asset import RigAsset, array, parents_of
from retarget_rig import resolve_profile, transfer
from retarget_cesium import MAPPING
from gltf_tools import append_accessor


@pytest.fixture
def character():
    rig = RigAsset.load(ROOT / 'assets/characters/cesium-man/CesiumMan.glb')
    profile = dict(schema='strep-rig-profile-v1', reference_pose='default_nodes',
                   mapping={role: node for node, role in MAPPING.items()})
    return rig, profile


def native_fixture(rig, profile):
    mapping, _ = resolve_profile(rig, profile)
    names = list(mapping)
    neutral = rig.reference[list(mapping.values()), :3, 3] - rig.reference[mapping['Hips'], :3, 3]
    skeleton = SimpleNamespace(bone_order_names=names, neutral_joints=neutral)
    root = np.array([rig.reference[mapping['Hips'], :3, 3] + [t, 0, -t] for t in [0, .1, .3]])
    motion = dict(root_positions=root, global_rot_mats=np.tile(np.eye(3), (3, len(names), 1, 1)))
    return skeleton, motion, mapping


def test_reference_identity_mesh_and_finite_root_preserved(character):
    rig, profile = character
    skeleton, motion, mapping = native_fixture(rig, profile)
    matrices, _, quaternions, scale, _ = transfer(rig, motion, skeleton, mapping, np.zeros(3))
    assert len(matrices) == 3 and scale == pytest.approx(1)
    np.testing.assert_allclose(matrices[0], rig.reference, atol=1e-6)
    np.testing.assert_allclose(rig.vertices(matrices[0]), rig.vertices(rig.reference), atol=1e-6)
    np.testing.assert_allclose(matrices[:, mapping['Hips'], :3, 3], motion['root_positions'], atol=1e-7)
    for q in quaternions.values():
        assert np.all(np.sum(q[:-1] * q[1:], axis=1) >= 0)


def test_mapping_is_independent_of_node_numbers(character):
    rig, profile = character
    skeleton, motion, mapping = native_fixture(rig, profile)
    expected = transfer(rig, motion, skeleton, mapping, np.zeros(3))[0]
    document = copy.deepcopy(rig.document)
    order = np.random.default_rng(42).permutation(len(document['nodes'])).tolist()
    remap = {old: new for new, old in enumerate(order)}
    document['nodes'] = [document['nodes'][old] for old in order]
    for node in document['nodes']:
        if 'children' in node:
            node['children'] = [remap[n] for n in node['children']]
    for scene in document['scenes']:
        scene['nodes'] = [remap[n] for n in scene['nodes']]
    for skin in document['skins']:
        skin['joints'] = [remap[n] for n in skin['joints']]
        skin['skeleton'] = remap[skin['skeleton']]
    shuffled = RigAsset(document, rig.binary)
    mapped = {role: remap[node] for role, node in mapping.items()}
    actual = transfer(shuffled, motion, skeleton, mapped, np.zeros(3))[0]
    np.testing.assert_allclose(actual, expected[:, order], atol=1e-7)
    np.testing.assert_allclose(shuffled.vertices(actual[2]), rig.vertices(expected[2]), atol=1e-7)


@pytest.mark.parametrize('fault', ['duplicate', 'missing', 'unknown', 'wrong_chain', 'ambiguous', 'offset'])
def test_profile_rejects_invalid_mapping(character, fault):
    rig, profile = character
    if fault == 'duplicate': profile['mapping']['LeftHand'] = profile['mapping']['RightHand']
    if fault == 'missing': del profile['mapping']['LeftHand']
    if fault == 'unknown': profile['mapping']['LeftElbow'] = 18
    if fault == 'wrong_chain': profile['mapping']['LeftShin'], profile['mapping']['RightShin'] = profile['mapping']['RightShin'], profile['mapping']['LeftShin']
    if fault == 'ambiguous':
        rig.document['nodes'][3]['name'] = rig.document['nodes'][4]['name'] = 'duplicate'
        profile['mapping']['Hips'] = 'duplicate'
    if fault == 'offset': profile['world_offset_m'] = [0, float('nan'), 0]
    with pytest.raises(ValueError): resolve_profile(rig, profile)


@pytest.mark.parametrize('fault', ['cycle', 'multiple', 'out_of_bounds', 'scale', 'reflection', 'morph', 'external_joint'])
def test_unsupported_rigs_fail_explicitly(character, fault):
    rig, _ = character
    document = copy.deepcopy(rig.document)
    if fault == 'cycle': document['nodes'][21]['children'] = [0]
    if fault == 'multiple': document['nodes'][21]['children'] = [3]
    if fault == 'out_of_bounds': document['nodes'][21]['children'] = [100]
    if fault == 'scale': document['nodes'][3]['scale'] = [1, 2, 1]
    if fault == 'reflection': document['nodes'][3]['scale'] = [-1, 1, 1]
    if fault == 'morph': document['meshes'][0]['primitives'][0]['targets'] = [{'POSITION': 3}]
    if fault == 'external_joint': document['skins'][0]['joints'][0] = 999
    with pytest.raises(ValueError): RigAsset(document, rig.binary)


def test_normalized_interleaved_weights_and_bounds():
    binary = bytes([255, 0, 0, 0, 99, 99, 99, 99, 128, 127, 0, 0])
    doc = dict(bufferViews=[dict(buffer=0, byteLength=12, byteStride=8)],
               accessors=[dict(bufferView=0, componentType=5121, count=2, type='VEC4', normalized=True)])
    np.testing.assert_allclose(array(doc, binary, 0), [[1, 0, 0, 0], [128/255, 127/255, 0, 0]])
    doc['bufferViews'][0]['byteLength'] = 11
    with pytest.raises(ValueError, match='bounds'): array(doc, binary, 0)


def test_mesh_node_transform_is_ignored_for_skinning(character):
    rig, _ = character
    changed = copy.deepcopy(rig.document)
    changed['nodes'][2]['translation'] = [12, 5, -3]
    moved = RigAsset(changed, rig.binary)
    np.testing.assert_allclose(moved.vertices(moved.reference), rig.vertices(rig.reference), atol=1e-7)


def test_explicit_world_offset_and_missing_optional_toes(character):
    rig, profile = character
    for name in ('LeftToeBase', 'RightToeBase'):
        del profile['mapping'][name]
    skeleton, motion, mapping = native_fixture(rig, profile)
    offset = np.array([3, .2, -2])
    result = transfer(rig, motion, skeleton, mapping, offset)[0]
    np.testing.assert_allclose(result[:, mapping['Hips'], :3, 3], motion['root_positions'] + offset, atol=1e-7)
    # Unmapped toe nodes still follow their animated parent with original TRS.
    np.testing.assert_allclose(result[0, 11, :3, 3], rig.reference[11, :3, 3] + offset, atol=1e-6)


def test_multiple_primitives_and_eight_influences_are_not_dropped(character):
    rig, _ = character
    document, binary = copy.deepcopy(rig.document), bytearray(rig.binary)
    primitive = document['meshes'][0]['primitives'][0]
    attributes = primitive['attributes']
    half_weights = array(document, binary, attributes['WEIGHTS_0']) * .5
    weights = append_accessor(document, binary, half_weights, 'VEC4')
    attributes.update(WEIGHTS_0=weights, WEIGHTS_1=weights, JOINTS_1=attributes['JOINTS_0'])
    document['meshes'][0]['primitives'].append(copy.deepcopy(primitive))
    expanded = RigAsset(document, binary)
    expected = rig.vertices(rig.reference)
    np.testing.assert_allclose(expanded.vertices(expanded.reference), np.concatenate([expected, expected]), atol=1e-7)
    assert [p['influences'] for p in expanded.inventory()['primitives']] == [8, 8]


def test_changed_leg_proportions_preserve_target_lengths(character):
    rig, profile = character
    skeleton, motion, mapping = native_fixture(rig, profile)
    document = copy.deepcopy(rig.document)
    for role in ('LeftShin', 'LeftFoot', 'RightShin', 'RightFoot'):
        node = document['nodes'][mapping[role]]
        node['translation'] = (np.array(node['translation']) * 1.2).tolist()
    changed = RigAsset(document, rig.binary)
    matrices, _, _, scale, _ = transfer(changed, motion, skeleton, mapping, np.zeros(3))
    assert scale == pytest.approx(1.2)
    for role in ('LeftShin', 'LeftFoot', 'RightShin', 'RightFoot'):
        node = mapping[role]; parent = changed.parents[node]
        expected = np.linalg.norm(changed.reference[node, :3, 3] - changed.reference[parent, :3, 3])
        np.testing.assert_allclose(np.linalg.norm(matrices[:, node, :3, 3] - matrices[:, parent, :3, 3], axis=1), expected, atol=1e-7)
    np.testing.assert_allclose(matrices[:, mapping['Hips'], :3, 3], motion['root_positions'] * 1.2, atol=1e-7)


def test_missing_inverse_binds_use_identity(character):
    rig, _ = character
    document = copy.deepcopy(rig.document)
    del document['skins'][0]['inverseBindMatrices']
    result = RigAsset(document, rig.binary)
    np.testing.assert_array_equal(result.inverse, np.tile(np.eye(4), (len(result.joints), 1, 1)))


def test_truncated_glb_is_rejected_before_numpy(tmp_path):
    from rig_asset import read_asset
    path = tmp_path / 'broken.glb'; path.write_bytes(b'glTF')
    with pytest.raises(ValueError, match='header'): read_asset(path)


def test_anatomical_axes_override_direction_heuristic(character):
    from scipy.spatial.transform import Rotation
    from retarget_rig import calibration
    rig, profile = character
    skeleton, _, mapping = native_fixture(rig, profile)
    quaternion = Rotation.from_euler('y', 25, degrees=True).as_quat().tolist()
    profile['axis_alignment_xyzw'] = {'LeftFoot': quaternion}
    resolve_profile(rig, profile)
    corrected, _, diagnostics = calibration(rig, mapping, skeleton, profile['axis_alignment_xyzw'])
    node = mapping['LeftFoot']
    np.testing.assert_allclose(corrected[node], Rotation.from_quat(quaternion).as_matrix() @ rig.reference[node, :3, :3])
    assert diagnostics['axis_alignment_xyzw'] == profile['axis_alignment_xyzw']
    profile['axis_alignment_xyzw']['LeftFoot'] = [0, 0, 0, 0]
    with pytest.raises(ValueError, match='quaternion'): resolve_profile(rig, profile)
