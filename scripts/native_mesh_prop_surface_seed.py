"""Surface-guided prop orientations; guidance never replaces complete geometry.

All proposals reference the original GripPoseEdit permissions. Incident winding
normals suggest opposing grip orientations and explicit twist samples. They do
not certify outwardness, a grasp, feasibility, or animation quality.
"""
import argparse
import copy
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial.transform import Rotation

from native_mesh_prop_pose import GripPoseEdit,conditions,metrics,pareto_improvement,METHODS as POSE_METHODS
from native_mesh_prop_scene import MeshPropScene,_json,guarded_output
from native_scene_geometry import faces_for
from native_observation_archive import ObservationArchive,verify
from strep import save,sha256

METHODS=tuple(sorted(set(POSE_METHODS)|{'native_mesh_prop_surface_seed.py'}))


def unit(value):
    if isinstance(value,(list,tuple)) and any(isinstance(v,(bool,np.bool_)) for v in value):raise ValueError('Finite nonzero three-vector required')
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.shape!=(3,) or not np.isfinite(raw).all():raise ValueError('Finite nonzero three-vector required')
    value=raw.astype(float);length=np.linalg.norm(value)
    if not np.isfinite(length) or length==0:raise ValueError('Finite nonzero three-vector required')
    return value/length


def opposing_orientation(local_normal,actor_normal,twist_degrees):
    """Oppose the winding normals, with twist about the actor's world normal."""
    if type(twist_degrees) not in (int,float) or not np.isfinite(twist_degrees) or not 0<=twist_degrees<360:raise ValueError('Explicit twist in[0,360) required')
    source=unit(local_normal);normal=unit(actor_normal);target=-normal
    cross=np.cross(source,target);length=np.linalg.norm(cross);dot=float(source@target)
    if length:
        align=Rotation.from_rotvec(cross/length*np.arctan2(length,dot))
    elif dot<0:
        axis=np.eye(3)[np.argmin(np.abs(source))];axis=unit(np.cross(source,axis));align=Rotation.from_rotvec(np.pi*axis)
    else:align=Rotation.identity()
    return Rotation.from_rotvec(np.radians(twist_degrees)*normal)*align


def incident_guidance(vertices,faces,ids):
    """Keep every incident face identity; non-incident faces remain in audits."""
    vertices=np.asarray(vertices);faces=np.asarray(faces);ids=np.asarray(ids)
    if vertices.dtype.kind not in 'fiu' or vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or not np.isfinite(vertices).all():raise ValueError('Complete finite world vertices required')
    if faces.dtype.kind not in 'iu' or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or np.any(faces<0) or np.any(faces>=len(vertices)):raise ValueError('Complete valid triangle indices required')
    if ids.dtype.kind not in 'iu' or ids.ndim!=1 or not 1<=len(ids)<=1024 or len(np.unique(ids))!=len(ids) or np.any(ids<0) or np.any(ids>=len(vertices)):raise ValueError('Distinct valid contact vertex indices required')
    incident=np.flatnonzero(np.isin(faces,ids).any(axis=1))
    if not 1<=len(incident)<=128:raise ValueError('Guidance requires1-128 incident faces; no incident faces silently omitted')
    triangles=vertices[faces[incident]].astype(float);cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
    if np.any(~np.isfinite(cross)) or np.any(~np.isfinite(lengths)) or np.any(lengths==0):raise ValueError('Degenerate incident face cannot supply guidance')
    directions=[];weighted=cross.sum(axis=0)
    if np.linalg.norm(weighted)>0:directions.append(dict(kind='area-weighted-winding',face=None,normal=unit(weighted).tolist()))
    directions += [dict(kind='incident-face-winding',face=int(index),normal=unit(value).tolist()) for index,value in zip(incident,cross)]
    return dict(contact_vertices=ids.tolist(),incident_faces=incident.tolist(),directions=directions,weighted_normal_available=bool(np.linalg.norm(weighted)>0),outward_normal_verified=False,self_intersection_checked=False,geometry_approval=False)


def surface_proposals(edit,twists_degrees=(0.,90.,180.,270.)):
    if not isinstance(twists_degrees,(tuple,list)) or not 1<=len(twists_degrees)<=16 or any(type(v) not in (int,float) or not np.isfinite(v) or not 0<=v<360 for v in twists_degrees) or len(set(twists_degrees))!=len(twists_degrees):raise ValueError('Declare1-16 distinct finite twist angles in[0,360)')
    entry=next(row for row in edit.scene._rows if row['authored']['id']==edit._spec['contact_id']);row=entry['authored'];stamp=edit._item['keyframes'][edit._key]['time_s']
    if not row['interval_s'][0]<=stamp<=row['interval_s'][1]:raise ValueError('Edited key must lie in the selected contact interval')
    actor=edit.scene._scene.actors[row['actor']];p,r=actor['placement'];vertices=actor['rig'].vertices(actor['sampler'].sample(stamp))@r.T+p;faces,_=faces_for(actor['rig'])
    guide=incident_guidance(vertices,faces,entry['ids']);guide.update(actor=row['actor'],contact_id=row['id'],key_index=edit._key,time_s=stamp,twists_degrees=list(twists_degrees),full_actor_faces=len(faces),source_relative=True,rotation_locked=edit._angle==0)
    proposals=[]
    if edit._angle:
        original=Rotation.from_quat(edit._item['keyframes'][edit._key]['rotation_xyzw'])
        for direction_index,direction in enumerate(guide['directions']):
            for twist in twists_degrees:
                target=opposing_orientation(entry['normal'],direction['normal'],twist);delta=original.inv()*target
                value=np.r_[delta.as_rotvec()/np.radians(edit._angle),1. if edit._clearance else 0.]
                proposals.append(dict(direction_index=direction_index,twist_degrees=twist,controls=value.tolist()))
    edit.check_inputs();return guide,proposals


def search(permissions_path,policy_path,output,*,maximum_candidates=32,twists_degrees=(0.,90.,180.,270.),warm_start_path=None):
    if type(maximum_candidates) is not int or not 1<=maximum_candidates<=256:raise ValueError('Candidate budget1-256 required')
    edit=GripPoseEdit(permissions_path);policy_path=Path(policy_path).resolve();policy,policy_digest=_json(policy_path);times,_,_=edit.scene._clock(policy)
    guide,proposals=surface_proposals(edit,twists_degrees);table=[dict(kind='original',controls=[0.,0,0,0])];bindings={**edit.inputs,str(policy_path):policy_digest}
    if warm_start_path is not None:
        warm_start_path=Path(warm_start_path).resolve();warm,digest=_json(warm_start_path)
        if set(warm)!={'schema','permissions_sha256','controls'} or warm['schema']!='strep-prop-source-relative-warm-start-v1' or warm['permissions_sha256']!=sha256(permissions_path):raise ValueError('Warm start must bind original pose permissions')
        value=edit._value(warm['controls']);table.append(dict(kind='source-relative-warm-start',controls=value.tolist()));bindings[str(warm_start_path)]=digest
    table += [dict(kind='surface-guided',**row) for row in proposals];output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh surface-guided search output required')
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={name:sha256(Path(__file__).parent/name) for name in METHODS}
    for name in METHODS:shutil.copyfile(Path(__file__).parent/name,archive/name)
    save(output/'input.json',dict(inputs_sha256=bindings,implementation_sha256=methods,candidate_table=table,maximum_candidates=maximum_candidates,geometry_clock_s=times.tolist(),guidance=guide,source_rebased=False,quality_approved=False))
    history=[];baseline=None;baseline_measure=None;best=None;best_measure=None;feasible=None
    for index,item in enumerate(table[:maximum_candidates]):
        value=item['controls'];row=dict(probe=index,**item)
        try:response=edit.evaluate(value)
        except ValueError:
            row.update(native_pose_permissions_pass=False,accepted=False,reason='control_domain');history.append(row);save(output/'history.json',history);continue
        row['native_pose_permissions_pass']=response['report']['native_pose_permissions_pass']
        if not row['native_pose_permissions_pass']:
            row.update(accepted=False,reason='native_pose_permissions');history.append(row);save(output/'history.json',history);continue
        folder=output/f'probe-{index:03d}';manifest=edit.write(value,folder);candidate=MeshPropScene(manifest)
        bound,bound_arrays=edit.sampled_permissions(candidate,policy);save(folder/'sampled-permissions.json',bound);np.savez_compressed(folder/'sampled-permissions.npz',**bound_arrays)
        contact,arrays=candidate.contact_audit();save(folder/'contacts.json',contact);np.savez_compressed(folder/'contact-observations.npz',**arrays)
        derived=copy.deepcopy(policy);derived['mesh_scene_sha256']=sha256(manifest);save(folder/'policy.json',derived)
        with ObservationArchive(folder/'geometry-observations.npz') as sink:geometry,_=candidate.geometry(derived,observation_sink=sink)
        verify(folder/'geometry-observations.npz');save(folder/'geometry.json',geometry);current=conditions(geometry);measure=metrics(geometry)
        if baseline is None:
            assert index==0;baseline=current;baseline_measure=measure.copy();save(output/'baseline.json',dict(metrics=measure,conditions=[dict(id=list(key),passed=value) for key,value in baseline.items()]))
        if current.keys()!=baseline.keys():raise ValueError('Original complete condition population changed')
        new_failures=sum(baseline[key] and not current[key] for key in baseline);no_worse=all(measure[key]<=baseline_measure[key] for key in baseline_measure)
        allowed=bool(bound['all_sampled_pose_permissions_pass'] and contact['all_declared_point_contacts_pass'] and new_failures==0 and no_worse)
        improved=bool(allowed and pareto_improvement(measure,best_measure));clean=bool(allowed and geometry['sampled_conditions_pass'])
        if improved:best=index;best_measure=measure.copy()
        if clean:feasible=index
        row.update(sampled_pose_permissions_pass=bound['all_sampled_pose_permissions_pass'],all_declared_point_contacts_pass=contact['all_declared_point_contacts_pass'],new_failed_geometry_conditions=new_failures,metrics=measure,collision_metrics_no_worse_than_source=no_worse,admissible_for_comparison=allowed,improves_best=improved,sampled_geometry_pass=geometry['sampled_conditions_pass'],sampled_candidate_pass=clean)
        save(folder/'decision.json',dict(row,original_selected=True,quality_approved=False,release_approved=False));history.append(row);save(output/'history.json',history);print(row,flush=True)
        if clean:break
    edit.check_inputs()
    if any(sha256(path)!=digest for path,digest in bindings.items()) or any(sha256(Path(__file__).parent/name)!=digest or sha256(archive/name)!=digest for name,digest in methods.items()):raise ValueError('Source or implementation changed')
    result=dict(status='complete',best_admissible_probe=best,sampled_feasible_probe=feasible,candidates_recorded=len(history),candidate_table_size=len(table),candidate_limit=maximum_candidates,complete_table_evaluated=len(history)==len(table),history=history,geometry_times=len(times),source_assets_and_author_permissions_unchanged=True,source_rebased=False,character_motion_edited=False,original_selected=True,continuous_collision_certified=False,physics_verified=False,quality_approved=False,release_approved=False,scope='Finite winding-normal/twist-guided proposals with original source/caps/frozen keys, complete native/frame pose bounds, all declared contacts and every geometry policy condition. Original passing conditions and all source collision metrics protected. Winding guidance is not an outward-normal, grasp, global feasibility, complete-clock/continuous geometry, dynamics, engine, semantic or human certificate.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['permissions','policy','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--maximum-candidates',type=int,default=32);parser.add_argument('--warm-start',type=Path);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):print(search(args.permissions,args.policy,args.output,maximum_candidates=args.maximum_candidates,warm_start_path=args.warm_start))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.policy.resolve()),str(args.output/'search'),'--worker','--maximum-candidates',str(args.maximum_candidates)]
        if args.warm_start:arguments+=['--warm-start',str(args.warm_start.resolve())]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result);raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
