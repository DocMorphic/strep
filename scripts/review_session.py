"""Randomized local reviewer packets and strict import of human-entered evidence."""
import argparse,copy,hashlib,json,math,random,shutil,uuid
from pathlib import Path
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb,write_glb

CATEGORIES=['action','weight_balance','coordination_timing','contacts_collisions','starts_ends']

def scrub(value):
    if isinstance(value,dict):return {k:scrub(v) for k,v in value.items() if k!='extras'}
    if isinstance(value,list):return [scrub(v) for v in value]
    return value

def build(job,output,key_path,seed):
    return build_many([job],output,key_path,seed)


def build_many(jobs,output,key_path,seed,contexts=None):
    """Keep every supplied trial, including poor clips; contexts describe absent evidence."""
    jobs=[Path(job).resolve() for job in jobs];output=Path(output).resolve();key_path=Path(key_path).resolve()
    contexts=contexts or {}
    if key_path.is_relative_to(output):raise ValueError('Keep condition key outside reviewer packet')
    if output.exists() or key_path.exists():raise ValueError('Do not overwrite a reviewer packet or key')
    if not jobs or len(set(jobs))!=len(jobs):raise ValueError('Supply distinct completed jobs')
    trials=[];sources=set()
    for job in jobs:
        if read(job/'pipeline.json')['status']!='complete':raise ValueError('Review only completed jobs')
        for trial in copy.deepcopy(read(job/'summary.json')['trials']):
            source=(job/'takes'/trial['id']/'soma.glb').resolve()
            if not source.is_relative_to(job/'takes') or source in sources:raise ValueError('Duplicate or escaping source clip')
            if sha256(source)!=trial['hashes']['soma.glb']:raise ValueError('Source clip changed')
            sources.add(source);trials.append((trial,source))
    if not trials:raise ValueError('No clips to review')
    random.Random(seed).shuffle(trials)
    output.mkdir(parents=True);(output/'clips').mkdir();cases=[];keys=[]
    for i,(trial,source) in enumerate(trials):
        identifier=f'clip-{i+1:03d}'
        if sha256(source)!=trial['hashes']['soma.glb']:raise ValueError('Source clip changed')
        doc,binary=read_glb(source);clean=scrub(doc)
        if any(item.get('uri') and not item['uri'].startswith('data:') for kind in ['buffers','images'] for item in clean.get(kind,[])):
            raise ValueError('Reviewer clips must be self-contained')
        for animation in clean.get('animations',[]):animation['name']='Motion'
        for scene in clean.get('scenes',[]):scene['name']='Character'
        dest=output/'clips'/(identifier+'.glb');write_glb(dest,clean,binary)
        checked,actual_binary=read_glb(dest)
        if checked!=clean or actual_binary!=binary:raise ValueError('Review copy changed motion data')
        context=copy.deepcopy(contexts.get(trial['request']['id'],{}))
        unavailable=context.get('unavailable_categories',{})
        if not isinstance(unavailable,dict) or any(k not in CATEGORIES or k=='action' or not isinstance(v,str) or not v.strip() for k,v in unavailable.items()):
            raise ValueError('Invalid unavailable review categories')
        cases.append(dict(id=identifier,path='clips/'+identifier+'.glb',sha256=sha256(dest),frames=trial['frames'],fps=30,segments=trial['request']['segments'],review_context=context))
        keys.append(dict(id=identifier,source=str(source),source_sha256=sha256(source),review_sha256=sha256(dest),trial_id=trial['id'],request_id=trial['request']['id'],seed=trial['seed']))
    manifest=dict(schema='strep-review-packet-v1',packet_id=uuid.uuid4().hex,created_at=now(),categories=CATEGORIES,cases=cases,
        instructions='Independent human review. Watch at normal speed first. Ratings1 wrong/unusable,2 major defects,3 needs noticeable cleanup,4 usable with minor cleanup,5 polished. Do not infer force/contact validity from numeric diagnostics. No generator, condition or seed labels are displayed.',
        blinding='Condition labels hidden and animation extras removed in review copies. Study organizer retains the key outside this packet. Reviewers must not inspect organizer files; this is not an access-control system.')
    save(output/'manifest.json',manifest);save(key_path,dict(packet_id=manifest['packet_id'],manifest_sha256=sha256(output/'manifest.json'),randomization_seed=seed,cases=keys))
    shutil.copyfile(ROOT/'scripts/human-review.html',output/'viewer.html');shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'LICENSE.txt')
    print(dict(packet=str(output),key=str(key_path),cases=len(cases)))
    return manifest

def validate(data,manifest,digest):
    if not isinstance(data,dict) or set(data)!={'schema','packet_id','manifest_sha256','reviewer_id','independent_human','reviews'} or data['schema']!='strep-human-review-v1':raise ValueError('Invalid human review schema')
    if data['packet_id']!=manifest['packet_id'] or data['manifest_sha256']!=digest:raise ValueError('Review belongs to another packet')
    if data['independent_human'] is not True:raise ValueError('Independent human attestation required')
    if manifest.get('review_type','independent')!='independent':raise ValueError('Independent review requires an independent packet')
    return _validate_rows(data,manifest,digest)


def _validate_rows(data,manifest,digest):
    """Shared rubric checks; the caller must enforce identity and attestation."""
    if not isinstance(data['reviewer_id'],str) or not 1<=len(data['reviewer_id'].strip())<=120:raise ValueError('Reviewer identifier required')
    if not isinstance(data['reviews'],list):raise ValueError('Reviews must be a list')
    valid={c['id'] for c in manifest['cases']};seen=set()
    for row in data['reviews']:
        if not isinstance(row,dict) or set(row)!={'clip_id','scores','not_applicable','major_defect','confidence','notes','cleanup'}:raise ValueError('Invalid review entry')
        identifier=row['clip_id']
        if not isinstance(identifier,str) or identifier not in valid or identifier in seen:raise ValueError('Unknown or repeated clip')
        seen.add(identifier);scores=row['scores'];na=row['not_applicable']
        if not isinstance(scores,dict) or set(scores)!=set(CATEGORIES) or not isinstance(na,dict):raise ValueError('Missing rubric fields')
        if set(na)!={k for k,v in scores.items() if v is None}:raise ValueError('Explain every not-applicable score')
        if any(type(v)is not int or not 1<=v<=5 for v in scores.values() if v is not None):raise ValueError('Scores must be1–5 integers')
        if scores['action'] is None or any(not isinstance(v,str) or not 1<=len(v.strip())<=500 for v in na.values()):raise ValueError('Action is required and N/A needs a reason')
        context=next(c for c in manifest['cases'] if c['id']==identifier).get('review_context',{})
        if any(scores[k] is not None for k in context.get('unavailable_categories',{})):
            raise ValueError('Cannot score a category whose required scene evidence is absent')
        if type(row['major_defect'])is not bool or row['confidence'] not in ['low','medium','high']:raise ValueError('Defect and confidence required')
        if not isinstance(row['notes'],str) or len(row['notes'])>4000:raise ValueError('Invalid notes')
        cleanup=row['cleanup']
        if not isinstance(cleanup,dict) or set(cleanup)!={'status','active_seconds','operations','time_limit_seconds'}:raise ValueError('Invalid cleanup record')
        status=cleanup['status'];elapsed=cleanup['active_seconds'];limit=cleanup['time_limit_seconds']
        if status not in ['not_performed','completed','time_limit','abandoned']:raise ValueError('Unknown cleanup status')
        if not isinstance(cleanup['operations'],str) or len(cleanup['operations'])>4000:raise ValueError('Invalid cleanup operations')
        for value in [elapsed,limit]:
            if value is not None and (type(value)not in (int,float) or not math.isfinite(value) or value<0):raise ValueError('Cleanup times must be finite nonnegative seconds')
        if status=='not_performed':
            if elapsed is not None or limit is not None or cleanup['operations']:raise ValueError('Unperformed cleanup has no measured time')
        elif elapsed is None or not cleanup['operations'].strip():raise ValueError('Record actual edit time and operations')
        if status=='time_limit' and (limit is None or limit<=0 or elapsed<limit):raise ValueError('Censored trial requires reached time limit')
    return dict(reviewed=len(seen),missing=sorted(valid-seen),complete=seen==valid,quality_approved=False,scope='Validated user-entered evidence; identity, independence and actual editing are attestations, not machine verified. Release gating and paired cleanup analysis remain separate.')

def import_reviews(packet,response,output):
    packet=Path(packet);output=Path(output)
    if output.exists():raise ValueError('Preserve earlier imported evidence')
    manifest=read(packet/'manifest.json');data=read(response);result=validate(data,manifest,sha256(packet/'manifest.json'))
    for case in manifest['cases']:
        path=(packet/case['path']).resolve()
        if not path.is_relative_to(packet.resolve()) or sha256(path)!=case['sha256']:raise ValueError('Review clip changed or outside packet')
    output.mkdir(parents=True);shutil.copyfile(response,output/'response.json');save(output/'validation.json',dict(created_at=now(),response_sha256=sha256(response),**result));print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('job',type=Path);b.add_argument('--output',type=Path,required=True);b.add_argument('--key',type=Path,required=True);b.add_argument('--seed',type=int,required=True)
    v=sub.add_parser('import');v.add_argument('packet',type=Path);v.add_argument('response',type=Path);v.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.job,a.output,a.key,a.seed) if a.command=='build' else import_reviews(a.packet,a.response,a.output)
