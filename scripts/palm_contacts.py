"""Geometry-derived SOMA palm candidates, requiring anatomical/animator review.

Use metacarpal/finger geometry to choose a surface point, then evaluate its actual
eight-weight skin motion. A rigid wrist offset alone is not assumed exact.
"""
import numpy as np
from floor_contact import Surface


def calibrate(skin):
    surface=Surface(skin);names=surface.names;bind=skin['bind_rig_transform'];result={}
    for side in ['Left','Right']:
        hand=names.index(side+'Hand');origin=bind[hand,:3,3];rotation=bind[hand,:3,:3]
        def local(name):return (bind[names.index(side+name),:3,3]-origin)@rotation
        knuckles=np.array([local('Hand'+finger+'2') for finger in ['Index','Middle','Ring','Pinky']])
        longitudinal=knuckles.mean(0);longitudinal/=np.linalg.norm(longitudinal)
        across=knuckles[0]-knuckles[-1];normal=np.cross(longitudinal,across);normal/=np.linalg.norm(normal)
        bend=local('HandMiddleEnd')-local('HandMiddle2');bend-=longitudinal*(bend@longitudinal)
        if normal@bend<0:normal=-normal
        center=knuckles.mean(0)*.55
        ids=surface.regions[side+'Hand'];points=(skin['bind_vertices'][ids]-origin)@rotation
        # Choose the skin nearest the palm-side probe, within the central palm.
        nearby=np.linalg.norm(points-center,axis=1)<.045
        candidates=ids[nearby];local_points=points[nearby]
        if not len(candidates):raise ValueError('No central palm skin vertices')
        target=center+normal*.025
        i=int(np.linalg.norm(local_points-target,axis=1).argmin());vertex=int(candidates[i]);offset=local_points[i]
        result[side+'Hand']=dict(surface_vertex=vertex,joint=side+'Hand',offset_m=offset.tolist(),palm_normal_local=normal.tolist(),
            center_local_m=center.tolist(),label='geometry-derived palm surface candidate',status='anatomical_review_pending')
    return result


def surface_track(actor,skin,vertex):
    if type(vertex)!=int or not 0<=vertex<len(skin['bind_vertices']):raise ValueError('Invalid surface vertex')
    surface=Surface(skin)
    return np.array([surface.vertices(r,p,[vertex])[0] for r,p in zip(actor['rotations'],actor['positions'])])


def surface_normal_track(actor,skin,vertex):
    """Area-weighted normal of the actual skinned triangles touching a vertex.

    Uses mesh winding; does not replace anatomical calibration with a wrist axis.
    Degenerate geometry is rejected rather than assigned an arbitrary normal.
    """
    if type(vertex)!=int or not 0<=vertex<len(skin['bind_vertices']):raise ValueError('Invalid surface vertex')
    faces=skin['faces'][np.any(skin['faces']==vertex,axis=1)]
    if not len(faces):raise ValueError('Surface vertex has no adjacent triangles')
    ids,remap=np.unique(faces,return_inverse=True);triangles=remap.reshape(-1,3);surface=Surface(skin);normals=[]
    for rotation,position in zip(actor['rotations'],actor['positions']):
        # Recenter before taking tiny triangle differences. Float32 LBS weights
        # sum to one only to rounding precision; large world translations must
        # not amplify that error into a spurious change in normal direction.
        points=surface.vertices(rotation,position-position[0],ids)[triangles]
        normal=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]).sum(0)
        length=np.linalg.norm(normal)
        if length<1e-12:raise ValueError('Degenerate palm surface normal')
        normals.append(normal/length)
    return np.asarray(normals)


def hand_tangent_track(actor,skin,vertex,hand):
    """Wrist-to-knuckle direction projected into the actual palm tangent plane."""
    surface=Surface(skin);names=surface.names
    if hand not in ['LeftHand','RightHand']:raise ValueError('Hand tangent requires LeftHand or RightHand')
    joints=[names.index(hand+finger+'2') for finger in ['Index','Middle','Ring','Pinky']]
    normal=surface_normal_track(actor,skin,vertex)
    direction=actor['positions'][:,joints].mean(1)-actor['positions'][:,names.index(hand)]
    direction-=normal*np.sum(direction*normal,axis=-1,keepdims=True)
    length=np.linalg.norm(direction,axis=-1,keepdims=True)
    if np.any(length<1e-8):raise ValueError('Degenerate projected hand tangent')
    return direction/length
