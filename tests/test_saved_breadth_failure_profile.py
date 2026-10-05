import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import saved_breadth_failure_profile as profile


def fixture():
    cases = []
    for name, family, actors, context in [('backpedal','locomotion',['A'],'floor'),
            ('beckon','gestures',['A'],'floor'),('high-five','partner',['A','B'],'partner')]:
        cases.append(dict(id=name,family=family,actors=[dict(id=a) for a in actors],seeds=[1,2,3],context=context,
            flat_floor_screen_applicable=context=='floor',scene_validation='free-space' if context=='floor' else 'context-missing'))
    protocol = dict(schema=1,cases=cases,expected_cases=3,expected_actor_clips=12,
        screens=dict(joint_floor_depth_m=.01,predicted_foot_speed_p95_m_s=.15),held_out_claim='Development only')
    rows = []
    for case in cases:
        for actor in case['actors']:
            for seed in case['seeds']:
                eligible=case['flat_floor_screen_applicable']
                depth=.01 if case['id']=='backpedal' and seed==3 else .02
                rows.append(dict(case=case['id'],family=case['family'],actor=actor['id'],seed=seed,
                    exported=True,context=case['context'],scene_validation=case['scene_validation'],
                    flat_floor_screen_applicable=eligible,mesh_floor_depth_m=depth if eligible else None,
                    mesh_floor_screen=depth<=.01 if eligible else None,joint_floor_depth_m=.001,
                    joint_floor_screen=True if eligible else None,predicted_foot_speed_p95_m_s=.1,
                    predicted_foot_speed_screen=True if eligible else None,semantic_rating=None,
                    independent_human_review=False,quality_approved=False))
    coverage=dict(planned_cases=3,planned_actor_clips=12,exported=12,rows=rows,quality_approved=False,
        qualification='Saved diagnostic availability only')
    return protocol,coverage,dict(surface_threshold_m=.01)


def test_complete_seed_partner_population_and_recurrence():
    p,c,e=fixture();before=copy.deepcopy((p,c,e));v=profile.reduce(p,c,e)
    assert (p,c,e)==before
    assert v['totals']['actor_clips']==12 and v['totals']['floor_applicable']==6
    assert v['totals']['context_validation_not_established']==6
    assert v['totals']['screens']['mesh_floor']==dict(passed=1,failed=5,missing=0,not_applicable=6)
    assert [x['every_eligible_actor_seed_fails_mesh_floor'] for x in v['cases']]==[False,True,False]
    assert v['cases'][2]['actor_clips']==6 and v['cases'][2]['actors']==['A','B']
    assert all(v[k] is False for k in ['engine_executed','human_reviewed','quality_approved','release_approved','held_out_release_evidence'])
    assert len(v['families'])==3 and v['totals']['semantic_reviews_verified']==0


def test_missing_exports_and_diagnostics_stay_in_denominator():
    p,c,e=fixture();r=c['rows'][0];r['exported']=False;c['exported']-=1
    for metric,flag in profile.SCREENS.values():r[metric]=r[flag]=None
    v=profile.reduce(p,c,e)
    assert v['totals']['actor_clips']==12 and v['totals']['missing_exports']==1
    assert v['totals']['screens']['mesh_floor']==dict(passed=1,failed=4,missing=1,not_applicable=6)
    assert not v['cases'][0]['every_eligible_actor_seed_fails_mesh_floor']


@pytest.mark.parametrize('change',[
    lambda p,c,e:c['rows'].pop(),
    lambda p,c,e:c['rows'].__setitem__(1,copy.deepcopy(c['rows'][0])),
    lambda p,c,e:c['rows'][0].update(case='unknown'),
    lambda p,c,e:c['rows'][0].update(actor='unknown'),
    lambda p,c,e:c['rows'][0].update(seed=4),
    lambda p,c,e:c['rows'][0].update(seed=True),
    lambda p,c,e:c['rows'][0].update(family='other'),
    lambda p,c,e:c['rows'][0].update(scene_validation='invented pass'),
    lambda p,c,e:c['rows'][0].update(context='chair'),
    lambda p,c,e:c['rows'][0].update(flat_floor_screen_applicable=1),
    lambda p,c,e:c['rows'][0].update(exported=1),
    lambda p,c,e:c['rows'][0].update(mesh_floor_screen=True),
    lambda p,c,e:c['rows'][0].update(mesh_floor_screen=None),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=None),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=float('nan')),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=float('inf')),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=True),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=-.01),
    lambda p,c,e:c['rows'][0].update(mesh_floor_depth_m=10**1000),
    lambda p,c,e:c['rows'][0].pop('mesh_floor_depth_m'),
    lambda p,c,e:c['rows'][0].pop('semantic_rating'),
    lambda p,c,e:c['rows'][-1].update(mesh_floor_screen=False),
    lambda p,c,e:c['rows'][0].update(independent_human_review=True),
    lambda p,c,e:c['rows'][0].update(semantic_rating=5),
    lambda p,c,e:c['rows'][0].update(quality_approved=True),
    lambda p,c,e:c.update(quality_approved=True),
    lambda p,c,e:c.update(exported=11),
    lambda p,c,e:c.update(planned_actor_clips=11),
    lambda p,c,e:p.update(expected_cases=True),
    lambda p,c,e:p.update(schema=True),
    lambda p,c,e:p.update(screens=None),
    lambda p,c,e:p['cases'].__setitem__(0,None),
    lambda p,c,e:p['cases'][0]['seeds'].append(1),
    lambda p,c,e:p['cases'][0]['actors'].append(dict(id='A')),
    lambda p,c,e:p['cases'][0].update(context='water'),
    lambda p,c,e:e.update(surface_threshold_m=.03),
    lambda p,c,e:e.update(surface_threshold_m=True),
])
def test_changed_or_incomplete_saved_evidence_rejects(change):
    p,c,e=fixture();change(p,c,e)
    with pytest.raises(ValueError):profile.reduce(p,c,e)


def save_inputs(tmp_path):
    values=fixture();paths=[];hashes={}
    for name,value in zip(['protocol','coverage','execution'],values):
        path=tmp_path/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8');paths.append(path)
        hashes[name+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return paths,hashes


def test_pinned_source_snapshots_and_immutable_output(tmp_path):
    paths,hashes=save_inputs(tmp_path);out=tmp_path/'result';v=profile.run(*paths,out,**hashes)
    assert v['complete_saved_population'] and not v['export_artifact_hashes_revalidated']
    for source,name in zip(paths,['protocol','coverage','execution']):assert source.read_bytes()==(out/(name+'.json')).read_bytes()
    with pytest.raises(ValueError,match='Fresh'):profile.run(*paths,out,**hashes)


def test_changed_source_binding_rejects_before_output(tmp_path):
    paths,hashes=save_inputs(tmp_path);paths[1].write_text('{}')
    with pytest.raises(ValueError,match='Changed'):profile.run(*paths,tmp_path/'result',**hashes)
    assert not (tmp_path/'result').exists()


def test_invalid_top_level_json_object_rejects(tmp_path):
    paths,hashes=save_inputs(tmp_path);paths[0].write_text('[]')
    hashes['protocol_sha256']=hashlib.sha256(paths[0].read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='JSON objects'):profile.run(*paths,tmp_path/'result',**hashes)
    assert not (tmp_path/'result').exists()


def test_complete_byte_and_population_budgets(tmp_path,monkeypatch):
    paths,hashes=save_inputs(tmp_path);monkeypatch.setattr(profile,'MAX_BYTES',1)
    with pytest.raises(ValueError,match='bounded'):profile.run(*paths,tmp_path/'result',**hashes)
    p,c,e=fixture();monkeypatch.setattr(profile,'MAX_ROWS',11)
    with pytest.raises(ValueError,match='budget'):profile.reduce(p,c,e)


def test_mid_reduction_mutation_prevents_complete_output(tmp_path,monkeypatch):
    paths,hashes=save_inputs(tmp_path);original=profile.reduce
    def changed(*args):
        result=original(*args);paths[1].write_text('{}');return result
    monkeypatch.setattr(profile,'reduce',changed)
    with pytest.raises(ValueError,match='changed during'):profile.run(*paths,tmp_path/'result',**hashes)
    assert not (tmp_path/'result').exists()


@pytest.mark.parametrize('change_method',[False,True])
def test_mutation_during_snapshotting_preserves_partial_output(tmp_path,monkeypatch,change_method):
    paths,hashes=save_inputs(tmp_path);out=tmp_path/'result'
    method=tmp_path/'synthetic-method.py';method.write_bytes(b'original synthetic method')
    monkeypatch.setattr(profile,'__file__',str(method))
    original=Path.mkdir
    def altered(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        if self==out:
            if change_method:method.write_bytes(b'changed synthetic method')
            else:paths[1].write_text('{}')
        return result
    monkeypatch.setattr(Path,'mkdir',altered)
    with pytest.raises(ValueError,match='before completion'):profile.run(*paths,out,**hashes)
    assert out.exists() and (out/'coverage.json').exists() and not (out/'result.json').exists()
