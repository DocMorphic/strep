"""Frozen warm-start trial of coordinated controls on retained target misses."""
import shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_pose_trajectory import PoseTrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter,window_basis
from rig_loop import encode
from action_worker_lock import worker_lock

OUT=ROOT/'reports/coupled-pose-v1'
SOURCE=ROOT/'reports/pose-trajectory-v1'


def run_case(case):
    original=SOURCE/case;out=OUT/case;out.mkdir()
    assert read(original/'pipeline.json')['status']=='complete'
    request=read(original/'request.json');spec=read(original/'spec.json')
    with np.load(original/'fit.npz',allow_pickle=False) as archive:
        data={k:archive[k] for k in archive.files}
    for name in ['original.glb','target.npz','request.json','spec.json','LICENSE.txt']:
        shutil.copyfile(original/name,out/name)
    shutil.copyfile(original/'candidate.glb',out/'coordinate.glb')
    provenance={name:sha256(original/name) for name in ['fit.npz','candidate.glb','request.json','spec.json']}
    save(out/'warm-start.json',dict(source=str(original.relative_to(ROOT)),files=provenance))
    rig=RigAsset.load(out/'original.glb')
    fitter=PoseTrajectoryFitter(rig,spec,data['local_before'],
        {k:np.array(v) for k,v in request['targets_m'].items()},request['envelope'],
        request['supports'],[request['joint_goal']])
    for frame,x in enumerate(data['parameters']):fitter.accept(frame,x)
    basis=window_basis(request['envelope'],spacing=10)
    np.save(out/'basis.npy',basis,allow_pickle=False)
    coupled=CoupledPoseFitter(fitter,basis)
    save(out/'pipeline.json',dict(status='fitting_coupled',started_at=now(),controls=coupled.shape))
    with threadpool_limits(limits=1):values,trace,summary=coupled.solve(out,max_iterations=60)
    after=fitter.world.copy();after[np.array(request['envelope'])==0]=data['before'][np.array(request['envelope'])==0]
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    _,roundtrip=encode(rig,after,animated,spec['root_node'],out/'candidate.glb','Coordinated temporal target candidate')
    np.savez_compressed(out/'fit.npz',before=data['before'],after=after,parameters=values,
                        local_before=data['local_before'],warm_start=data['after'],warm_parameters=data['parameters'])
    save(out/'optimizer-trace.json',trace)
    save(out/'solver.json',[dict(success=summary['solver_success'],cost_before=summary['cost_before'],cost_after=summary['cost_after'])])
    save(out/'fit-summary.json',dict(convergence=summary,export=roundtrip,quality_approved=False))
    assert all(sha256(original/name)==digest for name,digest in provenance.items())
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))
    print(case,summary,flush=True)


def run():
    if OUT.exists():raise ValueError('Preserve previous trial output')
    with worker_lock():
        OUT.mkdir();protocol=read(SOURCE/'protocol.json')
        protocol.update(created_at=now(),source_study='pose-trajectory-v1',
            method='Cubic coordinated controls, warm-started from the retained four-sweep coordinate candidates.',
            selection='Same three posthoc failures, no held-out or equal-compute comparison.',
            max_iterations=60,knot_spacing_frames=10,objective_weights_unchanged=True,
            hard_limits_unchanged=True,original_fit_max_sweeps=protocol.pop('max_sweeps'),
            return_policy='Best objective-decreasing feasible point; test segment backtracking if final endpoint is infeasible.')
        save(OUT/'protocol.json',protocol)
        snapshot=OUT/'implementation';snapshot.mkdir();digests={}
        for name in ['study_coupled_pose.py','rig_coupled_pose.py','rig_pose_trajectory.py',
                     'rig_trajectory_fit.py','rig_clearance_fit.py','target_rig_contact.py',
                     'rig_periodic_contact.py','rig_loop.py','support_contact_v5.py','verify_pose_trajectory.py']:
            shutil.copyfile(ROOT/'scripts'/name,snapshot/name);digests[name]=sha256(snapshot/name)
        save(OUT/'implementation.json',dict(created_at=now(),files=digests))
        for case in protocol['cases']:
            save(OUT/'pipeline.json',dict(status='fitting',case=case,updated_at=now()));run_case(case)
        save(OUT/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':run()
