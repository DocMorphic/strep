import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_soma_preview import ASSET
from palm_contacts import calibrate,surface_normal_track
from scene_constraints import transform_motion
from audit_scene_orientation import inward_box_face


def test_surface_normal_rotates_with_actor_and_ignores_translation():
    skin=dict(np.load(ASSET));bind=skin['bind_rig_transform'];motion=dict(posed_joints=bind[None,:,:3,3],global_rot_mats=bind[None,:,:3,:3])
    vertex=calibrate(skin)['RightHand']['surface_vertex'];q=Rotation.from_euler('xyz',[10,30,90],degrees=True)
    a=transform_motion(motion,dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))
    b=transform_motion(motion,dict(translation_m=[5,2,-1],rotation_xyzw=q.as_quat().tolist()))
    np.testing.assert_allclose(surface_normal_track(b,skin,vertex),q.apply(surface_normal_track(a,skin,vertex)),atol=1e-5)
    assert np.linalg.norm(surface_normal_track(a,skin,vertex)[0])==pytest.approx(1)


def test_box_contact_normals_point_into_opposite_faces():
    np.testing.assert_array_equal(inward_box_face([.2,.1,0],[.4,.4,.4]),[-1,0,0])
    np.testing.assert_array_equal(inward_box_face([-.2,.1,0],[.4,.4,.4]),[1,0,0])


@pytest.mark.parametrize('point',[[0,0,0],[.2,.2,0],[.3,0,0]])
def test_ambiguous_or_non_surface_grip_is_rejected(point):
    with pytest.raises(ValueError):inward_box_face(point,[.4,.4,.4])
