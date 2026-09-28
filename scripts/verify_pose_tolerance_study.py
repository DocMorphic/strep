"""Independent target acceptance and quality tradeoffs for feasibility outputs."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from verify_coupled_pose import total
import verify_pose_trajectory

OUT=ROOT/'reports/pose-tolerances-v1'


def run():
    protocol=read(OUT/'protocol.json')
    verify_pose_trajectory.OUT=OUT;verify_pose_trajectory.verify()
    common=read(OUT/'verification.json');rows=[]
    for row in common['cases']:
        case=row['case'];folder=OUT/case;source=ROOT/'reports/coupled-pose-v1'/case
        provenance=read(folder/'warm-start.json')
        assert all(sha256(source/name)==digest for name,digest in provenance['files'].items())
        assert sha256(folder/'coupled.glb')==provenance['files']['candidate.glb']
        data=dict(np.load(folder/'fit.npz',allow_pickle=False));warm=dict(np.load(source/'fit.npz',allow_pickle=False))
        for new,old in [('before','before'),('warm_start','after'),('warm_parameters','parameters')]:assert np.array_equal(data[new],warm[old])
        basis=np.load(folder/'basis.npy',allow_pickle=False);change=data['parameters']-data['warm_parameters']
        assert np.max(np.abs(basis@np.linalg.lstsq(basis,change,rcond=None)[0]-change))<1e-9
        request=read(folder/'request.json');spec=read(folder/'spec.json');summary=read(folder/'fit-summary.json')['target_feasibility']
        error=row['goal_errors']['candidate']
        reached=error['position_m']<=protocol['position_tolerance_m'] and error['orientation_degrees']<=protocol['orientation_tolerance_degrees']
        assert reached==summary['targets_reached'] and summary['infeasibility_proven'] is False
        goal=request['joint_goal'];merit={}
        for stage in ['warm_start','after']:
            transform=data[stage][goal['frame'],goal['node']]
            distance=np.linalg.norm(transform[:3,3]-goal['position_m'])
            denominator=2*(1-np.cos(np.radians(protocol['orientation_tolerance_degrees'])))
            pos=1-(distance/protocol['position_tolerance_m'])**2
            rot=(np.sum(np.array(goal['rotation_matrix'])*transform[:3,:3])-1-2*np.cos(np.radians(protocol['orientation_tolerance_degrees'])))/denominator
            merit[stage]=max(0.,float(protocol['target_interior_margin']-min(pos,rot)))
        assert abs(merit['warm_start']-summary['initial_target_violation'])<1e-5
        assert abs(merit['after']-summary['final_target_violation'])<1e-5
        assert merit['after']<=merit['warm_start']+1e-7
        rig=RigAsset.load(folder/'original.glb')
        points={stage:np.array([rig.vertices(w) for w in data[stage]]) for stage in ['before','warm_start','after']}
        energies={stage:total(data[stage],points[stage],data['before'],points['before'],data['local_before'],rig.parents,spec,request) for stage in ['warm_start','after']}
        root=spec['root_node'];save(folder/'root-motion.json',dict(times_s=(np.arange(len(data['after']))/30).tolist(),
            positions_m=data['after'][:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(data['after'][:,root,:3,:3]).as_quat().tolist(),
            source_glb_sha256=sha256(folder/'candidate.glb'),space='SOMA pelvis world transform after target feasibility',quality_approved=False))
        rows.append(dict(case=case,targets_reached=reached,source_and_warm_start_verified=True,
            normalized_target_violation=merit,previous_weighted_energy=energies,energy_increased=energies['after']>energies['warm_start'],
            flags=row['flags'],quality_approved=False))
    save(OUT/'target-verification.json',dict(verified_at=now(),checks_passed=True,cases=rows,quality_approved=False,
        scope='Independent decoded target acceptance, fixed context, edit/motion bounds, target merit and source provenance. Energy regressions are reported, not hidden; no semantic, contact or physical approval.'))


if __name__=='__main__':run()
