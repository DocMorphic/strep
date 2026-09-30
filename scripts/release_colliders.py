"""Explicit static scene boxes and independent oriented-box separation screens."""
import re
import numpy as np
from scipy.spatial.transform import Rotation
from object_dynamics import finite_array
from scene_constraints import sample_object
from release_geometry import body_geometry,geometry_fields,primitive_gap,floor_gaps,require_release_geometry


def validate_colliders(values):
    if not isinstance(values,list) or len(values)>32:raise ValueError('Expected at most 32 static colliders')
    result=[];seen=set()
    for item in values:
        geometry_key='geometry' if isinstance(item,dict) and 'geometry' in item else 'size_m'
        if not isinstance(item,dict) or set(item)!={'id','position_m','rotation_xyzw',geometry_key,'friction','restitution'}:raise ValueError('Invalid static collider fields')
        name=item['id']
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_:-]{0,80}',name) or name=='floor' or name in seen:raise ValueError('Invalid or duplicate collider ID')
        seen.add(name);p=finite_array(item['position_m'],(3,),'collider position');geometry=require_release_geometry(body_geometry(item));q=finite_array(item['rotation_xyzw'],(4,),'collider rotation')
        if max(geometry.dimensions)*(2 if geometry.shape=='sphere' else 1)>100 or abs(np.linalg.norm(q)-1)>1e-6:raise ValueError('Invalid collider shape or orientation')
        for field in ['friction','restitution']:
            if type(item[field]) not in (int,float) or not np.isfinite(item[field]) or not 0<=item[field]<=1:raise ValueError('Invalid collider material')
        result.append(dict(item,position_m=p.tolist(),rotation_xyzw=q.tolist()))
    return result


def compile_colliders(scene,released,release_frame,*,friction,restitution):
    result=[]
    for name,obj in scene['objects'].items():
        if name==released:continue
        p,r=sample_object(obj,scene['frame_count']);tail=slice(release_frame,None)
        if np.max(np.abs(p[tail]-p[release_frame]))>1e-8 or np.max(np.abs(r[tail]-r[release_frame]))>1e-8:
            raise ValueError(f'Object {name} moves after release; static collision mode cannot freeze its animation')
        result.append(dict(id='object:'+name,position_m=p[release_frame].tolist(),rotation_xyzw=Rotation.from_matrix(r[release_frame]).as_quat().tolist(),**geometry_fields(obj),friction=friction,restitution=restitution))
    return validate_colliders(result)


def box_separation(p,r,size,other_p,other_r,other_size):
    """Maximum signed separating-axis gap; negative is minimum escape depth.

    For separated boxes a positive gap is an axis projection, not the Euclidean
    closest-point distance. Full 15-axis SAT detects edge-edge overlap too.
    """
    a=np.asarray(r);b=np.asarray(other_r);axes=[*a.T,*b.T]
    axes.extend(np.cross(u,v) for u in a.T for v in b.T)
    axes=np.asarray([v/np.linalg.norm(v) for v in axes if np.linalg.norm(v)>1e-10])
    distance=np.abs(axes@(np.asarray(other_p)-p))
    radii=np.abs(axes@a)@(np.asarray(size)/2)+np.abs(axes@b)@(np.asarray(other_size)/2)
    return float(np.max(distance-radii))


def audit_collisions(request,observations,release_frame):
    rows=[];p=np.array([o['position_m'] for o in observations]);r=Rotation.from_quat([o['rotation_xyzw'] for o in observations]).as_matrix()
    geometry=require_release_geometry(body_geometry(request))
    moving=request.get('moving_colliders',[])
    for item in request.get('static_colliders',[])+moving:
        is_moving='positions_m' in item
        other_p=np.array(item['positions_m'][1:]) if is_moving else np.repeat([item['position_m']],len(p),axis=0)
        other_r=Rotation.from_quat(item['rotations_xyzw'][1:] if is_moving else [item['rotation_xyzw']]*len(p)).as_matrix()
        if item.get('shape')=='convex':
            from convex_colliders import ConvexBoxTest,ConvexSphereTest
            test=ConvexBoxTest(item['points_m']) if geometry.shape=='box' else ConvexSphereTest(item['points_m'])
            gaps=np.array([test.gap(pos,rot,geometry.dimensions,op,orr) if geometry.shape=='box' else test.gap(pos,geometry.dimensions[0],op,orr) for pos,rot,op,orr in zip(p,r,other_p,other_r)])
        else:gaps=np.array([primitive_gap(geometry,pos,rot,body_geometry(item),op,orr) for pos,rot,op,orr in zip(p,r,other_p,other_r)])
        contacts=[o['tick'] for o in observations if item['id'] in o.get('contact_colliders',[])]
        rows.append(dict(id=item['id'],shape='convex' if item.get('shape')=='convex' else body_geometry(item).shape,motion='prescribed' if is_moving else 'static',max_penetration_m=float(max(0.,-gaps.min())),final_signed_axis_gap_m=float(gaps[-1]),
            first_contact_source_frame=release_frame+contacts[0]*30/request['physics_fps'] if contacts else None,
            ticks_with_reported_contact=len(contacts)))
    final_ids=sorted(set(observations[-1].get('contact_colliders',[])))
    final_speed=float(np.linalg.norm(observations[-1]['linear_velocity_m_s']))
    final_angular=float(np.linalg.norm(observations[-1]['angular_velocity_rad_s']))
    gaps_to_floor=floor_gaps(geometry,p,r,request['floor_height_m'])
    floor_depth=float(max(0.,-gaps_to_floor.min())) if request['floor_enabled'] else 0.
    final_gaps={item['id']:abs(item['final_signed_axis_gap_m']) for item in rows}
    if request['floor_enabled']:final_gaps['floor']=abs(float(gaps_to_floor[-1]))
    # A resting candidate needs observed contact and small geometry error;
    # proximity alone must never count as observed support.
    final_touching=any(name in final_gaps and final_gaps[name]<=.01 for name in final_ids)
    relative=[]
    states={x['id']:x for x in observations[-1].get('moving_colliders',[])}
    for name in final_ids:
        v=np.zeros(3);w=np.zeros(3)
        if name in states:
            state=states[name];w=np.array(state['angular_velocity_rad_s'])
            support_com=np.array(state['position_m'])+Rotation.from_quat(state['rotation_xyzw']).apply(state.get('center_of_mass_local_m',[0,0,0]))
            v=np.array(state['linear_velocity_m_s'])+np.cross(w,p[-1]-support_com)
        relative.append(dict(id=name,linear_speed_m_s=float(np.linalg.norm(np.array(observations[-1]['linear_velocity_m_s'])-v)),
            angular_speed_rad_s=float(np.linalg.norm(np.array(observations[-1]['angular_velocity_rad_s'])-w))))
    # Compare rigid motion at the released COM with every observed support.
    # World velocity alone would incorrectly reject a box riding a platform.
    settled=bool(relative) and all(x['linear_speed_m_s']<=.1 and x['angular_speed_rad_s']<=.1 for x in relative)
    passed=floor_depth<=.01 and all(row['max_penetration_m']<=.01 for row in rows) and final_touching and settled
    return dict(colliders=rows,max_floor_penetration_m=floor_depth,final_contact_colliders=final_ids,final_speed_m_s=final_speed,final_angular_speed_rad_s=final_angular,
        final_relative_support_motion=relative,collision_and_settling_screens_passed=bool(passed),actor_collisions_simulated=any(x['id'].startswith('actor:') for x in moving),actor_motion_responds=False,
        scope='Discrete simulation-rate primitive distances or convex SAT and observed contact IDs; 10mm depth/gap, relative support motion at COM 0.1m/s and 0.1rad/s. Prescribed colliders do not react to impacts. Settling excludes valid rolling/bouncing motion and is not a universal action criterion. Not continuous collision, force balance, actor response or animator approval.')
