"""Static synthetic primitive checks; no reserved motion generation or review."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reserved_object_fixtures as fixtures
from gltf_tools import read_glb, write_glb
from strep import read, save, sha256


def catalog():
    geometries = [dict(schema='strep-object-geometry-v1', shape='box', size_m=[.4, .6, .8]),
                  dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.3),
                  dict(schema='strep-object-geometry-v1', shape='cylinder', radius_m=.3, height_m=1.2)]
    return dict(schema='strep-reserved-object-fixtures-v1', status='reserved_not_motion_evaluated',
                use_policy='Synthetic reservation fixture; not real evaluation data', limitations=['Synthetic geometry only'],
                objects=[dict(id='synthetic-' + g['shape'], geometry=g, motion_trial_executed=False) for g in geometries])


def test_all_shapes_save_decode_repeat_exactly_and_preserve_local_and_world_contracts(tmp_path):
    source = tmp_path / 'catalog.json'
    save(source, catalog())
    original = sha256(source)
    result = fixtures.build(source, tmp_path / 'first')
    second = fixtures.build(source, tmp_path / 'second')
    assert result['distinct_geometries'] == 3 and result['shape_families'] == ['box', 'cylinder', 'sphere']
    assert result['static_geometry_pass'] and result['motion_trials_executed'] == 0
    assert not result['engine_checked'] and not result['physics_checked']
    assert not result['held_out_scene_package_complete'] and not result['quality_approved'] and not result['release_approved']
    assert sha256(source) == original
    for a, b in zip(result['objects'], second['objects']):
        assert a['glb_sha256'] == b['glb_sha256']
        assert a['maximum_stored_surface_error_m'] < 1e-6 and a['triangles'] > 0
        folder = tmp_path / 'first' / 'objects' / a['id']
        descriptor = read(folder / 'descriptor.json')
        assert not descriptor['scene_or_partner_binding_complete']
        pose = descriptor['canonical_grounded_pose']['translation_m']
        np.testing.assert_array_equal(pose, [0, fixtures._extent(a['geometry'])[1], 0])
        assert descriptor['anchors'][0]['outward_normal'] == [-1., 0., 0.]
        assert descriptor['anchors'][1]['outward_normal'] == [1., 0., 0.]
        assert descriptor['glb_sha256'] == a['glb_sha256']
        assert descriptor['approximation']['conservative_preview_inset_with_rounding_m'] <= .001001
    with pytest.raises(ValueError, match='Fresh'):
        fixtures.build(source, tmp_path / 'first')


@pytest.mark.parametrize('fault', ['evaluated', 'duplicate_id', 'duplicate_geometry', 'escape_id', 'empty',
                                 'extra', 'boolean_dimension', 'nan_dimension', 'out_of_range', 'unsupported', 'status'])
def test_bad_or_exposed_catalogs_fail_before_creating_output(tmp_path, fault):
    data = catalog()
    if fault == 'evaluated': data['objects'][0]['motion_trial_executed'] = True
    if fault == 'duplicate_id': data['objects'][1]['id'] = data['objects'][0]['id']
    if fault == 'duplicate_geometry': data['objects'][1]['geometry'] = copy.deepcopy(data['objects'][0]['geometry'])
    if fault == 'escape_id': data['objects'][0]['id'] = '../escape'
    if fault == 'empty': data['objects'] = []
    if fault == 'extra': data['quality_approved'] = True
    if fault == 'boolean_dimension': data['objects'][0]['geometry']['size_m'][0] = True
    if fault == 'nan_dimension': data['objects'][0]['geometry']['size_m'][0] = float('nan')
    if fault == 'out_of_range': data['objects'][0]['geometry']['size_m'][0] = 11
    if fault == 'unsupported': data['objects'][0]['geometry']['shape'] = 'arbitrary-mesh'
    if fault == 'status': data['status'] = 'approved'
    path = tmp_path / 'catalog.json'
    if fault == 'nan_dimension':
        import json
        path.write_text(json.dumps(data))
    else: save(path, data)
    with pytest.raises(ValueError): fixtures.build(path, tmp_path / 'bad')
    assert not (tmp_path / 'bad').exists()


@pytest.mark.parametrize('fault', ['animation', 'transformed', 'wrong_geometry', 'bad_bounds', 'bad_normal',
                                 'bad_vertex', 'inward', 'wrong_inset', 'external_buffer', 'wrong_scene'])
def test_changed_saved_geometry_cannot_pass_decoder(tmp_path, fault):
    data = catalog()
    path = tmp_path / 'catalog.json'
    save(path, data)
    result = fixtures.build(path, tmp_path / 'built')
    case = result['objects'][0]
    asset = tmp_path / 'built' / case['path']
    descriptor = read(asset.parent / 'descriptor.json')
    doc, binary = read_glb(asset)
    if fault == 'animation': doc['animations'] = [dict(channels=[], samplers=[])]
    if fault == 'transformed': doc['nodes'][0]['translation'] = [1, 0, 0]
    if fault == 'wrong_geometry': doc['nodes'][0]['extras']['strep_geometry']['size_m'][0] = 9
    if fault == 'bad_bounds': doc['accessors'][0]['max'] = [9, 9, 9]
    if fault == 'external_buffer': doc['images'] = [dict(uri='outside.png')]
    if fault == 'wrong_scene': doc['scenes'][0]['nodes'] = []
    if fault in ('bad_normal', 'bad_vertex', 'inward'):
        index = 1 if fault == 'bad_normal' else 0
        item = doc['accessors'][index]
        view = doc['bufferViews'][item['bufferView']]
        offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
        binary = bytearray(binary)
        values = np.ndarray((item['count'], 3), dtype='<f4', buffer=binary, offset=offset)
        if fault == 'bad_normal': values[0] *= -1
        elif fault == 'bad_vertex': values[0] *= 2
        else: values[[0, 1]] = values[[1, 0]]
    if fault == 'wrong_inset': descriptor['approximation']['conservative_preview_inset_with_rounding_m'] = .002
    write_glb(asset, doc, binary)
    with pytest.raises(ValueError): fixtures.decode_check(asset, case['geometry'], descriptor['approximation'])


def test_source_mutation_is_preserved_but_not_claimed_success(tmp_path, monkeypatch):
    path = tmp_path / 'catalog.json'
    save(path, catalog())
    original = fixtures.decode_check
    def changed(*args):
        path.write_text('{}')
        return original(*args)
    monkeypatch.setattr(fixtures, 'decode_check', changed)
    with pytest.raises(ValueError, match='changed during construction'):
        fixtures.build(path, tmp_path / 'partial')
    assert (tmp_path / 'partial/request.json').exists()
    assert not (tmp_path / 'partial/result.json').exists()
