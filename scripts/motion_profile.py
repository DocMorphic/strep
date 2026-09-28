"""Explicit designer-owned stat-to-description rules, not learned physiology."""
import copy
import hashlib
import json
import re
from pathlib import Path

SCHEMA='strep-motion-profile-v1'
COMPILER_VERSION=1


def default_profile():
    rules={
        'agility':['Careful, unhurried changes of direction.','Controlled changes of direction.','Quick, precise changes of direction.'],
        'strength':['Gentle, low-force-looking movements.','Moderately forceful movements.','Powerful, forceful-looking movements.'],
        'balance':['Cautious, visibly tentative balance.','Steady balance.','Steady, well-controlled balance.'],
        'mobility':['Compact movements within a limited comfortable range.','A comfortable movement range.','Wide, supple movement range.'],
        'coordination':['Hesitant, less fluid coordination.','Coordinated movements.','Fluid, precise coordination.'],
        'endurance':None,
    }
    return dict(schema=SCHEMA,name='My character',policy_name='Editable game-style examples v1',style='',training='',state='',
                stats=[dict(id=k,label=k.title(),value=50,levels=v) for k,v in rules.items()])


def _text(value,maximum,name,empty=True):
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()):
        raise ValueError(f'{name} must be text of '+('0' if empty else '1')+f'–{maximum} characters')


def validate(profile):
    if not isinstance(profile,dict) or set(profile)!={'schema','name','policy_name','style','training','state','stats'} or profile['schema']!=SCHEMA:
        raise ValueError('Invalid movement profile schema')
    for field,size in [('name',80),('policy_name',100),('style',300),('training',200),('state',200)]:
        _text(profile[field],size,field,empty=field not in ('name','policy_name'))
    stats=profile['stats']
    if not isinstance(stats,list) or len(stats)>12:raise ValueError('Use at most 12 profile stats')
    ids=set()
    for stat in stats:
        if not isinstance(stat,dict) or set(stat)!={'id','label','value','levels'}:raise ValueError('Invalid profile stat')
        key=stat['id']
        if not isinstance(key,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',key) or key in ids:raise ValueError('Profile stat IDs must be unique lowercase identifiers')
        ids.add(key);_text(stat['label'],60,'Stat label',empty=False)
        if type(stat['value']) is not int or not 0<=stat['value']<=100:raise ValueError('Profile stat values must be integers from 0 to 100')
        if stat['levels'] is not None:
            if not isinstance(stat['levels'],list) or len(stat['levels'])!=3:raise ValueError('A stat rule needs low, middle and high descriptions, or no rule')
            for text in stat['levels']:_text(text,180,'Stat rule',empty=False)
    return profile


def resolve(profile):
    validate(profile);phrases=[];applied=[];unmapped=[]
    for field,label in [('style','Movement style'),('training','Training'),('state','Current state')]:
        if profile[field].strip():phrases.append(label+': '+profile[field].strip().rstrip('.')+'.')
    for stat in profile['stats']:
        if stat['levels'] is None:
            unmapped.append(dict(id=stat['id'],label=stat['label'],value=stat['value']));continue
        level=0 if stat['value']<34 else 1 if stat['value']<67 else 2
        description=stat['levels'][level].strip().rstrip('.')+'.'
        phrases.append(description);applied.append(dict(id=stat['id'],label=stat['label'],value=stat['value'],band=['0–33','34–66','67–100'][level],description=description))
    return dict(schema='strep-resolved-motion-profile-v1',compiler_version=COMPILER_VERSION,
                compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),profile=copy.deepcopy(profile),
                description=' '.join(phrases),applied_rules=applied,unmapped_stats=unmapped,
                interpretation='Designer-authored text direction; not trained stat channels, force limits, endurance simulation or calibrated motion control.',
                response_validated=False)


def brief(request):
    profile=request.get('motion_profile')
    if profile is None:return None
    result=resolve(profile);segments=[]
    for segment in request['segments']:
        text=segment['prompt'].strip()
        if result['description']:
            text=text.rstrip('.')+'. '+result['description']
        if len(text)>1000:raise ValueError('Resolved motion description exceeds 1000 characters; shorten the action or profile rules')
        segments.append(dict(original_prompt=segment['prompt'],conditioning_prompt=text,duration_s=segment['duration_s']))
    result['segments']=segments
    result['resolution_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def resolved_segments(request):
    value=brief(request)
    if value is None:return copy.deepcopy(request['segments'])
    return [dict(prompt=s['conditioning_prompt'],duration_s=s['duration_s']) for s in value['segments']]
