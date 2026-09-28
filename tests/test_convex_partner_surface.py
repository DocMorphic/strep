import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
from convex_partner_surface import candidates,penetration
from bounded_partner_surface import penetration as reference


def test_convex_rejection_preserves_depth_count_and_global_vertex(monkeypatch):
    mesh=trimesh.creation.box(extents=[2,.25,.4])
    mesh.apply_transform(trimesh.transformations.rotation_matrix(.8,[0,0,1]))
    points=np.random.default_rng(77).uniform(-1.2,1.2,(900,3))
    points=np.vstack([points,mesh.vertices,mesh.triangles_center])
    expected=reference(points,mesh.vertices,mesh.faces)
    sizes=[];signed=trimesh.proximity.signed_distance
    def observed(m,p):sizes.append(len(p));return signed(m,p)
    monkeypatch.setattr(trimesh.proximity,'signed_distance',observed)
    actual=penetration(points,mesh.vertices,mesh.faces)
    assert actual['convex_broadphase']['hull_candidates']<actual['broadphase_candidates']*.6
    assert max(sizes)<=32
    assert actual['max_depth_m']==pytest.approx(expected['max_depth_m'],abs=1e-12)
    assert actual['vertices_over_tolerance']==expected['vertices_over_tolerance']
    assert actual['deepest_vertex']==expected['deepest_vertex']


def test_nonconvex_target_and_translations_preserve_interior_queries():
    # Disconnected closed components leave empty space within their hull.
    # That space must be queried normally, not treated as solid hull geometry.
    first=trimesh.creation.box();second=first.copy();second.apply_translation([2,0,0])
    mesh=trimesh.util.concatenate([first,second]);points=np.array([[0,0,0],[1,0,0],[2,0,0],[1,1,0]])
    rot=Rotation.from_euler('xyz',[21,53,11],degrees=True).as_matrix();shift=np.array([100,-50,30])
    for translated in [False,True]:
        vertices=mesh.vertices@rot.T+shift if translated else mesh.vertices
        queries=points@rot.T+shift if translated else points
        actual=penetration(queries,vertices,mesh.faces);expected=reference(queries,vertices,mesh.faces)
        assert actual['vertices_over_tolerance']==expected['vertices_over_tolerance']==2
        assert actual['max_depth_m']==pytest.approx(expected['max_depth_m'],abs=1e-12)
        ids,_=candidates(vertices,vertices)
        assert ids.tolist()==list(range(len(vertices)))


def test_degenerate_hull_falls_back_and_invalid_inputs_fail():
    target=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0]])
    ids,info=candidates(np.array([[.5,.5,0],[2,2,0]]),target)
    assert ids.tolist()==[0] and info['hull_fallback']
    with pytest.raises(ValueError):candidates([[np.nan,0,0]],target)
    with pytest.raises(ValueError):candidates([[0,0,0]],target,padding=0)
