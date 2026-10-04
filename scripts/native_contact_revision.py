"""Explicit contact patch revisions; preserve the whole original authoring draft."""
import copy
from native_scene_contacts import fields

SCHEMA='strep-native-contact-revision-v1'
DRAFT_FIELDS=('schema','scene','geometry','object_edit')


def patch(value,actor):
    fields(value,('glb_sha256','vertices','reduction'),'explicit revised patch')
    if value['glb_sha256']!=actor['sha256']:raise ValueError('Revised patch belongs to another character clip')
    refs=value['vertices']
    if (not isinstance(refs,list) or not 1<=len(refs)<=256
            or any(not isinstance(r,list) or len(r)!=3 or any(type(i) is not int or i<0 for i in r) for r in refs)
            or len({tuple(r) for r in refs})!=len(refs)):
        raise ValueError('Choose 1-256 distinct explicit mesh references; no truncation')
    if value['reduction'] not in ('individual','centroid'):raise ValueError('Choose explicit point or centroid reduction')
    return copy.deepcopy(refs),value['reduction']


def apply(baseline,edits):
    fields(baseline,DRAFT_FIELDS,'original Studio draft')
    if baseline['schema']!='strep-studio-native-scene-v1':raise ValueError('Original Studio scene draft required')
    if not isinstance(edits,list) or not 1<=len(edits)<=64:raise ValueError('Choose 1-64 explicit contact revisions')
    result=copy.deepcopy(baseline);seen=set();contacts={c['id']:c for c in result['scene']['contacts']}
    for edit in edits:
        fields(edit,('id','source','partner'),'contact revision')
        name=edit['id']
        if not isinstance(name,str) or name not in contacts or name in seen:raise ValueError('Choose distinct existing contacts to revise')
        seen.add(name);row=contacts[name]
        if edit['source'] is None and edit['partner'] is None:raise ValueError('Explicit source or partner patch change required')
        if edit['source'] is not None:
            row['vertices'],row['reduction']=patch(edit['source'],result['scene']['actors'][row['actor']])
        if edit['partner'] is not None:
            if row['target']['space']!='actor':raise ValueError('Only a partner target has a partner patch')
            target=row['target'];target['vertices'],target['reduction']=patch(edit['partner'],result['scene']['actors'][target['actor']])
        count=1 if row['reduction']=='centroid' else len(row['vertices'])
        target=row['target'];other=(1 if target['reduction']=='centroid' else len(target['vertices'])) if target['space']=='actor' else len(target['points_m'])
        if count!=other:raise ValueError('Preserve explicit one-to-one point correspondence; revise both partner sides together when needed')
        original=next(c for c in baseline['scene']['contacts'] if c['id']==name)
        if row==original:raise ValueError('Contact revision makes no change')
    return result


def validate(payload):
    if 'contact_revision' not in payload:
        fields(payload,DRAFT_FIELDS,'Studio native scene draft');return payload,None
    fields(payload,DRAFT_FIELDS+('contact_revision',),'revised Studio native scene draft')
    revision=payload['contact_revision'];fields(revision,('schema','baseline','edits'),'contact revision provenance')
    if revision['schema']!=SCHEMA:raise ValueError('Contact revision schema required')
    expected=apply(revision['baseline'],revision['edits'])
    actual={k:payload[k] for k in DRAFT_FIELDS}
    if actual!=expected:raise ValueError('Contact revision changes protected draft fields or differs from explicit patches')
    return actual,revision


def portable_record(payload):
    _,revision=validate(payload)
    if revision is None:raise ValueError('Revised draft required')
    return dict(schema=SCHEMA,original_contacts=copy.deepcopy(revision['baseline']['scene']['contacts']),
        authored_contacts=copy.deepcopy(payload['scene']['contacts']),explicit_edits=copy.deepcopy(revision['edits']),
        actor_sha256={n:a['sha256'] for n,a in payload['scene']['actors'].items()},
        contact_timing_and_limits_unchanged=True,other_authoring_fields_unchanged=True,
        original_intent_retained=True,contact_intent_revised=True,animation_edited=False,
        anatomical_review_pending=True,quality_approved=False,training_admitted=False,release_approved=False)
