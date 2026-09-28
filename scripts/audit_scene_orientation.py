"""Actual skin-normal diagnostics for opposing palms and primitive-surface contacts."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_constraints import transform_motion,sample_object,vector
from palm_contacts import surface_normal_track,hand_tangent_track
from build_soma_preview import ASSET
from object_geometry import scene_geometry


def inward_box_face(point,size):
    point=np.asarray(point,dtype=float);half=np.asarray(size,dtype=float)/2
    faces=np.flatnonzero(np.isclose(np.abs(point),half,rtol=0,atol=1e-6))
    if len(faces)!=1 or np.any(np.abs(point)>half+1e-6):raise ValueError('Grip must lie on one unambiguous box face')
    normal=np.zeros(3);axis=faces[0];normal[axis]=-np.sign(point[axis]);return normal


def audit(scene,skin,tolerance_degrees=15):
    actors={};sources={}
    for name,entry in scene['actors'].items():
        path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Actor source escapes project')
        sources[name]=sha256(path);actors[name]=transform_motion(dict(np.load(path)),entry['transform'])
    records=[]
    for c in scene['contacts']:
        target=c['target'];vertex=c['effector'].get('surface_vertex')
        if vertex is None:continue
        actual=surface_normal_track(actors[c['actor']],skin,vertex)
        request=c.get('normal_target')
        if request:
            direction=vector(request.get('direction'),3,'normal direction')
            if abs(np.linalg.norm(direction)-1)>1e-6:raise ValueError('Normal direction must be unit length')
            if request.get('space')=='world':desired=np.tile(direction,(scene['frame_count'],1))
            elif request.get('space')=='object' and request.get('object') in scene.get('objects',{}):
                _,rotation=sample_object(scene['objects'][request['object']],scene['frame_count'])
                desired=np.einsum('fij,j->fi',rotation,direction)
            else:raise ValueError('Normal target must be world or a known object')
            provenance='Explicit authored normal target'
        elif target['space']=='actor':
            if 'surface_vertex' not in target:continue
            desired=-surface_normal_track(actors[target['actor']],skin,target['surface_vertex'])
            provenance='Opposing actual partner skin normal'
        elif target['space']=='object':
            obj=scene['objects'][target['object']];_,rotation=sample_object(obj,scene['frame_count'])
            geometry=scene_geometry(obj)
            direction=inward_box_face(target['point_m'],geometry.dimensions) if geometry.shape=='box' else -geometry.local_surface_normal(target['point_m'])
            desired=np.einsum('fij,j->fi',rotation,direction)
            provenance='Inward analytic primitive surface normal at the grip'
        else:continue
        angles=np.rad2deg(np.arccos(np.clip(np.sum(actual*desired,axis=-1),-1,1)));a,b=c['start_frame'],c['end_frame'];interval=angles[a:b+1]
        records.append(dict(id=c['id'],start_frame=a,end_frame=b,provenance=provenance,max_error_degrees=float(interval.max()),
            mean_error_degrees=float(interval.mean()),frames_over_tolerance=int(np.sum(interval>tolerance_degrees)),frame_count=len(interval),
            actual_normals_world=actual.tolist(),desired_normals_world=desired.tolist(),per_frame_error_degrees=angles.tolist()))
        tangent=c.get('tangent_target')
        if tangent:
            direction=vector(tangent.get('direction'),3,'tangent direction')
            if abs(np.linalg.norm(direction)-1)>1e-6:raise ValueError('Tangent direction must be unit length')
            if tangent.get('space')=='world':wanted=np.tile(direction,(scene['frame_count'],1))
            elif tangent.get('space')=='object' and tangent.get('object') in scene.get('objects',{}):
                _,rotation=sample_object(scene['objects'][tangent['object']],scene['frame_count']);wanted=np.einsum('fij,j->fi',rotation,direction)
            else:raise ValueError('Tangent must be world or a known object')
            if np.any(np.abs(np.sum(wanted*desired,axis=-1))>1e-6):raise ValueError('Authored normal and tangent must be orthogonal')
            measured=hand_tangent_track(actors[c['actor']],skin,vertex,c['effector']['joint'])
            error=np.rad2deg(np.arccos(np.clip(np.sum(measured*wanted,axis=-1),-1,1)));interval=error[a:b+1]
            records[-1].update(tangent_max_error_degrees=float(interval.max()),tangent_frames_over_tolerance=int(np.sum(interval>tolerance_degrees)),
                per_frame_tangent_error_degrees=error.tolist(),actual_tangents_world=measured.tolist(),desired_tangents_world=wanted.tolist())
    return dict(scene_id=scene['id'],sources=sources,tolerance_degrees=tolerance_degrees,contacts=records,
        scope='Area-weighted skinned triangle normals at the chosen contact vertex, not anatomical hand-plane calibration or full hand orientation. 15 degrees is a provisional diagnostic, not an animator-approved acceptance threshold.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('scene',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    data=read(args.scene);scene=data.get('scene',data);result=audit(scene,dict(np.load(ASSET)))
    save(args.output,dict(**result,created_at=now(),scene_sha256=sha256(args.scene),auditor_sha256=sha256(__file__),geometry_sha256=sha256(ROOT/'scripts/object_geometry.py'),palm_code_sha256=sha256(ROOT/'scripts/palm_contacts.py')))
    print([(c['id'],round(c['max_error_degrees'],2),c['frames_over_tolerance']) for c in result['contacts']])
