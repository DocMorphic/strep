"""Build local all-seed skeleton and exported-GLB review pages."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
from strep import ROOT, read
from correct_stance import load_motion
from correct_loops import repeat_motion
from inspect_motion import skeleton_metadata
from evaluate_grid import loop_screen


def main(study, character):
    study, character = Path(study), Path(character)
    summary = read(study/'summary.json')
    names, parents, _ = skeleton_metadata(77)
    targets = read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    payload={'fps':30,'parents':parents,'names':names,'trials':[]}
    for t in summary['trials']:
        before=repeat_motion(load_motion(t['source']),np.array(t['cycle_displacement_m']),4)
        after=load_motion(study/f'seed-{t["seed"]}/repeated-four-cycles.npz')
        screen=loop_screen(before,30,targets)
        payload['trials'].append({'seed':t['seed'],'frames_per_cycle':t['cycle_frames'],'source_start_frame':0,
            'root_mode':'unchanged horizontal root; stance IK','accepted':t['accepted'],'regressions':t['regressions'],
            'raw_positions':before['posed_joints'].round(5).tolist(),'corrected_positions':after['posed_joints'].round(5).tolist(),
            'raw_seam_cm':screen['next_pose_prediction_rms_m']*100,'corrected_seam_cm':t['screen']['next_pose_prediction_rms_m']*100,
            'raw_speed_cm_s':t['before']['foot_horizontal_speed_predicted_contact_m_s']['p95']*100,
            'corrected_speed_cm_s':t['after']['foot_horizontal_speed_predicted_contact_m_s']['p95']*100})
    template=(ROOT/'scripts/loop-comparison.html').read_text(encoding='utf-8')
    template=template.replace('run-loop correction','stance correction').replace('loop correction comparison','stance correction comparison')
    template=template.replace('Same selected source section before and after correction','Same loop-corrected source before and after stance correction')
    template=template.replace('Selected raw cycle, repeated','Before stance IK, repeated').replace('Repeated raw source cycle','Before stance IK')
    template=template.replace('Raw seam','Before seam').replace('Raw contact p95','Before contact p95')
    template=template.replace('conservatively unioned during blending','held unchanged during stance correction')
    (study/'comparison.html').write_text(template.replace('__LOOP_STUDY__',json.dumps(payload).replace('<','\\u003c')),encoding='utf-8')
    report=read(character/'report.json')
    if (character/'quality.json').exists():
        report['quality']=read(character/'quality.json')
    template=(ROOT/'scripts/character-comparison.html').read_text(encoding='utf-8')
    template=template.replace('../stance-correction-v1/comparison.html',Path(os.path.relpath(study/'comparison.html',character)).as_posix())
    (character/'comparison.html').write_text(template.replace('__CHARACTER_REPORT__',json.dumps(report).replace('<','\\u003c')),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--character',type=Path,required=True)
    args=parser.parse_args()
    main(args.study,args.character)
