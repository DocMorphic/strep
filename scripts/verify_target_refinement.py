"""Audit reached targets, full mesh/support guards and unchanged source evidence."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_coupled_pose import total
import verify_pose_trajectory

OUT=ROOT/'reports/target-refinement-v1'


def run():
    protocol=read(OUT/'protocol.json');source_report=read(ROOT/'reports/pose-tolerances-v1/target-verification.json')
    assert protocol['cases']==[r['case'] for r in source_report['cases'] if r['targets_reached']]
    assert [r['case'] for r in protocol['rejected_inputs']]==[r['case'] for r in source_report['cases'] if not r['targets_reached']]
    verify_pose_trajectory.OUT=OUT;verify_pose_trajectory.verify();common=read(OUT/'verification.json');rows=[]
    for result in common['cases']:
        case=result['case'];folder=OUT/case;source=ROOT/'reports/pose-tolerances-v1'/case
        provenance=read(folder/'warm-start.json');assert all(sha256(source/name)==digest for name,digest in provenance['files'].items())
        assert sha256(folder/'target-met.glb')==provenance['files']['candidate.glb']
        data=dict(np.load(folder/'fit.npz',allow_pickle=False));warm=dict(np.load(source/'fit.npz',allow_pickle=False))
        for new,old in [('before','before'),('warm_start','after'),('warm_parameters','parameters')]:assert np.array_equal(data[new],warm[old])
        basis=np.load(folder/'basis.npy',allow_pickle=False);change=data['parameters']-data['warm_parameters']
        assert np.max(np.abs(basis@np.linalg.lstsq(basis,change,rcond=None)[0]-change))<1e-9
        request=read(folder/'request.json');spec=read(folder/'spec.json');guards=read(folder/'guards.json')
        rig=RigAsset.load(folder/'original.glb');points={s:np.array([rig.vertices(w) for w in data[s]]) for s in ['before','warm_start','after']}
        floor={s:np.maximum(0,-points[s][:,:,1].min(axis=1)) for s in ['warm_start','after']}
        np.testing.assert_allclose(guards['floor_caps_m'],floor['warm_start']+1e-6,atol=1e-10,rtol=0)
        assert np.all(floor['after']<=np.array(guards['floor_caps_m'])+1e-9)
        supports=[]
        assert len(request['supports'])==len(guards['supports'])
        for support,caps in zip(request['supports'],guards['supports']):
            a,b=support['start_frame'],support['end_frame_exclusive'];tracks={s:points[s][a:b][:,support['vertices']].mean(axis=1) for s in ['warm_start','after']}
            errors={s:np.linalg.norm(track-support['target_position_m'],axis=1) for s,track in tracks.items()}
            edges={s:np.linalg.norm(np.diff(track,axis=0),axis=1) for s,track in tracks.items()}
            np.testing.assert_allclose(caps['position'],np.maximum(errors['warm_start'],1e-4),atol=1e-10,rtol=0)
            np.testing.assert_allclose(caps['edge'],np.maximum(edges['warm_start'],1e-5),atol=1e-10,rtol=0)
            assert np.all(errors['after']<=np.array(caps['position'])+1e-8) and np.all(edges['after']<=np.array(caps['edge'])+1e-8)
            supports.append(dict(side=support['side'],position_change_max_m=float((errors['after']-errors['warm_start']).max()),
                edge_speed_change_max_m_s=float((edges['after']-edges['warm_start']).max()*30) if len(edges['after']) else None))
        assert result['goal_errors']['candidate']['position_m']<=.005 and result['goal_errors']['candidate']['orientation_degrees']<=5
        energies={s:total(data[s],points[s],data['before'],points['before'],data['local_before'],rig.parents,spec,request) for s in ['warm_start','after']}
        summary=read(folder/'fit-summary.json')['refinement']
        assert abs(energies['warm_start']-summary['cost_before'])<1e-5 and abs(energies['after']-summary['cost_after'])<1e-5
        assert energies['after']<=energies['warm_start']+1e-7
        half={};exported={}
        for label,name in [('warm_start','target-met.glb'),('after','candidate.glb')]:
            asset=RigAsset.load(folder/name);sampler=AnimationSampler(asset.document,asset.binary,0)
            exported[label]=np.array([asset.vertices(sampler.sample(float(np.float32(frame/30)))) for frame in range(len(data['after']))])
            half[label]=np.array([max(0.,-float(asset.vertices(sampler.sample((frame+.5)/30))[:,1].min())) for frame in range(len(data['after'])-1)])
        # Audit the delivered animation too, not just the optimizer's float64 poses.
        # Report any new guard violations explicitly; never silently enlarge a cap.
        exported_floor=np.maximum(0,-exported['after'][:,:,1].min(axis=1))
        delivered_floor_excess=float(np.maximum(0,exported_floor-np.array(guards['floor_caps_m'])).max())
        delivered_support_excess=[]
        for support,caps in zip(request['supports'],guards['supports']):
            a,b=support['start_frame'],support['end_frame_exclusive']
            track=exported['after'][a:b][:,support['vertices']].mean(axis=1)
            position=np.linalg.norm(track-support['target_position_m'],axis=1)
            edge=np.linalg.norm(np.diff(track,axis=0),axis=1)
            delivered_support_excess.append(dict(side=support['side'],
                position_cap_excess_m=float(np.maximum(0,position-np.array(caps['position'])).max()),
                edge_cap_excess_m=float(np.maximum(0,edge-np.array(caps['edge'])).max()) if len(edge) else 0.))
        delivered_guards_exact=delivered_floor_excess==0 and all(r['position_cap_excess_m']==0 and r['edge_cap_excess_m']==0 for r in delivered_support_excess)
        root=spec['root_node'];save(folder/'root-motion.json',dict(times_s=(np.arange(len(data['after']))/30).tolist(),
            positions_m=data['after'][:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(data['after'][:,root,:3,:3]).as_quat().tolist(),
            source_glb_sha256=sha256(folder/'candidate.glb'),space='SOMA pelvis world transform after target-preserving refinement',quality_approved=False))
        rows.append(dict(case=case,targets_preserved=True,source_and_control_space_verified=True,integer_floor_and_support_guards_passed=True,
            independent_energy=energies,support_changes=supports,half_frame_floor_regression_max_m=float((half['after']-half['warm_start']).max()),
            decoded_guard_caps_exactly_met=delivered_guards_exact,decoded_floor_cap_excess_m=delivered_floor_excess,
            decoded_support_cap_excess=delivered_support_excess,
            flags=result['flags'],quality_approved=False))
    save(OUT/'refinement-verification.json',dict(verified_at=now(),checks_passed=True,cases=rows,
        requested_case_count=len(protocol['requested_cases']),rejected_inputs=protocol['rejected_inputs'],quality_approved=False,
        scope='Integer floor/support guards and target preservation; half-frame changes measured separately. Predicted supports unconfirmed; no semantic/physical approval.'))


if __name__=='__main__':run()
