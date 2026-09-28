"""Finite convex collision geometry and box/polyhedron separating-axis tests."""
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection, QhullError
from object_dynamics import finite_array


def validate_points(values):
    if not isinstance(values,list) or not 4<=len(values)<=128:raise ValueError('Convex collider needs 4–128 points')
    points=finite_array(values,(len(values),3),'convex points')
    if np.abs(points).max()>100:raise ValueError('Convex geometry exceeds local size limit')
    try:hull=ConvexHull(points)
    except QhullError as exc:raise ValueError('Convex collider must have volume') from exc
    if hull.volume<1e-9:raise ValueError('Convex collider volume too small')
    if len(hull.vertices)!=len(points):raise ValueError('Convex points must be unique hull vertices')
    return points


def direction_hull(directions, supports):
    """Outer polytope from measured support planes; does not shrink the skin."""
    from scipy.optimize import linprog
    d=np.asarray(directions);s=np.asarray(supports)
    # Largest inscribed ball supplies a strict interior point for Qhull.
    fit=linprog([0,0,0,-1],A_ub=np.c_[d,np.ones(len(d))],b_ub=s,bounds=[(None,None)]*3+[(0,None)],method='highs')
    if not fit.success or fit.x[3]<1e-6:raise ValueError('Body region lacks finite 3D volume')
    points=HalfspaceIntersection(np.c_[d,-s],fit.x[:3]).intersections
    hull=ConvexHull(points);points=points[hull.vertices]
    return validate_points(points.tolist())


def volume_centroid(points):
    """Uniform convex solid COM by signed tetrahedra, independent of engine."""
    p=np.asarray(points,dtype=float);hull=ConvexHull(p);triangles=p[hull.simplices].copy()
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    flip=np.einsum('ij,ij->i',normals,hull.equations[:,:3])<0
    triangles[flip]=triangles[flip][:,[0,2,1]]
    volumes=np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2]))/6
    return np.sum(triangles.sum(axis=1)*volumes[:,None]/4,axis=0)/volumes.sum()


class ConvexBoxTest:
    def __init__(self, points):
        self.points=validate_points(points)
        hull=ConvexHull(self.points)
        self.normals=np.unique(np.round(hull.equations[:,:3],10),axis=0)
        edges={}
        for number,face in enumerate(hull.simplices):
            for a,b in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])]:
                edges.setdefault(tuple(sorted((int(a),int(b)))),[]).append(number)
        # Triangulation diagonals inside one planar face are not polyhedron
        # edges. Including them changes reported positive projection gaps.
        real=[edge for edge,faces in edges.items() if len(faces)!=2 or np.linalg.norm(np.cross(hull.equations[faces[0],:3],hull.equations[faces[1],:3]))>1e-8]
        vectors=np.array([self.points[b]-self.points[a] for a,b in real]);vectors/=np.linalg.norm(vectors,axis=1)[:,None]
        self.edges=np.unique(np.round(vectors,10),axis=0)

    def gap(self, box_p, box_r, size, convex_p, convex_r):
        # Recenter in convex-local coordinates before projections; the box
        # radii support formula is independent of the runtime collision code.
        rel=convex_r.T@box_r;center=(np.asarray(box_p)-convex_p)@convex_r
        axes=np.concatenate([self.normals,rel.T,np.cross(rel.T[:,None,:],self.edges[None,:,:]).reshape(-1,3)])
        lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>1e-9]/lengths[lengths>1e-9,None]
        projected=self.points@axes.T;lo=projected.min(axis=0);hi=projected.max(axis=0)
        middle=axes@center;radius=np.abs(axes@rel)@(np.asarray(size)/2)
        return float(np.maximum(lo-(middle+radius),(middle-radius)-hi).max())


class ConvexSphereTest:
    """Euclidean sphere/polyhedron gap, including face/edge/vertex proximity."""
    def __init__(self,points):
        self.points=validate_points(points);hull=ConvexHull(self.points)
        self.triangles=self.points[hull.simplices];self.planes=hull.equations

    def gap(self,center,radius,convex_p,convex_r):
        from trimesh.triangles import closest_point
        center=(np.asarray(center)-convex_p)@convex_r
        signed=self.planes[:,:3]@center+self.planes[:,3]
        if signed.max()<=0:distance=float(signed.max())
        else:
            nearest=closest_point(self.triangles,np.broadcast_to(center,(len(self.triangles),3)))
            distance=float(np.linalg.norm(nearest-center,axis=1).min())
        return distance-radius
