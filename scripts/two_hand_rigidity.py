"""Necessary two-grip feasibility checks; does not modify hands or object tracks."""
import argparse
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from scene_constraints import transform_motion,effector_track,sample_object


def shortest_rotation(source,target):
    source=np.asarray(source,dtype=float);target=np.asarray(target,dtype=float)
    if not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError('Non-finite grip axis')
    ns,nt=np.linalg.norm(source),np.linalg.norm(target)
    if min(ns,nt)<1e-10:raise ValueError('Coincident grips have no defined two-hand axis')
    a,b=source/ns,target/nt;dot=np.clip(a@b,-1,1);axis=np.cross(a,b);sine=np.linalg.norm(axis)
    if sine<1e-10:
        if dot>0:return np.eye(3)
        basis=np.eye(3)[np.argmin(np.abs(a))];axis=np.cross(a,basis);axis/=np.linalg.norm(axis)
        return Rotation.from_rotvec(np.pi*axis).as_matrix()
    return Rotation.from_rotvec(np.arctan2(sine,dot)*axis/sine).as_matrix()


def fit_two_grips(local_grips,world_palms,reference_rotation):
    """Point-optimal rigid pose with the smallest axis correction to a reference.

    The two points leave twist unconstrained. This choice is a diagnostic, not
    evidence of wrist orientation, collision clearance or physical attachment.
    """
    grips=np.asarray(local_grips,dtype=float);palms=np.asarray(world_palms,dtype=float);reference=np.asarray(reference_rotation,dtype=float)
    if grips.shape!=(2,3) or palms.shape!=(2,3) or reference.shape!=(3,3):raise ValueError('Two XYZ grips and one rotation required')
    if not np.isfinite(grips).all() or not np.isfinite(palms).all() or not np.isfinite(reference).all():raise ValueError('Non-finite fit')
    if not np.allclose(reference.T@reference,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(reference),1,atol=1e-6):raise ValueError('Reference must be a proper rigid rotation')
    local_axis=grips[1]-grips[0];world_axis=palms[1]-palms[0]
    r=shortest_rotation(reference@local_axis,world_axis)@reference
    p=palms.mean(0)-r@grips.mean(0)
    bound=abs(np.linalg.norm(world_axis)-np.linalg.norm(local_axis))/2
    return p,r,float(bound)


def audit(scene,skin):
    sources={};actors={};records=[]
    for actor,entry in scene['actors'].items():
        path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Motion escapes project')
        sources[actor]=sha256(path);actors[actor]=transform_motion(dict(np.load(path)),entry['transform'])
    for object_id,obj in scene.get('objects',{}).items():
        contacts=[c for c in scene['contacts'] if c['target']['space']=='object' and c['target']['object']==object_id]
        if len(contacts)!=2:continue
        left,right=contacts;a=max(left['start_frame'],right['start_frame']);b=min(left['end_frame'],right['end_frame'])
        if a>b:continue
        palms=np.stack([effector_track(actors[c['actor']],c['effector'],skin) for c in contacts],axis=1)
        grips=np.array([c['target']['point_m'] for c in contacts]);p,r=sample_object(obj,scene['frame_count']);frames=[]
        separation=np.linalg.norm(grips[1]-grips[0]);tolerance_sum=sum(c['tolerance_m'] for c in contacts)
        for f in range(a,b+1):
            distance=float(np.linalg.norm(palms[f,1]-palms[f,0]));separation_error=abs(distance-separation)
            item=dict(frame=f,palm_separation_m=distance,grip_separation_m=float(separation),separation_error_m=float(separation_error),
                free_rigid_object_feasible_for_point_tolerances=bool(separation_error<=tolerance_sum),equal_tolerance_lower_bound_m=float(separation_error/2))
            try:
                fitted_p,fitted_r,bound=fit_two_grips(grips,palms[f],r[f])
                actual=np.linalg.norm(grips@fitted_r.T+fitted_p-palms[f],axis=1)
                np.testing.assert_allclose(actual,bound,atol=1e-10)
                item.update(best_fit_translation_m=fitted_p.tolist(),best_fit_rotation_xyzw=Rotation.from_matrix(fitted_r).as_quat().tolist(),
                    required_object_translation_m=float(np.linalg.norm(fitted_p-p[f])),required_object_rotation_degrees=float(np.rad2deg(Rotation.from_matrix(r[f].T@fitted_r).magnitude())))
            except ValueError as error:item['fit_error']=str(error)
            frames.append(item)
        records.append(dict(object=object_id,contact_ids=[c['id'] for c in contacts],start_frame=a,end_frame=b,
            impossible_point_frames=sum(not f['free_rigid_object_feasible_for_point_tolerances'] for f in frames),
            max_equal_tolerance_lower_bound_m=max(f['equal_tolerance_lower_bound_m'] for f in frames),frames=frames))
    return dict(scene_id=scene['id'],sources=sources,objects=records,
        scope='Necessary fixed-hand two-point rigidity bound allowing a freely moving rigid object. Feasibility does not imply the authored object path, palm orientation, reachability, collision clearance or naturalness. Diagnostic fitted object poses are not applied.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--output',required=True);args=p.parse_args()
    d=read(args.scene);result=audit(d.get('scene',d),dict(np.load(ASSET)))
    save(args.output,dict(**result,created_at=now(),scene_sha256=sha256(args.scene),auditor_sha256=sha256(__file__)))
    print([(o['object'],o['impossible_point_frames'],o['max_equal_tolerance_lower_bound_m']) for o in result['objects']])
