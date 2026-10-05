"""Primitive geometry shared by release requests, overlap guards and audits."""
import numpy as np
from object_geometry import Geometry,scene_geometry


def body_geometry(record):
    if 'geometry' in record:return scene_geometry(record)
    if 'size_m' not in record:raise ValueError('Release body geometry required')
    return scene_geometry(dict(shape='box',size_m=record['size_m']))


def geometry_fields(record):
    geometry=body_geometry(record)
    return dict(geometry=geometry.record()) if 'geometry' in record else dict(size_m=list(geometry.dimensions))


def floor_gaps(geometry,positions,rotations,height=0.):
    positions=np.asarray(positions);rotations=np.asarray(rotations)
    if geometry.shape=='cylinder':
        axis=rotations[:,1,1];radius,height_cylinder=geometry.dimensions
        half=radius*np.sqrt(np.maximum(0,1-axis**2))+height_cylinder/2*abs(axis)
    else:half=np.full(len(positions),geometry.dimensions[0]) if geometry.shape=='sphere' else abs(rotations[:,1,:])@(np.asarray(geometry.dimensions)/2)
    return positions[:,1]-half-height


def require_release_geometry(geometry):
    if geometry.shape not in ['box','sphere','cylinder']:
        raise ValueError('Unsupported release primitive')
    return geometry


def preview_penetration_bounds(first,p,r,second,other_p,other_r,**settings):
    """Read-only cylinder-capable geometry preview, separate from release qualification."""
    from primitive_penetration_bounds import bounds
    return bounds(first,p,r,second,other_p,other_r,**settings)


def primitive_gap(first,p,r,second,other_p,other_r):
    require_release_geometry(first);require_release_geometry(second)
    if 'cylinder' in (first.shape,second.shape):
        result=preview_penetration_bounds(first,p,r,second,other_p,other_r)
        return result['outer_projection_gap_m']-result['numerical_padding_m']
    if first.shape=='sphere':
        if second.shape=='sphere':return float(np.linalg.norm(np.asarray(p)-other_p)-first.dimensions[0]-second.dimensions[0])
        return float(second.distance_gradient(np.asarray(p)[None],other_p,other_r)[0][0]-first.dimensions[0])
    if second.shape=='sphere':return primitive_gap(second,other_p,other_r,first,p,r)
    from release_colliders import box_separation
    return box_separation(p,r,first.dimensions,other_p,other_r,second.dimensions)


def convex_test(geometry,points):
    from convex_colliders import ConvexBoxTest,ConvexSphereTest,ConvexCylinderTest
    return {'box':ConvexBoxTest,'sphere':ConvexSphereTest,'cylinder':ConvexCylinderTest}[geometry.shape](points)


def convex_gap(test,geometry,p,r,other_p,other_r):
    if geometry.shape=='sphere':return test.gap(p,geometry.dimensions[0],other_p,other_r)
    return test.gap(p,r,geometry.dimensions,other_p,other_r)


def check_installed_geometry(expected,actual):
    imported=Geometry.parse(actual)
    if imported.shape!=expected.shape:raise ValueError('Installed collision shape mismatch')
    np.testing.assert_allclose(imported.dimensions,expected.dimensions,atol=1e-6,rtol=0)
