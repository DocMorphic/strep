"""Frozen actor-native object geometry and oriented contact constraints."""
import numpy as np
from scene_constraints import pose,sample_object,vector
from audit_scene_orientation import inward_box_face
from floor_contact import Surface
from object_geometry import scene_geometry,Geometry


def context_primitives(context):
    """Canonical objects, with support for previously saved box-only contexts."""
    if 'primitives' in context:
        return [(Geometry.parse(item['geometry']),item) for item in context['primitives']]
    return [(Geometry('box',tuple(item['size_m'])),item) for item in context.get('boxes',[])]


def compile_context(scene,actor_id,contact_ids,skin,*,release_endpoint_guards=False):
    if any('region_contact' in c for c in scene['contacts'] if c['id'] in contact_ids):
        raise ValueError('Legacy scene solver does not support distributed region contacts')
    origin,rotation=pose(scene['actors'][actor_id]['transform']);frames=scene['frame_count']
    if abs(origin[1])>1e-7 or not np.allclose(rotation@[0.,1.,0.],[0.,1.,0.],atol=1e-7):raise ValueError('Solver requires yaw-only actor placement on ground')
    boxes=[];primitives=[];sampled={}
    for name,obj in scene.get('objects',{}).items():
        p,r=sample_object(obj,frames);sampled[name]=(p,r)
        geometry=scene_geometry(obj)
        item=dict(id=name,positions_m=((p-origin)@rotation).tolist(),rotations=(rotation.T@r).tolist())
        primitives.append(dict(**item,geometry=geometry.record()))
        if geometry.shape=='box':boxes.append(dict(**item,size_m=list(geometry.dimensions)))
    normals=[]
    for c in scene['contacts']:
        if c['id'] not in contact_ids:continue
        if c['actor']!=actor_id:raise ValueError('Contact actor mismatch')
        vertex=c['effector'].get('surface_vertex')
        if type(vertex)!=int or not 0<=vertex<len(skin['bind_vertices']):raise ValueError('Oriented contact requires a surface vertex')
        target=c['target'];request=c.get('normal_target')
        if request:
            direction=vector(request.get('direction'),3,'normal direction')
            if abs(np.linalg.norm(direction)-1)>1e-6:raise ValueError('Normal direction must be unit length')
            if request.get('space')=='world':world=np.tile(direction,(frames,1))
            elif request.get('space')=='object' and request.get('object') in sampled:world=np.einsum('fij,j->fi',sampled[request['object']][1],direction)
            else:raise ValueError('Normal target must be world or a known object')
            provenance='Explicit authored normal target'
        elif target['space']=='object':
            geometry=scene_geometry(scene['objects'][target['object']])
            direction=inward_box_face(target['point_m'],geometry.dimensions) if geometry.shape=='box' else -geometry.local_surface_normal(target['point_m'])
            world=np.einsum('fij,j->fi',sampled[target['object']][1],direction)
            provenance='Inward analytic primitive surface normal at the selected grip'
        else:
            if c.get('tangent_target'):raise ValueError('A tangent target requires a normal target')
            continue
        a,b=c['start_frame'],c['end_frame']
        if type(a)!=int or type(b)!=int or not 0<=a<=b<frames:raise ValueError('Invalid oriented contact interval')
        item=dict(id=c['id'],surface_vertex=vertex,start_frame=a,end_frame=b,directions=(world@rotation).tolist(),provenance=provenance)
        tangent=c.get('tangent_target')
        if tangent:
            hand=c['effector'].get('joint');names=Surface(skin).names
            if hand not in ['LeftHand','RightHand']:raise ValueError('Tangent requires a hand effector')
            direction=vector(tangent.get('direction'),3,'tangent direction')
            if abs(np.linalg.norm(direction)-1)>1e-6:raise ValueError('Tangent direction must be unit length')
            if tangent.get('space')=='world':tw=np.tile(direction,(frames,1))
            elif tangent.get('space')=='object' and tangent.get('object') in sampled:tw=np.einsum('fij,j->fi',sampled[tangent['object']][1],direction)
            else:raise ValueError('Tangent must be world or a known object')
            if np.any(np.abs(np.sum(tw*world,axis=-1))>1e-6):raise ValueError('Authored normal and tangent must be orthogonal')
            item.update(tangent_directions=(tw@rotation).tolist(),hand_joint=names.index(hand),knuckle_joints=[names.index(hand+finger+'2') for finger in ['Index','Middle','Ring','Pinky']])
        normals.append(item)
    result=dict(frame_count=frames,normals=normals,boxes=boxes,primitives=primitives,
        scope='Frozen object poses and surface-frame targets in actor-native coordinates; optional local partner clearance cuts. No joint partner, object dynamics or anatomy constraints.')
    if scene.get('partner_cut_file'):
        from partner_surface_cuts import load_cuts
        result['partner_cuts'],result['partner_cut_provenance']=load_cuts(scene,actor_id,skin)
    if release_endpoint_guards:
        from scene_release_guards import compile_release_guards
        result['release_guards']=compile_release_guards(scene,actor_id,contact_ids)
    return result


def box_signed_distance(points,position,rotation,size):
    """Negative inside an oriented box, Euclidean distance outside."""
    q=np.abs((points-position)@rotation)-np.asarray(size)/2
    return np.linalg.norm(np.maximum(q,0),axis=-1)+np.minimum(q.max(-1),0)
