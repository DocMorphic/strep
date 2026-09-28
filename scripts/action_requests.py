"""Open-vocabulary single-humanoid requests. Examples never restrict action names."""
import hashlib
import json
import math
import re
from generation_constraints import validate_guides,validate_guide_origin


def validate_request(value):
    if not isinstance(value,dict) or set(value)-{'id','label','segments','seeds','scene_requirements','generation_constraints','guide_origin','first_heading_angle','motion_profile'}:
        raise ValueError('Expected id, label, segments, seeds and optional scene_requirements/generation_constraints')
    if not isinstance(value.get('id'),str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',value['id']):
        raise ValueError('ID must be a short lowercase filename-safe identifier')
    if not isinstance(value.get('label'),str) or not 1<=len(value['label'])<=120:
        raise ValueError('Provide a label of 1–120 characters')
    segments=value.get('segments')
    if not isinstance(segments,list) or not 1<=len(segments)<=6:
        raise ValueError('Provide 1–6 timed action segments')
    for segment in segments:
        if not isinstance(segment,dict) or set(segment)!={'prompt','duration_s'}:
            raise ValueError('Each segment needs prompt and duration_s')
        prompt=segment['prompt'];duration=segment['duration_s']
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=1000 or not any(c.isalnum() for c in prompt):
            raise ValueError('Provide an action description of up to 1000 characters')
        if isinstance(duration,bool) or not isinstance(duration,(float,int)) or not math.isfinite(duration) or not 1<=duration<=9:
            raise ValueError('Each segment must last 1–9 seconds')
    if sum(s['duration_s'] for s in segments)>30:raise ValueError('Local request limit: 30 seconds total')
    seeds=value.get('seeds')
    if not isinstance(seeds,list) or not 1<=len(seeds)<=4 or any(type(s)!=int or not 0<=s<2**32 for s in seeds) or len(set(seeds))!=len(seeds):
        raise ValueError('Provide 1–4 distinct integer seeds between 0 and 4294967295')
    scene=value.get('scene_requirements',[])
    if not isinstance(scene,list) or any(not isinstance(s,str) or not 1<=len(s)<=300 for s in scene) or len(scene)>10:
        raise ValueError('Scene requirements must be a short list of text descriptions')
    validate_guides(value.get('generation_constraints',[]),sum(round(s['duration_s']*30) for s in segments))
    validate_guide_origin(value,value.get('generation_constraints',[]))
    if 'first_heading_angle' in value and (type(value['first_heading_angle']) not in (int,float) or not math.isfinite(value['first_heading_angle']) or abs(value['first_heading_angle'])>math.pi):raise ValueError('Initial heading must be finite radians within [-pi, pi]')
    if 'motion_profile' in value:
        from motion_profile import brief,validate
        validate(value['motion_profile']);brief(value)
    return value


def validate_batch(batch):
    if not isinstance(batch,dict) or set(batch)!={'schema_version','requests'} or batch['schema_version']!=1:
        raise ValueError('Expected schema_version 1 and requests')
    if not isinstance(batch['requests'],list) or not 1<=len(batch['requests'])<=20:raise ValueError('Provide 1–20 requests')
    for value in batch['requests']:validate_request(value)
    ids=[r['id'] for r in batch['requests']]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate request IDs')
    return batch


def request_digest(batch):
    validate_batch(batch)
    from motion_profile import brief
    profiles={r['id']:brief(r) for r in batch['requests'] if 'motion_profile' in r}
    payload={'request':batch,'resolved_profiles':profiles} if profiles else batch
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def conditioning_texts(batch):
    from kimodo.sanitize import sanitize_texts
    from motion_profile import resolved_segments
    return sorted(set(sanitize_texts([s['prompt'] for r in validate_batch(batch)['requests'] for s in resolved_segments(r)])))


def timeline(request,fps=30):
    validate_request(request);start=0;result=[]
    for segment in request['segments']:
        count=round(segment['duration_s']*fps)
        result.append({**segment,'start_frame':start,'end_frame_exclusive':start+count,
                       'start_s':start/fps,'end_s':(start+count)/fps,
                       'blend_frames':[] if not result else list(range(start-5,start)),
                       'provenance':'Requested conditioning schedule, not detected action or gameplay events'})
        start+=count
    return result
