"""Frozen target-feasibility trial after verified coordinated correction."""
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_pose_trajectory import PoseTrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter,window_basis
from rig_pose_tolerances import PoseTolerances
from rig_loop import encode
from action_worker_lock import worker_lock

OUT=ROOT/'reports/pose-tolerances-v1'
SOURCE=ROOT/'reports/coupled-pose-v1'


def run_case(case):
    source=SOURCE/case;out=OUT/case;out.mkdir()
    request=read(source/'request.json');spec=read(source/'spec.json')
    with np.load(source/'fit.npz',allow_pickle=False) as archive:data={k:archive[k] for k in archive.files}
    hashes={name:sha256(source/name) for name in ['fit.npz','candidate.glb','request.json','spec.json']}
    for name in ['original.glb','target.npz','request.json','spec.json','LICENSE.txt']:
        shutil.copyfile(source/name,out/name)
    shutil.copyfile(source/'candidate.glb',out/'coupled.glb')
    save(out/'warm-start.json',dict(source=source.relative_to(ROOT).as_posix(),files=hashes))
    rig=RigAsset.load(out/'original.glb')
    fitter=PoseTrajectoryFitter(rig,spec,data['local_before'],
        {k:np.array(v) for k,v in request['targets_m'].items()},request['envelope'],request['supports'],[request['joint_goal']])
    for frame,parameters in enumerate(data['parameters']):fitter.accept(frame,parameters)
    basis=window_basis(request['envelope'],spacing=10);np.save(out/'basis.npy',basis,allow_pickle=False)
    target=PoseTolerances(CoupledPoseFitter(fitter,basis),position_m=.005,orientation_degrees=5.)
    save(out/'pipeline.json',dict(status='fitting_target_feasibility',started_at=now()))
    with threadpool_limits(limits=1):values,trace,summary=target.solve(out,max_iterations=150)
    after=fitter.world.copy();fixed=np.array(request['envelope'])==0;after[fixed]=data['before'][fixed]
    animated={channel['target']['node'] for channel in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    _,roundtrip=encode(rig,after,animated,spec['root_node'],out/'candidate.glb','Explicit target tolerance candidate')
    np.savez_compressed(out/'fit.npz',before=data['before'],after=after,parameters=values,
                        local_before=data['local_before'],warm_start=data['after'],warm_parameters=data['parameters'])
    save(out/'optimizer-trace.json',trace);save(out/'fit-summary.json',dict(target_feasibility=summary,export=roundtrip,quality_approved=False))
    save(out/'solver.json',[dict(success=summary['solver_success'],objective='max_normalized_target_violation',
        cost_before=summary['initial_target_violation'],cost_after=summary['final_target_violation'])])
    assert all(sha256(source/name)==digest for name,digest in hashes.items())
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))
    print(case,summary,flush=True)


def run():
    if OUT.exists():raise ValueError('Preserve previous trial output')
    assert read(SOURCE/'finalizer-state.json')['status']=='complete'
    assert read(SOURCE/'coupled-verification.json')['checks_passed']
    with worker_lock():
        OUT.mkdir()
        save(OUT/'protocol.json',dict(created_at=now(),cases=['jump-land','dance','get-up'],seed=502,
            source_study='coupled-pose-v1',selection='Same three posthoc development cases; no held-out or equal-compute claim.',
            position_screen_m=.005,orientation_screen_degrees=5.,floor_screen_m=.01,
            position_tolerance_m=.005,orientation_tolerance_degrees=5.,target_interior_margin=.01,
            max_iterations=150,knot_spacing_frames=10,hard_motion_limits_unchanged=True,
            objective='Minimize worst normalized target violation; surface/support energy is not optimized in this feasibility stage.',
            checkpoint_unchanged=True,quality_approved=False))
        snapshot=OUT/'implementation';snapshot.mkdir();hashes={}
        for name in ['study_pose_tolerances.py','rig_pose_tolerances.py','rig_coupled_pose.py','rig_pose_trajectory.py',
                     'rig_trajectory_fit.py','rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py',
                     'rig_loop.py','support_contact_v5.py','verify_pose_trajectory.py','verify_pose_tolerance_study.py',
                     'verify_coupled_pose.py','verify_trajectory_fit.py']:
            shutil.copyfile(ROOT/'scripts'/name,snapshot/name);hashes[name]=sha256(snapshot/name)
        save(OUT/'implementation.json',dict(created_at=now(),files=hashes))
        for case in ['jump-land','dance','get-up']:
            save(OUT/'pipeline.json',dict(status='fitting',case=case,updated_at=now()));run_case(case)
        save(OUT/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':run()
