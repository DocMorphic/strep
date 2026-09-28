import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hull_surface_correspondences import query
from paired_hand_clearance import correspondences as reference
from convex_partner_surface import candidates


def original(vertices,faces,margin):
    actors=[SimpleNamespace(dim=1,rotation=np.eye(3),translation=np.zeros(3),pose=lambda frame,x:None,
        rig=SimpleNamespace(vertices=lambda pose,v=v:v)) for v in vertices]
    return reference(actors,0,np.zeros(2),faces,margin)


@pytest.mark.parametrize('offset',[[0,0,0],[.15,.2,.1],[1.95,0,0],[2.001,0,0],[4,0,0]])
def test_intersecting_touching_near_and_separate_surfaces_match_original(offset):
    mesh=trimesh.creation.icosphere(subdivisions=1,radius=1)
    points=np.asarray(mesh.vertices);vertices=[points,points+offset]
    found,diagnostics=query(vertices,mesh.faces,.003)
    expected,old=original(vertices,mesh.faces,.003)
    for a,b in zip(diagnostics,old):
        for key in ['source','target','vertices_checked','vertices_over_5mm','active_constraints']:assert a[key]==b[key]
        assert a['max_depth_m']==pytest.approx(b['max_depth_m'],abs=1e-12)
    for a,b in zip(found,expected):
        assert len(a['points'])==len(b['points'])
        for pa,pb in zip(a['points'],b['points']):
            assert pa[0]==pb[0] and pa[1]==pb[1]
            np.testing.assert_allclose(pa[2],pb[2],atol=1e-12)
            np.testing.assert_allclose(pa[3],pb[3],atol=1e-12)


def test_expanded_hull_keeps_points_just_outside_a_rotated_face():
    mesh=trimesh.creation.box();r=Rotation.from_euler('xyz',[19,32,11],degrees=True).as_matrix()
    target=np.asarray(mesh.vertices)@r.T
    local=np.array([[.5+.0025,0,0],[.5+.004,0,0],[0,0,0],[1,1,1]])
    ids,stats=candidates(local@r.T,target,padding=.003)
    assert 0 in ids and 2 in ids and 1 not in ids and 3 not in ids


@pytest.mark.parametrize('margin',[-.1,float('nan'),float('inf')])
def test_invalid_margin_rejected(margin):
    mesh=trimesh.creation.box()
    with pytest.raises(ValueError):query([mesh.vertices,mesh.vertices],mesh.faces,margin)
