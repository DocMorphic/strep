"""Run one explicit contact edit with immutable inputs and independently checked exports."""
import argparse
import shutil
import time
import zipfile
from pathlib import Path
import numpy as np
from kimodo.skeleton import SOMASkeleton77
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now
from support_contact_v2 import refine,CONFIG
from contact_spec import validate
from support_contact import regions
from evaluate_body_contact import evaluate
from run_body_contact import export_motion
from build_soma_preview import ASSET
from inspect_motion import validate_motion,metrics
from evaluate_contact_spec import evaluate as evaluate_targets
from export_actions import sequence_diagnostics


def run(source,spec_path,output,checked_plan=None):
    source=Path(source).resolve();output=Path(output).resolve()
    skin=dict(np.load(ASSET));base=dict(np.load(source/'limb/motion.npz'))
    previous=dict(np.load(source/'motion.npz'));raw=dict(np.load(source/'raw/motion.npz'))
    spec=read(spec_path);validate(spec,len(base['root_positions']),regions(skin))
    limb=base;fit_refine=refine;config=CONFIG;solver_raw=raw;fit_options={}
    if checked_plan is not None:
        from support_contact_v8 import refine as fit_refine,CONFIG as config
        from contact_timing_job import validate_options
        from export_point_rate_objective import ExportPointRateObjective
        from inspect_motion import skeleton_metadata
        import torch
        options=read(checked_plan/'edit-request.json')['options'];validate_options(options,spec,len(previous['root_positions']))
        base=previous;solver_raw=previous
        _,parents,*_=skeleton_metadata(previous['posed_joints'].shape[1])
        torch.set_num_threads(2)
        guard=ExportPointRateObjective(torch.tensor(base['global_rot_mats'],dtype=torch.float64),torch.tensor(base['posed_joints'],dtype=torch.float64),parents,skin,spec,options['edit_window'])
        checked_reference=read(checked_plan/'rate-reference.json')
        if guard.record()!=checked_reference:raise ValueError('Recomputed rate reference differs from checked policy')
        fit_options=dict(edit_window=options['edit_window'],export_rate_guard=True,export_point_rate_guard=True,
            skin_backend='sparse',root_coordinate_mode='physical_box',outer_stage_count=2,iteration_count=60)
    parent=read(source/'evidence.json')
    if 'body_correction' not in parent:raise ValueError('This editor currently requires a body-corrected source take')
    output.mkdir(parents=True,exist_ok=False)
    save(output/'pipeline.json',dict(status='processing'))
    save(output/'contact-spec.json',spec)
    scripts=['support_contact_v2.py','contact_spec.py','support_contact.py','evaluate_body_contact.py','evaluate_floor_contact.py','evaluate_contact_spec.py','run_contact_edit.py']
    if checked_plan is not None:scripts=sorted(p.name for p in (ROOT/'scripts').glob('*.py'))
    implementation={n:sha256(ROOT/'scripts'/n) for n in scripts}
    sources={n:sha256(source/n) for n in ['motion.npz','limb/motion.npz','raw/motion.npz']}
    save(output/'freeze.json',dict(created_at=now(),implementation=implementation,sources=sources,config=config,contact_spec=spec,checked_plan=str(checked_plan) if checked_plan else None))
    try:
        with worker_lock():
            start=time.perf_counter()
            candidate,recipe=fit_refine(base,previous,skin,lambda r:print(r['evaluations'],r['loss'],flush=True),solver_raw,spec,**fit_options)
            evaluation,body=evaluate(raw,limb,candidate,skin,recipe)
            targets=evaluate_targets(base,candidate,skin,spec,.005 if checked_plan else .03)
            if any(r['frames_outside_tolerance'] for r in targets['intervals']):
                evaluation['flags'].append('authored_contact_target_missed')
                evaluation['screen_status']='flagged'
            # Independent float32 export checks, in addition to parameter bounds.
            delta=candidate['root_positions'][:,1]-base['root_positions'][:,1]
            if delta.min() < -2e-7 or delta.max()>config['max_root_lift_m']+2e-7:raise RuntimeError('Root budget invariant failed')
            if recipe['max_rotation_delta_degrees']>config['max_rotation_degrees']+1e-6:raise RuntimeError('Rotation budget invariant failed')
            trial_id=parent['id'];path=output/'takes'/trial_id;path.mkdir(parents=True)
            for name in ['raw','limb']:shutil.copytree(source/name,path/name)
            (path/'previous').mkdir()
            for name in ['motion.npz','motion.bvh','soma.glb','root-motion.json','contacts.json','evidence.json','request.json','timeline.json','generation-record.json']:
                shutil.copyfile(source/name,path/'previous'/name)
            for name in ['request.json','timeline.json','generation-record.json']:shutil.copyfile(source/name,path/name)
            validation=export_motion(path,candidate,skin,SOMASkeleton77(),evaluation['after']['per_frame_max_depth_m'])
            export_audit=None
            if checked_plan is not None:
                from audit_checked_contact import audit
                export_audit=audit(source/'soma.glb',path/'soma.glb',spec,options['edit_window'],checked_reference)
                save(path/'checked-export-audit.json',export_audit)
                save(path/'checked-rate-reference.json',checked_reference)
                if not export_audit['all_requested_pin_samples_within_5mm']:evaluation['flags'].append('exported_checked_pins_missed')
                if not export_audit['outside_preservation_passed']:evaluation['flags'].append('exported_outside_window_changed')
                if any(max(row['candidate_excess_over_checked'])>0 for row in export_audit['phase_rates']):evaluation['flags'].append('exported_point_rate_excess')
            evaluation['screen_status']='flagged' if evaluation['flags'] else 'within_provisional_screen'
            names,_,feet=validate_motion(candidate,30)
            record={k:v for k,v in parent.items() if k not in ['hashes','validation','previous_trial','support_correction']}
            record.update(previous_trial={k:v for k,v in parent.items() if k not in ['hashes','raw_trial','limb_trial','previous_trial']},
                metrics=metrics(candidate,names,feet,30),flags=evaluation['flags'],floor_correction=evaluation,body_correction=body,
                sequence=sequence_diagnostics(candidate,read(source/'timeline.json')['segments']),
                processing=('Checked stationary pins with source rate guards; experimental unapproved candidate' if checked_plan else 'Explicit contact edit with hard root/rotation budgets; experimental'),
                support_correction=dict(previous_flags=parent['flags'],previous_body=parent['body_correction'],support=recipe['support'],contact_spec=spec,
                    target_evaluation=targets,checked_fit=checked_plan is not None,export_audit=export_audit,policy='Unreviewed constraints and result; no automatic promotion'),validation=validation,
                correction_and_evaluation_time_s=time.perf_counter()-start,human_approved=False,engine_import=None)
            save(path/'recipe.json',recipe);save(path/'contact-spec.json',spec)
            save(path/'explicit-contact-evaluation.json',targets)
            save(path/'comparison.json',dict(raw=evaluation,body=body,previous=parent['body_correction']))
            save(path/'support-timeline.json',dict(fps=30,regions=recipe['support'],provenance='Authored constraints mixed with geometric candidates as recorded per region; not independently annotated force-bearing contacts.'))
            save(path/'evidence.json',record)
            with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in path.iterdir():
                    if file.is_file() and file.suffix!='.zip':z.write(file,file.name)
                z.write(ROOT/'vendor/kimodo/LICENSE','LICENSE.txt')
            record['hashes']={p.relative_to(path).as_posix():sha256(p) for p in path.rglob('*') if p.is_file()}
            for name,digest in sources.items():assert sha256(source/name)==digest
            shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
            save(output/'summary.json',dict(id=output.name,created_at=now(),trials=[record],config=config,implementation_hashes=implementation,
                scope='Contact authoring workflow test; no held-out quality or independent annotation claim.'))
            save(output/'pipeline.json',dict(status='complete'))
            print('RESULT',evaluation['flags'],'root range',float(delta.min()),float(delta.max()),flush=True)
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('spec',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.spec,a.output)
