"""Preserve body-v1 outputs and publish a separately flagged support experiment."""
import shutil
import time
import zipfile
from pathlib import Path
import numpy as np
from kimodo.skeleton import SOMASkeleton77
from strep import ROOT,read,save,sha256,now
from support_contact import refine,CONFIG
from evaluate_body_contact import evaluate
from inspect_motion import validate_motion,metrics
from run_body_contact import export_motion
from build_soma_preview import ASSET


def run():
    output=ROOT/'reports/support-contact-v1';output.mkdir(exist_ok=False)
    save(output/'pipeline.json',dict(status='processing'))
    skin=dict(np.load(ASSET));skeleton=SOMASkeleton77()
    hashes={n:sha256(ROOT/'scripts'/n) for n in ['support_contact.py','evaluate_body_contact.py','evaluate_floor_contact.py','run_support_contact.py']}
    summary=dict(id=output.name,created_at=now(),config=CONFIG,implementation_hashes=hashes,trials=[],unchanged=[],
                 scope='Development-set contact experiment, four previously seen failures. No new holdout, training, human approval or engine-import claim.')
    save(ROOT/'benchmarks/support-contact-v1-freeze.json',dict(created_at=now(),config=CONFIG,implementation_hashes=hashes,
         development_seeds=[11,22,55,77],selection='Existing body support gap or added speed flags; other clips untouched.'))
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    for study in ['body-contact-v1','body-contact-holdout-v1']:
        for trial in read(ROOT/'reports'/study/'summary.json')['trials']:
            origin=ROOT/'reports'/study/'takes'/trial['id']
            eligible=any('body_support_gap' in flag or flag=='added_joint_speed_above_1_5m_s' for flag in trial['flags'])
            if not eligible:
                summary['unchanged'].append(dict(id=trial['id'],collection=study,motion_sha256=sha256(origin/'motion.npz')))
                continue
            raw=dict(np.load(origin/'raw/motion.npz'));base=dict(np.load(origin/'limb/motion.npz'));old=dict(np.load(origin/'motion.npz'))
            for rel in ['raw/motion.npz','limb/motion.npz','motion.npz']:
                assert sha256(origin/rel)==trial['hashes'][rel]
            start=time.perf_counter()
            candidate,recipe=refine(base,old,skin,lambda r:print(trial['id'],r['evaluations'],round(r['loss'],5),flush=True),raw)
            evaluation,body=evaluate(raw,base,candidate,skin,recipe)
            if min(recipe['root_lift_m']) < -1e-5:evaluation['flags'].append('root_lowered_below_baseline')
            if recipe['max_rotation_delta_degrees']>CONFIG['max_rotation_degrees']+.1:evaluation['flags'].append('support_rotation_budget')
            evaluation['screen_status']='flagged' if evaluation['flags'] else 'within_provisional_screen'
            path=output/'takes'/trial['id'];path.mkdir(parents=True)
            for folder in ['raw','limb']:shutil.copytree(origin/folder,path/folder)
            (path/'previous').mkdir()
            for file in ['motion.npz','motion.bvh','soma.glb','root-motion.json','contacts.json','evidence.json','request.json','timeline.json','generation-record.json']:
                shutil.copyfile(origin/file,path/'previous'/file)
            validation=export_motion(path,candidate,skin,skeleton,evaluation['after']['per_frame_max_depth_m'])
            for file in ['request.json','timeline.json','generation-record.json']:shutil.copyfile(origin/file,path/file)
            names,_,feet=validate_motion(candidate,30)
            # Keep prior metrics and files directly accessible, never rewrite v1.
            old_trial={k:v for k,v in trial.items() if k not in ['hashes','raw_trial','limb_trial']}
            record={k:v for k,v in trial.items() if k not in ['hashes','validation']}
            record.update(previous_trial=old_trial,metrics=metrics(candidate,names,feet,30),flags=evaluation['flags'],
                floor_correction=evaluation,body_correction=body,processing='Experimental clip-wide support fit; not promoted to default correction',
                support_correction=dict(previous_flags=trial['flags'],previous_body=trial['body_correction'],support=recipe['support'],
                    policy='Separate review candidate; baseline retained even if numerical gates pass.'),
                validation=validation,source_body_sha256=sha256(origin/'motion.npz'),correction_and_evaluation_time_s=time.perf_counter()-start)
            save(path/'recipe.json',recipe);save(path/'comparison.json',dict(raw=evaluation,body=body,previous=trial['body_correction']))
            save(path/'support-timeline.json',dict(fps=30,regions=recipe['support'],provenance='Geometric low/slow candidates inferred from fixed hands/feet baseline; not annotated or measured forces.'))
            save(path/'evidence.json',record)
            with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in sorted(path.iterdir()):
                    if file.is_file() and file.suffix!='.zip':z.write(file,file.name)
                z.write(ROOT/'vendor/kimodo/LICENSE','LICENSE.txt')
            record['hashes']={p.relative_to(path).as_posix():sha256(p) for p in path.rglob('*') if p.is_file()}
            summary['trials'].append(record);save(output/'summary.json',summary)
            print('RESULT',trial['id'],evaluation['after']['mesh_max_depth_m'],evaluation['flags'],flush=True)
    for record in summary['unchanged']:
        assert sha256(ROOT/'reports'/record['collection']/'takes'/record['id']/'motion.npz')==record['motion_sha256']
    summary['finished_at']=now();save(output/'summary.json',summary);save(output/'pipeline.json',dict(status='complete'))


if __name__=='__main__':run()
