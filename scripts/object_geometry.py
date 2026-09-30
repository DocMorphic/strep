"""Versioned rigid primitive geometry for consistent queries and future scene wiring.

Shared primitive queries. Individual scene/release consumers declare their support.
Distances are analytic primitive distances, not triangle or continuous collision tests.
"""
from dataclasses import dataclass
import numpy as np


def finite(value,shape,label):
    try:a=np.asarray(value,dtype=float)
    except (TypeError,ValueError) as exc:raise ValueError('Invalid '+label) from exc
    if a.shape!=shape or not np.isfinite(a).all():raise ValueError('Invalid '+label)
    return a


def scene_geometry(obj):
    """Read a versioned descriptor, or the original unversioned box format.

    Reject mixed representations so different consumers cannot pick different
    dimensions. New non-box objects must use the explicit geometry schema.
    """
    if not isinstance(obj,dict):raise ValueError('Scene object must be a dictionary')
    fields={'shape','size_m','radius_m','height_m'}
    if 'geometry' in obj:
        if fields.intersection(obj):raise ValueError('Do not mix legacy dimensions and versioned geometry')
        return Geometry.parse(obj['geometry'])
    if obj.get('shape')!='box' or {'radius_m','height_m'}.intersection(obj):
        raise ValueError('Non-box scene objects require versioned geometry')
    return Geometry.parse(dict(schema='strep-object-geometry-v1',shape='box',size_m=obj.get('size_m')))


@dataclass(frozen=True)
class Geometry:
    shape: str
    dimensions: tuple

    def __post_init__(self):
        count={'box':3,'sphere':1,'cylinder':2}.get(self.shape)
        if count is None:raise ValueError('Unsupported primitive shape')
        values=finite(self.dimensions,(count,),'primitive dimensions')
        if np.any(values<=0):raise ValueError('Primitive dimensions must be positive metres')
        object.__setattr__(self,'dimensions',tuple(float(x) for x in values))

    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict) or value.get('schema')!='strep-object-geometry-v1':
            raise ValueError('Explicit object geometry schema required')
        shape=value.get('shape')
        if shape=='cylinder':
            if set(value)!={'schema','shape','radius_m','height_m'} or any(type(value[k]) not in (int,float) for k in ['radius_m','height_m']):
                raise ValueError('Numeric cylinder radius and full height required')
            return cls(shape,(value['radius_m'],value['height_m']))
        field={'box':'size_m','sphere':'radius_m'}.get(shape)
        if field is None or set(value)!={'schema','shape',field}:raise ValueError('Invalid geometry fields')
        dims=value[field] if shape=='box' else [value[field]]
        if shape=='sphere' and type(value[field]) not in (int,float):raise ValueError('Numeric sphere radius required')
        if shape=='box' and (not isinstance(dims,list) or any(type(x) not in (int,float) for x in dims)):
            raise ValueError('Numeric box dimensions required')
        return cls(shape,tuple(dims))

    def record(self):
        if self.shape=='cylinder':
            return dict(schema='strep-object-geometry-v1',shape=self.shape,radius_m=self.dimensions[0],height_m=self.dimensions[1])
        return dict(schema='strep-object-geometry-v1',shape=self.shape,
            **({'size_m':list(self.dimensions)} if self.shape=='box' else {'radius_m':self.dimensions[0]}))

    def distance_gradient(self,points,position,rotation):
        """Signed distance, outward world gradient and differentiability mask.

        Stable unit subgradients are returned on box ties; sphere center returns
        zero. The mask marks such ambiguous locations instead of inventing a
        uniquely defined grip normal there.
        """
        p=np.asarray(points,dtype=float)
        if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():raise ValueError('Finite Nx3 points required')
        center=finite(position,(3,),'position');r=finite(rotation,(3,3),'rotation')
        if not np.allclose(r.T@r,np.eye(3),atol=1e-8,rtol=0) or abs(np.linalg.det(r)-1)>1e-8:
            raise ValueError('A proper rigid rotation is required')
        local=(p-center)@r
        if self.shape=='sphere':
            length=np.linalg.norm(local,axis=1);defined=length>1e-12
            gradient=np.divide(local,length[:,None],out=np.zeros_like(local),where=defined[:,None])
            return length-self.dimensions[0],gradient@r.T,defined
        if self.shape=='cylinder':
            radius,height=self.dimensions;rho=np.linalg.norm(local[:,[0,2]],axis=1)
            q=np.stack([rho-radius,abs(local[:,1])-height/2],axis=1)
            positive=np.maximum(q,0);length=np.linalg.norm(positive,axis=1)
            maximum=q.max(axis=1);outside=length>1e-12
            weights=np.divide(positive,length[:,None],out=np.zeros_like(q),where=outside[:,None])
            index=q.argmax(axis=1);inside=np.flatnonzero(~outside);weights[inside,index[inside]]=1.
            radial=np.divide(local[:,[0,2]],rho[:,None],out=np.zeros((len(local),2)),where=(rho>1e-12)[:,None])
            gradient=np.zeros_like(local);gradient[:,[0,2]]=weights[:,0,None]*radial
            gradient[:,1]=weights[:,1]*np.where(local[:,1]>=0,1.,-1.)
            ties=np.isclose(q[:,0],q[:,1],atol=1e-12,rtol=0)
            defined=(outside|~ties)&((weights[:,0]==0)|(rho>1e-12))&((weights[:,1]==0)|(abs(local[:,1])>1e-12))
            return length+np.minimum(maximum,0),gradient@r.T,defined
        q=abs(local)-np.asarray(self.dimensions)/2;positive=np.maximum(q,0)
        length=np.linalg.norm(positive,axis=1);maximum=q.max(axis=1)
        distance=length+np.minimum(maximum,0);outside=length>1e-12
        gradient=np.divide(positive,length[:,None],out=np.zeros_like(local),where=outside[:,None])*np.sign(local)
        index=q.argmax(axis=1);inside=np.flatnonzero(~outside)
        gradient[inside,index[inside]]=np.where(local[inside,index[inside]]>=0,1.,-1.)
        ties=np.sum(np.isclose(q,maximum[:,None],atol=1e-12,rtol=0),axis=1)>1
        defined=outside|(~ties & (abs(local[np.arange(len(local)),index])>1e-12))
        return distance,gradient@r.T,defined

    def penetration_depth(self,points,position,rotation):
        return np.maximum(0.,-self.distance_gradient(points,position,rotation)[0])

    def local_surface_normal(self,point,tolerance_m=1e-6):
        if type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or tolerance_m<=0:
            raise ValueError('Positive finite surface tolerance required')
        point=finite(point,(3,),'surface point')
        distance,normal,defined=self.distance_gradient(point[None],np.zeros(3),np.eye(3))
        if abs(distance[0])>tolerance_m or not defined[0]:
            raise ValueError('A unique surface normal requires a point on a smooth face')
        return normal[0]

    def world_half_extents(self,rotation):
        r=finite(rotation,(3,3),'rotation')
        if not np.allclose(r.T@r,np.eye(3),atol=1e-8,rtol=0) or abs(np.linalg.det(r)-1)>1e-8:
            raise ValueError('A proper rigid rotation is required')
        if self.shape=='cylinder':
            axis=r[:,1];radius,height=self.dimensions
            return radius*np.sqrt(np.maximum(0,1-axis**2))+height/2*abs(axis)
        return abs(r)@(np.asarray(self.dimensions)/2) if self.shape=='box' else np.full(3,self.dimensions[0])

    def local_size(self):
        if self.shape=='box':return np.asarray(self.dimensions)
        if self.shape=='sphere':return np.full(3,2*self.dimensions[0])
        radius,height=self.dimensions
        return np.array([2*radius,height,2*radius])

    def bounding_radius(self):
        if self.shape=='sphere':return self.dimensions[0]
        if self.shape=='cylinder':return float(np.hypot(self.dimensions[0],self.dimensions[1]/2))
        return float(np.linalg.norm(np.asarray(self.dimensions)/2))

    def uniform_inertia(self,mass_kg):
        if type(mass_kg) not in (int,float) or not np.isfinite(mass_kg) or mass_kg<=0:
            raise ValueError('Positive finite mass in kg required')
        if self.shape=='sphere':return np.eye(3)*(.4*mass_kg*self.dimensions[0]**2)
        if self.shape=='cylinder':
            radius,height=self.dimensions
            transverse=mass_kg*(3*radius**2+height**2)/12
            return np.diag([transverse,mass_kg*radius**2/2,transverse])
        size=np.asarray(self.dimensions)
        return np.diag(mass_kg*(np.sum(size**2)-size**2)/12)
