"""Independent all-frame checks of bounded joint-goal trajectory candidates."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize

OUT=ROOT/'reports/pose-trajectory-v1'
def angles(matrices):
    shape=matrices.shape[:-2];return np.degrees(Rotation.from_matrix(matrices.reshape(-1,3,3)).magnitude()).reshape(shape)

def verify():
    protocol=read(OUT/'protocol.json');assert read(OUT/'pipeline.json')['status']=='complete';rows=[];manifest=[]
    for case in protocol['cases']:
        folder=OUT/case;request=read(folder/'request.json');spec=read(folder/'spec.json');assert read(folder/'pipeline.json')['status']=='complete'
        source=ROOT/'reports/action-jobs/pose-response-v1/takes'/f'{case}-offset-seed-502'
        assert sha256(source/'soma.glb')==request['source_glb_sha256'] and sha256(source/'motion.npz')==request['source_npz_sha256']
        assert sha256(folder/'original.glb')==request['source_glb_sha256'] and sha256(folder/'target.npz')==request['target_sha256']
        data=dict(np.load(folder/'fit.npz',allow_pickle=False));before,after,params=data['before'],data['after'],data['parameters'];envelope=np.array(request['envelope']);editable=envelope>0
        assert np.array_equal(after[~editable],before[~editable]) and not np.any(params[~editable])
        rig=RigAsset.load(folder/'original.glb');root=spec['root_node'];nodes=[v['node'] for v in spec['edit_joints'].values()]
        original_local=localize(before,rig.parents);candidate_local=localize(after,rig.parents)
        untouched=[i for i in range(len(rig.parents)) if i not in nodes and i!=root]
        assert np.max(np.abs(candidate_local[:,untouched]-original_local[:,untouched]))<1e-9
        delta=np.linalg.solve(original_local[:,nodes,:3,:3],candidate_local[:,nodes,:3,:3]);edits=angles(delta)
        limits=np.array([e['limit_degrees'] for e in spec['edit_joints'].values()]);assert np.all(edits<=envelope[:,None]*limits[None]+1e-5)
        shift=after[:,root,:3,3]-before[:,root,:3,3];lim=spec['limits']
        assert np.all(np.linalg.norm(shift[:,[0,2]],axis=1)<=envelope*lim['root_horizontal_m']+1e-7) and np.all(np.abs(shift[:,1])<=envelope*lim['root_vertical_m']+1e-7)
        root_steps=np.linalg.norm(np.diff(shift,axis=0),axis=1);edit_steps=angles(np.linalg.solve(delta[:-1],delta[1:]))
        assert root_steps.max()<=lim['root_step_m']+1e-7 and edit_steps.max()<=lim['joint_step_degrees']+1e-5
        source_step=angles(np.linalg.solve(original_local[:-1,nodes,:3,:3],original_local[1:,nodes,:3,:3]));actual_step=angles(np.linalg.solve(candidate_local[:-1,nodes,:3,:3],candidate_local[1:,nodes,:3,:3]))
        assert np.all(actual_step<=np.minimum(180,source_step+.5)+1e-4)
        decoded={};floor={};half={};points={};max_error=0.
        for mode,expected in [('original',before),('candidate',after)]:
            path=folder/(mode+'.glb');asset=RigAsset.load(path);sampler=AnimationSampler(asset.document,asset.binary,0)
            decoded[mode]=np.array([sampler.sample(float(np.float32(f/30))) for f in range(len(expected))]);error=float(np.max(np.abs(decoded[mode]-expected)));assert error<1e-5;max_error=max(max_error,error)
            points[mode]=np.array([asset.vertices(w) for w in decoded[mode]]);floor[mode]=np.maximum(0,-points[mode][:,:,1].min(axis=1))
            half[mode]=[max(0.,-float(asset.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(len(expected)-1)]
            manifest.append(dict(id=case+'-'+mode,path=case+'/'+mode+'.glb',sha256=sha256(path),frames=len(expected),fps=30))
        goal=request['joint_goal'];f,n=goal['frame'],goal['node'];errors={}
        for mode in ['original','candidate']:
            world=decoded[mode][f,n];errors[mode]=dict(position_m=float(np.linalg.norm(world[:3,3]-goal['position_m'])),orientation_degrees=float(angles(np.linalg.solve(np.array(goal['rotation_matrix']),world[:3,:3]))))
        supports=[]
        for s in request['supports']:
            a,b=s['start_frame'],s['end_frame_exclusive'];ids=s['vertices'];indices=np.arange(a,b);active=indices[editable[indices]]
            if not len(active):continue
            stats={}
            for mode in ['original','candidate']:
                track=points[mode][:,ids].mean(axis=1);speed=np.linalg.norm(np.diff(track[a:b],axis=0),axis=1)*30
                stats[mode]=dict(position_error_max_m=float(np.linalg.norm(track[active]-s['target_position_m'],axis=1).max()),whole_predicted_interval_speed_p95_m_s=float(np.percentile(speed,95)) if len(speed) else None)
            supports.append(dict(side=s['side'],start_frame=a,end_frame_exclusive=b,provenance=s['provenance'],metrics=stats))
        flags=[]
        if errors['candidate']['position_m']>protocol['position_screen_m']:flags.append('joint_position_target_missed')
        if errors['candidate']['orientation_degrees']>protocol['orientation_screen_degrees']:flags.append('joint_orientation_target_missed')
        if floor['candidate'][editable].max()>protocol['floor_screen_m']:flags.append('editable_floor_failed')
        if floor['candidate'].max()>protocol['floor_screen_m']:flags.append('whole_clip_floor_failed')
        if max(half['candidate'])>protocol['floor_screen_m']:flags.append('half_frame_floor_failed')
        records=read(folder/'solver.json');assert all(r['cost_after']<=r['cost_before']+1e-10 for r in records)
        rows.append(dict(case=case,frames=len(before),editable_frames=int(editable.sum()),goal_errors=errors,floor_depth_m={m:dict(whole=float(v.max()),editable=float(v[editable].max()),half_frames=float(max(half[m]))) for m,v in floor.items()},
            max_joint_edit_degrees=float(edits.max()),max_edit_step_degrees=float(edit_steps.max()),max_actual_rotation_step_increase_degrees=float((actual_step-source_step).max()),max_root_horizontal_shift_m=float(np.linalg.norm(shift[:,[0,2]],axis=1).max()),max_root_vertical_shift_m=float(np.abs(shift[:,1]).max()),max_root_edit_step_m=float(root_steps.max()),outside_world_matrices_exact=True,unchanged_local_chains=True,decoded_max_matrix_error=max_error,
            predicted_support_diagnostics=supports,solver_non_success_updates=sum(not r['success'] for r in records),flags=flags,quality_approved=False))
    save(OUT/'verification.json',dict(created_at=now(),invariants_passed=True,cases=rows,quality_approved=False,scope='Hard edit/context/rotation-step bounds and full-surface integer/half-frame diagnostics. Joint targets are soft objectives and can fail. Supports inherited from predictions; no physical/semantic/animator approval.'))
    review_rows=[];review_cases=[]
    for row in rows:
        request=read(OUT/row['case']/'request.json');data=dict(np.load(OUT/row['case']/'fit.npz',allow_pickle=False));goal=request['joint_goal']
        original=data['before'][goal['frame'],goal['node'],:3,3].tolist()
        review_cases.append(dict(action=row['case'],frame=goal['frame']))
        for mode in ['original','candidate']:
            review_rows.append(dict(action=row['case'],condition=mode,seed=502,frames=row['frames'],frame=goal['frame'],offset_target_error_m=row['goal_errors'][mode]['position_m'],orientation_degrees=row['goal_errors'][mode]['orientation_degrees'],mesh_floor_depth_m=row['floor_depth_m'][mode]['whole'],editable_floor_depth_m=row['floor_depth_m'][mode]['editable'],original_target_m=original,offset_target_m=goal['position_m']))
    save(OUT/'review-analysis.json',dict(cases=review_rows,actions={r['case']:r for r in rows},quality_approved=False))
    save(OUT/'review-protocol.json',dict(cases=review_cases))
    save(OUT/'manifest.json',dict(cases=manifest));print([{k:r[k] for k in ['case','goal_errors','floor_depth_m','flags']} for r in rows])

if __name__=='__main__':verify()
