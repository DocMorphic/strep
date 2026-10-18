"""Source-bound sufficient preflight for box-only fitting at its edited key.

This does not judge a domain permitting character edits. Unknown is never clear.
The archived fitter implementations remain unchanged.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from fixed_grip_box_obstruction import discover,verify
from native_mesh_prop_pose import GripPoseEdit,METHODS as POSE_METHODS
from native_mesh_prop_scene import guarded_output
from native_scene_geometry import faces_for
from strep import save,sha256

METHODS=tuple(sorted(set(POSE_METHODS)|{'fixed_grip_box_obstruction.py','exact_triangle_crossing_witness.py','native_mesh_prop_obstruction_preflight.py'}))


def preflight(permissions_path,output,*,maximum_candidates=10000,maximum_tetrahedra=128):
    for value,cap in [(maximum_candidates,10000),(maximum_tetrahedra,512)]:
        if type(value) is not int or not 1<=value<=cap:raise ValueError('Explicit bounded preflight budget required')
    edit=GripPoseEdit(permissions_path);output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh preflight directory required')
    source=edit.scene;entry=next(r for r in source._rows if r['authored']['id']==edit._spec['contact_id']);row=entry['authored'];stamp=edit._item['keyframes'][edit._key]['time_s']
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={n:sha256(Path(__file__).parent/n) for n in METHODS}
    for n in METHODS:shutil.copyfile(Path(__file__).parent/n,archive/n)
    save(output/'input.json',dict(inputs_sha256=edit.inputs,implementation_sha256=methods,prop=edit._name,contact_id=row['id'],time_s=stamp,maximum_candidates=maximum_candidates,maximum_tetrahedra=maximum_tetrahedra,assumption='fixed-character-world-geometry-at-contact',source_rebased=False,quality_approved=False))
    if row['interval_s'][0]<=stamp<=row['interval_s'][1]:
        centre=source._scene.actor_points(row['actor'],entry['ids'],np.array([stamp])).mean(axis=1)[0];actors={}
        for name,actor in source._scene.actors.items():
            position,rotation=actor['placement'];world=actor['rig'].vertices(actor['sampler'].sample(stamp))@rotation.T+position;actors[name]=(world,faces_for(actor['rig'])[0])
        asset=source._props[edit._name]['asset'];args=(asset.vertices_m,asset.faces,edit._point,centre,row['limits']['position_m'],actors)
        result=discover(*args,maximum_candidates=maximum_candidates,maximum_tetrahedra=maximum_tetrahedra)
        if result['proof'] is not None:result['verification']=verify(*args,result['proof'])
        save(output/'contact-centre.json',dict(world_hex=[float(v).hex() for v in centre]))
    else:result=dict(status='unknown',reason='edited_key_outside_required_contact_interval',proof=None,candidates=0,tetrahedra_checked=0)
    edit.check_inputs()
    if any(sha256(Path(__file__).parent/n)!=sha256(archive/n) or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Preflight implementation changed')
    result.update(job_status='complete',source_inputs_unchanged=True,source_rebased=False,character_motion_edited=False,body_edit_domain_blocked=False,correction_applied=False,whole_animation_certified=False,quality_approved=False,release_approved=False,scope='Sufficient fixed represented actor geometry / ideal rigid box and original grip tolerance obstruction at one mandatory time only. Discovery failure or unsupported shape is unknown, never feasibility. Original rotation/translation caps are not enlarged. Character edits, earlier arithmetic, full motion, dynamics, engines and human review are outside this model.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['permissions','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--maximum-candidates',type=int,default=10000);parser.add_argument('--maximum-tetrahedra',type=int,default=128);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):
            result=preflight(args.permissions,args.output,maximum_candidates=args.maximum_candidates,maximum_tetrahedra=args.maximum_tetrahedra);print({k:result[k] for k in ['job_status','status','reason','candidates','tetrahedra_checked']})
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.output/'preflight'),'--worker','--maximum-candidates',str(args.maximum_candidates),'--maximum-tetrahedra',str(args.maximum_tetrahedra)]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=300),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result);raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
