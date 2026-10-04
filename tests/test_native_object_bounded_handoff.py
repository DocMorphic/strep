"""Original author budgets and exact encoded exterior preservation are distinct."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
from test_native_object_correspondence_fit import fixture
from native_scene_contacts import SceneContacts
from native_object_asset import ObjectAsset,export
from native_object_bounded_handoff import evaluate,validate_fit
from native_object_correspondence_fit import proposal,saved_keys
from strep import save,sha256


def assets(tmp_path,change=None):
    _,path,spec,scene,value=fixture(tmp_path);keys,_,_=proposal(scene,value,sha256(path))
    candidate=copy.deepcopy(spec);candidate['objects']['item']['keyframes']=saved_keys(keys,spec,value)
    if change:change(candidate)
    proposed=SceneContacts(candidate,tmp_path)
    export(scene,tmp_path/'original.glb');export(proposed,tmp_path/'candidate.glb')
    reference=ObjectAsset(tmp_path/'original.glb');asset=ObjectAsset(tmp_path/'candidate.glb')
    times=np.unique(np.r_[reference.objects['item']['translation'][0],asset.objects['item']['translation'][0],0.,scene.duration])
    return scene,reference,asset,times,value


def test_exact_encoded_protection_can_pass_despite_float64_roundtrip(tmp_path):
    scene,reference,asset,times,value=assets(tmp_path)
    report,arrays=evaluate(scene,reference,asset,reference,asset,times,value)
    assert report['movement_limits_pass'] and report['object_epoch_conditions_pass']
    assert report['author_frozen_roundtrip_maximum_component_error']>1e-12
    assert not report['author_frozen_float64_identity']
    assert all(r['passed'] and r['maximum_component_error']==0 for r in report['encoded_protected_originals']+report['actual_protected_originals'])
    assert len(arrays['times_s'])==len(times)
    assert not report['actor_engine_import_checked'] and not report['full_imported_geometry_checked']


def test_original_author_epoch_cannot_be_reset_to_the_candidate(tmp_path):
    scene,reference,asset,times,value=assets(tmp_path);value['maximum_translation_m']=.0001
    report,_=evaluate(scene,reference,asset,reference,asset,times,value)
    assert report['maximum_original_relative_translation_m']>.001
    assert not report['movement_limits_pass'] and not report['object_epoch_conditions_pass']
    assert all(r['passed'] for r in report['encoded_protected_originals']+report['actual_protected_originals'])


def test_exterior_edit_is_rejected_even_when_inside_movement_budget(tmp_path):
    def change(spec):spec['objects']['item']['keyframes'][0]['translation_m'][1]+=.0001
    scene,reference,asset,times,value=assets(tmp_path,change)
    report,_=evaluate(scene,reference,asset,reference,asset,times,value)
    assert report['movement_limits_pass'] and not report['object_epoch_conditions_pass']
    assert not report['encoded_protected_originals'][0]['passed'] and not report['actual_protected_originals'][0]['passed']


def test_actual_engine_exterior_drift_cannot_be_hidden_by_same_assets(tmp_path):
    scene,reference,asset,times,value=assets(tmp_path)
    class Drift:
        objects=asset.objects
        def object_poses(self,name,clock):
            p,r=asset.object_poses(name,clock);p=p.copy();p[clock<=value['edit_window_s'][0],0]+=.000001;return p,r
    report,_=evaluate(scene,reference,asset,reference,Drift(),times,value)
    assert all(r['passed'] for r in report['encoded_protected_originals'])
    assert not report['actual_protected_originals'][0]['passed'] and not report['object_epoch_conditions_pass']


@pytest.mark.parametrize('fault',['nonfinite_clock','unsorted_clock','missing_object','geometry'])
def test_incomplete_or_changed_handoff_observations_reject(tmp_path,fault):
    scene,reference,asset,times,value=assets(tmp_path)
    if fault=='nonfinite_clock':times[1]=np.nan
    if fault=='unsorted_clock':times[1]=times[0]
    if fault=='missing_object':asset.objects.clear()
    if fault=='geometry':asset.document['nodes'][0]['extras']['strep_geometry']['size_m'][0]+=.01
    with pytest.raises(ValueError):evaluate(scene,reference,asset,reference,asset,times,value)


def test_failed_fit_is_not_relabelled_as_a_handoff_candidate(tmp_path):
    save(tmp_path/'pipeline.json',dict(status='complete'))
    save(tmp_path/'result.json',dict(status='complete',schema='strep-native-object-bounded-fit-v1',sampled_constraints_pass=False))
    with pytest.raises(ValueError,match='Passing bounded fit required'):validate_fit(tmp_path)
