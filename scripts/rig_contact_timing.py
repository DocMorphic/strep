"""Preserve authored mesh-contact clocks across immutable clip transformations.

Records retain authoring intent, never contact or animation-quality approval.
"""
import copy
from pathlib import Path
from strep import read,save,sha256
from rig_contact_fit_options import defaults,validate_shape

SCHEMA='strep-mesh-contact-timing-v1'
KEYS={'schema','glb_sha256','contact_spec_sha256','fit_options','operation','parent','interval_mapping','requires_review','quality_approved'}


def spec_path(glb):
    glb=Path(glb);local=glb.parent/'contact-spec.json'
    if local.exists() or glb.parent.name in ('input','following'):return local
    return glb.parent.parent/'contact-spec.json'


def validate(record,glb,spec_file):
    if type(record) is not dict or set(record)!=KEYS or record['schema']!=SCHEMA:
        raise ValueError('Invalid contact timing record')
    if record['requires_review'] is not True or record['quality_approved'] is not False:
        raise ValueError('Contact timing record cannot establish approval')
    if record['glb_sha256']!=sha256(glb) or record['contact_spec_sha256']!=sha256(spec_file):
        raise ValueError('Contact timing geometry or draft changed')
    spec=read(spec_file)
    if spec['glb_sha256']!=record['glb_sha256']:raise ValueError('Contact timing draft belongs to another clip')
    validate_shape(record['fit_options'],spec)
    mapping=record['interval_mapping']
    if type(mapping) is not list or len(mapping)!=len(spec['contacts']) or any(type(i)is not int or i<0 for i in mapping) or len(set(mapping))!=len(mapping):
        raise ValueError('Invalid contact timing interval mapping')
    if type(record['operation'])is not str or not record['operation'] or type(record['parent'])not in (dict,type(None)):
        raise ValueError('Invalid contact timing provenance')
    return spec,copy.deepcopy(record)


def load(glb):
    """Load a local bound record or the original contact-job option snapshot."""
    glb=Path(glb);path=spec_path(glb);record_path=glb.parent/'contact-timing.json'
    if record_path.exists():
        if not (glb.parent/'contact-spec.json').exists():raise ValueError('Contact timing record has no local draft')
        spec,record=validate(read(record_path),glb,path)
        return spec,record,dict(timing_sha256=sha256(record_path),glb_sha256=sha256(glb),spec_sha256=sha256(path))
    if not path.exists():return None
    spec=read(path);options=defaults();folder=glb.parent.parent;timing_digest=None
    request=read(folder/'request.json') if (folder/'request.json').exists() else {}
    if request.get('contact_fit') is not None and request.get('kind')=='contact_edit' and glb.parent.name in ('transfer','corrected'):
        saved=folder/'contact-fit.json'
        if sha256(saved)!=request.get('contact_fit_sha256') or read(saved)!=request['contact_fit'] or sha256(path)!=request['authored_spec_sha256']:
            raise ValueError('Saved contact fitting choice or draft changed')
        options=validate_shape(request['contact_fit'],spec)
        timing_digest=sha256(saved)
    spec=copy.deepcopy(spec);spec['glb_sha256']=sha256(glb)
    record=dict(fit_options=options)
    parent=dict(timing_sha256=timing_digest,
                glb_sha256=sha256(glb),spec_sha256=sha256(path))
    return spec,record,parent


def write(folder,spec,options,operation,parent=None,mapping=None):
    folder=Path(folder);spec=copy.deepcopy(spec);spec['glb_sha256']=sha256(folder/'character.glb')
    options=validate_shape(options,spec)
    save(folder/'contact-spec.json',spec)
    record=dict(schema=SCHEMA,glb_sha256=spec['glb_sha256'],contact_spec_sha256=sha256(folder/'contact-spec.json'),
        fit_options=options,operation=operation,parent=copy.deepcopy(parent),
        interval_mapping=list(range(len(spec['contacts']))) if mapping is None else list(mapping),
        requires_review=True,quality_approved=False)
    validate(record,folder/'character.glb',folder/'contact-spec.json');save(folder/'contact-timing.json',record)
    return record


def snapshot(glb,destination):
    data=load(glb)
    if data is None:return None
    spec,record,parent=data
    return write(destination,spec,record['fit_options'],'source_snapshot',parent)


def bind_inputs(folder,request):
    folder=Path(folder)
    hashes={name:sha256(folder/name/'contact-timing.json') for name in ('input','following') if (folder/name/'contact-timing.json').exists()}
    if hashes:request['contact_timing_inputs']=hashes
    reviews={name:sha256(folder/name/'contact-review.json') for name in ('input','following') if (folder/name/'contact-review.json').exists()}
    if reviews:request['contact_timing_reviews']=reviews


def verify_inputs(folder,request):
    folder=Path(folder)
    existing={name for name in ('input','following') if (folder/name/'contact-timing.json').exists()}
    if existing!=set(request.get('contact_timing_inputs',{})):raise ValueError('Contact timing input bindings missing or changed')
    for name,digest in request.get('contact_timing_inputs',{}).items():
        if name not in ('input','following') or sha256(folder/name/'contact-timing.json')!=digest:
            raise ValueError('Contact timing input snapshot changed')
        load(folder/name/'character.glb')
    reviews={name for name in ('input','following') if (folder/name/'contact-review.json').exists()}
    if reviews!=set(request.get('contact_timing_reviews',{})):raise ValueError('Contact timing review bindings missing or changed')
    from mesh_contact_clock import validate_clock
    for name,digest in request.get('contact_timing_reviews',{}).items():
        if name not in ('input','following') or sha256(folder/name/'contact-review.json')!=digest:
            raise ValueError('Contact timing review snapshot changed')
        for target in read(folder/name/'contact-review.json')['authored_targets']:
            if 'contact_clock' in target:validate_clock(target['contact_clock'])


def clocks(record,count):
    options=record['fit_options'];overrides=options.get('contact_clock_overrides',{})
    return [overrides.get(str(i),options['contact_clock']) for i in range(count)]


def retime(input_folder,output_folder,spec,dropped):
    input_folder=Path(input_folder);data=load(input_folder/'character.glb')
    if data is None:return None
    old,record,parent=data;kept=[i for i in range(len(old['contacts'])) if i not in dropped]
    if len(kept)!=len(spec['contacts']):raise ValueError('Retimed contact count differs from interval mapping')
    options=copy.deepcopy(record['fit_options']);overrides=options.get('contact_clock_overrides')
    if overrides is not None:options['contact_clock_overrides']={str(n):overrides[str(i)] for n,i in enumerate(kept) if str(i) in overrides}
    return write(output_folder,spec,options,'trim_retime_pose',parent,kept)


def target_rows(input_folder):
    """Source targets plus clocks for review-only blends/reflections."""
    input_folder=Path(input_folder);data=load(input_folder/'character.glb')
    if data is None:return None
    spec,record,parent=data;selected=clocks(record,len(spec['contacts']))
    return [dict(patch=c['patch'],vertices=spec['patches'][c['patch']]['vertices'],target_position_m=c['target_position_m'],
        original_interval=copy.deepcopy(c),contact_clock=selected[i],source_interval_index=i,source_contact_timing=parent,
        output_frames=[dict(frame=f,weight=1.) for f in range(c['start_frame'],c['end_frame_exclusive'])]) for i,c in enumerate(spec['contacts'])]
