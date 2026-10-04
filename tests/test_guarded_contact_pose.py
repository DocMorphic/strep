"""Passing contacts cannot be traded for lower aggregate pose error."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import guarded_contact_pose as guarded
from native_contact_pose import ContactPose
from native_scene_contacts import SceneContacts
from test_native_scene_geometry import closed_fixture
from test_native_surface_contact import policy as surface_policy
from native_surface_contact import normals
from native_scene_geometry import faces_for
from strep import save, sha256


def fixture(tmp_path):
    _,path,spec=closed_fixture(tmp_path)
    spec['contacts'][0]['mode']='touch';spec['contacts'][0]['interval_s']=[1.,1.]
    spec['contacts'][0]['limits']=dict(position_m=.5)
    source_scene=SceneContacts(spec,tmp_path);actor=source_scene.actors['A'];world=actor['sampler'].sample(1.)
    vertices=actor['rig'].vertices(world);spec['contacts'][0]['target']['points_m']=[vertices[0].tolist()]
    spec['objects']['far-object']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.1),
        keyframes=[dict(time_s=t,translation_m=[10.,10.,10.],rotation_xyzw=[0.,0.,0.,1.]) for t in [0.,2.]])
    save(path,spec);digest=sha256(path);surface=surface_policy(path,spec)
    normal=normals(vertices,faces_for(actor['rig'])[0],[[0]],minimum_area=1e-14,minimum_coherence=.1)[0]['normal_world']
    axis=vertices[0]-world[3,:3,3];axis/=np.linalg.norm(axis)
    surface['contacts'][spec['contacts'][0]['id']]['target_normal']['normals']=[Rotation.from_rotvec(axis*np.deg2rad(80)).apply(-np.asarray(normal)).tolist()]
    permission=dict(schema='strep-native-contact-pose-permissions-v1',contacts_sha256=digest,actors=dict(A=dict(
        rotation_tracks=[dict(node=3,maximum_change_degrees=45.)],maximum_joint_displacement_m=.22)))
    problem=ContactPose(SceneContacts(spec,tmp_path),surface,digest,1.,permission)
    policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=digest,
        clock=dict(mode='explicit',times_s=[0.,2.]),limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),planes={})
    return problem,policy,digest


def test_each_passing_or_failed_row_is_protected_even_when_total_score_improves():
    before=np.array([1.,-1.,.2]);geometry=dict(sampled_conditions_pass=True)
    assert guarded.acceptable(before,np.array([.9,-.1,.1]),geometry)
    assert not guarded.acceptable(before,np.array([.1,.001,.1]),geometry)
    assert not guarded.acceptable(before,np.array([.1,-1.,.21]),geometry)
    assert not guarded.acceptable(before,before,geometry)
    assert not guarded.acceptable(before,np.zeros(3),dict(sampled_conditions_pass=False))


@pytest.mark.parametrize('fault',['shape','nan','empty'])
def test_invalid_condition_populations_reject(fault):
    before=np.array([1.,-1.]);after=before.copy()
    if fault=='shape':after=after[:1]
    if fault=='nan':after[0]=np.nan
    if fault=='empty':before=after=np.array([])
    with pytest.raises(ValueError):guarded.acceptable(before,after,dict(sampled_conditions_pass=True))


def test_pose_view_preserves_sources_and_both_endpoint_samples(tmp_path):
    problem,policy,digest=fixture(tmp_path);before=problem.scene.actors['A']['sampler'].sample(1.)
    worlds,_=problem.worlds(np.ones(problem.size)*.1);view=guarded.PosedScene(problem,worlds)
    np.testing.assert_array_equal(view.actors['A']['sampler'].sample(1.),worlds['A'])
    for stamp in [0.,2.]:np.testing.assert_array_equal(view.actors['A']['sampler'].sample(stamp),problem.scene.actors['A']['sampler'].sample(stamp))
    np.testing.assert_array_equal(problem.scene.actors['A']['sampler'].sample(1.),before)
    pose_policy=guarded.pose_policy(problem,policy,digest)
    assert policy['clock']['times_s']==[0.,2.] and pose_policy['clock']['times_s']==[0.,1.,2.]


def test_actual_synthetic_complete_triangle_audits_gate_retained_pose(tmp_path):
    problem,policy,digest=fixture(tmp_path);observed=[]
    def observe(label,value,contacts,geometry,arrays):
        assert geometry['times_s']==[0.,1.,2.] and len(geometry['samples'])==3
        assert len(geometry['samples'][1]['actor_objects'])==1
        assert arrays['frame_1_A_far-object_depth_upper_m'].shape[0]==len(problem.faces['A'])
        observed.append(label)
    candidate,result=guarded.fit(problem,policy,digest,iterations=2,solve_iterations=10,observer=observe)
    assert result['original_condition_rows_preserved'] and result['full_declared_three_pose_geometry_pass']
    assert result['final_score'][1]<result['initial_score'][1]
    assert observed[0]=='seed' and observed[-1]=='final' and result['trials']
    assert all(not t['accepted'] or (t['row_guard_pass'] and t['full_geometry_pass']) for t in result['trials'])
    assert not result['temporal_constraints_checked'] and not result['quality_approved'] and not result['release_approved']
    assert np.any(candidate!=0)


def test_failed_full_geometry_rejects_every_backoff_and_keeps_source(tmp_path,monkeypatch):
    problem,policy,digest=fixture(tmp_path);original=guarded.audit
    def failed(candidate_problem,value,*args):
        contacts,full,arrays=original(candidate_problem,value,*args)
        if np.any(value!=0):full['sampled_conditions_pass']=False
        return contacts,full,arrays
    monkeypatch.setattr(guarded,'audit',failed)
    candidate,result=guarded.fit(problem,policy,digest,iterations=1,solve_iterations=10)
    np.testing.assert_array_equal(candidate,np.zeros(problem.size))
    assert len(result['trials'])==6 and not any(t['accepted'] for t in result['trials'])
    assert result['iteration_budget_exhausted'] and result['budget_exhausted']


def test_incomplete_starting_geometry_rejects_before_search(tmp_path,monkeypatch):
    problem,policy,digest=fixture(tmp_path);original=guarded.audit
    def unavailable(*args):
        contacts,full,arrays=original(*args);full['sampled_conditions_pass']=False
        return contacts,full,arrays
    monkeypatch.setattr(guarded,'audit',unavailable)
    with pytest.raises(ValueError,match='source start'):guarded.fit(problem,policy,digest)


def test_budget_exhaustion_returns_only_an_audited_retained_pose(tmp_path):
    problem,policy,digest=fixture(tmp_path)
    candidate,result=guarded.fit(problem,policy,digest,maximum_calls=1)
    assert result['budget_exhausted'] and result['proposal_measurement_calls']==1
    assert result['full_declared_three_pose_geometry_pass'] and result['original_condition_rows_preserved']
    np.testing.assert_array_equal(candidate,np.zeros(problem.size))


@pytest.mark.parametrize('option,value',[('iterations',True),('iterations',17),('trust',0.),('solve_iterations',0),('maximum_calls',0),('maximum_surface_rows',0)])
def test_invalid_search_budgets_reject(tmp_path,option,value):
    problem,policy,digest=fixture(tmp_path)
    with pytest.raises(ValueError):guarded.fit(problem,policy,digest,**{option:value})
