import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from intentional_object_clearance import compile_policy, validate, validate_constraints, margin_tracks
from scene_solver_context import compile_context, context_primitives
from object_geometry import scene_geometry


def fixture(shape='box'):
    names=['LeftHand','LeftHandIndex1','RightHand','LeftFoot','LeftToe1','Hips']+[f'Bone{i}' for i in range(71)]
    bones=np.array([0,0,1,2,5,3,4])
    skin=dict(rig_joint_names=np.array(names),bind_vertices=np.zeros((7,3)),
        bind_rig_transform=np.tile(np.eye(4),(77,1,1)),lbs_indices=np.column_stack([bones,np.full(7,5)]),
        lbs_weights=np.tile([.8,.2],(7,1)))
    geometry={'schema':'strep-object-geometry-v1','shape':shape}
    geometry.update({'size_m':[.1,.1,.1]} if shape=='box' else {'radius_m':.05})
    if shape=='cylinder':geometry['height_m']=.1
    obj=dict(geometry=geometry,keyframes=[dict(frame=f,translation_m=[f*.01,1,0],rotation_xyzw=[0,0,0,1]) for f in [0,9]])
    scene=dict(schema_version=1,id='fixture',fps=30,frame_count=10,
        actors={'A':dict(transform=dict(translation_m=[2,0,-1],rotation_xyzw=[0,0,0,1]))},
        objects={'target':obj,'other':copy.deepcopy(obj)},contacts=[dict(id='grip',actor='A',
            effector=dict(joint='LeftHand',surface_vertex=0),target=dict(space='object',object='target',point_m=[-.05,0,0]),
            start_frame=2,end_frame=5,tolerance_m=.001)])
    return scene,skin


def native_spec(context):
    policy=context['intentional_object_clearance'];entry=policy['contacts'][0];obj=context['primitives'][0]
    clock=entry['solver_frames'];p=np.asarray(obj['positions_m']);r=np.asarray(obj['rotations'])
    track=p[clock]+np.einsum('fij,j->fi',r[clock],entry['point_m'])
    return dict(frame_count=policy['frame_count'],regions={'LeftHand':dict(mode='explicit',segments=[
        dict(start_frame=clock[0],end_frame=clock[-1],vertex_id=entry['anchor_vertex'],space='track',positions_m=track.tolist())])})


@pytest.mark.parametrize('shape',['box','sphere','cylinder'])
def test_complete_region_only_loses_buffer_for_named_object_and_solver_contact_keys(shape):
    scene,skin=fixture(shape);original=copy.deepcopy(scene)
    old=compile_context(scene,'A',['grip'],skin,release_endpoint_guards=True)
    assert 'intentional_object_clearance' not in old
    context=compile_context(scene,'A',['grip'],skin,release_endpoint_guards=True,intentional_object_contacts=True)
    policy=context['intentional_object_clearance'];assert scene==original
    validate_constraints(policy,native_spec(context),context_primitives(context))
    assert policy['contacts'][0]['region_vertices']==[0,1,2]
    assert policy['contacts'][0]['solver_frames']==[2,3,4,5,6]
    selected=np.arange(7);expected=np.full((10,7),.002);expected[2:7,:3]=0
    np.testing.assert_array_equal(margin_tracks(policy,'target',selected,.002),expected)
    np.testing.assert_array_equal(margin_tracks(policy,'other',selected,.002),np.full((10,7),.002))
    # Buffer removal never supplies a negative allowed penetration.
    assert np.min(expected)==0 and expected[1,0]==expected[7,0]==expected[3,3]==.002


def test_no_release_guard_preserves_inclusive_authored_clock_and_final_contact():
    scene,skin=fixture();policy=compile_policy(scene,'A',['grip'],skin)
    assert policy['contacts'][0]['solver_frames']==[2,3,4,5]
    scene['contacts'][0]['end_frame']=9
    context=compile_context(scene,'A',['grip'],skin,release_endpoint_guards=True,intentional_object_contacts=True)
    assert context['intentional_object_clearance']['contacts'][0]['solver_frames']==list(range(2,10))


@pytest.mark.parametrize('defect',['region','partial_region','foreign_vertex','boolean_vertex','interior_point','outside_point',
    'missing_key','extra_key','geometry','clock','unknown_object','duplicate_contact','extra_field'])
def test_invalid_or_rebound_policy_rejects(defect):
    scene,skin=fixture();policy=compile_policy(scene,'A',['grip'],skin);row=policy['contacts'][0]
    if defect=='region':row['region']='Torso'
    if defect=='partial_region':row['region_vertices']=[0]
    if defect=='foreign_vertex':row['region_vertices'].append(4)
    if defect=='boolean_vertex':row['region_vertices'][1]=True
    if defect=='interior_point':row['point_m']=[0,0,0]
    if defect=='outside_point':row['point_m']=[-.06,0,0]
    if defect=='missing_key':row['solver_frames'].remove(3)
    if defect=='extra_key':row['solver_frames'].append(8)
    if defect=='geometry':row['geometry']['size_m'][0]=.2
    if defect=='clock':policy['frame_count']=4
    if defect=='unknown_object':row['object']='missing'
    if defect=='duplicate_contact':policy['contacts'].append(copy.deepcopy(row))
    if defect=='extra_field':row['allow_penetration_m']=.002
    primitives=[(scene_geometry(obj),dict(id=name)) for name,obj in scene['objects'].items()]
    with pytest.raises(ValueError):validate(policy,skin,primitives)


@pytest.mark.parametrize('defect',['target','vertex','interval','region','object_clock'])
def test_clearance_changes_bind_to_actual_fitted_point_tracks(defect):
    scene,skin=fixture();context=compile_context(scene,'A',['grip'],skin,intentional_object_contacts=True)
    spec=native_spec(context);segment=spec['regions']['LeftHand']['segments'][0]
    if defect=='target':segment['positions_m'][1][0]+=.01
    if defect=='vertex':segment['vertex_id']=1
    if defect=='interval':segment['end_frame']=6
    if defect=='region':spec['regions']['LeftHand']['mode']='disabled'
    if defect=='object_clock':context['primitives'][0]['positions_m'].pop()
    with pytest.raises(ValueError):validate_constraints(context['intentional_object_clearance'],spec,context_primitives(context))


def test_overlap_union_and_complete_sampling_no_hidden_thinning():
    scene,skin=fixture();scene['contacts'].append(dict(scene['contacts'][0],id='second',start_frame=5,end_frame=8))
    policy=compile_policy(scene,'A',['grip','second'],skin)
    expected=np.full((10,7),.002);expected[2:9,:3]=0
    np.testing.assert_array_equal(margin_tracks(policy,'target',np.arange(7),.002),expected)
    with pytest.raises(ValueError,match='Complete'):margin_tracks(policy,'target',np.array([0,2,3,4,5,6]),.002)
    with pytest.raises(ValueError,match='Sorted'):margin_tracks(policy,'target',np.array([0,0,1,2]),.002)
    with pytest.raises(ValueError):margin_tracks(policy,'target',np.arange(7),-.001)


def test_foot_policy_and_unknown_selection_reject_without_changing_scene():
    scene,skin=fixture();scene['contacts'][0]['effector']=dict(joint='LeftFoot',surface_vertex=5)
    policy=compile_policy(scene,'A',['grip'],skin);assert policy['contacts'][0]['region_vertices']==[5,6]
    with pytest.raises(ValueError):compile_policy(scene,'A',['missing'],skin)
    with pytest.raises(ValueError):compile_policy(scene,'A',['grip','grip'],skin)
