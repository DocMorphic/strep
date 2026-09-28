"""Quality refinement of reached targets; failed inputs stay explicitly rejected."""
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_pose_trajectory import PoseTrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter,window_basis
from rig_target_refinement import TargetPreservingRefiner
from rig_loop import encode
from action_worker_lock import worker_lock

OUT=ROOT/'reports/target-refinement-v1';SOURCE=ROOT/'reports/pose-tolerances-v1'


def run_case(case):
    source=SOURCE/case;out=OUT/case;out.mkdir()
    request=read(source/'request.json');spec=read(source/'spec.json')
    data=dict(np.load(source/'fit.npz',allow_pickle=False))
    hashes={name:sha256(source/name) for name in ['fit.npz','candidate.glb','request.json','spec.json']}
    for name in ['original.glb','target.npz','request.json','spec.json','LICENSE.txt']:shutil.copyfile(source/name,out/name)
    shutil.copyfile(source/'candidate.glb',out/'target-met.glb')
    save(out/'warm-start.json',dict(source=source.relative_to(ROOT).as_posix(),files=hashes))
    rig=RigAsset.load(out/'original.glb')
    fitter=PoseTrajectoryFitter(rig,spec,data['local_before'],{k:np.array(v) for k,v in request['targets_m'].items()},
                              request['envelope'],request['supports'],[request['joint_goal']])
    for frame,x in enumerate(data['parameters']):fitter.accept(frame,x)
    basis=window_basis(request['envelope'],spacing=10);np.save(out/'basis.npy',basis,allow_pickle=False)
    refiner=TargetPreservingRefiner(CoupledPoseFitter(fitter,basis))
    save(out/'guards.json',dict(floor_caps_m=refiner.floor_caps.tolist(),target_interior_margin=refiner.target_margin,
        supports=[{k:v.tolist() for k,v in caps.items()} for caps in refiner.support_caps]))
    with threadpool_limits(limits=1):values,trace,summary=refiner.solve(out,max_iterations=40)
    after=fitter.world.copy();fixed=np.array(request['envelope'])==0;after[fixed]=data['before'][fixed]
    animated={channel['target']['node'] for channel in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    _,roundtrip=encode(rig,after,animated,spec['root_node'],out/'candidate.glb','Target-preserving refinement')
    np.savez_compressed(out/'fit.npz',before=data['before'],after=after,parameters=values,local_before=data['local_before'],
                        warm_start=data['after'],warm_parameters=data['parameters'])
    save(out/'optimizer-trace.json',trace);save(out/'fit-summary.json',dict(refinement=summary,export=roundtrip,quality_approved=False))
    save(out/'solver.json',[dict(success=summary['solver_success'],cost_before=summary['cost_before'],cost_after=summary['cost_after'])])
    assert all(sha256(source/name)==digest for name,digest in hashes.items())
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False));print(case,summary,flush=True)


def run():
    if OUT.exists():raise ValueError('Preserve previous trial')
    assert read(SOURCE/'finalizer-state.json')['status']=='complete'
    verified=read(SOURCE/'target-verification.json');assert verified['checks_passed']
    eligible=[row['case'] for row in verified['cases'] if row['targets_reached']]
    rejected=[dict(case=row['case'],reason='Input joint targets not reached',source_flags=row['flags']) for row in verified['cases'] if not row['targets_reached']]
    with worker_lock():
        OUT.mkdir();save(OUT/'protocol.json',dict(created_at=now(),requested_cases=[r['case'] for r in verified['cases']],cases=eligible,rejected_inputs=rejected,
            source_study='pose-tolerances-v1',seed=502,position_screen_m=.005,orientation_screen_degrees=5.,floor_screen_m=.01,
            max_iterations=40,knot_spacing_frames=10,floor_guard_slack_m=1e-6,support_position_min_radius_m=1e-4,
            support_edge_min_radius_m=1e-5,target_margin_policy='min(0.001, half the initial minimum normalized target margin)',
            selection='Refine only reached targets; rejected original requests remain in the denominator. Posthoc development fixtures.',quality_approved=False))
        snapshot=OUT/'implementation';snapshot.mkdir();files={}
        for name in ['study_target_refinement.py','rig_target_refinement.py','rig_pose_tolerances.py','rig_coupled_pose.py','rig_pose_trajectory.py',
                     'rig_trajectory_fit.py','rig_clearance_fit.py','target_rig_contact.py','rig_periodic_contact.py','rig_loop.py','support_contact_v5.py']:
            shutil.copyfile(ROOT/'scripts'/name,snapshot/name);files[name]=sha256(snapshot/name)
        save(OUT/'implementation.json',dict(created_at=now(),files=files))
        for case in eligible:
            save(OUT/'pipeline.json',dict(status='fitting',case=case,updated_at=now()));run_case(case)
        save(OUT/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':run()
