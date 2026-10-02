"""Immutable public limits and stricter optional proposal-policy construction."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_plant_headroom import reserve_policy,run


def policy():
    return dict(schema='strep-native-foot-plant-v1',source_sha256='a'*64,base_sha256='b'*64,draft_sha256='c'*64,
        supports=[dict(id='left',maximum_patch_anchor_error_m=.001,maximum_patch_speed_m_s=.005),
                  dict(id='right',maximum_patch_anchor_error_m=.002,maximum_patch_speed_m_s=.01)])


def test_reserve_tightens_each_speed_only_and_does_not_mutate_public_policy():
    public=policy();before=copy.deepcopy(public);target=reserve_policy(public,.00001)
    assert public==before and target['source_sha256']==public['source_sha256']
    assert target['base_sha256']==public['base_sha256'] and target['draft_sha256']==public['draft_sha256']
    assert [p['maximum_patch_anchor_error_m'] for p in target['supports']]==[.001,.002]
    assert [p['maximum_patch_speed_m_s'] for p in target['supports']]==pytest.approx([.00499,.00999])


@pytest.mark.parametrize('reserve',[True,-1e-6,float('nan'),float('inf'),.000100001])
def test_invalid_reserve_rejected(reserve):
    with pytest.raises(ValueError):reserve_policy(policy(),reserve)


@pytest.mark.parametrize('speed',[0,.00001,.000001])
def test_reserve_must_not_silently_clamp_or_remove_zero_speed_requirement(speed):
    public=policy();public['supports'][0]['maximum_patch_speed_m_s']=speed
    with pytest.raises(ValueError):reserve_policy(public,.00001)
    assert reserve_policy(public,0)['supports'][0]['maximum_patch_speed_m_s']==speed


@pytest.mark.parametrize('fault',['unknown','unbound','duplicate','bad_anchor','bad_speed'])
def test_invalid_original_policy_rejected(fault):
    public=policy()
    if fault=='unknown':public['extra']=True
    if fault=='unbound':public['source_sha256']='bad'
    if fault=='duplicate':public['supports'][1]['id']='left'
    if fault=='bad_anchor':public['supports'][0]['maximum_patch_anchor_error_m']=float('nan')
    if fault=='bad_speed':public['supports'][0]['maximum_patch_speed_m_s']=True
    with pytest.raises(ValueError):reserve_policy(public,.00001)


def test_actual_toy_job_preserves_source_and_full_public_audit(tmp_path):
    from test_native_foot_plant import setup
    from strep import save,sha256,read
    source,_,_,spec,draft,public,_,_=setup(tmp_path)
    path=tmp_path/'policy.json';save(path,public)
    bindings={str(p):sha256(p) for p in (source,draft,path)}
    result=run(source,source,draft,path,tmp_path/'job',iterations=1)
    assert all(sha256(p)==h for p,h in bindings.items())
    assert read(tmp_path/'job/public-policy.json')==public
    assert read(tmp_path/'job/proposal-policy.json')!=public
    assert result['public_limits_changed'] is False
    assert result['quality_approved'] is False and result['engine_contacts_verified'] is False
    assert result['native_npz_conversion_verified'] is False
    assert result['public_candidate_audit']['passed'] is False
    assert result['retained_input'] is True
    assert sha256(tmp_path/'job/fit/candidate.glb')==sha256(source)
