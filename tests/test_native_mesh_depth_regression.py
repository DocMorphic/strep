"""A smaller local penetration cannot hide behind another query's larger peak."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_mesh_depth_regression import compare_depths
from native_mesh_prop_pose import conditions,metrics


def report():
    def pair(left,right,typed=True):
        result=dict(surface=dict(records=[]),vertex_containment=[dict(source=a,target=b,available=True,max_depth_m=.001) for a,b in [(left,right),(right,left)]],passed=False)
        result.update(dict(left=left,right=right) if typed else dict(actors=[left,right]))
        return result
    base=dict(time_s=0.,world_planes=[dict(actor='A',plane='floor',maximum_depth_m=.02,passed=False),dict(actor='B',plane='floor',maximum_depth_m=.001,passed=False)],
              actor_objects=[dict(actor='A',object='wall',maximum_depth_upper_m=.001,passed=False)],
              actor_pairs=[pair('A','B',False)])
    sample=dict(index=0,time_s=0.,base_scene=base,mesh_pairs=[pair(['actor','A'],['prop','box']),pair(['prop','box'],['prop','other'])],
                mesh_world_planes=[dict(prop='box',plane='floor',maximum_depth_m=.001,passed=False)],
                mesh_primitive_pairs=[dict(prop='box',object='wall',maximum_depth_upper_m=.001,passed=False)],passed=False)
    return dict(schema='strep-native-mesh-prop-geometry-result-v1',all_policy_samples_evaluated=True,complete_clock_s=[0.],times_s=[0.],sample_indices=[0],
                samples=[sample],limits={'depth_m':.0001},clock_mode='native-and-frame-populations',actor_faces={'A':12,'B':12},prop_faces={'box':12,'other':12})


def target(value,kind):
    s=value['samples'][0]
    if kind=='actor-plane':return s['base_scene']['world_planes'][1],'maximum_depth_m'
    if kind=='prop-plane':return s['mesh_world_planes'][0],'maximum_depth_m'
    if kind=='actor-primitive':return s['base_scene']['actor_objects'][0],'maximum_depth_upper_m'
    if kind=='prop-primitive':return s['mesh_primitive_pairs'][0],'maximum_depth_upper_m'
    if kind=='actor-partner':return s['base_scene']['actor_pairs'][0]['vertex_containment'][0],'max_depth_m'
    return s['mesh_pairs'][0 if kind=='actor-prop' else 1]['vertex_containment'][0],'max_depth_m'


@pytest.mark.parametrize('kind',['actor-plane','prop-plane','actor-primitive','prop-primitive','actor-partner','actor-prop','prop-prop'])
def test_local_regression_hidden_by_global_peak_is_rejected(kind):
    original=report();candidate=copy.deepcopy(original);row,key=target(candidate,kind);row[key]=.002
    assert conditions(original)==conditions(candidate) and metrics(original)==metrics(candidate)
    result=compare_depths(original,candidate)
    assert not result['passed'] and len(result['regressions'])==1 and not result['unavailable']
    assert result['maximum_increase_m']==.001
    assert not result['quality_approved'] and not result['release_approved']


def test_unchanged_and_improving_depths_are_nonregressing_without_quality_approval():
    original=report();candidate=copy.deepcopy(original)
    assert compare_depths(original,candidate)['passed']
    row,key=target(candidate,'actor-prop');row[key]=0.
    result=compare_depths(original,candidate)
    assert result['passed'] and result['observations']==11 and result['maximum_increase_m']==0
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('side',['original','candidate','both'])
def test_unavailable_containment_cannot_claim_local_nonregression(side):
    original=report();candidate=copy.deepcopy(original)
    for which in ([original,candidate] if side=='both' else [original if side=='original' else candidate]):
        row,_=target(which,'actor-prop');row['available']=False;row.pop('max_depth_m')
    result=compare_depths(original,candidate)
    assert not result['passed'] and len(result['unavailable'])==1 and not result['regressions']


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-.001,True,'0',None])
def test_invalid_depths_fail_closed(value):
    original=report();candidate=copy.deepcopy(original);row,key=target(candidate,'actor-prop');row[key]=value
    with pytest.raises(ValueError):compare_depths(original,candidate)


@pytest.mark.parametrize('fault',['partial','clock','limits','topology','index','index-list','time-list','missing-direction','duplicate-direction','missing-query','duplicate-query','missing-field'])
def test_changed_or_incomplete_comparison_population_is_rejected(fault):
    original=report();candidate=copy.deepcopy(original);s=candidate['samples'][0]
    if fault=='partial':candidate['all_policy_samples_evaluated']=False
    elif fault=='clock':candidate['complete_clock_s']=[.1]
    elif fault=='limits':candidate['limits']['depth_m']=.01
    elif fault=='topology':candidate['actor_faces']['A']=13
    elif fault=='index':s['index']=False
    elif fault=='index-list':candidate['sample_indices']=[False]
    elif fault=='time-list':candidate['times_s']=[False]
    elif fault=='missing-direction':s['mesh_pairs'][0]['vertex_containment'].pop()
    elif fault=='duplicate-direction':s['mesh_pairs'][0]['vertex_containment'][1]=copy.deepcopy(s['mesh_pairs'][0]['vertex_containment'][0])
    elif fault=='missing-query':s['mesh_world_planes']=[]
    elif fault=='duplicate-query':s['mesh_world_planes'].append(copy.deepcopy(s['mesh_world_planes'][0]))
    else:s.pop('base_scene')
    with pytest.raises(ValueError):compare_depths(original,candidate)


@pytest.mark.parametrize('recoverable',[False,True])
def test_character_correction_requires_local_depth_pass_even_when_other_geometry_passes(tmp_path,monkeypatch,recoverable):
    import action_worker_lock
    import native_mesh_character_fit as fitting
    import native_mesh_character_recovery as recovery
    from strep import read,sha256
    from test_native_mesh_character_fit import prepared
    from test_native_mesh_character_recovery import until
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'locks')
    _,permissions,policy=prepared(tmp_path);calls=[]
    original_guard=fitting.compare_depths
    def rejected_local_depth(before,after):
        result=original_guard(before,after)
        assert result['passed'] # This fixture otherwise has clean full geometry.
        calls.append(True)
        result.update(passed=False,maximum_increase_m=.001,
            regressions=[dict(time_s=1.,query=['containment','actor','A','prop','crate'],original_depth_m=0.,candidate_depth_m=.001,increase_m=.001)])
        return result
    monkeypatch.setattr(fitting,'compare_depths',rejected_local_depth)
    folder=tmp_path/'fit'
    if recoverable:
        receipt=recovery.prepare(permissions,policy,folder,iterations=1,trust=.25,backtracks=4)
        receipt=until(folder,receipt,'decision');pinned=sha256(folder/receipt['checkpoint'])
        final=recovery.finish(folder,receipt['checkpoint'],receipt['sha256'])
        assert sha256(folder/receipt['checkpoint'])==pinned
        assert recovery.verify(folder,final['checkpoint'],final['sha256'])['optimizer_completed']
    else:fitting.fit(permissions,policy,folder,iterations=1,trust=.25,backtracks=4)
    assert calls
    probes=read(folder/'probes.json');checked=[r for r in probes if r['geometry_evaluated']]
    assert checked and all(r['geometry_conditions_no_regression'] and r['geometry_metrics_no_worse'] for r in checked)
    assert all(not r['geometry_local_depths_pass'] and not r['accepted'] for r in checked)
    reports=list(folder.rglob('local-depth-regression.json'))
    assert len(reports)==len(checked) and all(not read(p)['passed'] for p in reports)
    if recoverable:
        state=read(folder/final['checkpoint'])
        assert all(state['files'][p.relative_to(folder).as_posix()]==sha256(p) for p in reports)
    result=read(folder/'result.json');assert result['accepted_steps']==0 and result['candidate'] is None
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
