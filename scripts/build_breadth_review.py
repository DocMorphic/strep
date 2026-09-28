"""Prepare one complete breadth round for human review, without selecting good takes."""
import argparse
from pathlib import Path
from strep import ROOT,read,save,sha256,now
from breadth_study import validate_freeze,verify_complete
from review_session import build_many
from portable_review_packet import package


def prepare(study,round_number,output,key,archive,randomization_seed):
    study=Path(study).resolve();frozen=validate_freeze(study);protocol=read(study/'protocol.json')
    cases=[c for c in protocol['cases'] if c['round']==round_number]
    if not cases:raise ValueError('No cases for requested round')
    expected={(c['id']+'-'+a['id'].lower(),seed) for c in cases for a in c['actors'] for seed in c['seeds']}
    identifiers={r for r,_ in expected};jobs=[];actual=set();batches=[]
    for batch in frozen['batches']:
        requests=read(ROOT/batch['request'])['requests'];ids={r['id'] for r in requests}
        if not ids.intersection(identifiers):continue
        if not ids<=identifiers:raise ValueError('Batch crosses requested review round')
        trials=verify_complete(batch)
        for trial in trials:
            pair=(trial['request_id'],trial['seed'])
            if pair in actual:raise ValueError('Repeated study take')
            actual.add(pair)
        jobs.append(ROOT/batch['output']);batches.append(batch['id'])
    if actual!=expected:raise ValueError('Do not build an incomplete or selectively filtered review round')
    contexts={}
    for c in cases:
        missing=c['scene_validation']=='missing_required_context_validation'
        context=dict(flat_floor_screen_applicable=c['flat_floor_screen_applicable'],unavailable_categories={},
                     note='Review the visible actor motion. These scores do not establish physical correctness or release acceptance.')
        if missing:
            context['note']=('Review only the visible actor. Required context is absent: '+c['context'].replace('_',' ')+
                '. Full interaction/contact accuracy cannot be assessed from this clip. Use N/A with a reason for contacts/collisions. Action scores describe the visible actor, not a solved interaction.')
            context['unavailable_categories']={'contacts_collisions':'Required scene geometry, partner or physical context is absent.'}
        for a in c['actors']:contexts[c['id']+'-'+a['id'].lower()]=context
    manifest=build_many(jobs,output,key,randomization_seed,contexts)
    private=read(key);private['study']=dict(protocol_sha256=frozen['protocol_sha256'],round=round_number,batches=batches,
        scope='Complete raw diagnostic round; not final release evidence or a cleanup comparison.')
    save(key,private)
    result=package(output,archive)
    result.update(created_at=now(),round=round_number,planned_clips=len(expected),actual_clips=len(manifest['cases']),
                  no_quality_filtering=True,human_reviews_collected=0,quality_approved=False)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,default=ROOT/'reports/breadth-baseline-v2')
    p.add_argument('--round',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--key',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args()
    if a.evidence.exists():p.error('Preserve existing packet build evidence')
    result=prepare(a.study,a.round,a.output,a.key,a.archive,a.seed);save(a.evidence,result);print(result)
