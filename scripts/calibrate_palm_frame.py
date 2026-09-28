"""Select an unreviewed central-palm candidate with an aligned surface normal."""
import numpy as np
from palm_contacts import calibrate
from floor_contact import Surface


def candidate(skin,hand,normal_limit_degrees=5.,radius_m=.045):
    original=calibrate(skin)[hand];surface=Surface(skin);joint=surface.names.index(hand)
    origin=skin['bind_rig_transform'][joint,:3,3];rotation=skin['bind_rig_transform'][joint,:3,:3]
    p=skin['bind_vertices'];faces=skin['faces'];triangles=p[faces]
    raw=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normals=np.zeros_like(p)
    for k in range(3):np.add.at(normals,faces[:,k],raw)
    lengths=np.linalg.norm(normals,axis=1);normals/=np.maximum(lengths[:,None],1e-15)
    local=(p-origin)@rotation;hint=np.array(original['palm_normal_local']);center=np.array(original['center_local_m'])
    angles=np.degrees(np.arccos(np.clip(normals@rotation@hint,-1,1)));ids=surface.regions[hand]
    ids=ids[(np.linalg.norm(local[ids]-center,axis=1)<radius_m)&(angles[ids]<=normal_limit_degrees)&(lengths[ids]>1e-12)]
    if not len(ids):raise ValueError('No palm candidate satisfies the fixed geometry criteria')
    probe=center+hint*.025;vertex=int(ids[np.linalg.norm(local[ids]-probe,axis=1).argmin()])
    return dict(original=original,candidate={**original,'surface_vertex':vertex,'offset_m':local[vertex].tolist(),
        'label':'normal-aligned geometry-derived palm candidate','status':'anatomical_review_pending'},
        criteria=dict(normal_limit_degrees=normal_limit_degrees,radius_m=radius_m,candidate_count=len(ids),
            old_normal_error_degrees=float(angles[original['surface_vertex']]),new_normal_error_degrees=float(angles[vertex])),
        scope='Bind-mesh geometric heuristic using a knuckle-derived palm-plane hint. Not anatomical approval, contact-area calibration or a guarantee on posed geometry.')
