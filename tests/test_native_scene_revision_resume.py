"""Explicit revised contact intent retains original source bytes and solver bounds."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_resume import checkpoint
from test_native_scene_fit import prepare
from native_scene_fit import run
from native_scene_revision import SCHEMA, validate
from native_contact_revision import apply
from native_support_feasibility import merit
from strep import read,save,sha256


def revised(tmp_path,c,p):
    old=read(c)
    edits=[dict(id=old['contacts'][0]['id'],source=dict(glb_sha256=old['actors']['A']['sha256'],
        vertices=[[6,0,1],[6,0,2]],reduction='centroid'),partner=None)]
    current=apply(dict(schema='strep-studio-native-scene-v1',scene=old,geometry=None,object_edit=None),edits)['scene']
    contacts=tmp_path/'revised-contacts.json';save(contacts,current)
    permission=read(p);permission['contacts_sha256']=sha256(contacts)
    permissions=tmp_path/'revised-permissions.json';save(permissions,permission)
    receipt=tmp_path/'revision.json';save(receipt,dict(schema=SCHEMA,original_contacts_sha256=sha256(c),
        original_permissions_sha256=sha256(p),edits=edits))
    return contacts,permissions,receipt


def keep(monkeypatch,x=None):
    import native_scene_fit as fit
    def optimize(problem,evaluate,*args):
        if x is not None:np.testing.assert_array_equal(problem.initial,x)
        evaluate(problem.initial,'start')
        return problem.initial.copy(),dict(history=[],final_merit=list(merit(problem.model(problem.initial))))
    monkeypatch.setattr(fit,'optimize',optimize)


def test_revision_resume_replays_clip_caps_and_both_intents_then_chains(tmp_path,monkeypatch):
    source,c,p,prior,old,x=checkpoint(tmp_path,monkeypatch)
    current,permissions,receipt=revised(tmp_path,c,p);keep(monkeypatch,x)
    out=tmp_path/'revised-fit';result=run(current,permissions,out,resume_from=prior,contact_revision=receipt)
    assert result['original_selected'] and not result['quality_approved']
    assert sha256(out/'probes/start/A.glb')==sha256(prior/'probes/final/A.glb')
    assert sha256(out/'input/actor-0.glb')==sha256(source)
    assert sha256(out/'contact-revision.json')==sha256(receipt)
    with np.load(out/'source-rate-caps.npz') as now,np.load(prior/'source-rate-caps.npz') as before:
        assert set(now.files)==set(before.files)
        for k in now.files:
            assert now[k].dtype==before[k].dtype;np.testing.assert_array_equal(now[k],before[k])
    record=result['resume']['contact_revision']
    assert record['original_contacts_sha256']==sha256(c) and record['authored_contacts_sha256']==sha256(current)
    assert record['anatomical_review_pending'] and not record['release_approved']
    assert result['resume']['prior_merit_uses_original_contact_intent']
    a=read(out/'original-contact-audit/result.json');b=read(out/'contact-audit/result.json')
    assert a['contacts'][0]['maximum_position_error_m']!=b['contacts'][0]['maximum_position_error_m']
    assert result['original_contact_intent_pass']==a['passed']
    assert result['original_contact_intent_result_sha256']==sha256(out/'original-contact-audit/result.json')
    chain=tmp_path/'chain';next_result=run(current,permissions,chain,resume_from=out)
    assert next_result['completed_primary_iterations']==old['completed_primary_iterations']
    assert sha256(chain/'resume/contact-revision.json')==sha256(receipt)


@pytest.mark.parametrize('fault',['no-resume','no-proof','schema','old-contact-hash','old-permission-hash',
    'wrong-actor','missing-reference','target','timing','limit','placement','source-path','window','knots','bound','extra'])
def test_revision_cannot_reset_source_or_contact_contract(tmp_path,monkeypatch,fault):
    source,c,p,prior,old,x=checkpoint(tmp_path,monkeypatch)
    current,permissions,receipt=revised(tmp_path,c,p)
    v=read(current);permission=read(permissions);proof=read(receipt)
    if fault=='schema':proof['schema']='inferred-contact'
    if fault=='old-contact-hash':proof['original_contacts_sha256']='0'*64
    if fault=='old-permission-hash':proof['original_permissions_sha256']='0'*64
    if fault=='wrong-actor':proof['edits'][0]['source']['glb_sha256']='0'*64
    if fault=='missing-reference':v['contacts'][0]['vertices']=proof['edits'][0]['source']['vertices']=[[6,0,999]]
    if fault=='target':v['contacts'][0]['target']['points_m'][0][0]+=.001
    if fault=='timing':v['contacts'][0]['interval_s']=[.9,1.1]
    if fault=='limit':v['contacts'][0]['limits']['position_m']*=2
    if fault=='placement':v['actors']['A']['placement']['translation_m'][0]+=.001
    if fault=='source-path':v['actors']['A']['glb']=str(source.resolve())
    if fault=='window':permission['actors']['A']['window_s']=[.1,1.9]
    if fault=='knots':permission['actors']['A']['knots_s']=[0,.4,1,1.5,2]
    if fault=='bound':permission['actors']['A']['maximum_joint_displacement_m']=.021
    if fault=='extra':proof['quality_approved']=True
    save(current,v);permission['contacts_sha256']=sha256(current);save(permissions,permission);save(receipt,proof)
    output=tmp_path/'rejected'
    with pytest.raises(ValueError):run(current,permissions,output,
        resume_from=None if fault=='no-resume' else prior,contact_revision=None if fault=='no-proof' else receipt)
    assert not output.exists()


def test_partner_patches_change_atomically_without_changing_placement_or_targets(tmp_path):
    source,spec,c,p,permissions,scene,edits=prepare(tmp_path)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    save(c,spec);p['contacts_sha256']=sha256(c);save(permissions,p)
    proof=dict(schema=SCHEMA,original_contacts_sha256=sha256(c),original_permissions_sha256=sha256(permissions),
        edits=[dict(id=spec['contacts'][0]['id'],source=dict(glb_sha256=sha256(source),vertices=[[6,0,1],[6,0,2]],reduction='individual'),
            partner=dict(glb_sha256=sha256(source),vertices=[[6,0,3],[6,0,4]],reduction='individual'))])
    current=apply(dict(schema='strep-studio-native-scene-v1',scene=spec,geometry=None,object_edit=None),proof['edits'])['scene']
    permission=copy.deepcopy(p);permission['contacts_sha256']='a'*64
    assert validate(proof,spec,p,sha256(c),sha256(permissions),current,permission,'a'*64)['original_actor_epoch_required']
    bad=copy.deepcopy(proof);bad['edits'][0]['partner']=None
    with pytest.raises(ValueError):validate(bad,spec,p,sha256(c),sha256(permissions),current,permission,'a'*64)


@pytest.mark.parametrize('fault',['none','drop','ordinary-drop','plane','clock','limit','receipt-mutation','ancestor-receipt'])
def test_revision_retains_geometry_and_rejects_mutated_receipts(tmp_path,monkeypatch,fault):
    _,spec,c,p,permissions,scene,edits=prepare(tmp_path);keep(monkeypatch)
    policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(c),
        clock=dict(mode='explicit',times_s=[0.,1.,2.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0,1,0],offset_m=0.)))
    geometry=tmp_path/'geometry.json';save(geometry,policy);prior=tmp_path/'prior'
    run(c,permissions,prior,geometry_policy=geometry)
    current,new_permissions,receipt=revised(tmp_path,c,permissions)
    policy['contacts_sha256']=sha256(current)
    if fault=='plane':policy['planes']['floor']['offset_m']=.01
    if fault=='clock':policy['clock']['times_s']=[0.,2.]
    if fault=='limit':policy['limits']['penetration_m']=.006
    revised_geometry=tmp_path/'revised-geometry.json';save(revised_geometry,policy)
    out=tmp_path/'resumed'
    if fault=='ordinary-drop':
        with pytest.raises(ValueError):run(c,permissions,out,resume_from=prior)
        assert not out.exists();return
    if fault=='receipt-mutation':
        import native_scene_fit as fit
        def mutate(problem,evaluate,*args):
            evaluate(problem.initial,'start');receipt.write_bytes(receipt.read_bytes()+b' ')
            return problem.initial.copy(),dict(history=[],final_merit=list(merit(problem.model(problem.initial))))
        monkeypatch.setattr(fit,'optimize',mutate)
    if fault in ('drop','plane','clock','limit','receipt-mutation'):
        with pytest.raises(ValueError):run(current,new_permissions,out,resume_from=prior,contact_revision=receipt,
            geometry_policy=None if fault=='drop' else revised_geometry)
        if fault!='receipt-mutation':assert not out.exists()
        else:assert read(out/'pipeline.json')['status']=='failed'
    else:
        result=run(current,new_permissions,out,resume_from=prior,contact_revision=receipt,geometry_policy=revised_geometry)
        assert result['sampled_geometry_conditions_pass']
        if fault=='ancestor-receipt':
            (out/'contact-revision.json').write_bytes(b'changed')
            with pytest.raises(ValueError):run(current,new_permissions,tmp_path/'chain',resume_from=out,geometry_policy=revised_geometry)


def test_revision_cannot_silently_reinterpret_additional_surface_policy(tmp_path,monkeypatch):
    from test_native_surface_contact import fit_fixture
    source,c,p,surface=fit_fixture(tmp_path);keep(monkeypatch);prior=tmp_path/'prior'
    run(c,p,prior,surface_contact_policy=surface)
    current,permission,receipt=revised(tmp_path,c,p);out=tmp_path/'resumed'
    with pytest.raises(ValueError,match='surface contact policy'):
        run(current,permission,out,resume_from=prior,contact_revision=receipt,surface_contact_policy=surface)
    assert not out.exists()


def test_equal_values_with_changed_cap_dtype_cannot_resume(tmp_path,monkeypatch):
    source,c,p,prior,old,x=checkpoint(tmp_path,monkeypatch)
    values=dict(np.load(prior/'source-rate-caps.npz'));values['A_metric_0']=values['A_metric_0'].astype(np.float32)
    np.savez(prior/'source-rate-caps.npz',**values)
    result=read(prior/'result.json');result['source_rate_caps_sha256']=sha256(prior/'source-rate-caps.npz');save(prior/'result.json',result)
    keep(monkeypatch,x)
    with pytest.raises(ValueError):run(c,p,tmp_path/'resumed',resume_from=prior)
