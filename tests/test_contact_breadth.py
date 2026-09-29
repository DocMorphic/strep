import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import study_contact_breadth as study
from strep import ROOT,read,save


def protocol():
    return read(ROOT/'benchmarks/contact-breadth-v1.json')


def test_catalog_contains_every_declared_family_and_seed_without_release_overlap():
    plan=study.validate_protocol(protocol())
    assert len(plan['cases'])==8
    assert {row['family'] for row in plan['cases']}=={'gestures','ground_movement','combat','parkour'}
    for family in {row['family'] for row in plan['cases']}:
        assert {row['seed'] for row in plan['cases'] if row['family']==family}=={11,22}
    reserved={seed for c in read(ROOT/'benchmarks/release-prompt-reservations-v1.json')['cases'] for seed in c['seeds']}
    assert not reserved.intersection(row['seed'] for row in plan['cases'])


@pytest.mark.parametrize('mutate',[
    lambda p:p['cases'].append(copy.deepcopy(p['cases'][0])),
    lambda p:p['cases'][0].update(id='../escape'),
    lambda p:p['cases'][0].update(window=[50,109]),
    lambda p:p['fit'].update(iteration_count=121),
    lambda p:p['repair'].update(trust_m=.001),
    lambda p:p.update(quality_approved=True),
])
def test_invalid_or_silently_changed_protocol_is_rejected(mutate):
    plan=protocol();mutate(plan)
    with pytest.raises(ValueError):study.validate_protocol(plan)


def test_binding_keeps_material_identity_uses_midpoint_and_does_not_mutate_source(monkeypatch):
    plan=protocol();case=plan['cases'][0]
    r=np.tile(np.eye(3),(120,1,1,1));p=np.zeros((120,1,3));p[:,0,0]=np.arange(120)*.01
    motion=dict(root_positions=p[:,0].copy(),posed_joints=p,global_rot_mats=r)
    before={k:v.copy() for k,v in motion.items()}
    skin=dict(rig_joint_names=['LeftFoot'],lbs_indices=np.zeros((2,8),int),lbs_weights=np.ones((2,8))/8,
        bind_vertices=np.array([[1.,-.001,0.],[2.,.02,0.]]),bind_rig_transform=np.eye(4)[None])
    monkeypatch.setattr(study,'regions',lambda _:dict(LeftFoot=np.array([0,1])))
    spec=study.bind_case(plan,case,motion,skin);pin=spec['regions']['LeftFoot']['segments'][0]
    assert pin['vertex_id']==0 and [pin['start_frame'],pin['end_frame']]==[50,70]
    np.testing.assert_allclose(pin['position_m'],[1.603,.002,0.])
    assert all(np.array_equal(motion[k],v) for k,v in before.items())
    assert study.bind_case(plan,case,motion,skin)==spec


def test_timing_conflict_is_retained_without_starting_a_fit(tmp_path,monkeypatch):
    plan=protocol();case=plan['cases'][0]
    save(tmp_path/'protocol.json',plan)
    save(tmp_path/'preflight.json',dict(complete=True,cases=[dict(id=case['id'],status='needs_authoring_change',conflicts=2)]))
    monkeypatch.setattr(study,'verify_suite',lambda _:None)
    monkeypatch.setattr(study,'prepare_fit',lambda *args,**kwargs:pytest.fail('Rejected timing must not launch fitting'))
    study.run_case(tmp_path,case['id'])
    result=read(tmp_path/'cases'/(case['id']+'.json'))
    assert result['status']=='timing_rejected' and result['fit_started'] is False and result['conflicts']==2
    with pytest.raises(ValueError,match='Preserve existing'):study.run_case(tmp_path,case['id'])
