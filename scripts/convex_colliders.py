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


class ConvexCylinderTest:
    """Complete nested-prism bounds against the whole supplied convex hull.

    Keep all hull triangle edges, including redundant planar diagonals: these
    add valid axes and never omit a true edge. No angular cutoff or rounding.
    Positive projection gaps are not Euclidean distances.
    """
    def __init__(self, points):
        self.points=validate_points(points)
        hull=ConvexHull(self.points)
        self.normals=hull.equations[:,:3]
        edges=set()
        for a,b,c in hull.simplices:
            edges.update([tuple(sorted((int(a),int(b)))),tuple(sorted((int(b),int(c)))),tuple(sorted((int(c),int(a))))])
        self.edges=np.array([self.points[b]-self.points[a] for a,b in sorted(edges)])
        self.radius=float(np.linalg.norm(self.points,axis=1).max())

    def bounds(self, cylinder_p, cylinder_r, dimensions, convex_p, convex_r, *,
               radial_tolerance_m=.001, maximum_segments=128, numerical_padding_m=1e-9):
        from object_geometry import Geometry,finite
        from primitive_penetration_bounds import rigid,resolution,polytope,support,require
        geometry=Geometry('cylinder',tuple(dimensions))
        require(type(radial_tolerance_m) in (int,float) and np.isfinite(radial_tolerance_m) and radial_tolerance_m>0,
                'Positive finite radial approximation tolerance required')
        require(type(maximum_segments) is int and maximum_segments in (4,8,16,32,64,128),
                'Power-of-two segment budget from 4 through 128 required')
        require(type(numerical_padding_m) in (int,float) and np.isfinite(numerical_padding_m) and numerical_padding_m>=0,
                'Finite nonnegative arithmetic pad required')
        p=finite(cylinder_p,(3,),'cylinder position');q=finite(convex_p,(3,),'convex position')
        r,s=rigid(cylinder_r),rigid(convex_r)
        center=(p-q)@s;rel=s.T@r
        require(np.isfinite(center).all(),'Finite relative collision position required')
        n,error=resolution(geometry,radial_tolerance_m,maximum_segments)
        pad=float(numerical_padding_m+64*np.finfo(float).eps*(np.linalg.norm(center)+geometry.bounding_radius()+self.radius))
        require(np.isfinite(pad),'Finite arithmetic uncertainty required')
        gaps=[];count=0
        for outer in (False,True):
            normals,edges=polytope(geometry,rel,n,outer)
            axes=np.concatenate([self.normals,normals,np.cross(edges[:,None],self.edges[None]).reshape(-1,3)])
            lengths=np.hypot(np.hypot(axes[:,0],axes[:,1]),axes[:,2])
            axes=axes[lengths>0]/lengths[lengths>0,None]
            projected=self.points@axes.T;lo=projected.min(axis=0);hi=projected.max(axis=0)
            middle=axes@center;radius=support(geometry,rel,n,axes,outer)
            gaps.append(float(np.maximum(lo-middle-radius,middle-radius-hi).max()));count+=len(axes)
        inner,outer=gaps
        require(np.isfinite(gaps).all(),'Finite collision projections required')
        lower=max(0.,-inner-pad);upper=0. if outer>pad else max(0.,-outer)+pad
        require(lower<=upper+pad,'Ordered penetration interval required')
        return dict(schema='strep-convex-cylinder-penetration-bounds-v1',method='complete-nested-prism-convex-sat',
                    penetration_lower_m=lower,penetration_upper_m=upper,inner_projection_gap_m=inner,outer_projection_gap_m=outer,
                    radial_segments=n,approximation_radial_expansion_m=error,
                    approximation_radial_inset_m=geometry.dimensions[0]*(1-np.cos(np.pi/n)),axes_evaluated=count,
                    numerical_padding_m=pad,definitely_separated=outer>pad,definitely_penetrating=inner < -pad,
                    hull_vertices=len(self.points),floating_point_interval_certified=False,continuous_collision_certified=False,
                    physics_release_qualified=False,quality_approved=False,release_approved=False)

    def gap(self,cylinder_p,cylinder_r,dimensions,convex_p,convex_r):
        result=self.bounds(cylinder_p,cylinder_r,dimensions,convex_p,convex_r)
        return result['outer_projection_gap_m']-result['numerical_padding_m']
