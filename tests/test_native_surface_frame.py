"""Material-facing/twist constraints use geometry, including affine skin motion."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_surface_frame import measure,constraints


def data():
    p=np.array([[0.,0.,0.],[.1,0,0],[.1,.2,0],[0,.2,0]])
    faces=np.array([[0,1,2],[0,2,3]])
    s=dict(face_indices=[0,1],origin_weights=[.25]*4,proximal_weights=[.5,.5,0,0],distal_weights=[0,0,.5,.5],
        minimum_twice_area_m2=1e-12,minimum_coherence=.5,minimum_tangent_m=1e-6)
    return p,faces,s


def test_complete_material_frame_has_signed_winding_and_tangent():
    p,f,s=data();value=measure(p,np.zeros((4,3,1)),f,s)
    np.testing.assert_allclose(value['origin_m'],[.05,.1,0]);np.testing.assert_array_equal(value['normal_world'],[0,0,1]);np.testing.assert_array_equal(value['tangent_world'],[0,1,0])
    opposite=measure(p,np.zeros((4,3,1)),f[:,::-1],s)
    np.testing.assert_array_equal(opposite['normal_world'],[0,0,-1]);np.testing.assert_array_equal(opposite['tangent_world'],value['tangent_world'])


def test_full_frame_jacobian_matches_independent_finite_differences_under_nonrigid_motion():
    p,f,s=data();rng=np.random.default_rng(74);jac=rng.normal(size=(4,3,7))*.03
    p=p@np.array([[1.,.2,.1],[0,1.3,.2],[.1,.0,.9]]).T+[.3,.1,-.2]
    original=p.copy();frame=measure(p,jac,f,s);h=1e-6
    for k in range(7):
        plus=measure(p+h*jac[:,:,k],jac,f,s);minus=measure(p-h*jac[:,:,k],jac,f,s)
        for key,dkey in [('origin_m','origin_jacobian'),('normal_world','normal_jacobian'),('tangent_world','tangent_jacobian')]:
            np.testing.assert_allclose(frame[dkey][:,k],(plus[key]-minus[key])/(2*h),atol=4e-10,rtol=2e-8)
    np.testing.assert_array_equal(p,original)


@pytest.mark.parametrize('degrees,expected',[(0,True),(4,True),(6,False),(180,False)])
def test_signed_chord_constraints_enforce_actual_angle_limits(degrees,expected):
    p,f,s=data();r=Rotation.from_euler('x',degrees,degrees=True).as_matrix();value=measure(p@r.T,np.zeros((4,3,1)),f,s)
    target=dict(position_m=value['origin_m'].tolist(),normal_world=[0,0,1],tangent_world=[0,1,0]);limits=dict(position_m=.001,normal_degrees=5,tangent_degrees=5)
    rows,jac=constraints(value,target,limits);assert bool(np.all(rows.residual()<=0)) is expected and jac.shape==(9,1)


@pytest.mark.parametrize('fault',['missing','extra','duplicate','bool-face','invalid-face','weight-sum','negative-weight','bool-weight','zero-tangent','collapsed','cancelled','nan','jacobian-size','negative-area','bad-coherence'])
def test_invalid_or_ambiguous_material_frames_reject(fault):
    p,f,s=data();j=np.zeros((4,3,1))
    if fault=='missing':s.pop('minimum_coherence')
    elif fault=='extra':s['anatomy_approved']=True
    elif fault=='duplicate':s['face_indices']=[0,0]
    elif fault=='bool-face':s['face_indices']=[True]
    elif fault=='invalid-face':s['face_indices']=[5]
    elif fault=='weight-sum':s['origin_weights'][0]=.5
    elif fault=='negative-weight':s['origin_weights'][0]=-.25
    elif fault=='bool-weight':s['proximal_weights'][0]=True
    elif fault=='zero-tangent':s['distal_weights']=s['proximal_weights'].copy()
    elif fault=='collapsed':p[2]=p[1]
    elif fault=='cancelled':f=np.array([[0,1,2],[2,1,0]])
    elif fault=='nan':j[0,0,0]=float('nan')
    elif fault=='jacobian-size':j=np.zeros((4,3,97))
    elif fault=='negative-area':s['minimum_twice_area_m2']=-1.
    else:s['minimum_coherence']=0.
    with pytest.raises(ValueError):measure(p,j,f,s)


@pytest.mark.parametrize('fault',['nonunit','parallel','negative-limit','bool-limit'])
def test_invalid_target_orientation_or_limits_reject(fault):
    p,f,s=data();frame=measure(p,np.zeros((4,3,1)),f,s)
    t=dict(position_m=[.05,.1,0],normal_world=[0,0,1],tangent_world=[0,1,0]);limits=dict(position_m=.001,normal_degrees=5,tangent_degrees=5)
    if fault=='nonunit':t['normal_world']=[0,0,2]
    elif fault=='parallel':t['tangent_world']=[0,0,1]
    elif fault=='negative-limit':limits['position_m']=-1.
    else:limits['normal_degrees']=True
    with pytest.raises(ValueError):constraints(frame,t,limits)


def test_native_affine_skin_frame_derivative_matches_fresh_pose_evaluations(tmp_path):
    from test_native_affine_key_pose import affine_setup
    from native_affine_key_pose import AffineKeyPose
    from native_scene_geometry import faces_for
    _,scene,*_=affine_setup(tmp_path);actor=scene.actors['A'];model=AffineKeyPose(actor,1.,[3],[30.])
    faces=faces_for(actor['rig'])[0];ids=np.unique(faces[0]);assert len(ids)==3
    selection=dict(face_indices=[0],origin_weights=[1/3]*3,proximal_weights=[1,0,0],distal_weights=[0,1,0],
        minimum_twice_area_m2=1e-12,minimum_coherence=.9,minimum_tangent_m=1e-6)
    value=np.array([.13,-.09,.21]);_,points,jac,_=model.evaluate(value);frame=measure(points,jac,faces,selection);h=1e-6
    for column in range(3):
        delta=np.eye(3)[column]*h
        observations=[]
        for x in (value+delta,value-delta):
            _,p,j,_=model.evaluate(x);observations.append(measure(p,j,faces,selection))
        for key,dkey in [('origin_m','origin_jacobian'),('normal_world','normal_jacobian'),('tangent_world','tangent_jacobian')]:
            np.testing.assert_allclose(frame[dkey][:,column],(observations[0][key]-observations[1][key])/(2*h),atol=2e-9,rtol=2e-7)
