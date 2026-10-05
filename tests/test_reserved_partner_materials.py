"""Complete portable neutral material inventories; no anatomical or motion approval."""
import copy
from pathlib import Path
import shutil
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read, save, sha256
from test_reserved_partner_fixtures import build as build_fixtures
import reserved_partner_materials as materials


def build(tmp_path):
    root, fixtures, _ = build_fixtures(tmp_path)
    output = tmp_path/'materials'
    result = materials.run(fixtures, output)
    return root, fixtures, output, result


def rebind(output, path, value):
    save(path, value)
    request = read(output/'request.json'); result = read(output/'result.json')
    relative = path.relative_to(output).as_posix()
    if relative == 'request.json':
        result['request_sha256'] = sha256(path)
    else:
        for row in result['hands']:
            if row['path'] == relative:
                row['sha256'] = sha256(path)
    save(output/'result.json', result)


def test_full_twelve_hand_population_survives_move_and_original_removal(tmp_path):
    root, fixtures, out, result = build(tmp_path)
    assert len(result['hands']) == 12 and all(r['eligible_faces'] == r['eligible_vertices'] == 0 for r in result['hands'])
    assert all(r['selected_patches'] == 0 and not r['anatomy_verified'] for r in result['hands'])
    assert result['reserved_motion_trials_executed'] == result['selected_patches'] == 0
    assert not any(result[k] for k in ('anatomy_verified', 'contact_targets_bound', 'engine_executed',
                                     'quality_approved', 'release_approved'))
    moved = tmp_path/'moved materials'; shutil.move(str(out), str(moved))
    shutil.move(str(root), str(tmp_path/'original assets moved'))
    shutil.move(str(fixtures), str(tmp_path/'original fixtures moved'))
    assert materials.verify(moved) == result
    # The tiny neutral fixture binds all vertices to Hips: no hand is invented.
    for row in result['hands']:
        value = read(moved/row['path'])
        assert value['owned_face_count'] == 0 and value['requires_explicit_selection']


def test_construction_inputs_and_neutral_scenes_remain_unchanged(tmp_path):
    _, fixtures, _ = build_fixtures(tmp_path)
    before = materials.files(fixtures)
    out = tmp_path/'material result'; materials.run(fixtures, out)
    assert materials.files(fixtures) == before == materials.files(out/'fixtures')
    for row in read(fixtures/'result.json')['pairings']:
        scene = read(out/'fixtures/pairs'/row['id']/'scene.json')
        assert not scene['contacts'] and not scene['animations'] and not scene['anatomical_facing_reviewed']


@pytest.mark.parametrize('change', ['remove-hand', 'duplicate-hand', 'swap-actor', 'reverse-pairs', 'extra-file',
                                  'missing-file', 'eligible-count', 'rig-id', 'normal-approval'])
def test_complete_population_identity_reductions_and_false_approval_reject(tmp_path, change):
    _, _, out, result = build(tmp_path)
    if change == 'remove-hand': result['hands'].pop()
    elif change == 'duplicate-hand': result['hands'][1] = copy.deepcopy(result['hands'][0])
    elif change == 'swap-actor': result['hands'][0]['actor'] = 'B'
    elif change == 'reverse-pairs': result['hands'] = list(reversed(result['hands']))
    elif change == 'extra-file': save(out/'candidates/extra.json', {})
    elif change == 'missing-file': (out/result['hands'][0]['path']).unlink()
    elif change == 'eligible-count': result['hands'][0]['eligible_faces'] = 1
    elif change == 'rig-id': result['hands'][0]['rig_id'] = 'wrong'
    else: result['hands'][0]['anatomy_verified'] = True
    save(out/'result.json', result)
    with pytest.raises((ValueError, FileNotFoundError)): materials.verify(out)


@pytest.mark.parametrize('field,value', [('face_references',[[19,0,0]]), ('reference_positions_m',[[0,0,0]]),
    ('vertex_references',[[19,0,0]]), ('anatomy_verified',True), ('source',{}), ('requires_explicit_selection',False)])
def test_changed_candidate_rejects_even_if_hash_is_rebound(tmp_path, field, value):
    _, _, out, result = build(tmp_path)
    path = out/result['hands'][0]['path']; candidate = read(path); candidate[field] = value
    rebind(out, path, candidate)
    with pytest.raises(ValueError, match='candidate replay'): materials.verify(out)


@pytest.mark.parametrize('field,value', [('anatomy_verified',True), ('contact_targets_bound',True),
    ('engine_executed',True), ('quality_approved',True), ('release_approved',True),
    ('reserved_motion_trials_executed',1), ('selected_patches',1), ('scope','motion quality')])
def test_inventory_cannot_be_relabelled_as_motion_or_release_approval(tmp_path, field, value):
    _, _, out, result = build(tmp_path); result[field] = value; save(out/'result.json',result)
    with pytest.raises(ValueError, match='cannot grant'): materials.verify(out)


@pytest.mark.parametrize('change', ['selector', 'method-set', 'archived-method', 'fixture-file', 'result-binding'])
def test_bound_inputs_methods_parameters_reject_even_after_rebinding(tmp_path, change):
    _, _, out, _ = build(tmp_path)
    request = read(out/'request.json')
    if change == 'selector': request['parameters']['minimum_weight'] = .1
    elif change == 'method-set': request['implementation_sha256'].pop('rig_material_patch.py')
    elif change == 'archived-method':
        path = out/'implementation/rig_material_patch.py'; path.write_text('# changed')
        request['implementation_sha256']['rig_material_patch.py'] = sha256(path)
    elif change == 'fixture-file':
        path = out/'fixtures/pairs/pair-0/actors/A/LICENSE.md'; path.write_text('changed')
    else: request['source_bundle_result_sha256'] = '0'*64
    rebind(out, out/'request.json', request)
    with pytest.raises(ValueError): materials.verify(out)


def test_existing_and_nested_output_reject_without_changing_inputs(tmp_path):
    _, fixtures, _ = build_fixtures(tmp_path); before = materials.files(fixtures)
    out = tmp_path/'exists'; out.mkdir()
    for invalid in (out, fixtures/'nested'):
        with pytest.raises(ValueError, match='Fresh separate'): materials.run(fixtures, invalid)
    assert materials.files(fixtures) == before


def test_source_change_during_candidate_generation_preserves_failed_output(tmp_path, monkeypatch):
    _, fixtures, _ = build_fixtures(tmp_path)
    original = materials.candidate
    def changed(row, cache):
        value = original(row, cache)
        (fixtures/'pairs/pair-0/actors/A/LICENSE.md').write_text('changed during build')
        return value
    monkeypatch.setattr(materials, 'candidate', changed)
    out = tmp_path/'failed'
    with pytest.raises(ValueError, match='Original neutral'): materials.run(fixtures, out)
    assert read(out/'pipeline.json')['status'] == 'failed' and (out/'request.json').exists()
    assert not (out/'result.json').exists()
