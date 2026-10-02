"""Source-bound developer correction review; no automatic ratings or training."""
import copy
from pathlib import Path
import re
import struct
import uuid

from strep import ROOT,read,save,sha256,now

NAME=re.compile(r'[A-Za-z0-9_-]{1,100}')
NAMESPACE='native-correction-packs'
PREVIEWS='native-correction-previews'


def _draft(identifier):
    if not isinstance(identifier,str) or not NAME.fullmatch(identifier) or not identifier.startswith('kimodo-target-review-'):
        raise ValueError('Choose a saved native target draft')
    path=(ROOT/'reports'/identifier/'draft.json').resolve()
    if path.parent.parent!=(ROOT/'reports').resolve():raise ValueError('Draft escapes reports')
    value=read(path)
    if not isinstance(value,dict) or value.get('schema')!='strep-native-target-review-draft-v1' or value.get('training_admitted') is not False or value.get('quality_approved') is not False:
        raise ValueError('Original unapproved target draft required')
    return path,value


def listing():
    entries=[];rejected=[]
    for folder in sorted((ROOT/'reports').glob('kimodo-target-review-*')):
        if not (folder/'draft.json').is_file():continue
        try:
            path,data=_draft(folder.name)
            entries.append({'id':folder.name,'sha256':sha256(path),'segments':len(data['items']),'quality_approved':False})
        except (ValueError,KeyError,OSError):rejected.append(folder.name)
    return {'drafts':entries,'rejected':rejected}


def _reported(path):
    if not isinstance(path,str) or not path.strip():raise ValueError('Existing project report file required')
    resolved=(ROOT/path).resolve()
    if not resolved.is_relative_to((ROOT/'reports').resolve()) or not resolved.is_file():
        raise ValueError('File must already exist within project reports')
    return resolved


def metadata(identifier,expected_hash,item_id,candidate=None,candidate_start=None):
    from pack_native_correction import selected,_motion
    from inspect_motion import skeleton_metadata
    path,draft=_draft(identifier)
    if sha256(path)!=expected_hash:raise ValueError('Draft changed; reload before reviewing')
    inputs={};item=selected(path,item_id,inputs)
    source=(path.parent/item['source_motion']).resolve();preview=(path.parent/item['source_preview']).resolve()
    base=(ROOT/'reports').resolve()
    if not source.is_relative_to(base) or not preview.is_relative_to(base/'action-jobs'):
        raise ValueError('Draft source/preview is outside the served native action jobs')
    from gltf_tools import read_glb
    try:document,_=read_glb(preview)
    except (struct.error,IndexError) as exc:raise ValueError('Valid self-contained native GLB required') from exc
    if any(item.get('uri') and not item['uri'].startswith('data:') for kind in ('buffers','images') for item in document.get(kind,[])):
        raise ValueError('Native reference preview must be self-contained')
    candidate=source if candidate is None else _reported(candidate)
    if candidate.suffix!='.npz' or candidate.stat().st_size>32*1024*1024:raise ValueError('Use a native NPZ below 32 MiB')
    if candidate_start is None:
        if candidate!=source:raise ValueError('Edited candidate needs its matching-window start frame')
        candidate_start=item['source_start_frame']
    frames=item['source_end_frame_exclusive']-item['source_start_frame']
    digest=sha256(candidate);_motion(candidate,candidate_start,frames)
    if sha256(candidate)!=digest:raise ValueError('Candidate changed during selection')
    names,_,_=skeleton_metadata(77)
    recipe={'schema':'strep-native-correction-pack-recipe-v1','draft':{'path':str(path),'sha256':expected_hash},
            'item_id':item_id,'candidate_motion':{'path':str(candidate),'sha256':digest},'candidate_start_frame':candidate_start,
            'fps':30,'joint_names':names,'units':'metres','coordinates':'right-handed-Y-up',
            'contacts':[{'joint':joint,'intervals':[{'start_frame':0,'end_frame_exclusive':frames,'contact':None}]} for joint in ('LeftFoot','LeftToeBase','RightFoot','RightToeBase')]}
    return {'draft_id':identifier,'draft_sha256':expected_hash,'draft':recipe['draft'],
            'items':[{'id':i['id'],'prompt':i['prompt']} for i in draft['items']],
            'item_id':item_id,'prompt':item['prompt'],'frames':frames,'fps':30,'source_start_frame':item['source_start_frame'],
            'source_motion_sha256':item['source_motion_sha256'],'candidate_relative':candidate.relative_to(ROOT).as_posix(),
            'recipe':recipe,'preview_url':'/files/'+preview.relative_to(base).as_posix(),'preview_sha256':item['source_preview_sha256'],
            'preview_start_s':item['source_start_frame']/30,'preview_end_s':(item['source_end_frame_exclusive']-1)/30,
            'preview_scope':'Original reference preview; assess an edited candidate in its authoring tool',
            'quality_approved':False,'training_admitted':False}


def first(identifier,expected_hash):
    _,draft=_draft(identifier)
    if not draft['items']:raise ValueError('Draft has no segments')
    return metadata(identifier,expected_hash,draft['items'][0]['id'])


def preview_request(payload):
    """Export a selected candidate's real pose tracks; no contacts are inferred."""
    import numpy as np
    from inspect_motion import skeleton_metadata
    from pack_native_correction import selected,_motion
    from native_candidate_preview import export_candidate
    fields={'draft_id','draft_sha256','item_id','candidate_motion','candidate_start_frame'}
    if not isinstance(payload,dict) or set(payload)!=fields or not isinstance(payload['candidate_motion'],dict) or set(payload['candidate_motion'])!={'path','sha256'}:
        raise ValueError('Bound candidate preview selection required')
    data=metadata(payload['draft_id'],payload['draft_sha256'],payload['item_id'],payload['candidate_motion']['path'],payload['candidate_start_frame'])
    if data['recipe']['candidate_motion']!=payload['candidate_motion']:raise ValueError('Selected candidate changed; bind it again')
    inputs={};item=selected(Path(data['draft']['path']),payload['item_id'],inputs)
    inputs[payload['candidate_motion']['path']]=payload['candidate_motion']['sha256']
    local,roots=_motion(payload['candidate_motion']['path'],payload['candidate_start_frame'],data['frames'])
    path=Path(data['draft']['path']);source=(path.parent/item['source_motion']).resolve();reference=(path.parent/item['source_preview']).resolve()
    with np.load(source,allow_pickle=False) as archive:
        original={key:archive[key][item['source_start_frame']:item['source_end_frame_exclusive']].copy() for key in ('local_rot_mats','root_positions','posed_joints','global_rot_mats')}
    names,parents,_=skeleton_metadata(77)
    identifier=uuid.uuid4().hex;folder=ROOT/'reports'/PREVIEWS/identifier;folder.mkdir(parents=True)
    record={'schema':'strep-native-candidate-preview-result-v1','status':'running','at':now(),
            'selection':payload,'inputs_sha256':inputs,'quality_approved':False,'training_admitted':False,'release_approved':False}
    save(folder/'result.json',record)
    try:
        methods={}
        for name in ('native_candidate_preview.py','studio_correction_review.py','gltf_tools.py','pack_native_correction.py','inspect_motion.py'):
            method=Path(__file__).parent/name;digest=sha256(method);dest=folder/'methods'/name
            dest.parent.mkdir(exist_ok=True);dest.write_bytes(method.read_bytes());inputs[str(method)]=digest;methods[name]=digest
        report=export_candidate(reference,original,local.numpy(),roots.numpy(),names,parents,folder/'candidate.glb')
        if any(sha256(p)!=h for p,h in inputs.items()):raise ValueError('Preview source or method changed during export')
        record.update(status='complete',report=report,methods_sha256=methods,
                      preview={'path':'candidate.glb','sha256':sha256(folder/'candidate.glb')})
        save(folder/'result.json',record)
        return {'id':identifier,'item_id':data['item_id'],'selection':payload,
                'preview_url':'/files/'+PREVIEWS+'/'+identifier+'/candidate.glb','preview_sha256':record['preview']['sha256'],
                'preview_start_s':0.,'preview_end_s':report['duration_s'],'preview_scope':'Selected candidate geometry; human review remains pending',
                'quality_approved':False,'training_admitted':False}
    except Exception as exc:
        record.update(status='failed',error=str(exc));save(folder/'result.json',record);raise


def served_preview(relative):
    parts=relative.split('/')
    if len(parts)!=3 or parts[0]!=PREVIEWS or not NAME.fullmatch(parts[1]) or parts[2]!='candidate.glb':return None
    folder=(ROOT/'reports'/PREVIEWS/parts[1]).resolve()
    if folder.parent!=(ROOT/'reports'/PREVIEWS).resolve():return None
    try:
        record=read(folder/'result.json');path=folder/'candidate.glb'
        if record.get('schema')!='strep-native-candidate-preview-result-v1' or record.get('status')!='complete' or record.get('quality_approved') is not False:
            return None
        if record['preview']['path']!='candidate.glb' or sha256(path)!=record['preview']['sha256']:return None
        return path
    except (ValueError,KeyError,OSError,TypeError):return None


def pack_request(payload):
    from pack_native_correction import pack
    from inspect_motion import skeleton_metadata
    if not isinstance(payload,dict) or set(payload)!={'draft_id','draft_sha256','recipe'}:raise ValueError('Bound draft and annotation recipe required')
    recipe=payload['recipe']
    if not isinstance(recipe,dict) or not isinstance(recipe.get('candidate_motion'),dict):
        raise ValueError('Native annotation recipe required')
    data=metadata(payload['draft_id'],payload['draft_sha256'],recipe['item_id'],recipe['candidate_motion']['path'],recipe['candidate_start_frame'])
    expected=copy.deepcopy(data['recipe']);expected['contacts']=recipe['contacts']
    if recipe!=expected:raise ValueError('Annotation source/clock differs from selected draft')
    identifier=uuid.uuid4().hex;folder=ROOT/'reports'/NAMESPACE/identifier
    folder.mkdir(parents=True);save(folder/'recipe.json',recipe)
    try:
        names,_,_=skeleton_metadata(77);result=pack(folder/'recipe.json',folder/'packed',names)
    except Exception:
        save(folder/'status.json',{'status':'failed','at':now(),'training_admitted':False});raise
    save(folder/'status.json',{'status':'complete','at':now(),'training_admitted':False})
    return {'id':identifier,'item_id':recipe['item_id'],'correction':result['correction'],
            'folder':folder.relative_to(ROOT).as_posix(),'training_admitted':False,'quality_approved':False}


def save_review(payload):
    """Save a complete source-bound human submission, without starting training."""
    from kimodo_training_corpus import validate,RIGHTS
    from inspect_motion import skeleton_metadata
    if not isinstance(payload,dict) or set(payload)!={'draft_id','draft_sha256','reviewer','items'}:
        raise ValueError('Bound draft, actual reviewer and every segment decision required')
    path,draft=_draft(payload['draft_id'])
    if sha256(path)!=payload['draft_sha256']:raise ValueError('Draft changed; reload')
    known={item['id']:item for item in draft['items']}
    if not isinstance(payload['items'],list) or len(payload['items'])!=len(known):raise ValueError('Every segment requires a decision')
    folder=ROOT/'reports/native-correction-submissions'/uuid.uuid4().hex;folder.mkdir(parents=True)
    rows=[];seen=set()
    try:
        for value in payload['items']:
            fields={'id','decision','split','semantic_pass','motion_quality_pass','contact_schedule_pass','cleanup_seconds','notes','pack_id','rights'}
            if not isinstance(value,dict) or set(value)!=fields or value['id'] not in known or value['id'] in seen:
                raise ValueError('Unknown, duplicate or incomplete segment review')
            seen.add(value['id']);row={k:v for k,v in value.items() if k not in ('pack_id','rights')}
            row.update(correction=None,rights_attestation=None)
            if value['decision']=='exclude':
                if value['pack_id'] is not None or value['rights'] is not None:raise ValueError('Excluded segment must not carry a correction or permission')
            elif value['decision']=='accept_corrected':
                if not isinstance(value['pack_id'],str) or not NAME.fullmatch(value['pack_id']):raise ValueError('Use a correction packed in this panel')
                pack_folder=(ROOT/'reports'/NAMESPACE/value['pack_id']).resolve()
                if pack_folder.parent!=(ROOT/'reports'/NAMESPACE).resolve():raise ValueError('Invalid packed correction')
                result=read(pack_folder/'packed/result.json');item=known[value['id']]
                if (result.get('schema')!='strep-native-correction-pack-result-v1' or result.get('status')!='complete'
                    or result['item_id']!=value['id'] or result['original_motion_sha256']!=item['source_motion_sha256']
                    or result['original_start_frame']!=item['source_start_frame']
                    or result['original_end_frame_exclusive']!=item['source_end_frame_exclusive']
                    or any(result.get(k) is not False for k in ('training_admitted','quality_approved','release_approved'))
                    or Path(result['correction']['path']).resolve()!=pack_folder/'packed/correction.safetensors'):
                    raise ValueError('Packed correction belongs to another original segment')
                if sha256(result['correction']['path'])!=result['correction']['sha256']:raise ValueError('Packed correction changed')
                rights=value['rights']
                rights_fields={'authorized_by','attested_at','permitted','evidence_paths','obligations','notes'}
                if not isinstance(rights,dict) or set(rights)!=rights_fields or not isinstance(rights['evidence_paths'],list):raise ValueError('Explicit human rights attestation required')
                evidence=[]
                for raw in rights['evidence_paths']:
                    evidence_path=(ROOT/raw).resolve() if isinstance(raw,str) else None
                    model_license=(ROOT/'models/checkpoints/Kimodo-SOMA-RP-v1.1/LICENSE').resolve()
                    if evidence_path!=model_license:evidence_path=_reported(raw)
                    if not evidence_path.is_file():raise ValueError('Retained rights evidence is missing')
                    evidence.append({'path':str(evidence_path),'sha256':sha256(evidence_path)})
                rights_record={k:v for k,v in rights.items() if k!='evidence_paths'}
                rights_record.update(schema=RIGHTS,source_motion_sha256=item['source_motion_sha256'],
                                     correction_sha256=result['correction']['sha256'],source_kind='model_output_and_authored_correction',
                                     use='commercial_generative_game_motion_training',evidence_files=evidence)
                rights_path=folder/(value['id']+'-rights.json')
                # IDs come from the pinned packet, but do not use them as arbitrary paths.
                if not NAME.fullmatch(value['id']):raise ValueError('Safe native segment ID required')
                save(rights_path,rights_record)
                row.update(correction=result['correction'],rights_attestation={'path':str(rights_path),'sha256':sha256(rights_path)})
            else:raise ValueError('Choose accept corrected or exclude for every segment')
            rows.append(row)
        submission={'schema':'strep-native-correction-submission-v1','draft':{'path':str(path),'sha256':payload['draft_sha256']},
                    'reviewer':payload['reviewer'],'items':rows}
        submission_path=folder/'submission.json';save(submission_path,submission)
        names,_,_=skeleton_metadata(77)
        _,accepted,_=validate(submission_path,ROOT/'benchmarks/release-prompt-reservations-v1.json',names,require_training=False)
        receipt={'schema':'strep-developer-correction-submission-result-v1','status':'complete','at':now(),
                 'submission':{'path':str(submission_path),'sha256':sha256(submission_path)},'reviewed_corrections':len(accepted),
                 'training_admitted':False,'quality_approved':False,'release_approved':False}
        save(folder/'result.json',receipt);return receipt
    except Exception as exc:
        save(folder/'result.json',{'status':'failed','at':now(),'error':str(exc),'training_admitted':False});raise
