"""Real tiny GLB skin/topology/contact checks without model or character payloads."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor, write_glb, global_matrices
from rig_asset import RigAsset
from native_support_skin import NativeSupportSkin
from native_scene_contacts import references, SceneContacts
from strep import save, sha256, read
import rig_material_patch as material


def unsigned(doc, binary, values, kind):
    values = np.asarray(values, dtype='<u2')
    while len(binary) % 4:
        binary.append(0)
    view = len(doc['bufferViews']); accessor = len(doc['accessors'])
    doc['bufferViews'].append(dict(buffer=0, byteOffset=len(binary), byteLength=values.nbytes))
    doc['accessors'].append(dict(bufferView=view, componentType=5123, count=len(values), type=kind))
    binary.extend(values.tobytes()); return accessor


def fixture(folder, *, animated=False):
    folder.mkdir(parents=True, exist_ok=True)
    nodes = [dict(name='root', children=[1, 2, 3, 4]), dict(name='unrelated label', children=[5]),
             dict(name='LeftHand fake forearm'), dict(name='other'), dict(name='right'),
             dict(name='digit', translation=[0, .125, 0]), dict(mesh=0, skin=0), dict(mesh=1, skin=0)]
    # Joint slot order intentionally differs from node IDs and labels.
    order = [4, 5, 0, 1, 3, 2]
    doc = dict(asset=dict(version='2.0'), buffers=[{}], bufferViews=[], accessors=[], nodes=nodes,
               skins=[dict(joints=order)], meshes=[dict(primitives=[]), dict(primitives=[])],
               scenes=[dict(nodes=[0, 6, 7])], scene=0)
    binary = bytearray()
    def primitive(points, slots, weights, faces=None):
        slots, weights = np.asarray(slots), np.asarray(weights)
        attrs = dict(POSITION=append_accessor(doc, binary, points, 'VEC3'),
            JOINTS_0=unsigned(doc, binary, slots[:, :4], 'VEC4'),
            WEIGHTS_0=append_accessor(doc, binary, weights[:, :4], 'VEC4'),
            JOINTS_1=unsigned(doc, binary, slots[:, 4:], 'VEC4'),
            WEIGHTS_1=append_accessor(doc, binary, weights[:, 4:], 'VEC4'))
        value = dict(attributes=attrs)
        if faces is not None:
            value['indices'] = unsigned(doc, binary, np.asarray(faces).reshape(-1), 'SCALAR')
        return value
    slots = [[3, 1, 3, 4, 1, 3, 1, 0]]*4
    weights = [[.125, .25, .125, 0, .25, .125, .125, 0]]*3 + [[.75, 0, 0, .25, 0, 0, 0, 0]]
    square = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    doc['meshes'][0]['primitives'].append(primitive(square, slots, weights,
        [[0, 1, 2], [0, 2, 3], [2, 1, 0], [0, 0, 1]]))
    doc['meshes'][0]['primitives'].append(primitive([[0, 0, 1], [1, 0, 1], [0, 1, 1]],
        [[0, 3, 2, 4, 1, 5, 3, 2]]*3, [[1, 0, 0, 0, 0, 0, 0, 0]]*3))
    doc['meshes'][1]['primitives'].append(primitive([[3, 0, 0], [4, 0, 0], [3, 1, 0]],
        [[3, 0, 1, 2, 3, 4, 5, 1]]*3, [[1, 0, 0, 0, 0, 0, 0, 0]]*3))
    doc['skins'][0]['inverseBindMatrices'] = append_accessor(doc, binary,
        np.linalg.inv(global_matrices(doc)[order]).transpose(0, 2, 1), 'MAT4')
    if animated:
        times = append_accessor(doc, binary, [0, 1], 'SCALAR')
        positions = append_accessor(doc, binary, [[0, 0, 0], [0, 0, 1]], 'VEC3')
        doc['animations'] = [dict(name='tiny', samplers=[dict(input=times, output=positions, interpolation='LINEAR')],
            channels=[dict(sampler=0, target=dict(node=1, path='translation'))])]
    character, profile = folder/'character.glb', folder/'profile.json'
    write_glb(character, doc, binary)
    save(profile, dict(schema='strep-rig-profile-v1', character_sha256=sha256(character),
        reference_pose='default_nodes', world_offset_m=[0, 0, 0], mapping=dict(Root=0, LeftHand=1, RightHand=4)))
    return character, profile


def load(folder, **kwargs):
    a, b = fixture(folder, **kwargs)
    return material.MaterialSurface(a, b, character_sha256=sha256(a), profile_sha256=sha256(b))


def select(surface, refs=None, **kwargs):
    config = dict(include_children=True, minimum_weight=1.)
    config.update(kwargs)
    return surface.patch('LeftHand', [[6, 0, 0]] if refs is None else refs, **config)


def test_complete_indexed_nonindexed_multimesh_eight_slot_ownership(tmp_path):
    surface = load(tmp_path)
    value = surface.candidates('LeftHand', include_children=True, minimum_weight=1.)
    assert value['face_references'] == [[6, 0, 0], [6, 0, 2], [7, 0, 0]]
    assert value['degenerate_face_references'] == [[6, 0, 3]] and value['owned_face_count'] == 4
    assert value['vertex_references'] == [[6, 0, 0], [6, 0, 1], [6, 0, 2], [7, 0, 0], [7, 0, 1], [7, 0, 2]]
    assert value['selected_nodes'] == [1, 5] and value['vertex_ownership'] == [1.]*6
    assert value['complete_surface_faces'] == 6 and value['complete_surface_vertices'] == 10
    assert surface.candidates('RightHand', include_children=True, minimum_weight=1.)['face_references'] == [[6, 1, 0]]
    assert surface.candidates('LeftHand', include_children=False, minimum_weight=1.)['face_references'] == [[7, 0, 0]]


def test_authored_mixed_ownership_is_explicit_and_not_anatomical(tmp_path):
    surface = load(tmp_path)
    value = select(surface, [[6, 0, 0], [6, 0, 1]], minimum_weight=.75)
    assert value['vertex_ownership'][-1] == .75
    assert value['winding']['normal_available'] and value['winding']['area_weighted_winding_normal'] == [0, 0, 1]
    assert value['winding']['summed_twice_area_m2'] == 2
    assert not any(value[k] for k in ('anatomy_verified', 'contact_target_approved', 'quality_approved', 'release_approved'))
    with pytest.raises(ValueError, match='ownership'):
        select(surface, [[6, 0, 1]])


def test_opposing_winding_does_not_invent_a_normal(tmp_path):
    surface = load(tmp_path); value = select(surface, [[6, 0, 0], [6, 0, 2]])
    assert value['winding']['normal_coherence'] == 0 and not value['winding']['normal_available']
    assert value['winding']['area_weighted_winding_normal'] is None


def test_patch_keeps_original_winding_order_and_native_material_points(tmp_path):
    surface = load(tmp_path); value = select(surface, [[6, 0, 2]])
    assert value['face_references'] == [[6, 0, 2]]
    assert value['winding']['area_weighted_winding_normal'] == [0, 0, -1]
    assert value['vertices'] == [[6, 0, 0], [6, 0, 1], [6, 0, 2]]
    ids = references(value['vertices'], NativeSupportSkin(surface.rig))
    np.testing.assert_array_equal(ids, [0, 1, 2])
    worlds = surface.rig.reference.copy(); worlds[[1, 5], :3, 3] += [.2, .3, .4]
    posed = surface.posed(value, worlds)
    # Weighted-sum evaluation differs from one addition by floating-point ULPs.
    np.testing.assert_allclose(posed['positions_m'], surface.points[ids]+[.2, .3, .4], atol=4*np.finfo(float).eps, rtol=0)
    np.testing.assert_allclose(posed['triangles_m'], (surface.points[ids]+[.2, .3, .4])[[[2, 1, 0]]], atol=4*np.finfo(float).eps, rtol=0)


def test_material_references_feed_actual_native_partner_contact_reader(tmp_path):
    surface = load(tmp_path, animated=True); patch = select(surface)
    pose = dict(translation_m=[0, 0, 0], rotation_xyzw=[0, 0, 0, 1])
    actor = dict(glb='character.glb', sha256=sha256(surface.character), animation_index=0, placement=pose)
    row = dict(id='touch', actor='A', vertices=patch['vertices'], reduction='individual',
        target=dict(space='actor', actor='B', vertices=patch['vertices'], reduction='individual'),
        mode='touch', interval_s=[.5, .5], limits=dict(position_m=0.))
    scene = SceneContacts(dict(schema='strep-native-scene-contacts-v1', duration_s=1.,
        actors=dict(A=actor, B=copy.deepcopy(actor)), objects={}, contacts=[row]), tmp_path)
    points = scene.actor_points('A', scene.rows[0]['ids'], [.5])[0]
    worlds = scene.actors['A']['sampler'].sample(.5)
    np.testing.assert_allclose(points, surface.posed(patch, worlds)['positions_m'], atol=1e-15, rtol=0)
    assert not np.array_equal(points[1], worlds[1, :3, 3])  # A mesh point, not a bone origin.


def test_pure_subtree_ownership_is_exact_one_even_for_nonunit_resummed_weights(tmp_path):
    surface = load(tmp_path)
    surface.skin.weights[:3] *= np.nextafter(np.float32(1.), np.float32(0.))
    assert np.all(surface.skin.weights[:3].sum(axis=1) < 1)
    _, weights = surface.ownership('LeftHand', True)
    np.testing.assert_array_equal(weights[:3], [1, 1, 1])


@pytest.mark.parametrize('refs', [[], [[True, 0, 0]], [[6, 0, .0]], [[99, 0, 0]], [[6, 9, 0]],
    [[6, 0, -1]], [[6, 0, 99]], [[6, 0, 0], [6, 0, 0]], [[6, 0, 3]],
    [[6, 0, 0], [7, 0, 0]], [[6, 1, 0]], 'bad'])
def test_invalid_degenerate_duplicate_disconnected_or_other_hand_patches_reject(tmp_path, refs):
    with pytest.raises(ValueError):
        select(load(tmp_path), refs)


@pytest.mark.parametrize('changes', [dict(include_children=1), dict(minimum_weight=True), dict(minimum_weight=0),
    dict(minimum_weight=1.1), dict(minimum_weight=float('nan')), dict(maximum_faces=True), dict(maximum_faces=0),
    dict(maximum_faces=513), dict(maximum_vertices=True), dict(maximum_vertices=2), dict(maximum_vertices=257),
    dict(minimum_twice_area_m2=0), dict(minimum_twice_area_m2=float('inf'))])
def test_invalid_patch_settings_reject(tmp_path, changes):
    with pytest.raises(ValueError):
        select(load(tmp_path), **changes)


def test_candidate_and_patch_budgets_never_return_a_subset(tmp_path):
    surface = load(tmp_path)
    with pytest.raises(ValueError, match='no subset'):
        surface.candidates('LeftHand', include_children=True, minimum_weight=1., maximum_faces=3)
    with pytest.raises(ValueError, match='vertex budget'):
        select(surface, [[6, 0, 0], [6, 0, 1]], minimum_weight=.75, maximum_vertices=3)
    with pytest.raises(ValueError, match='bounded material'):
        select(surface, [[6, 0, 0], [6, 0, 2]], maximum_faces=1)


@pytest.mark.parametrize('change', ['anatomy', 'positions', 'source', 'selector', 'normal', 'vertices'])
def test_rebound_or_changed_patch_rejects_before_pose_query(tmp_path, monkeypatch, change):
    surface = load(tmp_path); patch = select(surface)
    if change == 'anatomy': patch['anatomy_verified'] = True
    elif change == 'positions': patch['reference_positions_m'][0][0] += .01
    elif change == 'source': patch['source']['character_sha256'] = '0'*64
    elif change == 'selector': patch['selector']['extra'] = 1
    elif change == 'normal': patch['winding']['area_weighted_winding_normal'] = [0, 1, 0]
    else: patch['vertices'][0] = [99, 0, 0]
    monkeypatch.setattr(surface.rig, 'vertices', lambda _: pytest.fail('Changed patch must reject before pose query'))
    with pytest.raises(ValueError): surface.posed(patch, surface.rig.reference)


@pytest.mark.parametrize('field,value', [('schema','wrong'), ('reference_pose','bind'), ('character_sha256','0'*64),
    ('world_offset_m',[False,0,0]), ('world_offset_m',[0,1,0]), ('mapping',dict(LeftHand=True)),
    ('mapping',dict(LeftHand=1,RightHand=1)), ('mapping',dict(LeftHand=99))])
def test_incompatible_profile_rejects(tmp_path, field, value):
    a,b = fixture(tmp_path); profile = read(b); profile[field] = value; save(b,profile)
    with pytest.raises(ValueError): material.MaterialSurface(a,b,character_sha256=sha256(a),profile_sha256=sha256(b))


def test_source_change_before_or_during_inspection_rejects(tmp_path, monkeypatch):
    surface = load(tmp_path)
    before = {str(p): sha256(p) for p in tmp_path.iterdir() if p.is_file()}
    select(surface); surface.candidates('LeftHand', include_children=True, minimum_weight=1.)
    assert before == {str(p): sha256(p) for p in tmp_path.iterdir() if p.is_file()}
    original = surface.ownership
    def changed(*args):
        value = original(*args); surface.profile_path.write_text('{}'); return value
    monkeypatch.setattr(surface, 'ownership', changed)
    with pytest.raises(ValueError, match='source changed'): select(surface)
    with pytest.raises(ValueError, match='source changed'):
        surface.candidates('LeftHand', include_children=True, minimum_weight=1.)


@pytest.mark.parametrize('value', [np.zeros((1,4,4)), np.full((8,4,4), np.nan), np.ones((8,4,4))])
def test_incomplete_nonfinite_nonaffine_worlds_reject(tmp_path, value):
    surface = load(tmp_path)
    with pytest.raises(ValueError): surface.posed(select(surface), value)
