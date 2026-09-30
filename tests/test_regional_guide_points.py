import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_regional_guide_points import orientations,clearance_batch
from object_geometry import Geometry


def test_orientation_grid_preserves_normal_window_and_rotations():
    source=np.array([1.,0.,0.]);target=np.array([-1.,0.,0.]);rows=orientations(source,target)
    assert len(rows)==72 and rows==orientations(source,target)
    assert len({tuple(np.round(np.array(r['rotation']).ravel(),10)) for r in rows})==72
    for row in rows:
        matrix=np.array(row['rotation']);np.testing.assert_allclose(matrix.T@matrix,np.eye(3),atol=1e-14)
        angle=np.rad2deg(np.arccos(np.clip((matrix@source)@target,-1,1)))
        assert angle==pytest.approx(row['tilt_degrees'],abs=1e-6)
        assert np.linalg.det(matrix)==pytest.approx(1)


def test_batched_clearance_matches_each_rigid_hand():
    rng=np.random.default_rng(411);vertices=rng.normal(size=(17,3))*.03;anchors=vertices[[1,7,10]]
    matrix=Rotation.from_rotvec([.2,.8,.5]).as_matrix();point=np.array([.21,.1,.01]);geometry=Geometry('cylinder',(.2,.4))
    center=np.array([.01,.02,-.01]);rotation=Rotation.from_rotvec([.3,-.1,.2]).as_matrix()
    minima,worst=clearance_batch(vertices,anchors,matrix,point,geometry,center,rotation)
    for i,anchor in enumerate(anchors):
        gaps=geometry.distance_gradient((vertices-anchor)@matrix.T+point,center,rotation)[0]
        assert minima[i]==gaps.min() and worst[i]==gaps.argmin()


@pytest.mark.parametrize('angle',[0,90,-1,float('nan')])
def test_invalid_grid_tilt_rejected(angle):
    with pytest.raises(ValueError):orientations([1,0,0],[-1,0,0],angle)


def test_wrist_target_rigidly_moves_attached_points():
    from project_regional_guides import rigid_wrist_target
    wrist=np.array([.3,.7,-.2]);orientation=Rotation.from_rotvec([.2,.1,-.3]).as_matrix()
    anchor=np.array([.32,.72,-.16]);matrix=Rotation.from_rotvec([-.4,.3,.2]).as_matrix();point=np.array([-.2,.1,0.])
    position,rotation=rigid_wrist_target(wrist,orientation,anchor,matrix,point)
    local=np.array([[0.,0.,0.],[.01,-.04,.08]])
    original=local@orientation.T+wrist
    np.testing.assert_allclose(local@rotation.T+position,(original-anchor)@matrix.T+point,atol=1e-15)
