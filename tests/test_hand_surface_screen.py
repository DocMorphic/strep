import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hand_surface_screen import hand_vertices,screen


def test_hand_selection_includes_blended_seams_and_thumb_but_not_zero_weight_slots():
    # Joint palette is deliberately not node order. Node 2 is wrist, 3 thumb.
    rig=SimpleNamespace(parents=np.array([-1,0,1,2,0]),joints=[4,3,1,2],primitives=[dict(
        joints=np.array([[2,3],[2,1],[2,1],[0,2],[3,1]]),
        weights=np.array([[.999,.001],[0,1],[1,0],[.5,.5],[.4,.6]]))])
    np.testing.assert_array_equal(hand_vertices(rig,2),[0,1,4])
    with pytest.raises(ValueError):hand_vertices(rig,0.5)
    rig.primitives[0]['weights'][0,0]=np.nan
    with pytest.raises(ValueError):hand_vertices(rig,2)


def test_subset_depth_uses_complete_target_and_returns_original_source_id():
    mesh=trimesh.creation.box(extents=[2,2,2])
    source=np.array([[10,0,0],[.8,0,0],[0,0,0],[3,0,0]])
    result=screen(source,np.array([3,2,1]),mesh.vertices,mesh.faces)
    assert result['max_depth_m']==pytest.approx(1.)
    assert result['deepest_source_vertex']==2 and result['vertices_over_tolerance']==2
    assert result['vertices_checked']==3 and result['source_full_vertex_count']==4
    clear=screen(source,np.array([0,3]),mesh.vertices,mesh.faces)
    assert clear['deepest_source_vertex'] is None and clear['max_depth_m']==0
    for ids in [[],[1,1],[-1],[4],[.5]]:
        with pytest.raises(ValueError):screen(source,np.array(ids),mesh.vertices,mesh.faces)
    with pytest.raises(ValueError):screen(source,np.array([1]),mesh.vertices,mesh.faces[:-1])
