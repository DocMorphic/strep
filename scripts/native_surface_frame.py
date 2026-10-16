"""Actual skinned material frames and derivatives for native pose constraints.

An explicit triangle patch and material tangent weights define intent. No wrist
axis, dominant skin label or rigid projection substitutes for surface geometry.
"""
import numpy as np
from native_scene_contacts import fields,scalar,vector
from native_scene_norms import NormRows


def _weights(value,count):
    if not isinstance(value,list) or len(value)!=count:raise ValueError('One explicit weight per selected material vertex required')
    weights=np.array([scalar(v,0,1,'material frame weight') for v in value])
    if abs(weights.sum()-1)>1e-10:raise ValueError('Normalized complete material frame weights required')
    return weights


def _unit(value,jacobian,minimum):
    length=float(np.linalg.norm(value))
    if length<=minimum:raise ValueError('Degenerate material frame direction')
    direction=value/length
    return direction,(np.eye(3)-np.outer(direction,direction))@jacobian/length


def measure(points,derivatives,faces,selection):
    """Return centroid, winding normal, tangent and their complete Jacobians.

    Derivatives have shape [all source vertices,3,controls]. Weights follow
    sorted unique vertices of the explicitly selected original triangles.
    """
    points=np.asarray(points);derivatives=np.asarray(derivatives);faces=np.asarray(faces)
    if (points.dtype.kind not in 'fiu' or points.ndim!=2 or points.shape[1:]!=(3,) or not 1<=len(points)<=250000
            or not np.isfinite(points).all() or derivatives.dtype.kind not in 'fiu' or derivatives.ndim!=3
            or derivatives.shape[:2]!=points.shape or not 1<=derivatives.shape[2]<=96
            or derivatives.nbytes>128*1024**2 or not np.isfinite(derivatives).all()
            or faces.dtype.kind not in 'iu' or faces.ndim!=2 or faces.shape[1:]!=(3,) or not len(faces)
            or faces.min()<0 or faces.max()>=len(points)):
        raise ValueError('Complete bounded finite material geometry and derivatives required')
    fields(selection,('face_indices','origin_weights','proximal_weights','distal_weights',
        'minimum_twice_area_m2','minimum_coherence','minimum_tangent_m'),'material frame selection')
    chosen=selection['face_indices']
    if (not isinstance(chosen,list) or not 1<=len(chosen)<=512 or len(set(chosen))!=len(chosen)
            or any(type(i) is not int or not 0<=i<len(faces) for i in chosen)):
        raise ValueError('Distinct explicit existing patch faces required')
    minimum=scalar(selection['minimum_twice_area_m2'],1e-16,1e-4,'frame triangle area threshold')
    coherence=scalar(selection['minimum_coherence'],1e-6,1,'frame normal coherence')
    tangent_min=scalar(selection['minimum_tangent_m'],1e-9,1,'frame tangent threshold')
    tri_ids=faces[chosen];ids,remap=np.unique(tri_ids,return_inverse=True);local_faces=remap.reshape(-1,3)
    origin=_weights(selection['origin_weights'],len(ids));proximal=_weights(selection['proximal_weights'],len(ids));distal=_weights(selection['distal_weights'],len(ids))
    p=points[ids].astype(float);j=derivatives[ids].astype(float);tri=p[local_faces];dj=j[local_faces]
    a,b=tri[:,1]-tri[:,0],tri[:,2]-tri[:,0];da,db=dj[:,1]-dj[:,0],dj[:,2]-dj[:,0]
    cross=np.cross(a,b);area=np.linalg.norm(cross,axis=1);raw=cross.sum(axis=0)
    if np.any(area<=minimum) or np.linalg.norm(raw)/area.sum()<coherence:raise ValueError('Collapsed or incoherent patch cannot define orientation')
    dnormal=(np.cross(da.transpose(0,2,1),b[:,None,:])+np.cross(a[:,None,:],db.transpose(0,2,1))).sum(axis=0).T
    normal,jn=_unit(raw,dnormal,minimum)
    direction=(distal-proximal)@p;direction_jac=np.einsum('v,vic->ic',distal-proximal,j)
    projection=direction-normal*(normal@direction)
    derivative=direction_jac-jn*(normal@direction)-normal[:,None]*(direction@jn+normal@direction_jac)
    tangent,jt=_unit(projection,derivative,tangent_min)
    return dict(origin_m=origin@p,normal_world=normal,tangent_world=tangent,
        origin_jacobian=np.einsum('v,vic->ic',origin,j),normal_jacobian=jn,tangent_jacobian=jt,
        vertex_indices=ids,normal_coherence=float(np.linalg.norm(raw)/area.sum()),
        minimum_twice_area_m2=float(area.min()),projected_tangent_length_m=float(np.linalg.norm(projection)))


def constraints(frame,target,limits):
    """Three hard norm rows: material origin, signed normal and signed tangent.

    The unit-vector chord cap is exactly 2*sin(angle/2). This avoids an arbitrary
    angular penalty scale and distinguishes opposite facing from alignment.
    """
    fields(target,('position_m','normal_world','tangent_world'),'material frame target')
    fields(limits,('position_m','normal_degrees','tangent_degrees'),'material frame limits')
    point=vector(target['position_m'],3,'frame target position');normal=vector(target['normal_world'],3,'frame target normal');tangent=vector(target['tangent_world'],3,'frame target tangent')
    if abs(np.linalg.norm(normal)-1)>1e-8 or abs(np.linalg.norm(tangent)-1)>1e-8 or abs(normal@tangent)>1e-8:
        raise ValueError('Explicit orthonormal signed target directions required')
    position=scalar(limits['position_m'],1e-9,1,'material position tolerance')
    normal_angle=scalar(limits['normal_degrees'],1e-6,90,'material normal angle tolerance')
    tangent_angle=scalar(limits['tangent_degrees'],1e-6,90,'material tangent angle tolerance')
    values=np.array([frame['origin_m']-point,frame['normal_world']-normal,frame['tangent_world']-tangent])
    caps=np.array([position,2*np.sin(np.radians(normal_angle)/2),2*np.sin(np.radians(tangent_angle)/2)])
    jac=np.concatenate([frame[k] for k in ('origin_jacobian','normal_jacobian','tangent_jacobian')],axis=0)
    return NormRows(values,caps,caps.copy()),jac
