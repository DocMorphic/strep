"""Prescribed box trajectories on the release physics clock (not dynamic actors)."""
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from object_dynamics import finite_array
from release_colliders import validate_colliders
from scene_constraints import sample_object
from release_geometry import geometry_fields,body_geometry,check_installed_geometry


def validate_moving(values, steps, static=()):
    if not isinstance(values, list) or len(values)+len(static)>96:
        raise ValueError('Expected at most 96 total colliders')
    result=[];seen={x['id'] for x in static}
    for item in values:
        convex=isinstance(item,dict) and item.get('shape')=='convex'
        geometry={'shape','points_m'} if convex else ({'geometry'} if isinstance(item,dict) and 'geometry' in item else {'size_m'})
        if not isinstance(item,dict) or set(item)!={'id','friction','restitution','positions_m','rotations_xyzw'}|geometry:
            raise ValueError('Invalid moving collider fields')
        if not isinstance(item['id'],str) or item['id'] in seen:raise ValueError('Duplicate collider ID')
        if convex:
            from convex_colliders import validate_points
            points=validate_points(item['points_m']);size=np.ptp(points,axis=0).tolist()
        p=finite_array(item['positions_m'],(steps+2,3),'moving positions')
        q=finite_array(item['rotations_xyzw'],(steps+2,4),'moving rotations')
        if not np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-6,rtol=0):
            raise ValueError('Moving rotations must be unit quaternions')
        delta=Rotation.from_quat(q[1:])*Rotation.from_quat(q[:-1]).inv()
        if np.any(delta.magnitude()>=np.pi-1e-6):raise ValueError('Ambiguous collider rotation step')
        dimensions=dict(size_m=size) if convex else geometry_fields(item)
        validate_colliders([dict(id=item['id'],**dimensions,friction=item['friction'],restitution=item['restitution'],
            position_m=p[1].tolist(),rotation_xyzw=q[1].tolist())])
        seen.add(item['id'])
        entry=dict(item,positions_m=p.tolist(),rotations_xyzw=q.tolist())
        if convex:
            from convex_colliders import volume_centroid
            entry['center_of_mass_local_m']=volume_centroid(points).tolist()
        result.append(entry)
    return result


def compile_moving(scene, released, release_frame, *, physics_fps, friction, restitution):
    """Index 0 is one incoming tick; index 1 is release; last is final frame.

    Interpolate the SAME integer-frame samples used by the exported object GLB.
    The incoming sample establishes velocity without advancing the release pose.
    """
    count=scene['frame_count'];stride=physics_fps//30
    steps=(count-1-release_frame)*stride
    times=release_frame+np.arange(-1,steps+1)/stride
    result=[]
    for name,obj in scene['objects'].items():
        if name==released:continue
        p,r=sample_object(obj,count)
        positions=np.stack([np.interp(times,np.arange(count),p[:,axis]) for axis in range(3)],axis=1)
        rotations=Slerp(np.arange(count),Rotation.from_matrix(r))(times).as_quat()
        result.append(dict(id='object:'+name,**geometry_fields(obj),positions_m=positions.tolist(),rotations_xyzw=rotations.tolist(),friction=friction,restitution=restitution))
    return validate_moving(result,steps)


def audit_moving(request, observations, installed):
    expected=request.get('moving_colliders',[])
    if len(installed)!=len(expected):raise ValueError('Missing moving collider geometry')
    for a,b in zip(installed,expected):
        if a['id']!=b['id']:raise ValueError('Moving collider identity mismatch')
        convex=b.get('shape')=='convex'
        if a.get('shape','box')!=b.get('shape','box'):raise ValueError('Moving collider shape mismatch')
        if not convex and 'geometry' in b:check_installed_geometry(body_geometry(b),a['geometry'])
        for field in (['points_m'] if convex else ([] if 'geometry' in b else ['size_m']))+['friction','restitution']:
            np.testing.assert_allclose(a[field],b[field],atol=1e-6,rtol=0)
    for o in observations:
        if [x['id'] for x in o.get('moving_colliders',[])]!=[x['id'] for x in expected]:
            raise ValueError('Missing or reordered moving collider observations')
    for index,item in enumerate(expected):
        states=[o['moving_colliders'][index] for o in observations]
        p=np.array(item['positions_m']);r=Rotation.from_quat(item['rotations_xyzw'])
        center=np.zeros(3)
        if item.get('shape')=='convex':
            from convex_colliders import volume_centroid
            center=volume_centroid(item['points_m'])
            np.testing.assert_allclose([s['center_of_mass_local_m'] for s in states],np.broadcast_to(center,(len(states),3)),atol=1e-6,rtol=0)
        # PhysicsDirectBodyState velocity is at COM, which is not generally
        # the node origin for an asymmetric convex solid.
        com=p+r.apply(np.broadcast_to(center,p.shape))
        v=np.diff(com,axis=0)*request['physics_fps']
        w=(r[1:]*r[:-1].inv()).as_rotvec()*request['physics_fps']
        np.testing.assert_allclose([s['position_m'] for s in states],p[1:],atol=1e-6,rtol=0)
        np.testing.assert_allclose(Rotation.from_quat([s['rotation_xyzw'] for s in states]).as_matrix(),r[1:].as_matrix(),atol=1e-6,rtol=0)
        # Strict diagnostics may reject very large world coordinates / speeds;
        # retain that output rather than silently relaxing float32 precision.
        np.testing.assert_allclose([s['linear_velocity_m_s'] for s in states],v,atol=2e-4,rtol=0)
        np.testing.assert_allclose([s['angular_velocity_rad_s'] for s in states],w,atol=2e-4,rtol=0)
