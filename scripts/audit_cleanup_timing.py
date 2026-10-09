"""Replay reviewer-designated editing intervals; never certify actual editing or quality."""
import argparse
from datetime import datetime
import math
import json
from pathlib import Path
from strep import read,save,sha256,now


def unique_read(path):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('Duplicate timing or review field')
            value[key]=item
        return value
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)


def fields(value,expected):
    if not isinstance(value,dict) or set(value)!=set(expected):raise ValueError('Complete timing fields required')


def timestamp(value):
    if type(value) is not str:raise ValueError('Timestamp required')
    try:result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:raise ValueError('Timestamp required') from exc
    if result.tzinfo is None:raise ValueError('Timezone-aware timestamp required')


def digest(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('SHA-256 binding required')


def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Finite nonnegative monotonic clock required')


def audit(packet,trace,*,review=None,edited_glb=None):
    packet=Path(packet).resolve();trace=Path(trace).resolve()
    if trace.stat().st_size>1024**2:raise ValueError('Timing trace exceeds replay budget')
    inputs={str(trace):sha256(trace),str(packet/'manifest.json'):sha256(packet/'manifest.json')}
    data=unique_read(trace);manifest=unique_read(packet/'manifest.json')
    if manifest.get('schema')!='strep-review-packet-v1':raise ValueError('Versioned review packet required')
    fields(data,{'schema','session_id','context','preselected_limit_seconds','state','segments','open','interruptions','finished_at','output_artifact','quality_approved','release_approved','active_seconds','duration_complete'})
    if (data['schema']!='strep-cleanup-timing-v1' or data['state']!='finished' or data['open'] is not None
            or data['quality_approved'] is not False or data['release_approved'] is not False):raise ValueError('Finished unapproved cleanup timing trace required')
    if type(data['session_id']) is not str or not 1<=len(data['session_id'])<=120:raise ValueError('Session identity required')
    timestamp(data['finished_at']);context=data['context']
    fields(context,{'packet_id','manifest_sha256','clip_id','source_sha256','review_type','reviewer_id'})
    digest(context['manifest_sha256']);digest(context['source_sha256'])
    if (context['packet_id']!=manifest['packet_id'] or context['manifest_sha256']!=sha256(packet/'manifest.json')
            or context['review_type']!=manifest.get('review_type','independent')
            or context['review_type'] not in ('developer','independent')):raise ValueError('Timing belongs to another packet or review role')
    if type(context['reviewer_id']) is not str or not 1<=len(context['reviewer_id'].strip())<=120:raise ValueError('Reviewer identifier required')
    cases=[c for c in manifest['cases'] if c['id']==context['clip_id']]
    if len(cases)!=1:raise ValueError('Exact clip identity required')
    case=cases[0];source=(packet/case['path']).resolve()
    if not source.is_relative_to(packet) or context['source_sha256']!=case['sha256'] or sha256(source)!=case['sha256']:raise ValueError('Source clip changed')
    inputs[str(source)]=case['sha256']
    segments=data['segments'];interruptions=data['interruptions'];total=0.;ends={}
    if not isinstance(segments,list) or not 1<=len(segments)<=10000 or not isinstance(interruptions,list) or len(interruptions)>10000:raise ValueError('Bounded complete timing intervals required')
    for segment in segments:
        fields(segment,{'page_id','start_ms','end_ms','started_at','ended_at'})
        page=segment['page_id'];finite(segment['start_ms']);finite(segment['end_ms']);timestamp(segment['started_at']);timestamp(segment['ended_at'])
        if type(page) is not str or not 1<=len(page)<=120 or segment['end_ms']<segment['start_ms'] or segment['start_ms']<ends.get(page,0):raise ValueError('Overlapping or reversed active intervals')
        ends[page]=segment['end_ms'];total+=(segment['end_ms']-segment['start_ms'])/1000
    for interruption in interruptions:
        fields(interruption,{'page_id','start_ms','started_at','detected_at'});finite(interruption['start_ms']);timestamp(interruption['started_at']);timestamp(interruption['detected_at'])
        if type(interruption['page_id']) is not str or not 1<=len(interruption['page_id'])<=120:raise ValueError('Interrupted page identity required')
    finite(data['active_seconds'])
    if not math.isfinite(total) or not math.isclose(total,data['active_seconds'],rel_tol=0,abs_tol=1e-9):raise ValueError('Active time does not match recorded intervals')
    complete=not interruptions
    if data['duration_complete'] is not complete:raise ValueError('Interrupted timing cannot claim complete duration')
    limit=data['preselected_limit_seconds']
    if limit is not None:
        finite(limit)
        if limit<=0:raise ValueError('Positive preselected time limit required')
    artifact=data['output_artifact'];artifact_verified=False
    if artifact is not None:
        fields(artifact,{'name','bytes','sha256'});digest(artifact['sha256'])
        if (type(artifact['name']) is not str or len(artifact['name'])>255 or '/' in artifact['name'] or '\\' in artifact['name'] or not artifact['name'].lower().endswith('.glb')
                or type(artifact['bytes']) is not int or not 0<artifact['bytes']<=128*1024**2):raise ValueError('Bounded edited GLB fingerprint required')
        if edited_glb is not None:
            edited_glb=Path(edited_glb);from gltf_tools import read_glb
            if edited_glb.stat().st_size!=artifact['bytes'] or sha256(edited_glb)!=artifact['sha256']:raise ValueError('Edited GLB changed')
            inputs[str(edited_glb.resolve())]=artifact['sha256']
            doc,_=read_glb(edited_glb)
            if any(row.get('uri') and not row['uri'].startswith('data:') for k in ('buffers','images') for row in doc.get(k,[])):raise ValueError('Edited GLB must be self-contained')
            artifact_verified=True
    elif edited_glb is not None:raise ValueError('Trace has no edited artifact binding')
    if review is not None:
        inputs[str(Path(review).resolve())]=sha256(review);response=unique_read(review)
        if context['review_type']=='developer':from developer_packet_review import validate
        else:from review_session import validate
        validate(response,manifest,context['manifest_sha256'])
        if response['reviewer_id']!=context['reviewer_id']:raise ValueError('Reviewer mismatch')
        rows=[r for r in response['reviews'] if r['clip_id']==context['clip_id']]
        if len(rows)!=1:raise ValueError('Corresponding saved review required')
        cleanup=rows[0]['cleanup']
        if (not complete or cleanup['status']=='not_performed' or cleanup['time_limit_seconds']!=limit
                or not math.isclose(cleanup['active_seconds'],total,rel_tol=0,abs_tol=1e-9)):raise ValueError('Review duration or cleanup policy differs from its complete timing trace')
        if cleanup['status']=='completed' and not artifact_verified:raise ValueError('Completed cleanup requires its matching edited GLB')
    if any(sha256(path)!=value for path,value in inputs.items()):raise ValueError('Cleanup evidence changed during replay')
    return dict(schema='strep-cleanup-timing-replay-v1',at=now(),trace_sha256=inputs[str(trace)],inputs_sha256=inputs,context=context,
        intervals_replayed=len(segments),interrupted_intervals=len(interruptions),active_seconds=total,duration_complete=complete,
        preselected_limit_seconds=limit,overrun_seconds=max(0,total-limit) if limit is not None else None,
        saved_review_matched=review is not None,edited_artifact_verified=artifact_verified,quality_approved=False,release_approved=False,
        scope='Recorded reviewer-designated intervals and source/artifact bindings only. Actual editing, reviewer identity, independence, naturalness and completion quality are not machine verified.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('packet',type=Path);p.add_argument('trace',type=Path)
    p.add_argument('--review',type=Path);p.add_argument('--edited-glb',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    save(a.output,audit(a.packet,a.trace,review=a.review,edited_glb=a.edited_glb))
