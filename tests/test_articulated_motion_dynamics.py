import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from articulated_motion_dynamics import diagnose


def fixture():
    def body(name,parent,own,anchor):return dict(id=name,parent=parent,mass_kg=1.,inertia_body_about_com_kg_m2=(np.eye(3)*.1).tolist(),
        joint_from_own_com_local_m=own,joint_from_parent_com_local_m=anchor,provenance='Explicit analytical two-link test. No human assumptions.')
    profile=[body('first',None,[-.5,0,0],None),body('second','first',[-.5,0,0],[.5,0,0])]
    p=np.tile([[.5,0,0],[1.5,0,0]],(5,1,1));q=np.tile([0.,0,0,1],(5,2,1));force=np.zeros((5,2,3));torque=force.copy()
    args=dict(fps=30,gravity_world_m_s2=[0.,-10.,0.],phases=[dict(id='known',start_frame=0,end_frame_exclusive=5,support_assumption='supported')],
        anchor_tolerance_m=1e-6,force_tolerance_N=1e-6,torque_tolerance_Nm=1e-6)
    return profile,p,q,force,torque,args


def test_analytical_two_link_joint_loads_and_unsupported_floating_root():
    profile,p,q,f,t,args=fixture();r=diagnose(profile,p,q,f,t,**args)
    np.testing.assert_allclose(r['required_parent_on_body_force_world_N'],np.tile([[0,20,0],[0,10,0]],(3,1,1)))
    np.testing.assert_allclose(r['required_parent_on_body_torque_about_joint_world_Nm'],np.tile([[0,0,20],[0,0,5]],(3,1,1)))
    assert r['assessed_samples']==3 and r['floating_root_wrench_consistent_samples']==0
    assert not r['capacities_evaluated'] and not r['quality_approved'] and not r['release_approved']


def test_explicit_external_wrench_can_balance_root_without_erasing_internal_loads():
    profile,p,q,f,t,args=fixture();f[:,0,1]=20;t[:,0,2]=10;r=diagnose(profile,p,q,f,t,**args)
    np.testing.assert_allclose(r['residual_floating_root_force_world_N'],0,atol=1e-12)
    np.testing.assert_allclose(r['residual_floating_root_torque_world_Nm'],0,atol=1e-12)
    np.testing.assert_allclose(np.array(r['required_parent_on_body_torque_about_joint_world_Nm'])[:,1,2],5)
    assert r['floating_root_wrench_consistent_samples']==3 and r['physical_approval'] is None and not r['training_admitted']


def test_world_coordinate_rotation_and_translation_preserve_demands():
    profile,p,q,f,t,args=fixture();baseline=diagnose(profile,p,q,f,t,**args);rotation=Rotation.from_rotvec([.3,-.2,.4]);matrix=rotation.as_matrix()
    p=p@matrix.T+[10.,2.,-3.];q=np.tile(rotation.as_quat(),(5,2,1));args['gravity_world_m_s2']=(matrix@args['gravity_world_m_s2']).tolist()
    r=diagnose(profile,p,q,f,t,**args)
    for key in ['required_parent_on_body_force_world_N','required_parent_on_body_torque_about_joint_world_Nm']:
        np.testing.assert_allclose(r[key],np.asarray(baseline[key])@matrix.T,atol=1e-10)


def test_body_order_is_not_a_topological_assumption():
    profile,p,q,f,t,args=fixture();r=diagnose(profile[::-1],p[:,::-1],q[:,::-1],f[:,::-1],t[:,::-1],**args)
    assert r['root']=='first'
    np.testing.assert_allclose(np.array(r['required_parent_on_body_torque_about_joint_world_Nm'])[:,::-1],np.tile([[0,0,20],[0,0,5]],(3,1,1)))


def test_returned_assumptions_and_complete_wrenches_do_not_alias_caller_data():
    profile,p,q,f,t,args=fixture();r=diagnose(profile,p,q,f,t,**args)
    profile[0]['mass_kg']=99;p[0,0,0]=123;f[0,0,0]=42
    assert r['profile'][0]['mass_kg']==1 and r['world_com_positions_m'][0][0][0]==.5 and r['external_forces_world_N'][0][0][0]==0
    assert r['numerical_tolerances']==dict(anchor_m=1e-6,force_N=1e-6,torque_Nm=1e-6)


def test_phase_boundaries_unknowns_and_endpoints_cannot_pass_by_omission():
    profile,p,q,f,t,args=fixture();args['phases']=[dict(id='unknown',start_frame=0,end_frame_exclusive=2,support_assumption='unknown'),dict(id='known',start_frame=2,end_frame_exclusive=5,support_assumption='supported')]
    r=diagnose(profile,p,q,f,t,**args);assert r['assessed_samples']==1 and [s['assessed'] for s in r['samples']]==[False,False,True]
    assert r['unestimated_endpoint_frames']==[0,4] and not r['all_assessed_floating_root_wrenches_consistent']
    args['phases']=[dict(id='unknown',start_frame=0,end_frame_exclusive=5,support_assumption='unknown')]
    r=diagnose(profile,p,q,f,t,**args);assert r['assessed_samples']==0 and not r['all_assessed_floating_root_wrenches_consistent']


def test_nonprincipal_constant_spin_requires_gyroscopic_torque():
    profile,p,q,f,t,args=fixture();profile=profile[:1];profile[0]['joint_from_own_com_local_m']=[0,0,0];profile[0]['inertia_body_about_com_kg_m2']=np.diag([1.,2.,2.5]).tolist()
    omega=np.array([.2,.3,.4]);clock=np.arange(5)/30;rotation=Rotation.from_rotvec(clock[:,None]*omega)
    p=np.zeros((5,1,3));q=rotation.as_quat()[:,None];f=np.zeros((5,1,3));t=f.copy();args['gravity_world_m_s2']=[0.,0,0]
    r=diagnose(profile,p,q,f,t,**args);matrices=rotation.as_matrix()[1:-1];inertia=matrices@np.diag([1.,2.,2.5])@matrices.transpose(0,2,1)
    expected=np.cross(omega,np.einsum('fij,j->fi',inertia,omega))
    np.testing.assert_allclose(np.array(r['required_parent_on_body_torque_about_joint_world_Nm'])[:,0],expected,atol=1e-10)
    assert r['floating_root_wrench_consistent_samples']==0


@pytest.mark.parametrize('bad',['cycle','missing_parent','two_roots','anchor_disconnect','inertia','mass','missing_force','quaternion','fps','tolerance','nonfinite','provenance'])
def test_incomplete_or_inconsistent_physical_model_is_rejected(bad):
    profile,p,q,f,t,args=fixture()
    if bad=='cycle':profile[0]['parent']='second';profile[0]['joint_from_parent_com_local_m']=[.5,0,0]
    if bad=='missing_parent':profile[1]['parent']='absent'
    if bad=='two_roots':profile[1]['parent']=None;profile[1]['joint_from_parent_com_local_m']=None
    if bad=='anchor_disconnect':p[:,1,0]+=.01
    if bad=='inertia':profile[1]['inertia_body_about_com_kg_m2']=np.diag([1.,1.,3.]).tolist()
    if bad=='mass':profile[1]['mass_kg']=0
    if bad=='missing_force':f=f[:,:1]
    if bad=='quaternion':q[:,:,3]=2
    if bad=='fps':args['fps']=True
    if bad=='tolerance':args['anchor_tolerance_m']=0
    if bad=='nonfinite':p[0,0,0]=np.nan
    if bad=='provenance':profile[0]['provenance']=''
    with pytest.raises(ValueError):diagnose(profile,p,q,f,t,**args)
