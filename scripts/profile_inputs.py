"""Versioned, explicit profile briefs. Numeric stats are metadata in this pilot."""
import re
from pathlib import Path
from strep import ROOT,read,save,sha256

DEFAULT_STUDY=ROOT/'benchmarks/profile-pilot-v1.json'


def validate_study(study):
    if not re.fullmatch(r'[a-z][a-z0-9_-]*',study['id']):
        raise ValueError('Unsafe study identifier')
    if not study['profiles'] or not study['seeds']:
        raise ValueError('Study requires profiles and seeds')
    if study['fps']!=30 or not 1<=study['duration_s']<=10 or not 0<study['speed_m_s']<=10:
        raise ValueError('Unsupported timing/speed')
    ids=[p['id'] for p in study['profiles']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z][a-z0-9_-]*',x) for x in ids):
        raise ValueError('Unsafe or duplicate profile identifiers')
    if len(study['seeds'])!=len(set(study['seeds'])) or any(not isinstance(x,int) for x in study['seeds']):
        raise ValueError('Invalid seeds')
    for p in study['profiles']:
        if not p['prompt'].startswith('A person ') or p['prompt'].count('.')!=1 or not p['prompt'].endswith('.'):
            raise ValueError('Use one complete action sentence per pilot profile')
        if any(not isinstance(v,(int,float)) or not 0<=v<=100 for v in p['capabilities'].values()):
            raise ValueError('Capabilities must be between 0 and 100')
    return study


def texts_for(study):
    from kimodo.sanitize import sanitize_texts
    return sorted(set(sanitize_texts([p['prompt'] for p in validate_study(study)['profiles']])))


def constraints_for(study):
    count=round(study['fps']*study['duration_s'])
    return [{'type':'root2d','frame_indices':list(range(count)),
             'smooth_root_2d':[[0,frame/study['fps']*study['speed_m_s']] for frame in range(count)]}]


def brief(study,profile,seed):
    if seed not in study['seeds']:raise ValueError('Seed not in frozen study')
    return {'study_id':study['id'],'mapping_version':study['mapping_version'],'profile':profile,
            'prompt':profile['prompt'],'seed':seed,'fps':study['fps'],'duration_s':study['duration_s'],
            'speed_m_s':study['speed_m_s'],'stat_status':study['stat_status'],
            'load_status':'Body-style prompt only; no backpack mesh or load dynamics.' if 'load_kg' in profile else None}
