import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from object_geometry_mesh import triangle_mesh


@pytest.mark.parametrize('geometry',[Geometry('box',(.4,.6,.8)),Geometry('sphere',(.3,))])
def test_closed_outward_mesh_matches_analytic_surface_and_declared_inset(geometry):
    triangles,normals,report=triangle_mesh(geometry,tolerance_m=.001)
    flat=triangles.reshape(-1,3)
    distance=geometry.distance_gradient(flat,[0,0,0],np.eye(3))[0]
    np.testing.assert_allclose(distance,0,atol=1e-14)
    np.testing.assert_allclose(np.linalg.norm(normals,axis=-1),1,atol=1e-14)
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    assert np.all(np.einsum('ij,ij->i',cross,triangles.mean(1))>0)
    # Every geometric edge has exactly two incidents, with opposing directions.
    _,indices=np.unique(np.round(flat,12),axis=0,return_inverse=True)
    faces=indices.reshape(-1,3);edges={}
    for face in faces:
        for a,b in zip(face,np.roll(face,-1)):
            key=tuple(sorted((a,b)));edges.setdefault(key,[]).append(1 if a<b else -1)
    assert all(len(signs)==2 and sum(signs)==0 for signs in edges.values())
    # Independent dense barycentric samples must lie inside the analytic shape
    # by no more than the reported conservative preview error.
    for a in np.linspace(0,1,7):
        for b in np.linspace(0,1-a,7):
            points=a*triangles[:,0]+b*triangles[:,1]+(1-a-b)*triangles[:,2]
            depth=geometry.penetration_depth(points,[0,0,0],np.eye(3))
            assert depth.max()<=report['max_radial_inset_m']+1e-14
    assert report['max_radial_inset_m']<=.001


def test_sphere_impossible_preview_tolerance_fails_instead_of_silently_degrading():
    with pytest.raises(ValueError,match='resource limit'):
        triangle_mesh(Geometry('sphere',(1.,)),tolerance_m=1e-9,max_subdivisions=1)
