"""Triangle previews for analytic primitives, with an explicit sphere inset bound.

Collision queries must use the analytic Geometry, not this inscribed preview mesh.
"""
import numpy as np
from object_geometry import Geometry


def triangle_mesh(geometry, tolerance_m=0.001, max_subdivisions=6):
    if not isinstance(geometry, Geometry):raise ValueError('Geometry required')
    if type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or tolerance_m<=0:
        raise ValueError('Positive finite mesh tolerance required')
    if type(max_subdivisions) is not int or not 0<=max_subdivisions<=6:
        raise ValueError('Subdivision limit must be an integer from zero to six')
    if geometry.shape=='box':
        triangles=[];normals=[];size=np.array(geometry.dimensions)
        for axis in range(3):
            u,v=(axis+1)%3,(axis+2)%3
            for sign in [-1,1]:
                points=[];normal=np.zeros(3);normal[axis]=sign
                for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                    point=np.zeros(3);point[axis]=sign*size[axis]/2
                    point[u]=x*size[u]/2;point[v]=y*size[v]/2;points.append(point)
                for indices in ([[0,1,2],[0,2,3]] if sign>0 else [[0,2,1],[0,3,2]]):
                    triangles.append(np.array(points)[indices]);normals.append([normal]*3)
        return np.array(triangles),np.array(normals),dict(max_radial_inset_m=0.,subdivisions=0)
    # Octahedron faces cover the sphere. Normalized midpoint subdivision retains
    # that coverage; each planar face is inside the analytic sphere. Its plane
    # distance bounds the radial inset everywhere on the corresponding patch.
    triangles=np.array([[[x,0,0],[0,y,0],[0,0,z]]
                        for x in [-1,1] for y in [-1,1] for z in [-1,1]],dtype=float)
    radius=geometry.dimensions[0]
    for level in range(max_subdivisions+1):
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        inward=np.einsum('ij,ij->i',normals,triangles[:,0])<0
        triangles[inward]=triangles[inward][:,[0,2,1]]
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        normals/=np.linalg.norm(normals,axis=1)[:,None]
        plane=np.einsum('ij,ij->i',normals,triangles[:,0])
        inset=radius*(1-float(plane.min()))
        if inset<=tolerance_m:
            return triangles*radius,triangles.copy(),dict(max_radial_inset_m=inset,subdivisions=level)
        if level==max_subdivisions:raise ValueError('Mesh tolerance exceeds subdivision resource limit')
        a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
        def midpoint(x,y):
            m=x+y
            return m/np.linalg.norm(m,axis=1)[:,None]
        ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
        triangles=np.concatenate([np.stack(t,axis=1) for t in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]])
