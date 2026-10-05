"""Verified material bundles feed the existing protected native revision format."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_material_patch_bundle import author,target_from,move,scene_for
from native_contact_revision import validate
from native_scene_contacts import SceneContacts
from strep import read,save,sha256
import material_patch_revision as revision


def setup(tmp_path):
    a,b,_,out,_ = author(tmp_path); target,profile = target_from(a,b,tmp_path/'animated')
    bundle = tmp_path/'animated-regions'; move(out,target,profile,bundle)
    patch = read(bundle/'patches/left-surface.json'); scene,_ = scene_for(target,patch)
    draft = dict(schema='strep-studio-native-scene-v1',scene=scene,
        geometry=dict(planes=[],reserved='unchanged geometry settings'),object_edit=None)
    baseline = tmp_path/'baseline.json'; save(baseline,draft)
    def ref(order):
        return dict(bundle='animated-regions',result_sha256=sha256(bundle/'result.json'),
            patch_id='left-surface',vertex_indices=order,reduction='individual')
    spec = dict(schema=revision.SCHEMA,baseline_sha256=sha256(baseline),
        edits=[dict(id='touch',source=ref([2,0,1]),partner=ref([2,0,1]))])
    return draft,spec,baseline,bundle,out


def apply(tmp_path,draft,spec,baseline):
    return revision.revise(draft,spec,specification_base=tmp_path,scene_base=tmp_path,baseline_sha256=sha256(baseline))


def test_both_sides_use_explicit_vertex_order_and_preserve_complete_draft(tmp_path):
    draft,spec,baseline,_,_ = setup(tmp_path); before = copy.deepcopy(draft)
    updated,proof = apply(tmp_path,draft,spec,baseline)
    actual,lineage = validate(updated)
    assert draft == before and actual['geometry'] == draft['geometry'] and actual['object_edit'] is None
    assert actual['scene']['actors'] == draft['scene']['actors'] and actual['scene']['objects'] == draft['scene']['objects']
    original = draft['scene']['contacts'][0]; changed = actual['scene']['contacts'][0]
    for key in ('id','actor','mode','interval_s','limits'): assert original[key] == changed[key]
    assert changed['vertices'] == changed['target']['vertices'] == [original['vertices'][i] for i in [2,0,1]]
    assert lineage['baseline'] == draft and len(proof['material_bindings']) == 2
    scene = SceneContacts(actual['scene'],tmp_path)
    assert scene.actor_points('A',scene.rows[0]['ids'],[.5]).shape == (1,3,3)
    assert proof['anatomical_review_pending'] and not proof['motion_contacts_measured']
    assert not proof['animation_edited'] and not proof['quality_approved'] and not proof['release_approved']


@pytest.mark.parametrize('fault',['baseline','bundle-hash','missing-patch','static-file','negative-index','bool-index',
    'missing-index','duplicate-index','empty-index','auto-order','reduction','contact-id','duplicate-contact','no-change','no-edit','point-count'])
def test_bad_bindings_and_correspondence_reject(tmp_path,fault):
    draft,spec,baseline,bundle,static = setup(tmp_path); row = spec['edits'][0]; entry = row['source']
    if fault == 'baseline': spec['baseline_sha256'] = '0'*64
    elif fault == 'bundle-hash': entry['result_sha256'] = '0'*64
    elif fault == 'missing-patch': entry['patch_id'] = 'unknown'
    elif fault == 'static-file': entry.update(bundle=str(static),result_sha256=sha256(static/'result.json'))
    elif fault == 'negative-index': entry['vertex_indices'] = [-1]
    elif fault == 'bool-index': entry['vertex_indices'] = [True]
    elif fault == 'missing-index': entry['vertex_indices'] = [3]
    elif fault == 'duplicate-index': entry['vertex_indices'] = [0,0]
    elif fault == 'empty-index': entry['vertex_indices'] = []
    elif fault == 'auto-order': entry.pop('vertex_indices')
    elif fault == 'reduction': entry['reduction'] = 'auto'
    elif fault == 'contact-id': row['id'] = 'unknown'
    elif fault == 'duplicate-contact': spec['edits'] *= 2
    elif fault == 'no-change':
        row['source']['vertex_indices'] = [0,1,2]; row['partner']['vertex_indices'] = [0,1,2]
    elif fault == 'no-edit': row['source'] = row['partner'] = None
    else: entry['vertex_indices'] = [0]
    before = copy.deepcopy(draft)
    with pytest.raises(ValueError): apply(tmp_path,draft,spec,baseline)
    assert before == draft


def test_file_command_preserves_relative_paths_and_writes_bound_receipt(tmp_path):
    draft,spec,baseline,bundle,_ = setup(tmp_path)
    for actor in draft['scene']['actors'].values(): actor['glb'] = 'animated/character.glb'
    save(baseline,draft); spec['baseline_sha256'] = sha256(baseline)
    specification = tmp_path/'spec.json'; save(specification,spec); output = tmp_path/'revised.json'
    before = {str(p):sha256(p) for p in (baseline,specification)}
    revised = revision.run(baseline,specification,output)
    assert revised == read(output) and validate(revised)[0]['scene']['actors'] == draft['scene']['actors']
    receipt = read(tmp_path/'revised.json.material.json')
    assert receipt['revised_draft_sha256'] == sha256(output) and receipt['inputs_sha256'] == before
    assert before == {str(p):sha256(p) for p in (baseline,specification)}
    with pytest.raises(ValueError,match='Fresh'): revision.run(baseline,specification,output)
    with pytest.raises(ValueError,match='beside'): revision.run(baseline,specification,tmp_path/'moved/revised.json')


def test_selected_centroid_is_explicit_and_counts_still_must_correspond(tmp_path):
    draft,spec,baseline,_,_ = setup(tmp_path)
    for entry in (spec['edits'][0]['source'],spec['edits'][0]['partner']):
        entry['reduction'] = 'centroid'; entry['vertex_indices'] = [0,1,2]
    updated,proof = apply(tmp_path,draft,spec,baseline)
    assert updated['scene']['contacts'][0]['reduction'] == 'centroid'
    assert updated['scene']['contacts'][0]['target']['reduction'] == 'centroid'
    assert not proof['motion_contacts_measured']


@pytest.mark.parametrize('bad',[None,'',True,'A'*64,'0'*63])
@pytest.mark.parametrize('field',['baseline','bundle'])
def test_mandatory_sha_pins_cannot_disable_verification(tmp_path,bad,field):
    draft,spec,baseline,_,_ = setup(tmp_path)
    actual_baseline = sha256(baseline)
    if field == 'baseline':
        spec['baseline_sha256'] = actual_baseline = bad
    else: spec['edits'][0]['source']['result_sha256'] = bad
    with pytest.raises(ValueError,match='Explicit lowercase SHA256'):
        revision.revise(draft,spec,specification_base=tmp_path,scene_base=tmp_path,
                        baseline_sha256=actual_baseline)
