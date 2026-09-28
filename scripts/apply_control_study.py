"""Apply frozen controls to neutral corrected loops; retain every failed result."""
import copy
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from correct_stance import load_motion
from correct_loops import repeat_motion
from motion_controls import edit,edit_diagnostics
from profile_metrics import descriptors,speed_screen
from evaluate_grid import loop_screen
from inspect_motion import validate_motion,metrics

STUDY=ROOT/'benchmarks/control-calibration-v1.json'
FOLDER=ROOT/'reports/control-calibration-v1'


def main():
    import torch
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import save_motion_bvh,bvh_to_kimodo_motion
    study=read(STUDY);rules=study['calibration_protocol'];base=read(FOLDER/'text/summary.json')
    output=FOLDER/'direct';output.mkdir(exist_ok=True);skeleton=SOMASkeleton77()
    config=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    summary={'created_at':now(),'study':copy.deepcopy(study),'study_sha256':sha256(STUDY),'method':'Upper-body control after neutral loop/stance cleanup','trials':[]}
    summary['study']['profiles']=[p for p in study['profiles'] if p['control']!='neutral']
    for profile in summary['study']['profiles']:
        for seed in study['seeds']:
            baseline=next(t for t in base['trials'] if t['profile']=='neutral' and t['seed']==seed)
            path=FOLDER/'text/stance/neutral'/f'seed-{seed}/corrected.npz'
            assert sha256(path)==baseline['stance_report']['corrected_sha256']
            source=load_motion(path);motion,parameters=edit(source,skeleton,profile['control'],profile['target_degrees'])
            diagnostic=edit_diagnostics(source,motion,skeleton,profile['control'],profile['target_degrees'])
            trial=copy.deepcopy(baseline);trial.update(id=profile['id']+f'-{seed}',profile=profile['id'])
            delta=np.array(trial['processed_cycle_displacement_m']);tiled=repeat_motion(motion,delta,3)
            names,_,feet=validate_motion(motion,30);screen=loop_screen(tiled,30,config);after=metrics(tiled,names,feet,30)
            speed=speed_screen(motion,study,delta);flags=list(screen['screen_exceedances'])+speed['flags']
            if not baseline['accepted_source']:flags.append('neutral_baseline_quality')
            if diagnostic['target_error_degrees']>rules['source_error_degrees'][profile['control']]:flags.append('control_target')
            if diagnostic['unrelated_angle_change_degrees']>rules['maximum_unrelated_angle_change_degrees']:flags.append('unrelated_angle')
            if max(diagnostic['root_max_change_m'],diagnostic['lower_body_max_change_m'])>rules['unchanged_root_and_lower_body_tolerance_m']:flags.append('lower_body_changed')
            if diagnostic['max_local_edit_degrees']>rules['maximum_local_edit_degrees']:flags.append('edit_budget')
            if not diagnostic['contacts_unchanged']:flags.append('contacts_changed')
            if after['max_joint_ground_penetration_m']>baseline['stance_report']['after']['max_joint_ground_penetration_m']+.001:flags.append('joint_ground_regression')
            contact=after['foot_horizontal_speed_predicted_contact_m_s']
            if contact is None or contact['p95']>baseline['stance_report']['old_regression_limit_m_s']:flags.append('contact_regression')
            out=output/'stance'/profile['id']/f'seed-{seed}';out.mkdir(parents=True,exist_ok=False)
            np.savez(out/'corrected.npz',**motion)
            save_motion_bvh(out/'corrected.bvh',torch.from_numpy(motion['local_rot_mats']),torch.from_numpy(motion['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
            restored,fps=bvh_to_kimodo_motion(out/'corrected.bvh',skeleton=skeleton,standard_tpose=True)
            restored={k:v.numpy() if hasattr(v,'numpy') else v for k,v in restored.items()}
            error=float(np.max(np.linalg.norm(restored['posed_joints']-motion['posed_joints'],axis=-1)))
            if error>1e-4:raise RuntimeError('Edited BVH roundtrip failed')
            report={'method':summary['method'],'baseline_path':str(path),'baseline_sha256':sha256(path),'parameters':parameters,
                'diagnostics':diagnostic,'flags':flags,'accepted':not flags,'screen':screen,'before':baseline['stance_report']['after'],
                'after':after,'corrected_sha256':sha256(out/'corrected.npz'),'bvh_roundtrip_max_joint_error_m':error,
                'implementation_sha256':sha256(ROOT/'scripts/motion_controls.py'),'evaluation_sha256':sha256(Path(__file__)),
                'quality_scope':'New loop/contact/ground and edit-budget checks plus inherited neutral acceptance; no dynamics or self-collision test.'}
            save(out/'report.json',report)
            trial.update(stance_report=report,control_report=report,processed_descriptors=descriptors(repeat_motion(motion,delta,4)),
                processed_speed_screen=speed,accepted_source=not flags,flags=flags,neutral_baseline_id=baseline['id'])
            summary['trials'].append(trial);save(output/'summary.json',summary)
            print(f"Edited {trial['id']}: {flags or 'source checks pass'}",flush=True)
    summary['counts']={'generated':len(summary['trials']),'accepted_source':sum(t['accepted_source'] for t in summary['trials'])}
    save(output/'summary.json',summary)


if __name__=='__main__':main()
