"""Moving grips preserve the original prop epoch and all derivative columns."""
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from native_coupled_mesh_prop_pose import CoupledGripPose
from native_mesh_prop_pose import GripPoseEdit
from strep import save,sha256
from test_native_mesh_prop_pose import setup


def fixture(tmp_path):
    pp,_,_,_,permissions=setup(tmp_path);edit=GripPoseEdit(pp)
    return CoupledGripPose(edit),pp,permissions


def test_zero_pose_bytes_and_fixed_target_match_original_map(tmp_path):
    model,_,_=fixture(tmp_path);edit=model.edit
    zero=model.evaluate([0.,0,0,0],edit._pivot)
    assert zero['position_m'].tobytes()==edit._position.tobytes() and zero['rotation_xyzw'].tobytes()==np.asarray(edit._item['keyframes'][edit._key]['rotation_xyzw'],float).tobytes()
    value=[.03,-.04,.05,.3];actual=model.evaluate(value,edit._pivot);original=edit.evaluate(value)
    np.testing.assert_array_equal(actual['position_m'],original['position_m']);np.testing.assert_array_equal(actual['rotation_matrix'],original['rotation_matrix'])
    assert actual['report']['native_prop_pose_permissions_pass'] and not actual['report']['character_permissions_verified'] and not actual['report']['release_approved']


@pytest.mark.parametrize('controls',[[0.,0,0,0],[.1,-.2,.03,.4],[-.4,.3,.1,.7]])
def test_full_body_and_prop_derivatives_match_independent_perturbations(tmp_path,controls):
    model,_,_=fixture(tmp_path);edit=model.edit;matrix=np.random.default_rng(17).normal(size=(3,7))*.03;target=edit._pivot+[.01,-.02,.03];local=edit.scene._props[edit._name]['asset'].vertices_m
    points,jac,pose=model.points(controls,target,local,target_jacobian=matrix)
    for column in range(11):
        delta=np.eye(11)[column];h=1e-6;outputs=[];rotations=[];positions=[]
        for sign in [1,-1]:
            # Interior clearance for two-sided differences at the zero point.
            current=np.asarray(controls,float).copy();current[3]=.5 if current[3]==0 else current[3]
            response=model.evaluate(current+sign*h*delta[7:],target+sign*h*(matrix@delta[:7]));outputs.append(local@response['rotation_matrix'].T+response['position_m']);rotations.append(response['rotation_matrix']);positions.append(response['position_m'])
        middle=np.asarray(controls,float).copy();middle[3]=.5 if middle[3]==0 else middle[3];_,expected,base=model.points(middle,target,local,target_jacobian=matrix)
        np.testing.assert_allclose((outputs[0]-outputs[1])/(2*h),expected[:,:,column],atol=2e-9,rtol=1e-6)
        np.testing.assert_allclose((rotations[0]-rotations[1])/(2*h),base['rotation_jacobian'][:,:,column],atol=2e-9,rtol=1e-6)
    assert jac.shape==(len(local),3,11) and pose['report']['body_columns']==7


def test_hand_motion_moves_box_without_resetting_original_centre_limit(tmp_path):
    model,_,_=fixture(tmp_path);edit=model.edit;value=[.03,-.02,.01,.2];first=model.evaluate(value,edit._pivot);shift=np.array([.01,.02,-.01]);moved=model.evaluate(value,edit._pivot+shift)
    np.testing.assert_allclose(moved['position_m']-first['position_m'],shift,atol=1e-16,rtol=0)
    assert moved['report']['translation_change_m']==np.linalg.norm(moved['position_m']-edit._position)
    assert moved['report']['translation_cap_m']==edit._translation
    rejected=model.evaluate([0.,0,0,0],edit._pivot+[2.,0,0]);assert not rejected['report']['native_prop_pose_permissions_pass']
    assert rejected['position_m'][0]>edit._position[0]+1 and rejected['report']['source_rebased'] is False


def test_grip_follows_target_with_original_local_clearance(tmp_path):
    model,_,_=fixture(tmp_path);edit=model.edit;target=edit._pivot+[.01,0,0];value=[.04,.03,-.02,.6]
    pose=model.evaluate(value,target);world=pose['position_m']+pose['rotation_matrix']@edit._point
    np.testing.assert_allclose(world-target,pose['rotation_matrix']@edit._direction*edit._clearance*.6,atol=2e-16,rtol=0)
    assert abs(pose['report']['target_grip_error_m']-edit._clearance*.6)<2e-16


def test_source_permissions_are_not_rebased_after_target_moves(tmp_path):
    model,pp,permissions=fixture(tmp_path);model.evaluate([0.,0,0,0],model.edit._pivot+[.02,0,0]);permissions['maximum_translation_m']=1.;save(pp,permissions)
    with pytest.raises(ValueError,match='source changed'):model.evaluate([0.,0,0,0],model.edit._pivot)


@pytest.mark.parametrize('fault',['target-shape','target-nan','target-bool','jac-shape','jac-scalar','jac-zero-columns','jac-large','jac-nan','local-shape','local-nan','budget','controls'])
def test_incomplete_or_invalid_inputs_reject(tmp_path,fault):
    model,_,_=fixture(tmp_path);target=model.edit._pivot.copy();matrix=np.zeros((3,2));local=np.eye(3);kwargs={};controls=[0.,0,0,.5]
    if fault=='target-shape':target=[0.,0.]
    elif fault=='target-nan':target=np.full(3,np.nan)
    elif fault=='target-bool':target=np.ones(3,dtype=bool)
    elif fault=='jac-shape':matrix=np.zeros((2,3))
    elif fault=='jac-scalar':matrix=0.
    elif fault=='jac-zero-columns':matrix=np.zeros((3,0))
    elif fault=='jac-large':matrix=np.zeros((3,765))
    elif fault=='jac-nan':matrix[0,0]=np.nan
    elif fault=='local-shape':local=np.zeros((2,4))
    elif fault=='local-nan':local[0,0]=np.nan
    elif fault=='budget':kwargs['maximum_jacobian_bytes']=1
    else:controls=[1.,1.,1.,2.]
    with pytest.raises(ValueError):model.points(controls,target,local,target_jacobian=matrix,**kwargs)


def test_complete_last_body_column_and_duplicate_points_are_retained(tmp_path):
    model,_,_=fixture(tmp_path);matrix=np.zeros((3,764));matrix[:,-1]=[1.,2.,3.];local=np.zeros((2,3));values,jac,pose=model.points([0.,0,0,0],model.edit._pivot,local,target_jacobian=matrix)
    assert jac.shape==(2,3,768) and pose['report']['complete_columns']==768
    np.testing.assert_array_equal(jac[:,:,-5],np.tile([1.,2.,3.],(2,1)));np.testing.assert_array_equal(values[0],values[1])


def test_locked_prop_components_have_zero_derivatives(tmp_path):
    _,pp,permissions=fixture(tmp_path);permissions['maximum_rotation_degrees']=permissions['maximum_clearance_m']=0.;save(pp,permissions);model=CoupledGripPose(GripPoseEdit(pp));pose=model.evaluate([0.,0,0,0],model.edit._pivot,target_jacobian=np.eye(3))
    assert not np.any(pose['rotation_jacobian']) and not np.any(pose['position_jacobian'][:,3:]);np.testing.assert_array_equal(pose['position_jacobian'][:,:3],np.eye(3))
