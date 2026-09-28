import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_partner_surface import penetration


def test_signed_penetration_inside_boundary_and_outside_rotated_closed_box():
    mesh=trimesh.creation.box(extents=[2,2,2]);transform=trimesh.transformations.rotation_matrix(.6,[0,1,0]);transform[:3,3]=[2,0,-3]
    mesh.apply_transform(transform)
    points=trimesh.transform_points([[0,0,0],[1,0,0],[1.2,0,0]],transform)
    report=penetration(points,mesh.vertices,mesh.faces)
    assert report['deepest_vertex']==0;assert report['vertices_over_tolerance']==1
    assert abs(report['max_depth_m']-1)<1e-10;assert report['broadphase_candidates']>=2


def test_open_partner_surface_is_not_silently_treated_as_solid():
    mesh=trimesh.creation.box()
    with pytest.raises(ValueError,match='closed'):penetration([[0,0,0]],mesh.vertices,mesh.faces[:-1])
