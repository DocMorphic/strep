"""Actual native exports and motion-rate failures behind pose lifting."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pose_lift import PoseLift,knot_balls,fit
from native_contact_pose import ContactPose
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from test_native_contact_pose import prepare
from strep import sha256,save


def fixture(tmp_path, *, protected=None, times=(1.,)):
    spec,path,scene,policy,permission=prepare(tmp_path)
    if len(times)>1:
        spec['contacts'][0].update(mode='hold',interval_s=[min(times),max(times)],limits=dict(position_m=.5,relative_speed_m_s=.5))
        save(path,spec);scene=SceneContacts(spec,tmp_path);policy['contacts_sha256']=permission['contacts_sha256']=sha256(path)
    native=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        window_s=[0.,2.],protected_s=protected or [],knots_s=[0.,*times,2.],
        tracks=[dict(node=0,path='rotation',maximum_change=45.)],maximum_joint_displacement_m=.22)))
    edits=SceneEdits(native,scene,sha256(path),rotation_storage_policy='source-scale')
    poses=[ContactPose(scene,policy,sha256(path),stamp,permission) for stamp in times]
    targets=[(pose,np.array([.1,.2,-.05])) for pose in poses]
    return spec,path,native,scene,edits,poses,PoseLift(edits,targets)


def test_every_knot_and_complete_native_key_respects_vector_bound(tmp_path):
    _,_,_,_,edits,_,problem=fixture(tmp_path)
    raw=np.ones(problem.size)*20;value=knot_balls(raw,problem.size)
    assert np.all(np.linalg.norm(value.reshape(-1,3),axis=1)<1)
    for entry in edits.actors['A']['tracks']:
        assert np.all(np.linalg.norm(entry['weights']@value[entry['controls']],axis=1)<1)
    out=tmp_path/'bounded.glb';edits.export('A',value,out)
    assert edits.audit('A',out,0)['passed']
    np.testing.assert_array_equal(knot_balls(np.zeros(problem.size),problem.size),np.zeros(problem.size))


@pytest.mark.parametrize('raw',[[],[float('nan'),0.,0.],[21.,0.,0.],[0.,0.]])
def test_invalid_raw_controls_reject(raw):
    with pytest.raises(ValueError):knot_balls(raw,3)


def test_actual_saved_curve_matches_target_and_preserves_protected_source_data(tmp_path):
    _,_,_,scene,edits,_,problem=fixture(tmp_path)
    source_hashes=scene.inputs.copy();value,result=fit(problem,evaluations=20)
    output=tmp_path/'curve.glb';edits.export('A',value,output)
    _,decoded=problem.decoded(dict(A=output))
    assert decoded['native_payload_and_edit_limits_pass'] and decoded['maximum_angular_error_degrees']<1e-4
    assert result['quantized_target_report']['maximum_angular_error_degrees']==pytest.approx(decoded['maximum_angular_error_degrees'],abs=1e-10)
    candidate=RigAsset.load(output);sampler=NativeSupportSampler(candidate.document,candidate.binary,0)
    for before,after in zip(scene.actors['A']['sampler'].channels,sampler.channels):
        assert before[:2]==after[:2] and before[4]==after[4];np.testing.assert_array_equal(before[2],after[2])
        if before[:2]==(0,'rotation'):np.testing.assert_array_equal(before[3][[0,-1]],after[3][[0,-1]])
        else:np.testing.assert_array_equal(before[3],after[3])
    assert scene.inputs==source_hashes and all(sha256(p)==d for p,d in source_hashes.items())
    assert not decoded['temporal_constraints_checked'] and not decoded['quality_approved'] and not result['release_approved']


def test_good_pose_match_can_fail_original_motion_rate_conditions(tmp_path):
    _,_,_,scene,edits,_,problem=fixture(tmp_path)
    motion=SceneProblem(scene,edits);source_caps=[c.copy() for c in motion.caps['A'].caps]
    value,_=fit(problem,evaluations=20);output=tmp_path/'rate-failure.glb';edits.export('A',value,output)
    assert problem.decoded(dict(A=output))[1]['maximum_angular_error_degrees']<1e-4
    conditions,_=motion.decoded(dict(A=output),value)
    assert np.any(conditions[:motion.protected_rows]>0)
    for before,after in zip(source_caps,motion.caps['A'].caps):np.testing.assert_array_equal(before,after)


def test_protected_target_is_preserved_even_if_requested_pose_is_unreachable(tmp_path):
    _,_,_,scene,edits,_,problem=fixture(tmp_path,protected=[[1.,1.]])
    value,result=fit(problem,evaluations=5);output=tmp_path/'protected.glb';edits.export('A',value,output)
    rig=RigAsset.load(output);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    np.testing.assert_array_equal(sampler.sample(1.),scene.actors['A']['sampler'].sample(1.))
    assert result['quantized_target_report']['maximum_angular_error_degrees']>9
    assert not result['quality_approved'] and not result['release_approved']


def test_two_explicit_pose_targets_keep_complete_population_and_timing(tmp_path):
    _,_,_,_,edits,_,problem=fixture(tmp_path,times=(.8,1.2))
    value,result=fit(problem,evaluations=30);output=tmp_path/'two.glb';edits.export('A',value,output)
    _,decoded=problem.decoded(dict(A=output))
    assert [r['time_s'] for r in decoded['targets']]==[.8,1.2]
    assert decoded['maximum_angular_error_degrees']<1e-3
    assert len(result['history'])>1 and result['maximum_knot_norm']<1


def test_budgets_retain_observed_seed_without_fabricated_solver_success(tmp_path):
    _,_,_,_,_,_,problem=fixture(tmp_path)
    value,result=fit(problem,maximum_calls=1)
    np.testing.assert_array_equal(value,np.zeros(problem.size))
    assert result['objective_calls']==1 and result['budget_exhausted'] and result['time_or_call_budget_exhausted'] and not result['solver_success']
    _,evaluation=fit(problem,evaluations=1)
    assert evaluation['evaluation_budget_exhausted'] and evaluation['budget_exhausted'] and not evaluation['solver_success']


@pytest.mark.parametrize('fault',['empty','duplicate-time','other-source','track-population','translation','outside-window','missing-file'])
def test_ambiguous_or_incompatible_pose_transfer_rejects(tmp_path,fault):
    spec,path,native,scene,edits,poses,problem=fixture(tmp_path)
    targets=[(poses[0],np.zeros(poses[0].size))]
    if fault=='missing-file':
        with pytest.raises(ValueError):problem.decoded({})
        return
    if fault=='empty':targets=[]
    if fault=='duplicate-time':targets*=2
    if fault=='other-source':poses[0].scene=SceneContacts(spec,tmp_path)
    if fault=='track-population':poses[0].edits[0]['node']=3
    if fault=='translation':edits.actors['A']['tracks'][0]['path']='translation'
    if fault=='outside-window':edits.actors['A']['window']=np.array([1.,2.])
    with pytest.raises(ValueError):PoseLift(edits,targets)


def test_source_mutation_rejects_before_fit(tmp_path):
    _,_,_,scene,_,_,problem=fixture(tmp_path);source=Path(next(iter(scene.inputs)));source.write_bytes(source.read_bytes()+b'mutation')
    with pytest.raises(ValueError):fit(problem)


def test_parent_and_child_targets_transfer_as_local_rotations(tmp_path):
    spec,path,native,scene,_,poses,_=fixture(tmp_path)
    from test_native_surface_contact import policy as surface_policy
    permission=dict(schema='strep-native-contact-pose-permissions-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        rotation_tracks=[dict(node=n,maximum_change_degrees=45.) for n in [0,3]],maximum_joint_displacement_m=.22)))
    pose=ContactPose(scene,surface_policy(path,spec),sha256(path),1.,permission)
    native['actors']['A']['tracks']=[dict(node=n,path='rotation',maximum_change=45.) for n in [0,3]]
    edits=SceneEdits(native,scene,sha256(path));problem=PoseLift(edits,[(pose,np.array([.1,.2,0.,-.2,.1,.1]))])
    value,_=fit(problem,evaluations=25);output=tmp_path/'hierarchy.glb';edits.export('A',value,output)
    _,report=problem.decoded(dict(A=output))
    assert [r['node'] for r in report['targets']]==[0,3] and report['maximum_angular_error_degrees']<1e-4


def test_two_edited_actors_transfer_without_editing_a_third_actor(tmp_path):
    spec,path,native,_,_,_,_=fixture(tmp_path)
    from test_native_surface_contact import policy as surface_policy
    for name in ('B','C'):spec['actors'][name]=copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m']=[3.,0.,0.];spec['actors']['C']['placement']['translation_m']=[6.,0.,0.]
    save(path,spec);scene=SceneContacts(spec,tmp_path);native['contacts_sha256']=sha256(path)
    native['actors']['B']=copy.deepcopy(native['actors']['A']);edits=SceneEdits(native,scene,sha256(path))
    declaration=dict(rotation_tracks=[dict(node=0,maximum_change_degrees=45.)],maximum_joint_displacement_m=.22)
    permission=dict(schema='strep-native-contact-pose-permissions-v1',contacts_sha256=sha256(path),actors={n:copy.deepcopy(declaration) for n in ('A','B')})
    pose=ContactPose(scene,surface_policy(path,spec),sha256(path),1.,permission)
    unchanged=scene.actors['C']['sampler'].sample(1.).copy()
    problem=PoseLift(edits,[(pose,np.array([.1,.2,0.,-.1,0.,.2]))]);value,_=fit(problem,evaluations=25)
    files={n:tmp_path/(n+'.glb') for n in edits.actors}
    for name,output in files.items():edits.export(name,value,output)
    _,report=problem.decoded(files)
    assert {r['actor'] for r in report['targets']}=={'A','B'} and report['maximum_angular_error_degrees']<1e-4
    np.testing.assert_array_equal(scene.actors['C']['sampler'].sample(1.),unchanged)
    assert not (tmp_path/'C.glb').exists()


@pytest.mark.parametrize('key,value',[('evaluations',True),('evaluations',301),('maximum_calls',0),('maximum_seconds',0.)])
def test_invalid_search_budget_rejects(tmp_path,key,value):
    *_,problem=fixture(tmp_path)
    with pytest.raises(ValueError):fit(problem,**{key:value})
