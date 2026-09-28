import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read
from apply_control_study import STUDY
from analyze_control_study import assess
from motion_controls import KEYS


def fixtures():
    study=read(STUDY);text={'trials':[]};direct={'trials':[]};rig={'trials':[]}
    for p in study['profiles']:
        for seed in study['seeds']:
            d={KEYS['arm']:45.,KEYS['lean']:10.}
            if p['control']!='neutral':d[KEYS[p['control']]]=float(p['target_degrees'])
            t={'id':p['id']+f'-{seed}','raw_full_descriptors':d,'selected_raw_descriptors':d,
                'processed_descriptors':d,'flags':[],'accepted_source':True}
            text['trials'].append(t)
            if p['control']!='neutral':direct['trials'].append(copy.deepcopy(t))
            rig['trials'].append({'id':t['id'],'conditions':{'processed_loop':{'descriptors':d,
                'sampled_floor_penetration_m':0,'support_lowest_vertex_heights':[{'max_m':0}]}}})
    return study,text,direct,rig,copy.deepcopy(rig)


def test_held_out_failure_disables_level_despite_development_success():
    args=fixtures();before=assess(*args)
    assert all(l['enabled'] for r in before['release'].values() for l in r['levels'].values())
    held=next(t for t in args[2]['trials'] if t['id']=='arm-mid-55');held['flags']=['seam'];held['accepted_source']=False
    result=assess(*args)['release']['arm']['levels']
    assert not result['mid']['enabled'] and result['mid']['failed_seeds']==[55]
    assert result['low']['enabled'] and result['high']['enabled']


def test_transferred_response_failure_cannot_be_hidden_by_exact_source_angles():
    args=fixtures();target=next(t for t in args[4]['trials'] if t['id']=='lean-high-55')
    target['conditions']['processed_loop']['descriptors'][KEYS['lean']]=5.
    result=assess(*args)
    assert not result['release']['lean']['ordered_at_all_seeds_and_rig']
    assert not any(l['enabled'] for l in result['release']['lean']['levels'].values())
    bad=next(t for t in result['conditions'] if t['method']=='direct' and t['id']=='lean-high-55')
    assert 'rig_response_delta' in bad['flags']
