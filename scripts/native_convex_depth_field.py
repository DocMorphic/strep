"""Complete convex-mesh interior depth and smooth point derivatives.

Log-sum-exp bound: Boyd/Vandenberghe, Convex Optimization, sec.3.1.5.
Independent implementation; no book/example code copied. The real-arithmetic
upper approximation is guidance, not a floating collision certificate.
"""
import hashlib
import numpy as np
import trimesh

MAXIMUM_BYTES=64*1024**2


def _real(value,shape,label):
    a=np.asarray(value)
    if a.shape!=shape or a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all():raise ValueError('Complete finite real '+label+' required')
    return a.astype(float,copy=True)


class ConvexDepthField:
    def __init__(self,vertices,faces,*,maximum_working_bytes=MAXIMUM_BYTES):
        if type(maximum_working_bytes) is not int or not 1<=maximum_working_bytes<=MAXIMUM_BYTES:raise ValueError('Complete bounded array workspace required')
        v=np.asarray(vertices);f=np.asarray(faces)
        if v.ndim!=2 or v.shape[1:]!=(3,) or not 4<=len(v)<=65536 or f.ndim!=2 or f.shape[1:]!=(3,) or not 4<=len(f)<=4096 or f.dtype.kind not in 'iu' or f.dtype.itemsize>8:raise ValueError('Complete bounded convex mesh vertices/triangle indices required')
        if len(v)*len(f)>16777216:raise ValueError('Complete vertex/facet validation exceeds budget; no mesh elements dropped')
        workspace=8*(24*len(v)+48*len(f)+4*min(128,len(v))*len(f))
        if workspace>maximum_working_bytes:raise ValueError('Complete convex mesh array workspace exceeds budget')
        v=_real(v,v.shape,'mesh vertices')
        if np.max(np.abs(v))>1e6 or np.any(f>=len(v)) or np.any(f<0):raise ValueError('Finite bounded vertices/existing face indices required')
        f=f.astype(np.int64,copy=True);mesh=trimesh.Trimesh(v.copy(),f.copy(),process=False)
        if not mesh.is_volume or not mesh.is_convex:raise ValueError('Closed outward-wound convex mesh required; no repair or convex-hull replacement')
        origin=v[0].copy();tri=v[f]-origin;normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(normal,axis=1)
        if np.any(length<=1e-14):raise ValueError('Every supplied convex facet must be nondegenerate')
        normal/=length[:,None];offset=np.einsum('fi,fi->f',normal,tri[:,0]);excess=-np.inf
        for start in range(0,len(v),128):excess=max(excess,float(((v[start:start+128]-origin)@normal.T-offset).max()))
        numeric_limit=2e-11*(1+float(np.max(np.abs(v-origin))))
        if excess>numeric_limit:raise ValueError('Every supplied vertex must satisfy all represented outward facet planes')
        self._origin=origin;self._normals=normal;self._offset=offset;self._faces=len(f)
        self._digest=hashlib.sha256(v.astype('<f8').tobytes()+f.astype('<i8').tobytes()).hexdigest()
        self.report=dict(vertices=len(v),faces=len(f),geometry_sha256=self._digest,closed_outward_convex_precondition=True,all_vertex_facet_checks=len(v)*len(f),maximum_support_plane_excess_m=excess,numerical_precondition_limit_m=numeric_limit,mesh_repaired=False,mesh_hull_substituted=False,quality_approved=False)

    def evaluate(self,points,*,point_jacobian=None,temperature_m=1e-7,maximum_jacobian_bytes=MAXIMUM_BYTES,maximum_working_bytes=MAXIMUM_BYTES):
        p=np.asarray(points)
        if p.ndim!=2 or p.shape[1:]!=(3,) or not 1<=len(p)<=16384:raise ValueError('Complete bounded point chunk required')
        if type(temperature_m) not in (int,float) or not np.isfinite(temperature_m) or not 1e-9<=temperature_m<=1e-3:raise ValueError('Finite positive bounded guidance temperature required')
        for b in [maximum_jacobian_bytes,maximum_working_bytes]:
            if type(b) is not int or not 1<=b<=MAXIMUM_BYTES:raise ValueError('Complete bounded array budgets required')
        columns=0;raw=None
        if point_jacobian is not None:
            raw=np.asarray(point_jacobian)
            if raw.ndim!=3 or raw.shape[:2]!=(len(p),3) or not 1<=raw.shape[2]<=768:raise ValueError('Every point/xyz/derivative column required')
            columns=raw.shape[2]
        workspace=8*(10*len(p)*self._faces+8*len(p)*columns+24*len(p)+48*self._faces+16)
        if 8*len(p)*columns>maximum_jacobian_bytes or raw is not None and raw.size*8>maximum_jacobian_bytes or workspace>maximum_working_bytes:raise ValueError('Complete depth arrays exceed budget; no points/facets/columns dropped')
        p=_real(p,p.shape,'point chunk')
        if np.max(np.abs(p))>1e6:raise ValueError('Represented point positions within one million metres required')
        slack=self._offset-(p-self._origin)@self._normals.T;minimum=slack.min(axis=1);tau=float(temperature_m)
        with np.errstate(under='ignore'):
            weights=np.exp((minimum[:,None]-slack)/tau);mass=weights.sum(axis=1);weights/=mass[:,None]
            upper_min=minimum-tau*np.log(mass)+tau*np.log(self._faces)
            upper=tau*np.logaddexp(0.,upper_min/tau);activation=np.exp(-np.logaddexp(0.,-upper_min/tau))
        exact=np.maximum(minimum,0.);gradient=-activation[:,None]*(weights@self._normals);jac=None
        if columns:jac=np.einsum('vi,vic->vc',gradient,_real(raw,raw.shape,'complete point Jacobian'))
        if not np.isfinite(upper).all() or not np.isfinite(gradient).all() or jac is not None and not np.isfinite(jac).all():raise ValueError('Finite complete depth output required')
        return dict(exact_depth_m=exact,upper_depth_m=upper,upper_point_gradient=gradient,upper_jacobian=jac,report=dict(schema='strep-native-convex-depth-field-v1',geometry_sha256=self._digest,points=len(p),facets=self._faces,columns=columns,all_points_facets_columns_retained=True,temperature_m=tau,real_arithmetic_upper_error_bound_m=tau*np.log(2*self._faces),estimated_array_workspace_bytes=workspace,geometry_precondition_verified=True,collision_certified=False,quality_approved=False,release_approved=False,scope='Complete supplied points against fixed represented closed convex-mesh facets. Exact values are positive interior plane depth, zero outside; smooth upper uses corrected soft-min and softplus. Upper bound is mathematical, not a floating certificate or acceptance tolerance. Target deformation/scene permissions, complete clocks, raw/saved full-mesh/contact/quality tests remain caller-owned. No concave-target extension or mesh repair.'))
