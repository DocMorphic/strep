"""Compare a fixed arm/finger ablation without selecting away failures."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve comparison evidence')
    rows=[];requests=[];starts=[]
    for version,dim in [(5,12),(6,69)]:
        study=ROOT/f'reports/paired-palm-region-v{version}'
        export=ROOT/f'reports/paired-palm-region-export-v{version}'
        request=read(study/'request.json');requests.append(request)
        completion=read(export/'completion-verification.json')
        if completion['request_sha256']!=sha256(study/'request.json') or completion['history_sha256']!=sha256(study/'history.json'):raise ValueError('Study changed after audit')
        for name,digest in completion['files'].items():
            if sha256(export/name)!=digest:raise ValueError('Export audit payload changed')
        history=read(study/'history.json')['iterations'];parameters=np.array([h['parameters'] for h in history])
        if len(history)!=9 or parameters.shape!=(9,dim*2):raise ValueError('Wrong fixed budget or parameter population')
        start=parameters[0].reshape(2,dim);starts.append(start[:,:12])
        if dim>12 and np.any(start[:,12:]):raise ValueError('Finger experiment did not start from identical pose')
        seed=read(study/'initial-parameters.json')
        if sha256(study/'initial-parameters.json')!=request['continuation']['parameters_sha256'] or not np.array_equal(start[:,:12].ravel(),seed['values']):raise ValueError('Wrong continuation seed')
        last=parameters[-1].reshape(2,dim);delta=last-start
        saved=read(study/'parameters.json');bounds=np.array(saved['bounds'])
        if not np.array_equal(parameters[-1],saved['values']) or bounds.shape!=(dim*2,):raise ValueError('Final parameter record differs from history')
        rows.append(dict(version=version,study=str(study),export=str(export),request_sha256=sha256(study/'request.json'),
            completion_sha256=sha256(export/'completion-verification.json'),actor_parameters=dim,
            max_additional_arm_edit_degrees=float(np.degrees(np.linalg.norm(delta[:,:12].reshape(-1,3),axis=1)).max()),
            max_finger_edit_degrees=float(np.degrees(np.linalg.norm(last[:,12:].reshape(-1,3),axis=1)).max()) if dim>12 else 0.,
            contact_distance_trace_m=[max(max(d['distances_m']) for d in h['contact']) for h in history],
            penetration_trace_m=[max(d['max_depth_m'] for d in h['collision']) for h in history],
            max_joint_step_degrees=[float(np.degrees(np.linalg.norm(d.reshape(-1,3),axis=1)).max()) for d in np.diff(parameters,axis=0)],
            final_parameters_at_component_bound=int(np.sum(np.abs(np.abs(parameters[-1])-bounds)<1e-7)),
            accepted_steps=sum(any(t['accepted'] for t in h['step_trials']) for h in history[1:]),
            solver_success_flags=completion['solver_success_flags'],event_screens=completion['event_screens'],
            decoded_event_depth_m=completion['event_depth_m'],engine_actor_frames=completion['engine_actor_frames']))
    for key in ['continuation','scene_sha256','skin_sha256','input_manifest_sha256','iterations','safeguard','screen',
                'contact_weight','contact_gap_m','clearance_margin_m','proximity_selection_m','contacts_per_direction',
                'contact_spacing_m','inner_component_trust_degrees','safeguard_trials','safeguard_depth_precision_m']:
        if requests[0][key]!=requests[1][key]:raise ValueError('Paired experiment conditions differ: '+key)
    if [r['actor_kind'] for r in requests]!=['arms','arm_and_fingers']:raise ValueError('Wrong paired actor modes')
    for name,digest in requests[0]['implementation'].items():
        if requests[1]['implementation'].get(name)!=digest:raise ValueError('Common implementation differs: '+name)
    np.testing.assert_array_equal(*starts)
    save(output,dict(at=now(),script_sha256=sha256(__file__),rows=rows,identical_initial_pose=True,
        fixed_budget_iterations=8,human_review=False,quality_approved=False,
        scope='One observed development event. Same additional iteration budget, unequal dimensions/runtime. No held-out, anatomical, self-collision or temporal quality claim.'))
    print(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
