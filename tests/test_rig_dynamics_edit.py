from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, sha256, save
from rig_dynamics_edit import validate, prepare, run


def payload(job='20260926-195612-5047106e', variant='corrected'):
    p = ROOT/'reports/rig-jobs'/job/variant/'character.glb'
    return dict(schema='strep-rig-dynamics-v1', job=job, variant=variant,
                glb_sha256=sha256(p), label='Root cleanup integration test')


def test_selected_version_hash_must_match():
    p = payload()
    p['glb_sha256'] = '0'*64
    with pytest.raises(ValueError, match='Selected clip changed'):
        validate(p)


def test_finger_only_fixed_body_contract_is_not_silently_discarded():
    p = payload('20260927-175338-39f04f09', 'transfer')
    with pytest.raises(ValueError, match='Finger-only'):
        validate(p)


def test_joint_context_and_original_baseline_are_preserved(tmp_path):
    p=payload('20260927-043725-43fc4d62','transfer')
    snapshot,baseline,recipe,history=validate(p)
    assert history['kind']=='joint_edit' and history['status']=='rejected'
    out=tmp_path/'joint';request=prepare(p,out)
    assert sha256(out/'baseline/character.glb')==sha256(baseline)
    assert sha256(out/'joint-spec.json')==sha256(recipe)
    assert sha256(out/'joint-targets.json')==sha256(snapshot[0]/'joint-targets.json')
    assert read(out/'original-contact-spec.json')['contacts'][-1]['patch']=='joint-support-0'
    assert read(out/'input/contact-spec.json')['glb_sha256']==p['glb_sha256']


def test_chained_joint_context_is_preserved(tmp_path):
    p=payload('20260928-105143-aed550d4','transfer')
    snapshot,baseline,recipe,history=validate(p)
    out=tmp_path/'chain';request=prepare(p,out)
    assert history['kind']=='joint_edit'
    assert request['inherited_contact']==history
    assert sha256(out/'baseline/character.glb')==sha256(baseline)
    assert sha256(out/'original-contact-spec.json')==sha256(recipe)
    assert sha256(out/'joint-targets.json')==sha256(snapshot[0]/'joint-targets.json')


def test_chain_rejects_changed_parent_request(tmp_path,monkeypatch):
    import rig_dynamics_edit as worker
    from rig_contact_authoring import source
    p=payload('20260928-105143-aed550d4','transfer')
    folder,result,request,report,glb=source(p['job'],p['variant'])
    save(tmp_path/'request.json',request)
    save(tmp_path/'freeze.json',dict(request_sha256='0'*64))
    monkeypatch.setattr(worker,'source',lambda *_:(tmp_path,result,request,report,glb))
    with pytest.raises(ValueError,match='Saved correction request changed'):worker.validate(p)


def test_failed_source_status_and_original_target_binding_retained():
    snapshot, baseline, recipe, inherited = validate(payload('20260926-202244-c3c3bb14'))
    assert inherited['status'] == 'rejected'
    assert read(recipe)['glb_sha256'] == sha256(baseline)
    assert snapshot[2]['input_glb_sha256'] == sha256(baseline)


def test_prepared_request_is_frozen_and_source_untouched(tmp_path):
    p = payload()
    source = ROOT/'reports/rig-jobs'/p['job']/'corrected/character.glb'
    out = tmp_path/'job'
    request = prepare(p, out)
    assert sha256(source) == p['glb_sha256'] == sha256(out/'input/character.glb')
    assert request['inherited_contact']['status'] == 'provisional_pass'
    assert read(out/'input/contact-spec.json')['glb_sha256'] == p['glb_sha256']
    assert read(out/'original-contact-spec.json')['glb_sha256'] == sha256(out/'baseline/character.glb')
    request['policy']['root_correction_radius_m'] = 1.
    save(out/'request.json', request)
    with pytest.raises(ValueError, match='Frozen correction request changed'):
        run(out)
