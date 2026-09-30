"""Authored intent markers and deterministic source-contribution remapping."""
import hashlib
import re
from strep import read

BOUNDARIES={'cycle_boundary','transition_start','transition_end'}


def load(folder):
    path=folder/'events.json'
    return read(path) if path.exists() else dict(events=[])


def validate_markers(markers,frames):
    if not isinstance(markers,list) or len(markers)>128:raise ValueError('Use at most 128 authored markers')
    ids=set()
    for e in markers:
        if not isinstance(e,dict) or set(e)!={'id','name','frame','confirmed'}:raise ValueError('Marker requires id, name, frame and timing confirmation')
        if not isinstance(e['id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}',e['id']) or e['id'] in ids:raise ValueError('Marker IDs must be unique short identifiers')
        ids.add(e['id'])
        if not isinstance(e['name'],str) or not 1<=len(e['name'].strip())<=64 or e['name'].strip() in BOUNDARIES:raise ValueError('Name the event; authoring boundary names are reserved')
        if type(e['frame']) is not int or not 0<=e['frame']<frames or type(e['confirmed']) is not bool:raise ValueError('Marker frame must lie within the selected clip')


def edit(document,markers,source_hash,frames):
    validate_markers(markers,frames);old={e['id']:e for e in document['events'] if e.get('kind')=='authored' and 'id' in e}
    events=[e for e in document['events'] if e.get('kind')!='authored']
    for entry in markers:
        previous=old.get(entry['id']);lineage=previous.get('lineage',[]) if previous else []
        prior={k:previous[k] for k in ('id','name','frame','requires_review') if k in previous} if previous else None
        events.append(dict(id=entry['id'],name=entry['name'].strip(),frame=entry['frame'],time_s=entry['frame']/30,kind='authored',requires_review=not entry['confirmed'],origin_id=previous.get('origin_id',entry['id']) if previous else entry['id'],lineage=lineage+[dict(operation='author_marker',source_glb_sha256=source_hash,previous=prior,confirmed_timing=entry['confirmed'])]))
    events.sort(key=lambda e:e['frame'])
    return dict(fps=30,events=events,removed_authored_ids=sorted(set(old)-{e['id'] for e in markers}),provenance='Explicit authoring intent. Timing confirmation is not verified contact, action correctness or physics.')


def remap(documents,clocks,boundaries):
    """Carry each positive-weight event occurrence; never silently approve a blend."""
    events=[{**e,'kind':'authoring_boundary'} for e in boundaries];used=set();omitted=[]
    for f,entries in enumerate(clocks):
        for c in entries:
            source=c.get('source',0)
            if c['weight']<=0:continue
            for index,e in enumerate(documents[source]['events']):
                if e.get('name') in BOUNDARIES and e.get('kind')!='authored':continue
                if e['frame']!=c['frame']:continue
                used.add((source,index));identity=hashlib.sha256(f'{source}:{index}:{e.get("id","")}:{f}'.encode()).hexdigest()[:24]
                partial=c['weight']<1-1e-9
                events.append({**e,'id':identity,'origin_id':e.get('origin_id',e.get('id',str(index))),'frame':f,'time_s':f/30,'requires_review':e.get('requires_review') is not False or partial,
                    'lineage':e.get('lineage',[])+[dict(operation='source_contribution',source=source,source_event_id=e.get('id'),source_frame=e['frame'],output_frame=f,weight=c['weight'],cycle_offset=c.get('cycle_offset'))]})
    for source,doc in enumerate(documents):
        for i,e in enumerate(doc['events']):
            if (source,i) not in used:omitted.append(dict(source=source,index=i,event=e,reason='Replaced structural boundary' if e.get('name') in BOUNDARIES else 'Outside selected contributions or zero blend weight'))
    events.sort(key=lambda e:e['frame'])
    return dict(fps=30,events=events,omitted=omitted,provenance='Source events mapped through positive pose contributions. Partial blends retain intent but require explicit timing review before runtime dispatch.')


def runtime_markers(document,period):
    markers=[dict(name='cycle_boundary',phase_frame=0,first_cycle=1)];excluded=[]
    for e in document['events']:
        if e.get('kind')=='authored' and e.get('requires_review') is False and 0<=e['frame']<period:
            markers.append(dict(name=e['name'],phase_frame=e['frame'],first_cycle=0,event_id=e['id'],source_event=e))
        else:excluded.append(dict(event=e,reason='Only timing-confirmed authored events inside the first period dispatch; boundaries are generated separately'))
    markers.sort(key=lambda e:e['phase_frame'])
    return markers,excluded
