import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from region_grasp_track import object_local_targets,smoothstep5


def test_object_targets_preserve_rigid_local_coordinates():
    rotations=Rotation.from_euler('z',[25,60,140],degrees=True).as_matrix(); positions=np.array([[1,2,3],[2,3,4],[-1,1,2.]])
    point=np.array([1.2,2.3,3.4]); normal=np.array([1.,0,0]); tangent=np.array([0,1.,0])
    targets=object_local_targets(point,normal,tangent,positions,rotations,0)
    np.testing.assert_allclose(targets['points'][0],point)
    for i in range(3):
        np.testing.assert_allclose(rotations[i].T@(targets['points'][i]-positions[i]),rotations[0].T@(point-positions[0]),atol=1e-12)
        np.testing.assert_allclose(np.dot(targets['normals'][i],targets['tangents'][i]),0,atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(targets['normals'][i]),1,atol=1e-12)


def test_quintic_blend_is_convex_with_flat_endpoints():
    t=np.linspace(0,1,101); w=smoothstep5(t)
    assert w[0]==0 and w[-1]==1 and (np.diff(w)>=0).all() and (w>=0).all() and (w<=1).all()
    np.testing.assert_array_equal(smoothstep5([-1,2]),[0,1])
    h=1e-5
    assert smoothstep5(h)/h < 1e-8 and (1-smoothstep5(1-h))/h < 1e-8
