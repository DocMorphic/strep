"""Assess the frozen control rules with every seed retained."""
import numpy as np
from strep import ROOT,read,save,now,sha256
from apply_control_study import FOLDER,STUDY
from motion_controls import KEYS


def assess(study,text,direct,text_rig,direct_rig):
    rules=study['calibration_protocol'];conditions=[];ordering=[]
    text_map={t['id']:t for t in text['trials']};direct_map={t['id']:t for t in direct['trials']}
    rigs={'text':{t['id']:t for t in text_rig['trials']},'direct':{t['id']:t for t in direct_rig['trials']}}
    for p in study['profiles']:
        if p['control']=='neutral':continue
        key=KEYS[p['control']]
        for seed in study['seeds']:
            id=p['id']+f'-{seed}';base=text_map[f'neutral-{seed}'];base_rig=rigs['text'][base['id']]['conditions']['processed_loop']['descriptors']
            for method,mapping in [('text',text_map),('direct',direct_map)]:
                t=mapping[id];d=t['processed_descriptors'];rig=rigs[method][id]['conditions']['processed_loop'];rd=rig['descriptors']
                source_delta=d[key]-base['processed_descriptors'][key];rig_delta=rd[key]-base_rig[key]
                other=KEYS['lean' if p['control']=='arm' else 'arm']
                error=abs(rig_delta-source_delta);flags=list(t['flags'])
                if error>rules['maximum_target_delta_error_degrees']:flags.append('rig_response_delta')
                conditions.append({'id':id,'method':method,'control':p['control'],'level':p['level'],'seed':seed,
                    'split':'held_out' if seed in study['held_out_seeds'] else 'development','target_degrees':p['target_degrees'],
                    'raw_value_degrees':t['raw_full_descriptors'][key],'selected_raw_value_degrees':t['selected_raw_descriptors'][key],
                    'processed_value_degrees':d[key],'target_error_degrees':abs(d[key]-p['target_degrees']),
                    'rig_value_degrees':rd[key],'source_delta_degrees':source_delta,'rig_delta_degrees':rig_delta,
                    'rig_response_delta_error_degrees':error,'source_accepted':t['accepted_source'],'flags':flags,
                    'source_other_angle_change_degrees':abs(d[other]-base['processed_descriptors'][other]),
                    'rig_other_angle_change_degrees':abs(rd[other]-base_rig[other]),
                    'sampled_floor_penetration_m':rig['sampled_floor_penetration_m'],
                    'support_foot_height_max_m':max(v['max_m'] or 0 for v in rig['support_lowest_vertex_heights']),
                    'diagnostics':t.get('control_report',{}).get('diagnostics'),
                    'control_and_source_pass':not flags if method=='direct' else None})
    for control in KEYS:
        for method in ['text','direct']:
            for seed in study['seeds']:
                rows=sorted([x for x in conditions if x['control']==control and x['method']==method and x['seed']==seed],key=lambda x:x['target_degrees'])
                response={}
                for stage in ['raw_value_degrees','processed_value_degrees','rig_value_degrees']:
                    values=[x[stage] for x in rows];response[stage]={'values':values,'ordered':bool(np.all(np.diff(values)>=rules['minimum_ordered_step_degrees'][control]))}
                ordering.append({'control':control,'method':method,'seed':seed,'response':response})
    release={}
    for control in KEYS:
        order=[x for x in ordering if x['control']==control and x['method']=='direct']
        ordered=all(x['response'][stage]['ordered'] for x in order for stage in ['processed_value_degrees','rig_value_degrees'])
        levels={}
        for level in ['low','mid','high']:
            rows=[x for x in conditions if x['control']==control and x['method']=='direct' and x['level']==level]
            levels[level]={'target_degrees':rows[0]['target_degrees'],'enabled':ordered and all(x['control_and_source_pass'] for x in rows),
                'failed_seeds':[x['seed'] for x in rows if not x['control_and_source_pass']],
                'reasons':sorted(set(flag for row in rows for flag in row['flags']))+([] if ordered else ['control_ordering'])}
        release[control]={'ordered_at_all_seeds_and_rig':ordered,'levels':levels}
    return {'created_at':now(),'study':study,'conditions':conditions,'ordering':ordering,'release':release,
        'scope':'Tested source-space angle levels only. One held-out seed; no human realism, dynamics, unseen-rig or gameplay-stat calibration claim.'}


def main():
    study=read(STUDY)
    report=assess(study,read(FOLDER/'text/summary.json'),read(FOLDER/'direct/summary.json'),read(FOLDER/'text/character-quality.json'),read(FOLDER/'direct/character-quality.json'))
    report['study_sha256']=sha256(STUDY);report['implementation_sha256']=sha256(ROOT/'scripts/analyze_control_study.py')
    save(FOLDER/'analysis.json',report)
    mapping={'version':'explicit-angle-targets-v1','controls':report['release'],'supported_action':'straight running','target_space':'SOMA77 source; CesiumMan response evaluated separately',
        'capability_mapping':{'agility':None,'strength':None,'stamina':None,'fitness':None},
        'capability_status':'Unvalidated; no automatic conversion. Game-specific rules must be explicit author hypotheses.',
        'application_order':['generate neutral take','select/correct loop','stance correction','apply chosen upper-body control','retarget and verify'],
        'combination_status':'Arm and torso tested separately; combined edits are not qualified.',
        'analysis_sha256':sha256(FOLDER/'analysis.json')}
    save(FOLDER/'authoring-mapping.json',mapping);print(report['release'])


if __name__=='__main__':main()
